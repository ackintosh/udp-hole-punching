#!/usr/bin/env python

"""
Network with Restricted Cone NATs

           h0
           |
           s0
           |
    ----------------
    |              |
   nat1           nat2
    |              |
   s1              s2
    |              |
   h1              h2
"""

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.log import info
from mininet.cli import CLI
from mininet.util import irange
from mininet.node import Node


class RestrictedConeNAT(Node):
    def __init__(self, name, subnet='10.0/8', local_intf=None, **params):
        super(RestrictedConeNAT, self).__init__(name, **params)
        print('debug: __init__:', subnet, local_intf, params)

        self.subnet = subnet

        if not local_intf:
            local_intf = self.defaultIntf()
        self.local_intf = local_intf

        self.forwardState = self.cmd('sysctl -n net.ipv4.ip_forward').strip()

    def set_manual_config(self):
        """Prevent network-manager/networkd from messing with our interface
           by specifying manual configuration in /etc/network/interfaces"""
        cfile = '/etc/network/interfaces'
        line = '\niface %s inet manual\n' % self.local_intf
        try:
            with open(cfile) as f:
                config = f.read()
        except IOError:
            config = ''
        if line not in config:
            info('*** Adding "' + line.strip() + '" to ' + cfile + '\n')
            with open(cfile, 'a') as f:
                f.write(line)
            # Probably need to restart network manager to be safe -
            # hopefully this won't disconnect you
            self.cmd('service network-manager restart || netplan apply')

    # pylint: disable=arguments-differ
    def config(self, **params):
        """Configure the NAT and iptables"""

        self.set_manual_config()

        # Now we can configure manually without interference
        super(RestrictedConeNAT, self).config(**params)

        self.cmd('iptables -F')
        self.cmd('iptables -t nat -F')

        # Create default entries for unmatched traffic
        self.cmd('iptables -P INPUT ACCEPT')
        self.cmd('iptables -P OUTPUT ACCEPT')
        self.cmd('iptables -P FORWARD ACCEPT')

        # Install NAT rules
        # iptables -t nat -A POSTROUTING -o <public interface> -p udp -j SNAT --to-source <public ip>
        self.cmd(
            'iptables -t nat -A POSTROUTING',
            '-o',
            params.get('inetIntf'),
            '-p udp',
            '-j SNAT',
            '--to-source',
            params.get('ip').split('/')[0],
            verbose=True
        )

        # iptables -t nat -A PREROUTING -i <private interface> -p udp -j DNAT --to-destination <private ip>
        self.cmd(
            'iptables -t nat -A PREROUTING',
            '-i',
            params.get('inetIntf'),
            '-p udp',
            '-j DNAT',
            '--to-destination',
            params.get('hostIp').split('/')[0],
            verbose=True
        )

        # iptables -A FORWARD -i <public interface> -p udp -m state --state ESTABLISHED,RELATED -j ACCEPT
        self.cmd(
            'iptables -A FORWARD',
            '-i',
            params.get('inetIntf'),
            '-p udp',
            '-m state',
            '--state ESTABLISHED,RELATED',
            '-j ACCEPT',
            verbose=True
        )

        # iptables -A FORWARD -i <public interface> -p udp -m state --state NEW -j DROP
        self.cmd(
            'iptables -A FORWARD',
            '-i',
            params.get('inetIntf'),
            '-p udp',
            '-m state',
            '--state NEW',
            '-j DROP',
            verbose=True
        )

        # Instruct the kernel to perform forwarding
        self.cmd('sysctl net.ipv4.ip_forward=1')

    def terminate(self ):
        self.cmd('iptables -F')
        self.cmd('iptables -t nat -F')
        # Put the forwarding state back to what it was
        self.cmd('sysctl net.ipv4.ip_forward=%s' % self.forwardState)
        super(RestrictedConeNAT, self).terminate()


class NetworkTopology(Topo):
    # pylint: disable=arguments-differ
    def build(self, n=2, **_kwargs):
        # set up inet switch
        inet_switch = self.addSwitch('s0')
        # add bootstrap node
        inet_host = self.addHost('h0')
        self.addLink(inet_switch, inet_host)

        # add local nets
        for i in irange(1, n):
            inet_intf = 'nat%d-eth0' % i
            local_intf = 'nat%d-eth1' % i
            local_ip = '192.168.%d.1' % i
            local_subnet = '192.168.%d.0/24' % i
            host_ip = '192.168.%d.100/24' % i
            nat_params = {'ip': '%s/24' % local_ip}

            # add NAT to topology
            nat = self.addNode(
                'nat%d' % i,
                cls=RestrictedConeNAT,
                subnet=local_subnet,
                inetIntf=inet_intf,
                local_intf=local_intf,
                hostIp=host_ip
            )

            # add local switch to topology
            switch = self.addSwitch('s%d' % i)

            # connect NAT to inet and local switches
            self.addLink(nat, inet_switch, intfName1=inet_intf)
            self.addLink(nat, switch, intfName1=local_intf, params1=nat_params)

            # add host and connect to local switch
            host = self.addHost(
                'h%d' % i,
                ip=host_ip,
                defaultRoute='via %s' % local_ip
            )
            self.addLink(host, switch)


def run():
    """Create network and run the CLI"""
    topo = NetworkTopology()
    net = Mininet(topo=topo, waitConnected=True)
    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()
