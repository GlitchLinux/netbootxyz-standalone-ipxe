#!/usr/bin/env python3
"""
make-standalone.py - turn netboot.xyz per-distro menus into standalone iPXE
scripts suitable for embedding into their own iPXE ISO/EFI image
(make bin/ipxe.iso EMBED=ubuntu.ipxe).

Usage: make-standalone.py <src_dir_with_boot.cfg> <out_dir>

What it does per distro file:
  1. bootstrap header: arch detect, ${space}/${cls}, DHCP retry loop, ntp
  2. inline only the boot.cfg globals the file references (+ dependencies)
  3. set menu=<name> exactly like the parent netboot.xyz menu does
  4. rewrite every `exit` into a local exit menu (back / shell / reboot / quit)
  5. add stub labels for literal goto targets missing upstream
"""
import datetime
import os
import re
import sys

SRC, OUT = sys.argv[1], sys.argv[2]

# menus/infra that are not a single distro/tool
INFRA = {"menu", "about", "version", "linux", "linux-i386", "linux-arm", "live",
         "live-arm", "bsd", "unix", "utils-efi", "utils-arm", "utils-pcbios-32",
         "utils-pcbios-64", "netinfo", "lspci", "pciids", "nbxyz"}

VAR_RE = re.compile(r"\$\{([^}:]+)(?::[^}]*)?\}")
LABEL_RE = re.compile(r"^\s*:([A-Za-z0-9_.-]+)\s*$", re.M)
GOTO_RE = re.compile(r"\bgoto\s+([A-Za-z0-9_.-]+)(?=\s|$)")
EXIT_RE = re.compile(r"(^\s*|(?:&&|\|\|)\s*)exit(?:\s+\d+)?(?=\s*(?:\|\||&&|$))")


def boot_cfg_defs(path):
    """name -> definition line, for global vars + mirrors (before :architectures)."""
    defs = {}
    for line in open(path):
        if line.startswith(":architectures"):
            break
        m = re.match(r"^\s*(?:isset \$\{\S+\} \|\| )?set (\S+)(?:\s+(.*))?$", line.rstrip("\n"))
        if not m or m.group(1) in defs:
            continue
        name, val = m.group(1), (m.group(2) or "").rstrip()
        if name in ("sigs_enabled", "sigs", "ipxe_disk", "boot_timeout", "site_name"):
            continue  # menu-level only, distro menus never use them
        defs[name] = val
    return defs


def needed_vars(text, defs):
    todo, seen = set(VAR_RE.findall(text)), set()
    while todo:
        v = todo.pop()
        if v in seen or v not in defs:
            continue
        seen.add(v)
        todo |= set(VAR_RE.findall(defs[v]))
    # keep boot.cfg order so dependencies come first
    return [k for k in defs if k in seen]


HEADER = """#!ipxe
# {name}.ipxe - standalone netboot.xyz "{name}" menu
# Source : https://boot.netboot.xyz/{name}.ipxe (scraped {date})
# Built  : make-standalone.py - bootstrap + boot.cfg globals inlined,
#          exits redirected to a local exit menu.
# Embed  : make bin/ipxe.iso EMBED=/path/{name}.ipxe
#          make bin-x86_64-efi/ipxe.efi EMBED=/path/{name}.ipxe
# Original netboot.xyz code: https://github.com/netbootxyz/netboot.xyz (Apache-2.0)

########## standalone bootstrap ##########
:nbx_init
isset ${{arch}} && goto nbx_arch_done ||
cpuid --ext 29 && set arch x86_64 || set arch i386
iseq ${{buildarch}} arm64 && set arch arm64 ||
:nbx_arch_done
set space:hex 20:20
set space ${{space:string}}
iseq ${{cls}} serial && goto nbx_cls_done ||
set cls:hex 1b:5b:4a
set cls ${{cls:string}}
:nbx_cls_done

:nbx_net
isset ${{ip}} && goto nbx_net_done ||
echo Configuring network (DHCP)...
dhcp && goto nbx_net_done ||
echo DHCP failed - press any key to retry, or wait 10s for the iPXE shell.
prompt --timeout 10000 && goto nbx_net ||
echo Type "exit" in the shell to retry DHCP.
shell
goto nbx_net
:nbx_net_done
ntp 0.pool.ntp.org ||

########## netboot.xyz globals used by this menu (from boot.cfg) ##########
{globals}
########## original netboot.xyz menu ##########
:nbx_start
set menu {name}
"""

FOOTER = """
########## standalone stubs for labels missing upstream ##########
{stubs}
########## standalone exit menu ##########
:nbx_exit
menu {name} - netboot.xyz standalone
item nbx_restart ${{space}} Back to {name} menu
item nbx_shell ${{space}} iPXE shell
item nbx_reboot ${{space}} Reboot
item nbx_poweroff ${{space}} Power off
item nbx_quit ${{space}} Exit iPXE (continue firmware boot order)
choose --default nbx_restart nbx_choice || goto nbx_start
goto ${{nbx_choice}}
:nbx_restart
goto nbx_start
:nbx_shell
echo Type "exit" to return to the {name} menu.
shell
goto nbx_start
:nbx_reboot
reboot
goto nbx_start
:nbx_poweroff
poweroff
goto nbx_start
:nbx_quit
exit 1
"""


def convert(name, text, defs, date):
    body = text.split("\n", 1)[1] if text.startswith("#!ipxe") else text
    body = "\n".join(EXIT_RE.sub(r"\1goto nbx_exit", l) if not l.lstrip().startswith("#") else l
                     for l in body.split("\n"))
    gvars = needed_vars(body, defs)
    globals_txt = "".join(f"isset ${{{v}}} || set {v} {defs[v]}".rstrip() + "\n" for v in gvars) \
        or "# (none)\n"
    head = HEADER.format(name=name, date=date, globals=globals_txt)
    labels = set(LABEL_RE.findall(head + body + FOOTER))
    missing = sorted(set(GOTO_RE.findall(body)) - labels)
    stubs = "".join(f":{m}\necho {name}: menu target '{m}' does not exist upstream.\n"
                    f"prompt Press any key...\ngoto nbx_exit\n" for m in missing) or "# (none)\n"
    return head + body.rstrip("\n") + "\n" + FOOTER.format(name=name, stubs=stubs), gvars, missing


def main():
    defs = boot_cfg_defs(os.path.join(SRC, "boot.cfg"))
    date = datetime.date.today().isoformat()
    os.makedirs(OUT, exist_ok=True)
    n = 0
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".ipxe") or f[:-5] in INFRA:
            continue
        name = f[:-5]
        out, gvars, missing = convert(name, open(os.path.join(SRC, f)).read(), defs, date)
        with open(os.path.join(OUT, f), "w") as fh:
            fh.write(out)
        n += 1
        print(f"{name:18} globals={','.join(gvars) or '-'}" + (f"  stubs={missing}" if missing else ""))
    print(f"\n{n} standalone scripts written to {OUT}")


if __name__ == "__main__":
    main()
