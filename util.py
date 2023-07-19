import logging


def init_logger():
    logging.basicConfig(level=logging.INFO, filename='/tmp/udp-hole-punching.log', format='%(asctime)s - %(message)s')


def addr_from_args(args, host='127.0.0.1', port=9999):
    if len(args) >= 3:
        host, port = args[1], int(args[2])
    elif len(args) == 2:
        host, port = host, int(args[1])
    else:
        host, port = host, port
    return host, port


def msg_to_addr(data):
    ip, port = data.decode('utf-8').strip().split(':')
    return ip, int(port)


def addr_to_msg(addr):
    return '{}:{}'.format(addr[0], str(addr[1])).encode('utf-8')
