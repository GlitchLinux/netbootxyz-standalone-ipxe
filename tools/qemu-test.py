#!/usr/bin/env python3
"""
qemu-test.py - boot a standalone iPXE ISO headless (serial console) and drive
the menu with a list of expect/send steps. Writes a clean log.

usage: qemu-test.py <iso> <logfile> [timeout_s] -- 'expect=>keys' ...
  keys: \\r = Enter, \\x1b = Esc, \\x1b[B = Down arrow
"""
import os, pty, re, select, signal, subprocess, sys, time

iso, log = sys.argv[1], sys.argv[2]
timeout = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != "--" else 300
steps = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
steps = [s.split("=>", 1) for s in steps]

kvm = ["-enable-kvm", "-cpu", "host"] if os.access("/dev/kvm", os.W_OK) else []
cmd = ["qemu-system-x86_64", "-m", "3072", *kvm, "-cdrom", iso, "-boot", "d",
       "-display", "none", "-monitor", "none", "-serial", "stdio",
       "-nic", "user,model=e1000"]

master, slave = pty.openpty()
p = subprocess.Popen(cmd, stdin=slave, stdout=slave, stderr=slave, close_fds=True)
os.close(slave)
ansi = re.compile(rb"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][A-Za-z0-9]|\r")
buf, clean, start = b"", b"", time.time()
with open(log, "wb") as fh:
    fh.write(f"# cmd: {' '.join(cmd)}\n".encode())
    while time.time() - start < timeout and p.poll() is None:
        r, _, _ = select.select([master], [], [], 1)
        if r:
            try:
                data = os.read(master, 65536)
            except OSError:
                break
            buf += data
            c = ansi.sub(b"", data)
            clean += c
            fh.write(c)
            fh.flush()
        if steps:
            pat, keys = steps[0]
            if re.search(pat.encode(), clean):
                time.sleep(1.5)
                keys = keys.encode().decode("unicode_escape").encode()
                os.write(master, keys)
                fh.write(f"\n### [{time.time()-start:5.1f}s] matched {pat!r} -> sent {keys!r}\n".encode())
                clean = b""
                steps.pop(0)
        elif re.search(rb"initrd\.{0,3}\s*(ok|\d+%)", clean):
            fh.write(f"\n### [{time.time()-start:5.1f}s] initrd download in progress - test passed\n".encode())
            break
    fh.write(f"\n### end after {time.time()-start:.1f}s, steps left: {steps}\n".encode())
p.send_signal(signal.SIGTERM)
try:
    p.wait(5)
except subprocess.TimeoutExpired:
    p.kill()
