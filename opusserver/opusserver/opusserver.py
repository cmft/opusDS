#!/usr/bin/env python

import time
import serial
import socket
import win32pipe
import win32file
import subprocess
from threading import (Lock, Thread)


class SocketListenerThread(Thread):
    BUFFER_SIZE = 4096
    SLEEPING_SERIAL_TIME = 0.05

    def __init__(self, serversock):
        Thread.__init__(self)
        # Server Socket
        self.serversock = serversock
        self.serve = True
        self.clientsock = None
        self.createFileHandle()
        # Serial connection
        self._ser = None
        # Last server command
        self._last_cmd = None

    def runOpus(self):
        subprocess.call(['C:\Program Files (x86)\Bruker\OPUS_7.5.18\opus.exe',
                         '/LANGUAGE=ENGLISH /OPUSPIPE=ON'])

    def createFileHandle(self):
        try:
            pipe_name = "\\\\.\\PIPE\\OPUS"
            access_mode = win32file.GENERIC_READ | win32file.GENERIC_WRITE
            # pointer to name of the file
            # access mode
            # share mode
            # pointer to security attributes
            # how to create
            # file attributes
            # handle to file with attributes to copy
            self.fileHandle = win32file.CreateFile(pipe_name,
                                                   access_mode,
                                                   0, None,
                                                   win32file.OPEN_EXISTING,
                                                   0, None)
            self.isPIPEConnected = True
        except:
            self.isPIPEConnected = False

    def readFileHandle(self):
        hr, data = win32file.ReadFile(self.fileHandle, self.BUFFER_SIZE)
        fulldata = data

        while True:
            try:
                buffer, bytesToRead, result = \
                    win32pipe.PeekNamedPipe(self.fileHandle, 0)
            except:
                pass
            if bytesToRead == 0:
                break

            if bytesToRead > self.BUFFER_SIZE:
                bytesToRead = self.BUFFER_SIZE
            hr, data = win32file.ReadFile(self.fileHandle, bytesToRead)
            fulldata += data

        return fulldata

    def run(self):
        while self.serve:
            try:
                self.clientsock, addr = self.serversock.accept()
                try:
                    while True:
                        data = self.clientsock.recv(self.BUFFER_SIZE)
                        if data.lower() == '':
                            break
                        ans = self.parse_cmd(data.strip())
                        self.clientsock.send(ans)
                except Exception, e:
                    pass  # forced by a socket shutdown
            except Exception, e:
                pass  # forced by a socket shutdown

    def parse_cmd(self, cmd):
        if cmd.lower() == "exit":
            self.shutdown()

        # Serial commands
        if cmd.startswith('send_serial_cmd'):
            _, serial_cmd = cmd.split(' ', 1)
            if self._ser is None:
                self._create_serial_connection()

            serial_output = self.send_serial_cmd(serial_cmd)
            return "{0}\n".format(serial_output)

        # Pipe commands
        if cmd.lower() == "s_pipe":
            if self.isPIPEConnected:
                return "{0}\n".format('Pipe is connected')
            else:
                return "{0}\n".format('Pipe is not connected')

        if cmd.lower() == "o_pipe":
            self.createFileHandle()
            if self.isPIPEConnected:
                return "{0}\n".format('Pipe is connected')
            else:
                return "{0}\n".format('Pipe is not connected')

                # Opus commands
                #        if cmd.startwith('rm '):
                #            path = cmd.split('rm ')
                #            files = glob.glob('{0}/*'.format(path))
                #            for f in files:
                #                os.remove(f)
                #            return "ok\n"

        cmd = "{0}\n".format(cmd)
        print("writing... {0}".format(cmd))
        self._last_cmd = cmd

        # Execute macros with arguments
        if "RUN_MACRO" in cmd or "STAR_MACRO" in cmd and len(cmd.split()) > 2:
            return self._run_macro_with_args(cmd)

        if "READ_PKA" in cmd:
            return self._read_param_from_selected("PKA")

        if "UNLOAD_SELECTED_FILE" in cmd:
            return self._unload_selected()

        win32file.WriteFile(self.fileHandle, cmd)
        time.sleep(1)
        print("Reading...")
        data = self.readFileHandle()
        print "Data: ", data
        return "{0}\n".format(data)

    def _run_macro_with_args(self, cmd):
        # Run Opus macros with arguments
        splitted_cmd = cmd.split()
        nargs = (len(splitted_cmd) - 2) / 2
        run_cmd = "{0} {1} {2}\n".format(splitted_cmd[0], splitted_cmd[1],
                                         nargs)
        win32file.WriteFile(self.fileHandle, run_cmd)
        for i in range(nargs):
            run_cmd = "WRITE_PARAMETER {0} {1}\n".format(
                splitted_cmd[2 + i * 2].lower(),
                splitted_cmd[3 + i * 2])
            win32file.WriteFile(self.fileHandle, run_cmd)
        data = self.readFileHandle()
        return "{0}\n".format(data)

    def _read_param_from_selected(self, param):
        """ Read parameter form the selected file

            returns the read value or NaN
        """
        ans = self.parse_cmd("GET_SELECTED\n")
        try:
            if 'OK\n' in ans.upper():
                alignment_file = ans.split('\n')[1].split()[0]
        except IndexError:
            return "There is not selected file\n"

        self.parse_cmd("READ_FROM_FILE {0}\n".format(alignment_file))

        self.parse_cmd("FILE_PARAMETERS\n")
        ans = self.parse_cmd("READ_PARAMETER {0}\n".format(param))
        if 'OK\n' in ans:
            value = ans.split('\n')[1]
        else:
            value = "NaN"

        return "{0}\n".format(value)

    def _unload_selected(self):
        """ Unload selected file in OPUS software"""
        ans = self.parse_cmd("GET_SELECTED\n")
        try:
            if 'OK\n' in ans.upper():
                alignment_file = ans.split('\n')[1].split()[0]
                self.parse_cmd("UNLOAD_FILE {0}\n".format(alignment_file))
        except IndexError:
            pass
        return "OK\n"

    def shutdown(self):
        if self.clientsock is not None:
            self.clientsock.shutdown(0)
        self.serve = False
        self.serversock.shutdown(0)()
        self.fileHandle.close()

    def _create_serial_connection(self, port='COM4', baudrate=57600,
                                  timeout=1):
        self._ser = serial.Serial(port=port, baudrate=baudrate,
                                  timeout=timeout)
        self._ser.isOpen()

    def send_serial_cmd(self, cmd):
        if cmd == 'exit':
            self._ser.close()
            self._ser = None
            return "OK"
        else:
            if self._ser.isOpen():
                # flush input buffer, discarding all its contents
                self._ser.flushInput()
                # flush output buffer, aborting current output and discard all
                # that is in buffer
                self._ser.flushOutput()

            # send the character to the device
            # \r\n carriage return and line feed to the characters
            # this is requested by my device
            eol = '\r\n'
            self._ser.write(cmd + eol)
            out = ''
            # let's wait before reading output
            # (let's give device time to answer)
            time.sleep(self.SLEEPING_SERIAL_TIME)
            while self._ser.inWaiting() > 0:
                out += self._ser.read(1)
            return out


