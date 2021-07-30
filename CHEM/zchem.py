#!/usr/bin/env python3.6
import json
import argparse
import select
import random
import logging
import signal
import time
import sys,os
from threading import Lock, Thread, Event
from socket import *
import pickle
import zmq
import keyboard
import numpy as np
from enum import Enum


CHANNEL_UPDATE_PORT = 4999    # updated channels come through this port
MAX_PACKET_SIZE = 2048
zeroConnection = 2 # this value should be used for a no connection value in the .json file. DON'T MAKE THIS 0

lock = Lock() # protects the channel shared variable
channel = None
exit = Event()
threadActive = True
serverActive = True

##### setup logging ####
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('zchem')


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


######## Read the configuration ################
def getConfiguration(configFile):
    ''' Load the configuration file. Config currently
    just contains the number of nodes/clients
    '''
    try:
        with open(configFile) as json_data_file:
            configList = json.load(json_data_file)
        return configList
    except IOError as e:
        logger.error('Error reading ' + configFile)
        logger.error(e)
        return
    except ValueError as e:
        logger.error('Error parsing ' + configFile)
        logger.error(e)
        return
    except Exception as e:
        logger.error('Unexpected error parsing ' + configFile + ':' + str(sys.exc_info()[0]))
        logger.error(e)
        return
    logger.info('Parsed inputs')


def signal_handler(signal, frame):
    global serverActive, threadActive
    serverActive = False # kill the server on Ctrl+C
    threadActive = False
    print('Handling Ctrl+C')
    exit.set()


# Thread updating the channel - listens on port CHANNEL_UPDATE_PORT for updated channel matrices (via UDP)
def updateChannel():
    global channel, serverActive, threadActive, lock

    # Setup the channel update socket
    try:
        channelUpdateSocket = socket(AF_INET, SOCK_DGRAM)
        channelUpdateSocket.bind(('', CHANNEL_UPDATE_PORT))
        channelUpdateSocket.settimeout(1);  # 1 second - used for clean exit on Ctrl+C
    except error:
#        logger.critical('Failed to create channel update socket. Error Code : ' + msg)
        print('Failed to create channel update socket. Error Code : ', msg)
        sys.exit()

    while(threadActive):
        # wait for an updated channel in a UDP packet
        try:
            (payload, clientAddress) = channelUpdateSocket.recvfrom(MAX_PACKET_SIZE)
            lock.acquire()
            channel = pickle.loads(payload)
            lock.release()
        except Exception as error:
            #print('Failed to read the channel update socket - ',error)
            pass

#    logger.info('No more changes in the channel')
    print('No more changes in the channel')


# used to specify socket type from cli
class SocketType(Enum):
    pair = 'pair'
    pub_sub = 'pub_sub'
    req_rep = 'req_rep'

    def __str__(self):
        return self.value


class PairSockets:
    """Class to create and interact with zmq pair sockets.
    Intended to be used with zmq_tun.py in separate containers.
    """

    def __init__(self, context, numNodes):
        logger.info(f"Initializing zmq pair sockets")
        self.context = context
        self.numNodes = numNodes
        # zmq sockets
        self.sockets = []
        # zmq socket poller
        self.poller = zmq.Poller()

        # Create zmq sockets
        self.createSockets()
    # Creates zmq pair sockets for each client node
    def createSockets(self):
        """Create zmq pair sockets.
        Uses cli port to create sockets with consecutive port values.
        """
        port = CONTAINER_ONE_RECEIVING_PORT
        # Create zmq PendingDeprecationWarningSockets
        for i in range(self.numNodes):
            try:
                # Create PAIR pairSockets since we match one client with one socket
                newSocket = self.context.socket(zmq.PAIR)
                addr = f"tcp://*:{port + i}"
                # Bind new socket to the next tcp port
                logger.info(f"Binding to tcp addr {addr}")
                newSocket.bind(addr)
                self.sockets.append(newSocket)
            except error:
                logger.critical("Failed to create pair socket. Error Code : ", error)
                sys.exit()
        logger.info(f"Created {self.numNodes} zmq pairSockets")

        # Construct a zmq poller to poll every server socket at once
        for i in range(self.numNodes):
            # Add each server socket to the poller
            self.poller.register(self.sockets[i], zmq.POLLIN)


    # Poll the given pair sockets to receive and forward messages
    def poll(self, channel):
        """Check for messages on all pair sockets and forward
        data to all connected sockets based on channel matrix.
        """
        socketUpdates = dict(self.poller.poll())
        # check each server socket for messages
        for i in range(self.numNodes):
            if self.sockets[i] in socketUpdates:
                message = self.sockets[i].recv()
                for j in range(0,self.numNodes):
                    if random.random() < channel[i][j]:
                        self.sockets[j].send(message)


