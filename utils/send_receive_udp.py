import socket
import sys
import time
import json

#UDP_IP = "192.168.0.137"
UDP_IP = "127.0.0.1"
# DISAG port: 30169
UDP_PORT = 30169
MESSAGE = b"Hello, World!"


print("UDP target IP: %s" % UDP_IP)
print("UDP target port: %s" % UDP_PORT)
print("message: %s" % MESSAGE)


def send():
    # send
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
    print(f"sending {MESSAGE}")
    sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))



# receive
def receive():
    print("Receiving")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
    sock.bind(("", UDP_PORT))
    # sock.bind((UDP_IP, UDP_PORT))

    while True:
        data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
        try:
            jsondata = json.loads(data)
            with open("log.json","a") as fp:
                fp.write(str(data))
            print(f"received message: \n {json.dumps(jsondata)}")
        except:
            print("received message: %s" % data)
            raise


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "r":
        receive()
    else:
        for i in range(10):
            send()
            time.sleep(2)


if __name__ == "__main__":
    main()
