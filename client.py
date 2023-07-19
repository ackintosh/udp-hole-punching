import random
import socket
import subprocess
import sys
import time
from util import *

logger = logging.getLogger()
command = "ip -4 addr show | grep eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'"
private_ip = subprocess.check_output(command, shell=True).decode('utf-8').strip()


def info(message):
    logger.info('client(%s): %s', private_ip, message)


def main(host='127.0.0.1', port=9999):
    sock = socket.socket(
        socket.AF_INET,  # Internet
        socket.SOCK_DGRAM  # UDP
    )
    sock.sendto(b'0', (host, port))
    info('sent a message to the server')

    data, addr = sock.recvfrom(1024)
    if addr[0] != host:
        raise Exception('A message from unexpected host: %s' % addr)
    info('received a message from the server(%s): %s' % (addr[0], data))

    peer_addr = msg_to_addr(data)
    msg_seq = 0
    while True:
        time.sleep(random.uniform(1, 5))
        msg_seq += 1
        sock.sendto(b'seq:%d' % msg_seq, peer_addr)
        info('sent a message to: {}'.format(peer_addr))
        data, addr = sock.recvfrom(1024)
        info('received from {}: {}'.format(addr, data))


if __name__ == '__main__':
    init_logger()
    main(*addr_from_args(sys.argv))