class PubSubSockets:
    """Class to create and interact with zmq publish and subscribe socket pairs.
    Intended to be used with srsLTE nodes running in separate containers.
    """
    global CONTAINER_ADDR_PREFIX, CONTAINER_ONE_ADDR_SUFFIX
    def __init__(self, context, numNodes):
        logger.info(f"Initializing zmq pub/sub sockets")
        self.context = context
        self.numNodes = numNodes
        # zmq sockets
        self.publishers = []
        self.subscribers = []
        # zmq poller for subscriber sockets
        self.poller = zmq.Poller()

        # create zmq sockets
        self.createSockets()

    def createSockets(self):
        """Create zmq publish and subscribe socket pairs.
        Uses the cli address prefix, suffix, and port to create
        sockets with consecutive suffix and port values"""
        addrPrefix = CONTAINER_ADDR_PREFIX
        addrSuffix = CONTAINER_ONE_ADDR_SUFFIX
        receivingPort = CONTAINER_ONE_RECEIVING_PORT
        for i in range(self.numNodes):
            try:
                # Construct expected client address
                port = receivingPort + i
                pubAddr = f"tcp://{addrPrefix}{addrSuffix + i}:{port}"
                subAddr = f"tcp://*:{port}"

                logger.info("Created pub/sub sockets for address %s" % pubAddr)
                # Create a subscriber socket to the expected client address
                newSub = self.context.socket(zmq.SUB)
                newSub.bind(subAddr)
                # Subscribe to every mesage
                newSub.setsockopt(zmq.SUBSCRIBE, b"")

                # Create a publisher socket to the expected client address
                newPub = self.context.socket(zmq.PUB)
                newPub.connect(pubAddr)

                self.subscribers.append(newSub)
                self.publishers.append(newPub)
            except error:
                logger.critical("Failed to create server socket. Error Code : ", error)
                sys.exit()
        logger.info(f"Created {self.numNodes} subscriber and publisher sockets")

        # Construct a zmq poller to poll every server socket at once
        for i in range(self.numNodes):
            # Add each server socket to the poller
            self.poller.register(self.subscribers[i], zmq.POLLIN)


    def poll(self, channel):
        """Check for messages on all subscriber sockets and forward
        data to all connected publishers based on the channel matrix"""
        # poll all sockets to find which subscribers have messages to read
        socketUpdates = dict(self.poller.poll())

        # check each subscriber socket for messages
        for i in range(self.numNodes):
            if self.subSockets[i] in socketUpdates:
                message = self.subSockets[i].recv()
                # publish message to all connected nodes from channel matrix
                for j in range(0,self.numNodes):
                    if random.random() < channel[i][j]:
                        self.pubSockets[j].send(message)


