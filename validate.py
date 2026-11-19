#!/usr/bin/env python3
"""Validate topology.yaml: syntax, address conflicts, gateway match, route integrity."""
import ipaddress, sys, yaml

path = sys.argv[1] if len(sys.argv) > 1 else "topology.yaml"
net = yaml.safe_load(open(path))["network"]
errors = []

subnets = {k: ipaddress.ip_network(v["cidr"]) for k, v in net["subnets"].items()}
gateways = {k: ipaddress.ip_address(v["gateway"]) for k, v in net["subnets"].items()}
seen = {}

def check_iface(owner, subnet, ifc):
    ip = ipaddress.ip_address(ifc["ip"])
    if ip not in subnets[subnet]:
        errors.append(f"{owner}: {ip} not in {subnets[subnet]}")
    if ip in seen:
        errors.append(f"{owner}: {ip} duplicates {seen[ip]}")
    seen[ip] = owner

for ifc in net["router"]["interfaces"]:
    check_iface("router/" + ifc["name"], ifc["subnet"], ifc)
    if gateways[ifc["subnet"]] != ipaddress.ip_address(ifc["ip"]):
        errors.append(f"gateway of {ifc['subnet']} != router {ifc['name']} IP")

for h in net["hosts"]:
    for ifc in h["interfaces"]:
        check_iface(h["name"], h["subnet"], ifc)
    for r in h["routes"]:
        if r["destination"] == "default" and ipaddress.ip_address(r["via"]) != gateways[h["subnet"]]:
            errors.append(f"{h['name']}: default route via {r['via']} != gateway")

print("FAIL:\n  " + "\n  ".join(errors) if errors else "OK: topology.yaml is valid")
sys.exit(1 if errors else 0)
