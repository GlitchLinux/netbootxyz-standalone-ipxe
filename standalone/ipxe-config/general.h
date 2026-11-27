/*
 * config/local/general.h for netboot.xyz standalone scripts.
 *
 * Copy to ipxe/src/config/local/general.h before building.
 * Upstream iPXE disables several of these for BIOS (pcbios) builds;
 * the netboot.xyz menus need them (HTTPS for github live assets,
 * ntp for certificate time validation, md5sum, etc).
 */

#define DOWNLOAD_PROTO_HTTPS	/* github.com/netbootxyz live assets */
#define NTP_CMD			/* ntp 0.pool.ntp.org - fixes TLS cert time checks */
#define DIGEST_CMD		/* md5sum / sha1sum used after kernel load */
#define CONSOLE_CMD		/* console command */
#define PARAM_CMD		/* params / param */
#define PCI_CMD			/* pciscan */
#define IMAGE_TRUST_CMD		/* imgtrust / imgverify */
#define TIME_CMD		/* time command */
#define REBOOT_CMD		/* exit menu: reboot */
#define POWEROFF_CMD		/* exit menu: power off */
#define NSLOOKUP_CMD		/* DNS debugging from the shell */
#define PING_CMD		/* ping from the shell */