class ReqRepSockets:
    """Class to create and interact with zmq request and reply socket pairs.
    Intended to be used with srsLTE nodes running in separate containers.
    """
    global CONTAINER_ADDR_PREFIX, CONTAINER_ONE_ADDR_SUFFIX

    # Number of retries before recreating sockets
    MAX_RETRIES = 5
    # Timeout for polling request sockets
    REQUEST_TIMEOUT = 100
    # Timeout for polling reply sockets
    REPLY_TIMEOUT = 100

    EMPTY_DATA = b"\x00"*184320
    def __init__(self, context, numNodes):
        logger.info(f"Initializing zmq request/reply sockets")
        self.context = context
        self.numNodes = numNodes
        # zmq sockets
        self.reqSockets = []
        self.repSockets = []
        # zmq sockets for passing data between main polling thread
        # and each individual req/rep thread
        self.inprocSockets = []
        # zmq socket pollers
        self.reqPoller = zmq.Poller()
        self.repPoller = zmq.Poller()
        self.inprocPoller = zmq.Poller()
        # Store data received from req sockets
        self.dataDict = {}

        # Create zmq sockets
        self.createSockets()

        # counter for the number of timeouts missed per socket
        self.reqRetries = []
        self.repRetries = []
        for i in range(self.numNodes):
            self.reqRetries.append(0)
            self.repRetries.append(0)

        # req/rep polling threads
        self.pollingThreads = []
        self.createPollThreads()


    def createSockets(self):
        """Create zmq request and reply socket pairs.
        Uses the cli address prefix, suffix, and port to create
        sockets with consecutive suffix and port values
        """
        # Create zmq server sockets
        for i in range(self.numNodes):
            newReq, newRep, newInproc = self.createSocket(i)
            self.reqSockets.append(newReq)
            self.repSockets.append(newRep)
            self.inprocSockets.append(newInproc)
        logger.info(f"Created {self.numNodes} request and reply sockets")

        # Construct a zmq poller to poll every server socket at once
        for i in range(self.numNodes):
            # Add each request and reply socket to the poller
            self.reqPoller.register(self.reqSockets[i], zmq.POLLIN)
            self.repPoller.register(self.repSockets[i], zmq.POLLIN)
            self.inprocPoller.register(self.inprocSockets[i], zmq.POLLIN)

        for i in range(self.numNodes):
            self.dataDict.update({self.reqSockets[i]: b""})

    
    def createSocket(self, socketIdx):
        """Helper function to create or recreate a req/req socket pair.
        socketIdx is added to the address suffix and port values.
        """
        addrPrefix = CONTAINER_ADDR_PREFIX
        addrSuffix = CONTAINER_ONE_ADDR_SUFFIX
        receivingPort = CONTAINER_ONE_RECEIVING_PORT
        try:
            # Construct expected client address
            port = receivingPort + socketIdx
            reqAddr = f"tcp://{addrPrefix}{addrSuffix + socketIdx}:{port + 100}"
            # Accept requests from any ip
            repAddr = f"tcp://*:{port}"

            # Create a subscriber socket to the expected client address
            newRep = self.context.socket(zmq.REP)
            newRep.bind(repAddr)
            logger.info("Created reply socket with address %s" % repAddr)

            # Create a publisher socket to the expected client address
            newReq = self.context.socket(zmq.REQ)
            newReq.connect(reqAddr)
            logger.info("Created request socket with address %s" % reqAddr)

            # Create an inproc socket to communicate with req/rep thread
            newInproc = self.context.socket(zmq.PAIR)
            newInproc.bind(f"inproc://{socketIdx}")

            return (newReq, newRep, newInproc)
        except error:
            logger.critical("Failed to create server socket. Error Code : ", error)
            sys.exit()

    def recreateSocket(self, socketIdx):
        """Shutdown and recreate a req/rep socket pair
        Note:
            Curently unused, but may be helpful in the future.
        """

        # Unregister sockets from poller
        self.reqPoller.unregister(self.reqSockets[socketIdx])
        self.repPoller.unregister(self.repSockets[socketIdx])

        # Ensure the socket is closed cleanly
        self.reqSockets[socketIdx].setsockopt(zmq.LINGER, 0)
        self.repSockets[socketIdx].setsockopt(zmq.LINGER, 0)
        # close both req and rep sockets
        self.reqSockets[socketIdx].close()
        self.repSockets[socketIdx].close()
        time.sleep(0.1)

        newReq, newRep = self.createSocket(socketIdx)
        self.reqSockets[socketIdx] = newReq
        self.repSockets[socketIdx] = newRep

        # Add new sockets to poller
        self.reqPoller.register(self.reqSockets[socketIdx], zmq.POLLIN)
        self.repPoller.register(self.repSockets[socketIdx], zmq.POLLIN)

    def createPollThreads(self):
        """Create a thread to communicate with each srs node."""
        logger.info("Starting req/rep polling threads")
        for i in range(self.numNodes):
            thread = Thread(target=self.pollReqRep, args=(i,))
            thread.start()
            self.pollingThreads.append(thread)


    def pollReqRep(self, i):
        """Continuously poll a single req/rep pair. Creates a new
        inproc socket to communicate with the main polling loop.
        """
        socket = self.context.socket(zmq.PAIR)
        socket.connect(f"inproc://{i}")

        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        poller.register(self.reqSockets[i], zmq.POLLIN)
        while(threadActive):
            # Poll for new data
            updates = dict(poller.poll(self.REQUEST_TIMEOUT))
            if self.reqSockets[i] in updates:
                # Reset retry counter
                self.reqRetries[i] = 0
                msg = self.reqSockets[i].recv()
                data = np.frombuffer(msg, dtype=np.complex64, count=-1)
                # Send a new transmit request immediately
                self.reqSockets[i].send(b"\xff")
                # Send data to main polling loop
                #data = 0*data
                #print(data)
                socket.send(data)
            # Send a transmit request if socket is ready
            elif (self.reqSockets[i].getsockopt(zmq.EVENTS) & zmq.POLLOUT) != 0:
                self.reqSockets[i].send(b"\xff")
            if socket in updates:
                msg = socket.recv()
                data = np.frombuffer(msg, dtype=np.complex64, count=-1)
                # Wait to receive a transmit request
                self.repSockets[i].recv()
                # send data received from main loop
                self.repSockets[i].send(data)


    def poll(self, channel):
        """reqSockets send transmit requests to srsLTE TX sockets.
        After sending a tx request, poll until data is received.
        Wait for tx requests from all srsLTE RX sockets.
        Send data received to connected channelMatrix sockets.
        Send empty data to all unconnected channelMatrix sockets.
        """
        # check each request socket for new transmitted data
        #reqUpdates = dict(self.reqPoller.poll(self.REQUEST_TIMEOUT))
        inprocUpdates = dict(self.inprocPoller.poll(self.REQUEST_TIMEOUT))
        for i in range(self.numNodes):
            if self.inprocSockets[i] in inprocUpdates:
                msg = self.inprocSockets[i].recv()
                data = np.frombuffer(msg, dtype=np.complex64, count=-1)
                # Forward data to connected clients
                for j in range(self.numNodes):
                    x = random.random()
                    y = random.random()
                    z = complex(x,y)
                    #print(z)
                    if channel[i][j] == zeroConnection:
                        data=0*data
                        self.inprocSockets[j].send(data)
                    elif x < channel[i][j]:
                        #data=0*data
                        self.inprocSockets[j].send(data)
                    elif channel[i][j] != 0:
                        data=0*data
                        self.inprocSockets[j].send(data)


