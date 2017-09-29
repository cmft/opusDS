#!/usr/bin/env python

import time
import socket
import win32pipe
import win32file
import win32api
import winerror
from threading import (Lock, Thread)


pipe_name = "\\\\.\\PIPE\\OPUS"
# pointer ti bane of the file
# access mode
# share mode
# pointer to security attributes
# how to create
# file attributes
# handle to file with attributes to copy
fileHandle = win32file.CreateFile(pipe_name,
                              win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                              0, None,
                              win32file.OPEN_EXISTING,
                              0, None)


def readPipe():
    hr, data = win32file.ReadFile(fileHandle, 4096)
    fulldata = data
    n = 1
    while 1:
        try:
            buffer, bytesToRead, result = win32pipe.PeekNamedPipe(fileHandle, 0)
        except:
            pass
        if bytesToRead == 0:
            break
        print 'READING ', n
        if bytesToRead > 4096:
            bytesToRead = 4096
        hr, data = win32file.ReadFile(fileHandle, bytesToRead)
        fulldata += data
        n += 1
        time.sleep(0.01)
    print fulldata


while True:
    opus_cmd = raw_input("Give an OPUS cmd: ")
    if opus_cmd.lower() == "exit":
        break

    if opus_cmd.lower() == "read":
        data = readPipe()
        print data
        continue

    cmd = "{0}\n".format(opus_cmd)
    print("writing... {0}".format(cmd))
    win32file.WriteFile(fileHandle, cmd)
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
        data = "\n"
    else:
        self._numParm = 0

    if "WRITE_PARAMETER" in cmd and self._NumParm > 0:
        data = ''
    else:
        data = readPipe()
    print data

fileHandle.close()
