import sys
import argparse
import getopt
import threading
import logging
import zmq
from pytun import TunTapDevice


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zmq_tun")


def create_tun(addr, name, mtu):
    # Create tun device
    logger.info("create_tun: Creating tun device")
    tun = TunTapDevice(name=name)
    tun.addr = addr
    tun.dstaddr = addr
    tun.netmask = "255.255.255.0"
    tun.mtu = mtu
    logger.info("create_tun: Created " + name + " with address " + addr)

    return tun


def read_tun(tun, inproc_url, context=None):
    # Create zmq socket over inproc
    context = context or zmq.Context.instance()

    logger.info("read_tun: Creating zmq PAIR socket")
    socket = context.socket(zmq.PAIR)
    socket.connect(inproc_url)

    # Continually read from the tun interface
    # and forward data as inproc messages
    while True:
        try:
            # TODO this is really sketchy and I don't know why
            # this is needed for iperf to work
            buf = tun.read(tun.mtu+4)
            socket.send(buf)
        except Exception:
            logger.info("read_tun: Interrupt received, stopping")
            break

    # Cleanup
    logger.info("read_tun: Cleanup reached")
    socket.close()
    tun.down()


def main(argv):
    # Handle command line arguments
    parser = argparse.ArgumentParser(description="Script to forward packets to/from a tun interface and a host_ip")
    parser.add_argument("-c", "--client", action="store_true",
                        help="Run script in client mode")
    parser.add_argument("-s", "--server", action="store_true",
                        help="Run script in server mode")
    parser.add_argument("-i", "--host_ip", metavar="host ip",
                        type=str,
                        help="IP to forward tun packets to. Unused if run in server mode")
    parser.add_argument("-p", "--port", metavar="port",
                        type=int, required=True,
                        help="Port to forward packets to or read packets from")
    parser.add_argument("-t", "--tun_addr", metavar="tun address",
                        type=str, required=True,
                        help="Address of tun interface to create and read from")
    parser.add_argument("-n", "--tun_name", metavar="tun interface name",
                        type=str, default="tun0",
                        help="Name of tun interface to create and read from")
    parser.add_argument("-m", "--mtu", metavar="maximum packet size",
                        type=int, default=4096,
                        help="Maximum size of packet")

    args = parser.parse_args()

    # client or server mode
    client = None
    if args.client:
        client = True
    if args.server:
        if client is not None:
            logger.critical("Options -c and -s are mutually exclusive.")
            logger.critical("Cannot be both a client and a server instance.")
            sys.exit()
        client = False
    if client is None:
        logger.critical("You must specify either client or server mode.")
        sys.exit()

    # host ip
    if args.host_ip is not None:
        host_ip = args.host_ip
    elif client is True:
        logger.critical("You must specify host_ip in client mode")
        sys.exit()

    # port for host ip
    if args.port is not None:
        port = args.port
    else:
        logger.critical("You must specify port value")
        sys.exit()

    # address of tun interface
    if args.tun_addr is not None:
        tun_addr = args.tun_addr
    else:
        logger.critical("You must specify tun address")
        sys.exit()

    # name of tun interface
    if args.tun_name is not None:
        tun_name = args.tun_name

    # mtu
    if args.mtu is not None:
        mtu = args.mtu

    # Create tun interface
    tun = create_tun(tun_addr, tun_name, mtu)
    tun.up()

    #### ZMQ networking code ####

    # Initialize ZMQ context
    context = zmq.Context.instance()

    # Socket to talk to other nodes
    # connect to tcp address if client mode
    if client is True:
        tcp_socket = context.socket(zmq.PAIR)
        tcp_addr = "tcp://" + host_ip + ":" + str(port)
        logger.info("main: Creating tcp socket with addr " + tcp_addr)
        tcp_socket.connect(tcp_addr)
    # bind to tcp address if server mode
    if client is False:
        tcp_socket = context.socket(zmq.PAIR)
        tcp_addr = "tcp://*:" + str(port)
        logger.info("main: Binding tcp socket with addr " + tcp_addr)
        tcp_socket.bind(tcp_addr)
    tcp_socket.setsockopt(zmq.SNDBUF, mtu + 100)

    # zmq url for communicating with tun thread
    tun_inproc_url = "inproc://read_tun"
    tun_socket = context.socket(zmq.PAIR)
    tun_socket.bind(tun_inproc_url)
    tun_socket.setsockopt(zmq.SNDBUF, mtu + 100)

    # Create a thread for reading from the tun interface
    tun_thread = threading.Thread(target=read_tun,
                                  args=(tun, tun_inproc_url))
    tun_thread.daemon = True
    tun_thread.start()

    # Process messages from tun inproc and tcp
    poller = zmq.Poller()
    poller.register(tcp_socket, zmq.POLLIN)
    poller.register(tun_socket, zmq.POLLIN)

    # Catch all exceptions to ensure connections are closed
    try:
        while True:
            sockets = dict(poller.poll())
            if sockets.get(tcp_socket) == zmq.POLLIN:
                buf = tcp_socket.recv()
                tun.write(buf)
            if sockets.get(tun_socket) == zmq.POLLIN:
                buf = tun_socket.recv()
                tcp_socket.send(buf)
    except KeyboardInterrupt:
        logger.info("main: Interrupt received, stopping")
    finally:
        tcp_socket.close()
        tun_socket.close()
        context.term()
        exit()


if __name__ == "__main__":
    main(sys.argv[1:])
