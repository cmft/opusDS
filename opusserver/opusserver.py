#!/usr/bin/env python

import time
import socket
import win32pipe
import win32file
import subprocess
from threading import (Lock, Thread)


class SocketListenerThread(Thread):

    BUFFER_SIZE = 4096

    def __init__(self, serversock):
        Thread.__init__(self)
        self.serversock = serversock
        self.serve = True
        self.clientsock = None
        self.createFileHandle()
        self._last_cmd = None
        self._numParm = 0

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

#        if cmd.startwith('rm '):
#            path = cmd.split('rm ')
#            files = glob.glob('{0}/*'.format(path))
#            for f in files:
#                os.remove(f)
#            return "ok\n"

        cmd = "{0}\n".format(cmd)
        print("writing... {0}".format(cmd))
        win32file.WriteFile(self.fileHandle, cmd)
        time.sleep(1)
        print("Reading...")
        if "RUN_MACRO" in cmd or "STAR_MACRO" in cmd:
            # Parse cmd to get the expected parameters
            try:
                self._numParm = int(a.rsplit(' ', 1)[1])
            except ValueError:
                self._numParm = 0
        elif "WRITE_PARAMETER" in cmd and self._numParm > 0:
            self._numParm -= 1
            return "\n"
        else:
            self._numParm = 0
        data = self.readFileHandle()
        self._last_cmd = cmd
        print "Data: ", data
        return "{0}\n".format(data)

    def shutdown(self):
        if self.clientsock is not None:
            self.clientsock.shutdown(0)
        self.serve = False
        self.serversock.shutdown(0)()
        self.fileHandle.close()


if __name__ == '__main__':
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
