# Hard-disk driver (not included)

Some PP conversions (e.g. Hunter's Gamex loader) re-run the hard disk's boot code and need a real ACSI image
with a driver, not Hatari's GEMDOS-HD emulation. The harnesses build that image from files you supply here:

| File | What |
|---|---|
| `HDDRIVER.SYS` | the HDDRIVER driver (commercial, by Uwe Seimet; tested with V10.15) |
| `hddriver_root.bin` | 512 bytes: sector 0 (root sector) of a disk you formatted with HDDRIVER |
| `hddriver_pboot.bin` | 512 bytes: the boot sector of that disk's first partition (HDDRIVER's partition loader) |

Everything in this folder except this README is git-ignored.
