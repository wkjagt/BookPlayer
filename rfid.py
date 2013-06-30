#!/usr/bin/env python
# encoding: utf-8

"""
rfid.py

The RFID reader and RFID card classes
"""


__version_info__ = (0, 0, 1)
__version__ = '.'.join(map(str, __version_info__))
__author__ = "Willem van der Jagt"

import serial

class Reader(object):
    """The RFID reader class. Reads cards and returns their id"""

    def __init__(self, port_name, baudrate, string_length, timeout=1):
        """Constructor

        parameters:
        port_name : the device name of the serial port
        baudrate: baudrate to read at from the serial port
        string_length: the length of the string to read
        timeout: how to long to wait for data on the port
        """
        self.port = serial.Serial(port_name, baudrate=baudrate, timeout=timeout)
        self.string_length = string_length

    def read(self):
        """Read from self.port"""
        rcv = self.port.read(self.string_length)

        if not rcv:
            return None

        try:
            # note : data from the RFID reader is in HEX. We'll return
            # as int.
            tag = { "raw" : rcv,
                    "mfr" : int(rcv[1:5], 16),
                    "id" : int(rcv[5:11], 16),
                    "chk" : int(rcv[11:13], 16)}
                    
            return Card(tag)
        except:
            return None



class Card(object):

    def __init__(self, tag):
        self.tag = tag

    def get_id(self):
        """Return the id of the tag"""
        return self.tag['id']

    def get_mfr(self):
        """Return the mfr of the tag"""
        return self.tag['mfr']

    def get_chk(self):
        """Return the checksum of the tag"""
        return self.tag['chk']


    def __repr__(self):
        return str(self.get_id())

    def is_valid(self):
        """Uses the checksum to validate the RFID tag"""
        i2 = 0
        checksum = 0

        for i in range(0, 5):
            i2 = 2 * i
            checksum ^= int(self.tag.raw[i2 + 1:i2 + 3], 16)
        
        return checksum == tag['chk']
        
