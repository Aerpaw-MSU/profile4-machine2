#!/usr/bin/env python
import json
import argparse
import select
import random
import logging
import signal
import time
import sys,os
import pickle
import numpy as np
from threading import Event
from socket import *
sys.path.insert(2, '../MessageDefinitions/')

channel = None
MAX_PACKET_SIZE = 2048

##### setup logging ####
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('channelSimulator')
    
######## Wait for a key  ##################
def wait_key():
    ''' Wait for a key press on the console and return it. '''
    result = None
    if os.name == 'nt':
        import msvcrt
        result = msvcrt.getch()
    else:
        import termios
        fd = sys.stdin.fileno()

        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)

        try:
            result = sys.stdin.read(1)
        except IOError:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)

    return result

def signal_handler(signal, frame):
    sys.exit()

# function updating the channel - listens on port CHANNEL_UPDATE_PORT for updated channel matrices (via UDP)
def updateChannel(CHANNEL_UPDATE_PORT,ipaddress):
    global channel

    # Setup the channel update socket
    channelUpdateSocket = socket(AF_INET, SOCK_DGRAM)
    channelUpdateSocket.bind((ipaddress, CHANNEL_UPDATE_PORT))
    channelUpdateSocket.settimeout(1);  # 1 second - used for clean exit on Ctrl+C

    while True:
    # wait for an updated channel in a UDP packet
        try:
            (payload, clientAddress) = channelUpdateSocket.recvfrom(MAX_PACKET_SIZE)
            channel = pickle.loads(payload)
            print('Received matrix:')
            print(np.matrix(channel))
        except Exception as error: 
            pass
            

def main():
    global channel

    parser = argparse.ArgumentParser(description='Port and IP')
    parser.add_argument('-p','--gchemPort',help='port number', type=int, default=4999)
    parser.add_argument('-i','--gchemIP', help='ip address', type=str, default='127.0.0.1')
    args = parser.parse_args()

    signal.signal(signal.SIGINT,signal_handler)
    
    # Start the channel update function, verifying data received by gchem.py is as expected
    updateChannel(args.gchemPort,args.gchemIP)


if __name__ == "__main__":
    # execute only if run as a script
    main()
