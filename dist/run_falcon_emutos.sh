#!/usr/bin/env bash
# Boot the all-games hard disk image in Hatari as a Falcon running EmuTOS (4 MB, 16 MHz, VGA), over the Falcon's IDE port.
#   ./run_falcon_emutos.sh [IMAGE]          default: the newest AtariST_enhanced_games_*.vhd/.img next to this script
# NOT Atari TOS: this is a convenience for testing only. The games' Falcon fixes (Hunter's _MCH detection, Powermonger's
# fal_ym / FALCON byte, the HD TOS-region swap) were tested against real TOS 4.04, not EmuTOS.
# Why EmuTOS: HDDRIVER 10.15 and TOS 4.04's own IDE driver do not mount Hatari's Falcon IDE disk (HDDRIVER probes the status
# register, then issues no IDE command: "No partitions"); EmuTOS's IDE driver maps the same image as C:.
# The image is used directly, so game saves (e.g. Powermonger's SAVEDISK.DAT) persist in it.
# For real TOS 4.04 use the floppy builds: ./run_falcon.sh DISK1.st [DISK2.st]
# Hatari keys: F12 menu, AltGr+M mouse grab, AltGr+Q quit.
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
TOS="$HERE/../tos/EmuTOS_1024k.img"
IMG="${1:-$(ls -t "$HERE"/AtariST_enhanced_games_*.vhd "$HERE"/AtariST_enhanced_games_*.img 2>/dev/null | head -1)}"
[[ -f "$IMG" ]] || { echo "no hard disk image found (pass one as the first argument)" >&2; exit 1; }
[[ -f "$TOS" ]] || { echo "TOS image not found: $TOS (see gamebench/tos/README.md)" >&2; exit 1; }
echo "Falcon (EmuTOS, 4 MB, 16 MHz), IDE: $IMG"
exec hatari --machine falcon --tos "$TOS" --memsize 4096 --cpuclock 16 --monitor vga \
     --gemdos-drive skip --ide-master "$IMG" --confirm-quit no
