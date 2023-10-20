import time
# import RPi.GPIO as GPIO
import threading
import socket
import queue
import struct
from datetime import datetime
import logging
import logging.config
import yaml
import configparser
import os
import subprocess
import numpy as np

WATCHDOG = struct.pack("8s", "WATCHDOG".encode('utf-8'))


class StoppableThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._stopevent = threading.Event()

    def stop(self):
        self._stopevent.set()

    def is_stopped(self):
        return self._stopevent.isSet()


class ServerInterface(StoppableThread):
    def __init__(self,
                 host: str,
                 port: int,
                 timeout=60):
        StoppableThread.__init__(self)
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.connected = False
        self.inbound_stream = None
        self.address = None
        self.time_send_watchdog = time.time()
        self.time_receive_watchdog = time.time()
        self.retries_connection = 3
        self.pump_activated = False

    def connect(self):
        tries = 0
        while not self.connected and tries < self.retries_connection:
            try:
                print("Initialize connection.")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.bind(("", self.port))
                self.sock.listen()
                self.inbound_stream, self.address = self.sock.accept()
                self.inbound_stream.settimeout(self.timeout)
                self.connected = True
                print("Connection successful.")

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
                        self.close()
                        self.stop()
                time.sleep(5)

    def close(self):
        if self.connected:
            self.connected = False
            self.sock.close()


    def send(self, msg):
        totalsent = 0
        while totalsent < len(msg):
            sent = self.inbound_stream.send(msg[totalsent:])
            if sent == 0:
                print("socket connection broken")
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def receive(self):
        data = self.inbound_stream.recv(1024)
        if data == b'':
            self.pump_controler(self.codeSocketDoff_second)
            time.sleep(5)
            self.pump_controler(self.codeSocketDoff_first)
            print("Socket connection broken. Close connection and stop thread.")
            self.close()
            self.stop()
        return data

    def run(self):

        while not self.is_stopped():
            time.sleep(1)
            try:
                if not self.connected or int(time.time() - self.time_receive_watchdog) > 45:
                    if self.connected:
                        print("Did not receive watchdog!")
                    self.connect()
                    if not self.connected:
                        print("Close connection!")
                        self.close()
                        self.stop()
                        break
                    self.send(WATCHDOG)
                    print("Sent initial WATCHDOG!")
                    self.time_send_watchdog = time.time()
                print("Receiving message.")
                message = self.receive()
                print(message)
                if message == WATCHDOG:
                    print("Received WATCHDOG!")
                    self.time_receive_watchdog = time.time()
                    self.send(WATCHDOG)
                    print("Sent WATCHDOG!")

            except Exception as e:
                print(e)
                self.close()
                self.stop()
                time.sleep(10)


def main():
    host = "192.168.178.66"
    port = 8893
    server_interface = ServerInterface(host=host, port=port)
    server_interface.start()
    server_interface.join()
    server_interface.stop()


if __name__ == '__main__':
    main()
