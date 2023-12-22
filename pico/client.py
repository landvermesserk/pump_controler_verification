import time
import socket
import struct

WATCHDOG = struct.pack("8s", "WATCHDOG".encode('utf-8'))

def connect(host, port):
    timeout = 45
    retries_connection = 3
    tries = 0
    connected = False
    while not connected and tries < retries_connection:
        try:
            print("Connect to server")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            print("Connection successful")
            connected = True
            return sock, connected
        except Exception as e:
            print(e)
            tries += 1
            if tries == retries_connection:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except Exception as e:
                    pass
                finally:
                    connected = False
                    sock.close()
                    return None
            time.sleep(5)


def send(msg, sock):
    totalsent = 0
    while totalsent < len(msg):
        sent = sock.send(msg[totalsent:])
        if sent == 0:
            print("socket connection broken")
            raise RuntimeError("socket connection broken")
        totalsent = totalsent + sent


def receive(sock):
    data = sock.recv(1024)
    if data == b'':
        sock.close()
        print("Socket connection broken. Close connection and stop thread.")
    return data


def main(host, port):
    connected = False
    while True:
        time.sleep(1)
        try:
            if not connected:
                sock, connected = connect(host, port)
                if not sock:
                    print("Close connection!")
                    break
            message = receive(sock)
            moisture = struct.unpack("i", message)[0]
            print(moisture)
            send(WATCHDOG, sock)
            print("Sent WATCHDOG!")
            time.sleep(1)


        except Exception as e:
            print(e)
            sock.close()
            time.sleep(10)


# host = "192.168.0.64"
host = ""
port = 8893
main(host=host, port=port)
