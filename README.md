# udp-hole-punching

This repository provides a simulated _Restricted Cone NAT_ environment using [Mininet](https://mininet.org/) and iptables, and Python scripts for UDP Hole Punching.

Note that only Linux is supported since Mininet depends on the Linux network namespaces.

## Network Topology

<img width="750" alt="image" src="https://github.com/ackintosh/udp-hole-punching/assets/1885716/3acf9460-b4ec-4eca-be6d-21f6d858e550">

## UDP Hole Punching

```bash
# Start up the topology and run the Mininet CLI.
$ sudo python3 udp-hole-punching/network.py

# Run server script (bootstrap node) in the background.
mininet> h0 python3 -u udp-hole-punching/server.py 0.0.0.0 9000 &

# Run client script at h1.
mininet> h1 python3 -u udp-hole-punching/client.py h0 9000 &

# Run client script at h2. 
mininet> h2 python3 -u udp-hole-punching/client.py h0 9000 &

# See the logs by the server and clients.
mininet> h1 cat /tmp/udp-hole-punching.log

# See the iptable status of nat* nodes.
mininet> nat1 iptables -L -v -n
mininet> nat2 iptables -L -v -n
```

<img width="1468" alt="image" src="https://github.com/ackintosh/udp-hole-punching/assets/1885716/307d9944-5885-44c9-a51e-84e72449b46c">
