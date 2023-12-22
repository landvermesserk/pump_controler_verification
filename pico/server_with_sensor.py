import network
import socket
from time import sleep
from machine import ADC, Pin
import time
import struct

ssid = ''
password = ""
port = 8893

WATCHDOG = struct.pack("8s", "WATCHDOG".encode('utf-8'))
# Calibraton values
min_moisture = 19200
max_moisture = 49300
soil = ADC(Pin(26))


def connect():
    # Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
    print(wlan.ifconfig())
    return wlan.ifconfig()[0]


def open_socket(ip):
    # Open a socket
    address = (ip, port)
    connection = socket.socket()
    connection.bind(address)
    connection.listen(1)
    print(connection)
    return connection


def serve(connection):
    client = connection.accept()[0]
    print("Connection established.")
    client.send(WATCHDOG)
    print("Sent data.")
    try:
        while True:
            message = client.recv(1024)
            if message == WATCHDOG:
                print("Received WATCHDOG!")
                client.send(WATCHDOG)
                print("Sent WATCHDOG!")
            else:
                time.sleep(1)
            moisture = int((max_moisture - soil.read_u16()) * 100 / (max_moisture - min_moisture))
            print(moisture)
            # client.send(struct.pack("i", moisture))
    except Exception as e:
        print(e)
        client.close()


# serve(connection)


def server(connection):
    connected = False
    while True:
        print("Establish connection.")
        try:
            if not connected:
                server = serve(connection)
                connected = True
        except Exception as e:
            print(e)
            connected = False
            continue


ip = connect()
connection = open_socket(ip)
server(connection)





















