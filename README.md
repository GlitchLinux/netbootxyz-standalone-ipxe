# netbootxyz-menus

Snapshot of the rendered netboot.xyz iPXE menus, scraped from
https://boot.netboot.xyz/ on 2026-11-27 for study.

These are the generated output files, not the upstream Jinja2 templates
from https://github.com/netbootxyz/netboot.xyz. All credit to the
netboot.xyz project.

## Boot flow

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
