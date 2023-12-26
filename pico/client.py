import time
import socket
import struct
import os
import logging
import logging.config
import yaml

WATCHDOG = struct.pack("8s", "WATCHDOG".encode('utf-8'))
logger_trc = logging.getLogger("server_interface_trc")

def connect(host, port):
    timeout = 45
    retries_connection = 3
    tries = 0
    connected = False
    while not connected and tries < retries_connection:
        try:
            logger_trc.info("Connect to server")
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            logger_trc.info("Connection successful")
            connected = True
            return sock, connected
        except Exception as e:
            logger_trc.info(e)
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
            logger_trc.info("socket connection broken")
            raise RuntimeError("socket connection broken")
        totalsent = totalsent + sent


def receive(sock):
    data = sock.recv(1024)
    if data == b'':
        sock.close()
        logger_trc.info("Socket connection broken. Close connection and stop thread.")
    return data


def main(host, port):
    connected = False
    while True:
        time.sleep(1)
        try:
            if not connected:
                sock, connected = connect(host, port)
                if not sock:
                    logger_trc.info("Close connection!")
                    connected = False
                    time.sleep(5)
                    break
            if connected:
                message = receive(sock)
                moisture = struct.unpack("i", message)[0]
                logger_trc.info(f"Moisture level:m{moisture}")
                send(WATCHDOG, sock)
                logger_trc.info("Sent WATCHDOG!")
                time.sleep(1)
            else:
                time.sleep(2)


        except Exception as e:
            logger_trc.info(e)
            sock.close()
            connected = False
            time.sleep(10)


if __name__ == "__main__":
    logging_path = "/home/pi/PycharmProjects/pico/logging"
    with open(os.path.join(logging_path, "logging.yml")) as f:
        loggingconf = yaml.safe_load(f)
    logging.config.dictConfig(loggingconf)
    host = "192.168.178.20"
    port = 8893
    main(host=host, port=port)
