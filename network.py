#!/usr/bin/env python

"""
natnet.py: Example network with NATs


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
    def __init__( self, name, subnet='10.0/8',
                  localIntf=None, flush=False, **params):
        """Start NAT/forwarding between Mininet and external network
           subnet: Mininet subnet (default 10.0/8)
           flush: flush iptables before installing NAT rules"""
        super( RestrictedConeNAT, self ).__init__( name, **params )
        print('debug: __init__:', subnet, localIntf, flush, params)

        self.subnet = subnet
        self.localIntf = localIntf
        self.flush = flush
        self.forwardState = self.cmd( 'sysctl -n net.ipv4.ip_forward' ).strip()

    def setManualConfig( self, intf ):
        """Prevent network-manager/networkd from messing with our interface
           by specifying manual configuration in /etc/network/interfaces"""
        cfile = '/etc/network/interfaces'
        line = '\niface %s inet manual\n' % intf
        try:
            with open( cfile ) as f:
                config = f.read()
        except IOError:
            config = ''
        if ( line ) not in config:
            info( '*** Adding "' + line.strip() + '" to ' + cfile + '\n' )
            with open( cfile, 'a' ) as f:
                f.write( line )
            # Probably need to restart network manager to be safe -
            # hopefully this won't disconnect you
            self.cmd( 'service network-manager restart || netplan apply' )

    # pylint: disable=arguments-differ
    def config( self, **params ):
        """Configure the NAT and iptables"""

        print('debug: config:', params)
        if not self.localIntf:
            self.localIntf = self.defaultIntf()

        self.setManualConfig( self.localIntf )

        # Now we can configure manually without interference
        super(RestrictedConeNAT, self).config(**params)

        if self.flush:
            self.cmd( 'sysctl net.ipv4.ip_forward=0' )
            self.cmd( 'iptables -F' )

        self.cmd( 'iptables -t nat -F' )

        # Create default entries for unmatched traffic
        self.cmd( 'iptables -P INPUT ACCEPT' )
        self.cmd( 'iptables -P OUTPUT ACCEPT' )
        self.cmd( 'iptables -P FORWARD ACCEPT' )

        # # Install NAT rules
        # iptables -t nat -A POSTROUTING -o nat1-eth0 -p udp -j SNAT --to-source 10.0.0.4/8
        self.cmd( 'iptables -t nat -A POSTROUTING',
                  '-o', params.get('inetIntf'), '-p udp', '-j SNAT', '--to-source', params.get('ip').split('/')[0], verbose=True )

        # iptables -t nat -A PREROUTING -i eth1 -p udp -j DNAT --to-destination <private ip goes here>
        self.cmd( 'iptables -t nat -A PREROUTING',
                  '-i', params.get('inetIntf'), '-p udp', '-j DNAT', '--to-destination', params.get('hostIp'), verbose=True )

        # iptables -A INPUT -i eth1 -p udp -m state --state ESTABLISHED,RELATED -j ACCEPT
        self.cmd( 'iptables -A INPUT',
                  '-i', params.get('inetIntf'), '-p udp', '-m state', '--state ESTABLISHED,RELATED', '-j ACCEPT', verbose=True )

        # iptables -A INPUT -i eth1 -p udp -m state --state NEW -j DROP
        self.cmd( 'iptables -A INPUT',
                  '-i', params.get('inetIntf'), '-p udp', '-m state', '--state NEW', '-j DROP', verbose=True )



        # # 内部ネットワーク（192.168.0.0/24）から送られてきたパケットの送信元アドレスを、パブリックインターフェイス（eth0）のIPアドレスに変更する（NATを行う）
        # # iptables -t nat -A POSTROUTING -o eth0 -s 192.168.0.0/24 -j MASQUERADE
        # self.cmd( 'iptables -t nat -A POSTROUTING',
        #           '-o', params.get('inetIntf'), '-s', self.subnet, '-j MASQUERADE' )
        #
        # # パブリックインターフェイス（eth0）から送られてきたパケットを内部ネットワーク（192.168.0.0/24）に転送
        # # iptables -A FORWARD -i eth0 -o eth1 -m state --state RELATED,ESTABLISHED -j ACCEPT
        # self.cmd( 'iptables -A FORWARD',
        #           '-i', params.get('inetIntf'), '-o', self.localIntf, '-m state --state RELATED,ESTABLISHED -j ACCEPT' )
        #
        # # 内部ネットワーク（192.168.0.0/24）から送られてきたパケットをパブリックインターフェイス（eth0）に転送
        # # iptables -A FORWARD -i eth1 -o eth0 -j ACCEPT
        # self.cmd( 'iptables -A FORWARD',
        #           '-i', self.localIntf, '-o', params.get('inetIntf'), '-j ACCEPT' )

        # Instruct the kernel to perform forwarding
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        "Stop NAT/forwarding between Mininet and external network"
        # Remote NAT rules
        self.cmd( 'iptables -D FORWARD',
                  '-i', self.localIntf, '-d', self.subnet, '-j DROP' )
        self.cmd( 'iptables -D FORWARD',
                  '-i', self.localIntf, '-s', self.subnet, '-j ACCEPT' )
        self.cmd( 'iptables -D FORWARD',
                  '-o', self.localIntf, '-d', self.subnet, '-j ACCEPT' )
        self.cmd( 'iptables -t nat -D POSTROUTING',
                  '-s', self.subnet, '\'!\'', '-d', self.subnet,
                  '-j MASQUERADE' )
        # Put the forwarding state back to what it was
        self.cmd( 'sysctl net.ipv4.ip_forward=%s' % self.forwardState )
        super(RestrictedConeNAT, self).terminate()

class NetworkTopology(Topo):
    # pylint: disable=arguments-differ
    def build(self, n=2, **_kwargs ):
        # set up inet switch
        inetSwitch = self.addSwitch('s0')
        # add inet host
        inetHost = self.addHost('h0')
        self.addLink(inetSwitch, inetHost)

        # add local nets
        for i in irange(1, n):
            inetIntf = 'nat%d-eth0' % i
            localIntf = 'nat%d-eth1' % i
            localIP = '192.168.%d.1' % i
            localSubnet = '192.168.%d.0/24' % i
            hostIp = '192.168.%d.100/24' % i
            natParams = { 'ip' : '%s/24' % localIP }
            # add NAT to topology
            nat = self.addNode('nat%d' % i, cls=RestrictedConeNAT, subnet=localSubnet,
                               inetIntf=inetIntf, localIntf=localIntf, hostIp=hostIp)
            switch = self.addSwitch('s%d' % i)
            # connect NAT to inet and local switches
            self.addLink(nat, inetSwitch, intfName1=inetIntf)
            self.addLink(nat, switch, intfName1=localIntf, params1=natParams)
            # add host and connect to local switch
            host = self.addHost('h%d' % i,
                                ip=hostIp,
                                defaultRoute='via %s' % localIP)
            self.addLink(host, switch)

def run():
    "Create network and run the CLI"
    topo = NetworkTopology()
    net = Mininet(topo=topo, waitConnected=True)
    net.start()
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()
