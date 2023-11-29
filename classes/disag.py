import socket
import json
import threading

DISAG_DEFULT_SERVER_IP = "192.169.0.101"
DISAG_JSON_BROADCAST_PORT = 30169
SOCKET_TIMEOUT = 5

class DisagServer:
    def __init__(self, port=DISAG_JSON_BROADCAST_PORT, ip=""):
        self.port = port
        self.ip = ip

        self.sock = None
    
        self.raw_data = None
        self.data = None
        self.run = True
    
    def end(self):
        self.run=False
        print(f"waiting up to {SOCKET_TIMEOUT}s for socket close..")
#        self.sock.close()
#        self.listen.join()
       # raise()
        

    def listen(self):
        self._connect()
        self.listen = threading.Thread(target=self.listening_thread)
        self.listen.start()
    
    def _connect(self):
        # new UDP/IP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        # bind on given port
        self.sock.bind((self.ip, self.port))
        self.sock.settimeout(SOCKET_TIMEOUT)
    
    def listening_thread(self):
        '''
        that is a weird way to be able to interrupt a socket
        does that make me skip some data frames?
        '''
        while self.run:
            try:
                self.data_raw, addr = self.sock.recvfrom(1024)
                self.data = self.data_raw.decode()
            except socket.timeout:
                continue
        
    def get_data(self):
        data = None
        if self.data is not None:
            data = self.data
            self.data = None
        return data
    
    def data_received(self):
        if self.data is None:
            return False
        return True


def main():
    disag = DisagServer(ip="127.0.0.1")
    disag.listen()

    while True:
        if disag.data_received():
            print(disag.get_data())
    
    


if __name__ == "__main__":
    main()
    
