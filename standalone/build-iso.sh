#!/bin/bash
# build-iso.sh - build a hybrid BIOS+UEFI iPXE ISO with one embedded
# netboot.xyz standalone script.
#
# usage: ./build-iso.sh <script.ipxe> [output.iso]
#   env IPXE_SRC=/tmp/ipxe   iPXE git checkout (cloned if missing)
#   env SERIAL=1             also mirror the console to serial (ttyS0/COM1)
#
# example: ./build-iso.sh ubuntu.ipxe /tmp/netbootxyz-ubuntu.iso
set -euo pipefail

[ $# -ge 1 ] || { sed -n '2,10p' "$0"; exit 1; }
SCRIPT=$(readlink -f "$1")
NAME=$(basename "$SCRIPT" .ipxe)
OUT=$(readlink -m "${2:-/tmp/netbootxyz-$NAME.iso}")
IPXE_SRC=${IPXE_SRC:-/tmp/ipxe}
HERE=$(dirname "$(readlink -f "$0")")

[ -f "$SCRIPT" ] || { echo "no such script: $SCRIPT" >&2; exit 1; }
[ -d "$IPXE_SRC/src" ] || git clone --depth 1 https://github.com/ipxe/ipxe.git "$IPXE_SRC"

cp "$HERE/ipxe-config/general.h" "$IPXE_SRC/src/config/local/general.h"
if [ "${SERIAL:-0}" = 1 ]; then
    echo '#define CONSOLE_SERIAL' > "$IPXE_SRC/src/config/local/console.h"
else
    rm -f "$IPXE_SRC/src/config/local/console.h"
fi

cd "$IPXE_SRC/src"
make -j"$(nproc)" bin/ipxe.lkrn bin-x86_64-efi/ipxe.efi EMBED="$SCRIPT"
./util/genfsimg -o "$OUT" bin/ipxe.lkrn bin-x86_64-efi/ipxe.efi
echo "ISO ready: $OUT ($(du -h "$OUT" | cut -f1))"
