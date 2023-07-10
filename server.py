import socket
import sys
from util import *

logger = logging.getLogger()
addresses = []


def main(host='0.0.0.0', port=9999):
    sock = socket.socket(socket.AF_INET, # Internet
                         socket.SOCK_DGRAM) # UDP
    sock.bind((host, port))
    logger.info("server: listening on %s:%s", host, port)

    while True:
        logger.info("server: waiting for messages...")
        data, addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        logger.info("server: received a message from %s", addr)
        addresses.append(addr)

        if len(addresses) >= 2:
            logger.info("server: send client info to: %s", addresses[0])
            sock.sendto(addr_to_msg(addresses[1]), addresses[0])
            logger.info("server: send client info to: %s", addresses[1])
            sock.sendto(addr_to_msg(addresses[0]), addresses[1])
            addresses.pop(1)
            addresses.pop(0)


if __name__ == '__main__':
    init_logger()
    main(*addr_from_args(sys.argv))
