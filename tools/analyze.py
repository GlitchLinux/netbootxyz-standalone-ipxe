#!/usr/bin/env python3
"""Analyze netboot.xyz menu files: entry label, external gotos, external vars."""
import os, re, sys

SRC = sys.argv[1]
INFRA = {"menu", "about", "version", "linux", "linux-i386", "linux-arm", "live",
         "live-arm", "bsd", "unix", "utils-efi", "utils-arm", "utils-pcbios-32",
         "utils-pcbios-64", "netinfo", "lspci", "pciids", "nbxyz"}
# variables iPXE itself provides (settings), not netboot.xyz globals
BUILTIN = re.compile(r'^(net\d.*|netX.*|ip|netmask|gateway|dns|dhcp-server|next-server|'
                     r'filename|platform|buildarch|manufacturer|product|serial|uuid|'
                     r'asset|mac|busid|chip|hostname|domain|efi/.*|smbios/.*|pci/.*|'
                     r'unixtime|version|cpuid/.*|syslog|.*:string|.*:hex|.*:int\d*|'
                     r'.*:uristring|board-serial|user-class|root-path|priority)$')

def parse(path):
    txt = open(path, errors="replace").read()
    labels = set(re.findall(r'^\s*:([A-Za-z0-9_.${}-]+)\s*$', txt, re.M))
    gotos = set(re.findall(r'\bgoto\s+([A-Za-z0-9_.-]+)', txt))
    used = set(re.findall(r'\$\{([^}]+)\}', txt))
    setv = set(re.findall(r'\b(?:set|read|clear)\s+(?:--\S+\s+)?([A-Za-z0-9_.:/-]+)', txt))
    setv |= set(re.findall(r'\bchoose\s+(?:--\S+\s+\S+\s+)*([A-Za-z0-9_-]+)', txt))
    setv |= set(re.findall(r'\bselect\s+([A-Za-z0-9_-]+)', txt))
    first = re.search(r'^\s*goto\s+(\S+)', txt, re.M)
    return dict(labels=labels, gotos=gotos, used=used, setv=setv,
                first=first.group(1) if first else None, txt=txt)

for f in sorted(os.listdir(SRC)):
    if not f.endswith(".ipxe"):
        continue
    name = f[:-5]
    if name in INFRA:
        continue
    p = parse(os.path.join(SRC, f))
    ext_goto = sorted(g for g in p["gotos"] - p["labels"])
    ext_vars = sorted(v for v in p["used"] - p["setv"] if not BUILTIN.match(v))
    entry = name in p["labels"]
    print(f"{name:20} entry={'Y' if entry else 'N'} first={p['first']} "
          f"xgoto={ext_goto} xvars={ext_vars}")
