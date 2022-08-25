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
    def __init__(self, config: configparser.ConfigParser(),
                 timeout=60):
        StoppableThread.__init__(self)
        self.host = str(config.get("network", "host"))
        self.port = int(config.get("network", "port"))
        self.codeSocketDon_first = str(config.get("socket-control", "codeSocketDon_first"))
        self.codeSocketDoff_first = str(config.get("socket-control", "codeSocketDoff_first"))
        self.codeSocketDon_second = str(config.get("socket-control", "codeSocketDon_second"))
        self.codeSocketDoff_second = str(config.get("socket-control", "codeSocketDoff_second"))
        self.timeout = timeout
        self.sock = None
        self.connected = False
        self.inbound_stream = None
        self.address = None
        self.time_send_watchdog = time.time()
        self.time_receive_watchdog = time.time()
        self.retries_connection = 3
        self.pump_activated = False
        self.logger_trc = logging.getLogger("server_interface_trc")

    def connect(self):
        tries = 0
        while not self.connected and tries < self.retries_connection:
            try:
                self.logger_trc.info("Initialize connection.")
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.bind(("", self.port))
                self.sock.listen()
                self.inbound_stream, self.address = self.sock.accept()
                self.inbound_stream.settimeout(self.timeout)
                self.connected = True
                self.logger_trc.info("Connection successful.")

            except Exception as e:
                self.logger_trc.info(e)
                tries += 1
                if tries == self.retries_connection:
                    self.pump_controler(self.codeSocketDoff_second)
                    time.sleep(5)
                    self.pump_controler(self.codeSocketDoff_first)
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

    def pump_controler(self, status: str):
        cmd = "/home/pi/PycharmProjects/pump_controler_verification/433Utils/RPi_utils/steuerung " + status
        subprocess.call(cmd, shell=True)
        #time_difference = np.abs((datetime.now() - datetime.strptime(time.ctime(os.path.getmtime("/tmp/code_received.txt")),
        #                                                             "%a %b %d %H:%M:%S %Y")).total_seconds())
        #if time_difference > 2:
        #    self.logger_trc.info("Wireless socket is not working properly. Shut down application.")
        #    self.connected = False
        #    self.close()
        #    self.stop()

    def send(self, msg):
        totalsent = 0
        while totalsent < len(msg):
            sent = self.inbound_stream.send(msg[totalsent:])
            if sent == 0:
                self.pump_controler(self.codeSocketDoff_second)
                time.sleep(5)
                self.pump_controler(self.codeSocketDoff_first)
                self.logger_trc.info("socket connection broken")
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def receive(self):
        data = self.inbound_stream.recv(1024)
        if data == b'':
            self.pump_controler(self.codeSocketDoff_second)
            time.sleep(5)
            self.pump_controler(self.codeSocketDoff_first)
            self.logger_trc.info("Socket connection broken. Close connection and stop thread.")
            self.close()
            self.stop()
        return data

    def run(self):
        #if not os.path.exists("/tmp/code_received.txt"):
        #    f = open("/tmp/code_received.txt", "wb")
        #    f.close()
        while not self.is_stopped():
            time.sleep(1)
            try:
                if not self.connected or int(time.time() - self.time_receive_watchdog) > 45:
                    self.pump_activated = False
                    self.pump_controler(self.codeSocketDoff_second)
                    time.sleep(5)
                    self.pump_controler(self.codeSocketDoff_first)
                    if self.connected:
                        self.logger_trc.info("Did not receive watchdog!")
                    self.connect()
                    if not self.connected:
                        self.pump_activated = False
                        self.pump_controler(self.codeSocketDoff_second)
                        time.sleep(5)
                        self.pump_controler(self.codeSocketDoff_first)
                        self.logger_trc.info("Close connection!")
                        self.close()
                        self.stop()
                        break
                    self.send(WATCHDOG)
                    self.logger_trc.info("Sent initial WATCHDOG!")
                    self.time_send_watchdog = time.time()
                self.logger_trc.info("Receiving message.")
                message = self.receive()
                self.logger_trc.info(message)
                if message == WATCHDOG:
                    self.logger_trc.info("Received WATCHDOG!")
                    self.time_receive_watchdog = time.time()
                    self.send(WATCHDOG)
                    self.logger_trc.info("Sent WATCHDOG!")
                else:
                    sensor_status = struct.unpack("i", message)[0]
                    if sensor_status:
                        self.pump_activated = True
                        self.logger_trc.info("Activate pump!")
                        self.pump_controler(self.codeSocketDon_first)
                        time.sleep(5)
                        self.pump_controler(self.codeSocketDon_second)
                        #if not self.connected:
                        #    self.send(struct.pack("i", 0))
                    else:
                        self.pump_activated = False
                        self.logger_trc.info("Deactivate pump!")
                        self.pump_controler(self.codeSocketDoff_second)
                        time.sleep(5)
                        self.pump_controler(self.codeSocketDoff_first)

            except Exception as e:
                self.pump_activated = False
                self.pump_controler(self.codeSocketDoff_second)
                time.sleep(5)
                self.pump_controler(self.codeSocketDoff_first)
                self.logger_trc.info(e)
                self.close()
                self.stop()
                time.sleep(10)


def main():
    logging_path = "/home/pi/PycharmProjects/pump_controler_verification/src/logging"
    with open(os.path.join(logging_path, "logging.yml")) as f:
        loggingconf = yaml.safe_load(f)
    logging.config.dictConfig(loggingconf)
    config = configparser.ConfigParser()
    config.read("/home/pi/PycharmProjects/pump_controler_verification/config/config.ini")
    server_interface = ServerInterface(config=config)
    server_interface.start()
    server_interface.join()
    server_interface.stop()


if __name__ == '__main__':
    main()
