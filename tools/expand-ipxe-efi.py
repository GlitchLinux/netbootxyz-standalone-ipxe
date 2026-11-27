#!/usr/bin/env python3
"""
expand-ipxe-efi.py - rebuild ipxe-efi.img (rEFInd ESP image) as a larger FAT32
image containing every <Name>-ipxe.efi, plus a refind.conf menuentry for each.

usage: expand-ipxe-efi.py <ipxe-efi.img> <efi_dir>

- original is kept as <img>.orig-<timestamp> (first run only, re-runs reuse it)
- existing tree, label and volume serial are preserved
- refind.conf keeps its CR line endings; new entries go right after the
  Glitch-iPXE-WAN entry, in alphabetical order
"""
import glob, os, shutil, subprocess, sys, tempfile, time

IMG, EFI_DIR = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
ANCHOR = "loader /EFI/BOOT/Glitch-iPXE.efi"
ICON = "/EFI/BOOT/icons/os_network.png"


def run(*cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout


# ---- original image (backup once, always rebuild from it) ----
backups = sorted(glob.glob(IMG + ".orig-*"))
if backups:
    orig = backups[0]
else:
    orig = IMG + ".orig-" + time.strftime("%Y%m%d-%H%M")
    shutil.copy2(IMG, orig)
print(f"source image : {orig}")

info = run("minfo", "-i", orig, "::")
label, serial = "IPXE-EFI", None
for l in info.splitlines():
    if l.strip().startswith("disk label="):
        label = l.split("=", 1)[1].strip().strip('"').strip() or label
    elif l.strip().startswith("serial number:"):
        serial = l.split(":", 1)[1].strip()

work = tempfile.mkdtemp(prefix="ipxe-efi-")
tree = os.path.join(work, "tree")
os.makedirs(tree)
run("mcopy", "-s", "-m", "-n", "-i", orig, "::/*", tree + "/")
boot = os.path.join(tree, "EFI", "BOOT")
for d in ("icons", "vars", "themes"):            # make sure empty dirs survive
    os.makedirs(os.path.join(boot, d), exist_ok=True)

# ---- new EFI binaries ----
efis = sorted(glob.glob(os.path.join(EFI_DIR, "*-ipxe.efi")), key=lambda p: os.path.basename(p).lower())
for e in efis:
    shutil.copy2(e, boot)
names = [os.path.basename(e)[:-len("-ipxe.efi")] for e in efis]
print(f"efi files    : {len(efis)}")

# ---- refind.conf ----
conf_path = os.path.join(boot, "refind.conf")
raw = open(conf_path, "rb").read().decode()
nl = "\r\n" if "\r\n" in raw else ("\r" if "\r" in raw else "\n")
lines = raw.split(nl)
idx = next(i for i, l in enumerate(lines) if l.strip() == ANCHOR)
end = next(i for i in range(idx, len(lines)) if lines[i].strip() == "}")
block = []
for n in names:
    block += ["", f"menuentry {n} iPXE {{",
              f"    loader /EFI/BOOT/{n}-ipxe.efi",
              f"    icon {ICON}", "}"]
lines[end + 1:end + 1] = block
open(conf_path, "wb").write(nl.join(lines).encode())
print(f"refind.conf  : +{len(names)} entries after line {end + 1}, line ending {nl!r}")

# ---- new FAT32 image ----
used = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(tree) for f in fs)
mib = -(-(used + 8 * 2**20) // 2**20)            # content + 8 MiB headroom, rounded up
new = IMG + ".new"
if os.path.exists(new):
    os.remove(new)
mkfs = ["mkfs.fat", "-F", "32", "-n", label[:11], "-C", new, str(mib * 1024)]
if serial:
    mkfs[1:1] = ["-i", serial]
run(*mkfs)
run("mcopy", "-s", "-m", "-i", new, *[os.path.join(tree, x) for x in os.listdir(tree)], "::/")
for d in ("icons", "vars", "themes"):
    subprocess.run(["mmd", "-i", new, f"::/EFI/BOOT/{d}"], capture_output=True)

# ---- verify ----
check = tempfile.mkdtemp(prefix="ipxe-efi-chk-")
run("mcopy", "-s", "-n", "-i", new, "::/*", check + "/")
bad = [n for n in names if open(os.path.join(check, "EFI/BOOT", f"{n}-ipxe.efi"), "rb").read()
       != open(os.path.join(EFI_DIR, f"{n}-ipxe.efi"), "rb").read()]
if bad:
    sys.exit(f"verify FAILED for {bad}")

st = os.stat(orig)
os.replace(new, IMG)
os.chown(IMG, st.st_uid, st.st_gid)
os.chmod(IMG, st.st_mode & 0o777)
shutil.rmtree(work)
shutil.rmtree(check)
print(f"new image    : {IMG} ({mib} MiB FAT32, label {label}, serial {serial}, "
      f"{used / 2**20:.1f} MiB used)")
