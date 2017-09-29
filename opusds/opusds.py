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
        self.refreshPeriod = 0.3
        self.enabledEv = Event()

    def run(self):
        self.enabledEv.wait()
        while not self.stop:
            time.sleep(self.refreshPeriod)
            self.opusDevice._getMacroState()
            if self.opusDevice.get_state() == PyTango.DevState.RUNNING:
                self.enabledEv.clear()
                self.enabledEv.wait()


class OpusDS(Device):
    __metaclass__ = DeviceMeta

    IP = device_property(dtype=str)
    OPUS_MACRO_PATH = device_property(dtype=str)
    ALIGNMENT_SCAN_PATH = device_property(dtype=str)
    ALIGNMENT_SCAN_FILENAME = device_property(dtype=str)

    def init_device(self):
        Device.init_device(self)
        self._resetArgs()
        self.opusState = OpusState(self)
        self._createSocket()

    def delete_device(self):
        self.info_stream('OpusDS.delete_device')
        # Close socket
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        # Stop thead
        self.opusState.stop = True
        self.opusState.enabledEv.set()
        self.opusState.join()

    def _resetArgs(self):
        self._macro_id = None
        self._cmd = None
        self._xpm_filename = None
        # self._macro_filename = None
        self._args = None
        # self._n_args = None

    def _createSocket(self):
        # create socket connection
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_address = (self.IP, 5000)
        self.sock.settimeout(3)
        try:
            self.sock.connect(server_address)
            self._setStateOn()
        except:
            self.set_state(PyTango.DevState.FAULT)
            self.set_status('The DS could not connect to the Opus server')

    def _runOpusCmd(self, cmd, args=None):
        if not args in (None, ""):
            opus_cmd = "{0} {1}".format(cmd.upper(), args)
        else:
            opus_cmd = "{0}".format(cmd.upper())
        try:
            self.sock.sendall(opus_cmd)
            ans = self.sock.recv(4096)
            return ans
        except:
            self.set_state(PyTango.DevState.FAULT)
            msg = 'Could not connect with the opus server'
            self.set_status(msg)
            raise Exception(msg)

    def _isRunOpusCmdAllowed(self):
        return self.get_state() in (PyTango.DevState.ON, PyTango.DevState.ALARM)

    def _setStateOn(self):
        self.set_state(PyTango.DevState.ON)
        self.set_status('Ready')

    def _getMacroState(self):
        if self._macro_id is not None:
            ans = self._runOpusCmd("MACRO_RESULTS", self._macro_id)
            if 'OK\n' in ans:
                if int(ans.split('\n')[1]) == 1:
                    self._setStateOn()
                else:
                    self.set_state(PyTango.DevState.RUNNING)
                    self.set_status('Running macro {0}'.format(self._macro_id))
            else:
                self.set_state(PyTango.DevState.ALARM)
                self.set_status('Error reading macro status')

    ###########################################################################
    # Attributes
    ###########################################################################

    @attribute(label="macro_id", dtype=str)
    def macro_id(self):
        return self._macro_id

    # TODO replace  by dynamic attributes
    @attribute(label="args", dtype=str)
    def args(self):
        return self._args

    @args.write
    def args(self, args):
        self._args = args

    @attribute(label="xpm_file", dtype=str)
    def xpm_file(self):
        return self._xpm_file

    @xpm_file.write
    def xpm_file(self, args):
        self._xpm_file = xpm_file

    ###########################################################################
    # Commands
    ###########################################################################
    @command()
    def connect(self):
        self._createSocket()

    def runOpusMacro(self, macro_path, macro_args=None):
        if not _isRunOpusCmdAllowed:
            msg = 'The device is {0}.\n' \
                  'The RUN_MACRO command can ' \
                  'not be executed'.format(self.get_state())
            raise Exception(msg)

        self.set_state(PyTango.DevState.RUNNING)

        if macro_args is not None:
            nargs = len(macro_args)
            ans = self._runOpusCmd("RUN_MACRON", "{0} {1}".format(macro_path),
                             nargs)

            if "ok" not in ans:
                self.set_state(PyTango.DevState.ALARM)
                self.set_status(ans)
                return

            for i in range(nargs):
                self._runOpusCmd("WRITE_PARAMETER",
                                 "{0} {1}".format(macro_args[i][0],
                                                  macro_args[i][1]))
        else:
            ans = self._runOpusCmd("RUN_MACRON", macro_path)

        if "OK\n" in ans:
            self._macro_id = ans.split('\n')[1]
            self.opusState.enabledEv.set()
        else:
            self.set_state(PyTango.DevState.ALARM)
            self.set_status(ans)

    @command()
    def runOpusMeasureSample(self):

        if self._xpm_filename is not None:
            macro = os.path.join(self.OPUS_MACRO_PATH, "MeasureSample.mtx")
            path, file = self._xpm_filename.rsplit('/')
            self.runOpusMacro(macro, [("pth", path), ("fil",file)])
        else:
            msg = 'XPM file has not been set'
            self.set_status(msg)
            self.set_state(PyTango.DevState.ALARM)
            raise Exception(msg)

    @command(dtype_out=float)
    def readPKA(self):
        if not self._isRunOpusCmdAllowed:
            msg = 'The device is {0}.\n' \
                  'The OPUS command can ' \
                  'not be executed'.format(self.get_state())
            raise Exception(msg)

        # TODO
        alignment_file = os.path.join(self.ALIGNMENT_SCAN_PATH,
                                      self.ALIGNMENT_SCAN_FILENAME)
        ans = self._runOpusCmd("READ_FROM_FILE {0}".format(alignment_file))
        # file_id = ans.split('\n')[1]

        self._runOpusCmd("FILE_PARAMETERS")
        self.set_state(PyTango.DevState.RUNNING)
        ans = self._runOpusCmd("READ_PARAMETER", "PKA")
        if 'OK\n' in ans:
            self._setStateOn()
            pka = float(ans.split('\n')[1])
        else:
            self.set_state(PyTango.DevState.ALARM)
            pka = float("NaN")

        self._runOpusCmd("UNLOAD_FILE {0}".format(alignment_file))

        return pka

    @command()
    def abortMacro(self):
        if self._macro_id is not None:
            self._runOpusCmd("KILL_MACRO",self._macro_id)
            self._setStateOn()
        else:
            msg = 'There is not any macro running'
            self.set_status(msg)
            self.set_state(PyTango.DevState.ALARM)

    # @command()
    # def loadOpusMacro(self):
    #     # TODO parse opus macro
    #     # create dynamic attribute
    #     # emit interfaceChange event

    @command(dtype_in=str, dtype_out=str)
    def runOpusCmd(self, cmd):
        if not self._isRunOpusCmdAllowed:
            msg = 'The device is {0}.\n' \
                  'The OPUS command can ' \
                  'not be executed'.format(self.get_state())
            raise Exception(msg)

        splited_cmd = cmd.split(" ", 1)
        if len(splited_cmd) > 1:
            args = splited_cmd[1]
        else:
            args = None
        opus_cmd = splited_cmd[0]

        ans = self._runOpusCmd(opus_cmd, args)
        return ans


def runDS():
    run((OpusDS,))

if __name__ == "__main__":
    runDS()
