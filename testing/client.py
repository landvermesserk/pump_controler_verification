import configparser
import time
import threading
import socket
import queue
import struct
import datetime
import logging
import subprocess

WATCHDOG = struct.pack("8s", "WATCHDOG".encode('utf-8'))


class StoppableThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._stopevent = threading.Event()

    def stop(self):
        self._stopevent.set()

    def is_stopped(self):
        return self._stopevent.isSet()


class ClientInterface(StoppableThread):
    def __init__(self,
                 host: str,
                 port: int,
                 timeout=45):
        StoppableThread.__init__(self)
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.connected = False
        self.time_send_message = time.time()
        self.time_receive_watchdog = time.time()
        self.retries_connection = 3

    def connect(self):
        tries = 0
        while not self.connected and tries < self.retries_connection:
            try:
                print("Connect to server")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.connect((self.host, self.port))
                print("Connection successful")
                self.connected = True
            except Exception as e:
                print(e)
                tries += 1
                if tries == self.retries_connection:
                    try:
                        self.sock.shutdown(socket.SHUT_RDWR)
                    except Exception as e:
                        pass
                    finally:
                        self.connected = False
                        self.sock.close()
                        self.stop()
                time.sleep(5)

    def close(self):
        if self.connected:
            self.connected = False
            self.sock.close()

    def send(self, msg):
        totalsent = 0
        while totalsent < len(msg):
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                print("socket connection broken")
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def receive(self):
        data = self.sock.recv(1024)
        if data == b'':
            self.close()
            print("Socket connection broken. Close connection and stop thread.")
            self.stop()
        return data


    def run(self):
        while not self.is_stopped():
            time.sleep(1)
            try:
                if not self.connected or int(time.time() - self.time_receive_watchdog) > 45:
                    if self.connected:
                        print("Did no receive watchdog.")
                    self.connect()
                    self.time_send_message = time.time()
                    if not self.connected:
                        print("Close connection!")
                        self.close()
                        self.stop()
                        break
                if int(time.time() - self.time_receive_watchdog) > 2:
                    print("Receiving message.")
                    message = self.receive()
                    print(message)
                    if message == WATCHDOG:
                        print("Received WATCHDOG!")
                        self.time_receive_watchdog = time.time()
                        self.send(WATCHDOG)
                        print("Sent WATCHDOG!")
                        time.sleep(1)
                    else:
                        print("Received unknown message!")
                        self.close()
                        self.stop()

            except Exception as e:
                print(e)
                self.close()
                self.stop()
                time.sleep(10)


def main():
    #host = "192.168.178.66"
    #port = 8893
    host = '192.168.0.64'
    port = 80
    client_interface = ClientInterface(host=host, port=port)
    client_interface.start()
    client_interface.join()
    client_interface.stop()


if __name__ == '__main__':
    main()