def main():
    global channel, threadActive, serverActive, lock
    global CONTAINER_ADDR_PREFIX, CONTAINER_ONE_ADDR_SUFFIX, CONTAINER_ONE_RECEIVING_PORT
    # Initialize zmq context
    context = zmq.Context()

    signal.signal(signal.SIGINT, signal_handler)

    # Handle command line arguments
    parser = argparse.ArgumentParser(description='Optional config file')
    # number of nodes config
    parser.add_argument('-s', '--scenario', metavar='configFile',
                        type=argparse.FileType('r'),
                        nargs=1,
                        default='num_nodes.json',
                        help='The .json configuration file for the number of clients')
    # debug mode
    parser.add_argument('-d', '--debug', dest='debug', action='store_const',
                        const='debug', default='info',
                        help='Enable debug level for the logger')
    # What type of zmq sockets to create
    parser.add_argument('-t', '--socket_type', type=SocketType, choices=list(SocketType),
                        default="pub_sub",
                        help="What type of zmq sockets to create")
    # Prefix of container addresses
    parser.add_argument('-a', '--addr_prefix', type=str,
                        default="172.17.0.",
                        help="Entire address prefix of containers to connect to. `172.17.0.`")
    # Suffix of first container address
    parser.add_argument('-f', '--first_suffix', type=int,
                        default=1,
                        help="""Address suffix of first container to connect to.
                        Subsequent containers are assumed to have consecutive suffixes.""")
    # Port of first container to connect to
    parser.add_argument('-p', '--first_port', type=int,
                        default=5001,
                        help="""Port of first container to connect with. Subsequent
                        containers are assumed to use consecutive ports.""")

    args = parser.parse_args()

    if type(args.scenario) == type([]):
        configFile = args.scenario[0].name
    else:
        configFile = args.scenario.name
    # Load and parse config file
    config = getConfiguration(configFile)
    # Get the number of configured client nodes
    try:
        numNodes = config['N']
    except KeyError as e:
        logger.critical("Provided config file does not contain number of client nodes.")
        sys.exit()

    if args.debug == 'debug':
        logger.setLevel(logging.DEBUG)

    socketType = args.socket_type
    logger.debug(f"SocketType: {socketType}")

    # Global variables for determining container addresses
    CONTAINER_ADDR_PREFIX = args.addr_prefix
    CONTAINER_ONE_ADDR_SUFFIX = args.first_suffix
    CONTAINER_ONE_RECEIVING_PORT = args.first_port


    # Create zmq sockets based on the --socket_type argument
    if socketType is SocketType.pair:
        sockets = PairSockets(context, numNodes)
    elif socketType is SocketType.pub_sub:
        sockets = PubSubSockets(context, numNodes)
    elif socketType is SocketType.req_rep:
        sockets = ReqRepSockets(context, numNodes)

    # Start the channel update thread
    thread = Thread(target = updateChannel)
    thread.start()

    logger.info("Chilling until we get a channel...")
    while ((channel == None) and (serverActive)):
        time.sleep(1) # wait for the channel to get initialized
                      # by the update thread
    logger.info("Got it!")

    print('Server started, ready to forward, press Ctrl+C to end')
    while serverActive:
        # What's the point of locking here? I just
        # copied the locking that was already being done
        # but this seems pointless
        lock.acquire()
        newChannel = list(channel)
        lock.release()
        # Call poll function no matter what socket type is
        sockets.poll(newChannel)

    if threadActive:
        logger.info('Press any key to end the server')
        threadActive = False
    thread.join()
    logger.info('Server Down')

if __name__ == "__main__":
    # execute only if run as a script
    main()