def run_opus_server():
    lock = Lock()
    ip = socket.gethostbyname(socket.gethostname())
    ADDR = (ip, 5000)
    print("Running server: {0}".format(ip))
    serversock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversock.bind(ADDR)
    serversock.listen(1)
    slt = SocketListenerThread(serversock)
    slt.start()

if __name__ == '__main__':
    run_opus_server()

    """ TEST IT
    import socket, time
    ip = socket.gethostbyname(socket.gethostname()) # For local test
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (ip, 5000)
    sock.connect(server_address)

    def run_cmd(cmd):
        sock.sendall(cmd+'\n')
        ans = sock.recv(4096)
        print cmd,'->',ans

    run_cmd("send_serial_cmd ?pos")

    run_cmd("GET_VERSION")
    run_cmd("MEASURE_SAMPLE <Experiment file>")
    e.g
    run_cmd("MEASURE_SAMPLE L:\controls\devel\cfalcon\MCT_TRANS.XPM")
    run_cmd("READ_FROM_BLOCK")

    run_cmd("READ_FROM_FILE <file>")
    e.g.  run_cmd("READ_FROM_FILE L:\controls\devel\cfalcon\spectrum.1")
    "READ_FROM_FILE C:\users\sicilia\opus_test\spectrum.1"
    run_cmd("START_MACRO <Macro file name>[<Number of input parameters>]") # wait
    run_cmd("KILL_MACRO <MacroID>")
    run_cmd("RUN_MACRO <Macro file name>[<Number of input parameters>]")

    e.g.
    run_cmd("RUN_MACRO L:\controls\devel\cfalcon\MeasureSample.mtx 1")
    run_cmd("WRITE_PARAMETER lct 10")


    run_cmd("START_MACRO C:\Users\Public\Documents\Bruker\OPUS_7.5.18\at\macro\Alignment\MeasureSample.mtx 1")

    run_cmd("MEASURE_SAMPLE L:\controls\devel\cfalcon\MCT_TRANS.XPM")
    """
