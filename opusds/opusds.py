#!/usr/bin/env python

import os
import time
import socket
from threading import (Thread, Event)
import PyTango
from PyTango.server import (run,
                            Device,
                            DeviceMeta,
                            attribute,
                            command,
                            device_property)


class OpusState(Thread):
    def __init__(self, opus):
        Thread.__init__(self)
        self.opusDevice = opus
        self.stop = False
        self.refreshPeriod = 0.1
        self.enabledEv = Event()

    def run(self):
        self.enabledEv.wait()
        while not self.stop:
            time.sleep(self.refreshPeriod)
            self.opusDevice._getMacroState()
            if not self.opusDevice.get_state() == PyTango.DevState.RUNNING:
                self.enabledEv.clear()
                self.enabledEv.wait()


class OpusDS(Device):
    __metaclass__ = DeviceMeta

    IP = device_property(dtype=str)

    def init_device(self):
        self.info_stream('init_device')
        Device.init_device(self)
        self.opusState = OpusState(self)
        self.server_address = (self.IP, 5000)

        # connect socket
        self.sock = None
        self._connectSocket()
        # reset Opus macro_id
        self._macro_id = None
        self._last_cmd = "None"

        if not self.opusState.isAlive():
            self.opusState.start()

    def delete_device(self):
        self.info_stream('delete_device')
        # Close socket
        if self.sock is not None:
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        # Stop thread
        self.opusState.stop = True
        self.opusState.enabledEv.set()
        self.opusState.join()

    def _connectSocket(self):
        if self.sock is None:
            # create socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5)
        # Try to connect the socket
        try:
            self.sock.connect(self.server_address)
            self.isConnected = True
            self.info_stream('Connected to %s sever'
                             % self.IP)
            self._setStatusReady()
        except Exception as e:
            self.isConnected = False
            self.info_stream('Could not connect to %s sever. Reason: %r'
                             % (self.IP, e))
            self.set_state(PyTango.DevState.ALARM)
            self.set_status('Could not connect to the server')

    def _reconnectSocket(self):
        self.sock.close()
        self.sock = None
        self._connectSocket()

    def _runOpusCmd(self, cmd):
        self.sock.sendall(cmd + '\n')
        ans = self.sock.recv(4096)
        return ans

    def _isRunOpusCmdAllowed(self):
        return self.get_state() in (PyTango.DevState.ON,
                                    PyTango.DevState.ALARM)

    def _serverIsNotConnected(self):
        self.set_state(PyTango.DevState.ALARM)
        self.set_status('Can not connect to the server')

    def _setStatusRunning(self, cmd):
        self.set_state(PyTango.DevState.RUNNING)
        self.set_status('Running cmd: {0}'.format(cmd))

    def _setStatusReady(self):
        self.set_state(PyTango.DevState.ON)
        self.set_status('Ready')

    def _getMacroState(self):
        if self._macro_id is not None:
            ans = self._runOpusCmd("MACRO_RESULTS {0}".format(self._macro_id))
            self.info_stream('macroState %s' % ans)
            if 'OK\n' in ans.upper():
                if int(ans.split('\n')[1]) == 1:
                    self._setStatusReady()
                    self.info_stream('Macro %s has finished' % self._macro_id)
                else:
                    self.set_state(PyTango.DevState.RUNNING)
                    self.set_status('Running macro {0}'.format(self._macro_id))
            else:
                self.set_state(PyTango.DevState.ALARM)
                self.set_status('Error reading macro status')

    ###########################################################################
    # Commands
    ###########################################################################

    @command(dtype_out=bool)
    def connect(self):
        try:
            # Evaluate the connection
            self._runOpusCmd('s_pipe')
        except:
            # Try to reconnect the socket
            self._reconnectSocket()
        return self.isConnected

    @command(dtype_in=str)
    def runOpusMacro(self, macro_path):
        if self.isConnected:
            if self._isRunOpusCmdAllowed():
                self._last_cmd = "RUN_MACRO {0}".format(macro_path)
                self._setStatusRunning(self._last_cmd)
                ans = self._runOpusCmd(self._last_cmd)
                if "OK\n" in ans.upper():
                    self._macro_id = ans.split('\n')[1]
                    self.opusState.enabledEv.set()
                else:
                    self._macro_id = None
                    self.set_state(PyTango.DevState.ALARM)
                    self.set_status('Problem running macro: {0}'.format(ans))
        else:
            self._serverIsNotConnected()

    @command()
    def stopOpusMacro(self):
        if self.isConnected:
            if self._macro_id is not None:
                self._last_cmd = "KILL_MACRO {0}".format(self._macro_id)
                self._setStatusRunning(self._last_cmd)
                ans = self._runOpusCmd(self._last_cmd)
                self._macro_id = None
        else:
            self._serverIsNotConnected()

    @command(dtype_in=str, dtype_out=str)
    def runOpusCMD(self, cmd):
        cmd = cmd.upper()
        if cmd.startswith("RUN_MACRO"):
            raise Exception("runOpusCMD can not execute async commands")

        if self.isConnected:
            if self._isRunOpusCmdAllowed():
                self._setStatusRunning(cmd)
                self._last_cmd = cmd.upper()
                ans = self._runOpusCmd(self._last_cmd)
                self._setStatusReady()
                return ans
            else:
                raise Exception("CMD  %s can not be executed. Check the state"
                                % cmd)
        else:
            self._serverIsNotConnected()

    ###########################################################################
    ## Attributes
    ###########################################################################


def runDS():
    run((OpusDS,))


if __name__ == "__main__":
    runDS()
