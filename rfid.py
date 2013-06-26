import serial

class Reader(object):

    def __init__(self, port_name, baudrate, string_length, timeout=1):
        self.port = serial.Serial(port_name, baudrate=baudrate, timeout=timeout)
        self.string_length = string_length

    def read(self):
        rcv = self.port.read(self.string_length)

        if not rcv:
            return


        print rcv

        tag = {
            "raw" : rcv,
            "mfr" : int(rcv[1:5], 16),
            "id" : int(rcv[5:11], 16),
            "chk" : int(rcv[11:13], 16)
        }




        return Card(tag)



class Card(object):

    def __init__(self, tag):
        self.tag = tag

    def get_id(self):
        return self.tag['id']

    def get_mfr(self):
        return self.tag['mfr']

    def get_chk(self):
        return self.tag['chk']


    def __repr__(self):
        return str(self.get_id())

    def is_valid(self):
        i2 = 0
        checksum = 0

        for i in range(0, 5):
            i2 = 2 * i
            checksum ^= int(self.tag.raw[i2 + 1:i2 + 3], 16)
        
        return checksum == tag['chk']


