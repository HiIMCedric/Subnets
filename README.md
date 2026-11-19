# Two-Subnet Routed Network Lab

## Project Overview

Four hosts sit on two IPv4 subnets joined by one Linux router. Hosts on the same subnet talk directly (Layer 2). Hosts on different subnets send traffic to their default gateway, the router, which forwards it between its two interfaces (Layer 3). `topology.yaml` is the single source of truth for interfaces, addresses, gateways and routes.

| Subnet   | CIDR             | Router interface / gateway |
|----------|------------------|----------------------------|
| Subnet A | 192.168.10.0/24  | eth0 – 192.168.10.1        |
| Subnet B | 192.168.20.0/24  | eth1 – 192.168.20.1        |

| Host    | IP address       | Mask          | Default gateway |
|---------|------------------|---------------|-----------------|
| host-a1 | 192.168.10.10    | 255.255.255.0 | 192.168.10.1    |
| host-a2 | 192.168.10.11    | 255.255.255.0 | 192.168.10.1    |
| host-b1 | 192.168.20.10    | 255.255.255.0 | 192.168.20.1    |
| host-b2 | 192.168.20.11    | 255.255.255.0 | 192.168.20.1    |

## Topology Diagram

```
      Subnet A: 192.168.10.0/24                 Subnet B: 192.168.20.0/24

 +-----------+   +-----------+                +-----------+   +-----------+
 |  host-a1  |   |  host-a2  |                |  host-b1  |   |  host-b2  |
 | .10.10/24 |   | .10.11/24 |                | .20.10/24 |   | .20.11/24 |
 +-----+-----+   +-----+-----+                +-----+-----+   +-----+-----+
       |               |                            |               |
 ------+---------------+------+          +----------+---------------+------
                              | eth0     eth1 |
                              | .10.1   .20.1 |
                           +--+---------------+--+
                           |   router (ip_forward=1)   |
                           +---------------------------+
```

## Setup Instructions

Quick manual setup with Linux network namespaces (requires root):

```bash
# create namespaces
for n in router host-a1 host-a2 host-b1 host-b2; do ip netns add $n; done

# bridges for each subnet
ip link add br-a type bridge; ip link add br-b type bridge
ip link set br-a up; ip link set br-b up

# helper: attach <ns> to <bridge> with <ip/24>
attach() { ip link add v-$1 type veth peer name $1-eth0
  ip link set $1-eth0 netns $1; ip link set v-$1 master $2; ip link set v-$1 up
  ip -n $1 addr add $3 dev $1-eth0; ip -n $1 link set $1-eth0 up; ip -n $1 link set lo up; }

attach host-a1 br-a 192.168.10.10/24
attach host-a2 br-a 192.168.10.11/24
attach host-b1 br-b 192.168.20.10/24
attach host-b2 br-b 192.168.20.11/24
attach router  br-a 192.168.10.1/24
# second router interface on subnet B
ip link add v-router-b type veth peer name router-eth1
ip link set router-eth1 netns router; ip link set v-router-b master br-b; ip link set v-router-b up
ip -n router addr add 192.168.20.1/24 dev router-eth1; ip -n router link set router-eth1 up

# default routes + forwarding
ip netns exec host-a1 ip route add default via 192.168.10.1
ip netns exec host-a2 ip route add default via 192.168.10.1
ip netns exec host-b1 ip route add default via 192.168.20.1
ip netns exec host-b2 ip route add default via 192.168.20.1
ip netns exec router sysctl -w net.ipv4.ip_forward=1

# test
ip netns exec host-a1 ping -c2 192.168.10.11   # same subnet
ip netns exec host-a1 ping -c2 192.168.20.10   # via router
```

Note: inside the namespaces the router's interfaces are named `router-eth0` (Subnet A) and `router-eth1` (Subnet B); these correspond to `eth0`/`eth1` in `topology.yaml`.

## Destroy Instructions

```bash
for n in router host-a1 host-a2 host-b1 host-b2; do ip netns del $n; done
ip link del br-a; ip link del br-b
```

## Verification Instructions

Validate the YAML syntax and the addressing/gateway/route logic:

```bash
pip install pyyaml yamllint
yamllint topology.yaml          # syntax / indentation
python3 validate.py topology.yaml   # duplicate IPs, gateway match, routes
```

`validate.py` exits 0 and prints `OK` when the file is valid.
