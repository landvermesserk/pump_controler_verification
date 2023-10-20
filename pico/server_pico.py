import network
import socket
from time import sleep
# from picozero import pico_temp_sensor, pico_led
import machine

from machine import Pin
import time
import struct

# pico_led = machine.Pin("LED", machine.Pin.OUT)


ssid = ''
ssid = ''
password = ""
password = ""

WATCHDOG = struct.pack("8s", "WATCHDOG".encode('utf-8'))


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
    address = (ip, 80)
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
    while True:
        message = client.recv(1024)
        if message == WATCHDOG:
            print("Received WATCHDOG!")
            client.send(WATCHDOG)
            print("Sent WATCHDOG!")
        else:
            time.sleep(1)

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


















