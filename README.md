# netbootxyz-standalone-ipxe

Snapshot of the rendered netboot.xyz iPXE menus, scraped from
https://boot.netboot.xyz/ on 2026-11-27 for study, plus standalone
per-distro versions that can be embedded into their own iPXE ISO.

> **Unofficial build** - not affiliated with or endorsed by netboot.xyz.
> Report issues with these builds here, not upstream. The menus are a
> snapshot from 2026-11-27 and do not auto-update like the real netboot.xyz.

All credit to the netboot.xyz project (Apache-2.0, see `LICENSE` and `NOTICE`).
Bundled iPXE, SYSLINUX and rEFInd binaries keep their own licenses (see `NOTICE`).

## Repository layout

| Directory     | Contents |
|---------------|----------|
| `ipxe/`       | Original scraped menus (`*.ipxe` + `boot.cfg`), unmodified generated output (not the upstream Jinja2 templates) |
| `standalone/` | Self-contained per-distro scripts for `EMBED=`, Carbon theme, `build-iso.sh`, `ipxe-config/general.h` |
| `iso/`        | Built hybrid BIOS+UEFI ISOs: `<Distro>-ipxe.iso` + `SHA256SUMS` |
| `efi/`        | `BOOTx64.EFI` extracted from each ISO's `efi.img`: `<Distro>-ipxe.efi` + `SHA256SUMS` |
| `krn/`        | BIOS iPXE (`/boot/ipxe.krn`, Linux bzImage format) extracted from each ISO: `<Distro>-ipxe.krn` + `SHA256SUMS` - boot from GRUB (`linux16`), syslinux (`KERNEL`) or memdisk-free loaders |
| `refind/`     | `ipxe-efi.img.xz` - rEFInd FAT32 ESP image with all `<Distro>-ipxe.efi` + menu entries, `refind.conf` (CR line endings, as in the image), `SHA256SUMS` |
| `tools/`      | analyze, make-standalone, validate, qemu-test, expand-ipxe-efi |

The rEFInd image is 107 MiB uncompressed (over GitHub's 100 MiB file limit), so it is stored xz-compressed:
`xz -dk refind/ipxe-efi.img.xz && (cd refind && sha256sum -c SHA256SUMS)`

## Boot flow (upstream)

1. `menu.ipxe` - entry point. Detects arch (`cpuid --ext 29`), chains `boot.cfg`.
2. `boot.cfg` - global variables: site name, boot domain, signature URL,
   timeout, distro mirrors (`*_mirror` / `*_base_dir`), and `menu_*` flags
   that toggle menu sections.
3. `version.ipxe` - latest version check; chains a newer
   `netboot.xyz-snponly.efi` / `netboot.xyz-undionly.kpxe` if outdated.
4. Main menu - every item is guarded with `iseq ${menu_X} 1 && item X ...`.
5. Submenus - `chain ${menu}.ipxe`: the item ID is the filename, so
   `linux` -> `linux.ipxe` -> `debian.ipxe`, `ubuntu.ipxe`, ...
6. Signatures - when `sigs_enabled` is true, each submenu is checked with
   `imgverify ${menu}.ipxe ${sigs}${menu}.ipxe.sig` (disabled under Secure Boot).
7. Custom hooks - `${github_user}` (netboot.xyz-custom repo) and `${custom_url}`.

## Layout

- Section menus: `linux`, `linux-i386`, `linux-arm`, `live`, `live-arm`,
  `bsd`, `unix`, `windows`, `utils-efi`, `utils-pcbios-32`,
  `utils-pcbios-64`, `utils-arm`
- Distro installers: `debian`, `ubuntu`, `kali`, `archlinux`, `proxmox`, ...
- Live images: `live-*.ipxe`
- Tools: `clonezilla`, `gparted`, `systemrescue`, `shredos`, `dban`,
  `netinfo`, `lspci`, `pciids`, ...

`index.html` is the netboot.xyz front page at the time of scraping.

## standalone/ - one distro per ISO

`standalone/<name>.ipxe` is the same menu made self-contained, for
`make bin/ipxe.iso EMBED=<name>.ipxe`. Each file gets:

1. Bootstrap header - arch detect, `${space}` / `${cls}`, DHCP retry loop
   (falls back to the iPXE shell), `ntp` for TLS certificate time checks.
2. Only the `boot.cfg` globals that menu uses (mirrors, `live_endpoint`,
   `memdisk`, ...) as `isset ${x} || set x ...`.
3. `set menu <name>` - exactly what the parent netboot.xyz menu sets
   before `chain <name>.ipxe`, so the original `goto ${menu}` dispatch works.
4. Every `exit` redirected to a local exit menu: back to menu, iPXE shell,
   reboot, power off, or real exit.
5. Stub labels for goto targets missing upstream
   (`kickstart_device` in almalinux/centos/openEuler, `fail` in smartos).

Not converted (menu infrastructure, not a single distro): `menu`, `about`,
`version`, the section menus above, `netinfo`, `lspci`, `pciids`, `nbxyz`.

### Build an ISO

```
cd standalone
./build-iso.sh ubuntu.ipxe /tmp/netbootxyz-ubuntu.iso      # BIOS + UEFI hybrid
SERIAL=1 ./build-iso.sh debian.ipxe                         # + serial console
```

`build-iso.sh` clones iPXE to `/tmp/ipxe` if needed, installs
`ipxe-config/general.h` as `config/local/general.h` (re-enables HTTPS, ntp,
md5sum etc. that upstream iPXE disables for BIOS builds), builds
`bin/ipxe.lkrn` + `bin-x86_64-efi/ipxe.efi` and combines them with
`util/genfsimg`.

### Regenerate

```
python3 tools/make-standalone.py ipxe standalone
python3 tools/validate.py standalone
python3 tools/qemu-test.py <iso> <log> 300 -- 'regex=>keys' ...
```

Known upstream quirks kept as-is: `live-q4os.ipxe` has a duplicate `:6.10`
label (harmless), `live-peppermint.ipxe` uses `${kernel_url}` / `${squash_url}`
which nothing sets.
