#!/usr/bin/env bash
# Boot the all-games hard disk image in Hatari as a Mega STE (TOS 2.06, 4 MB, 16 MHz).
#   ./run_megaste.sh [IMAGE]          default: the newest AtariST_enhanced_games_*.vhd/.img next to this script
# The image is used directly, so game saves (e.g. Powermonger's SAVEDISK.DAT) persist in it.
# Hatari keys: F12 menu, AltGr+M mouse grab, AltGr+Q quit.
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
TOS="$HERE/../tos/TOS_2_06.img"
IMG="${1:-$(ls -t "$HERE"/AtariST_enhanced_games_*.vhd "$HERE"/AtariST_enhanced_games_*.img 2>/dev/null | head -1)}"
[[ -f "$IMG" ]] || { echo "no hard disk image found (pass one as the first argument)" >&2; exit 1; }
[[ -f "$TOS" ]] || { echo "TOS image not found: $TOS (see gamebench/tos/README.md)" >&2; exit 1; }
echo "Mega STE (TOS 2.06, 4 MB, 16 MHz): $IMG"
exec hatari --machine megaste --tos "$TOS" --memsize 4096 --cpuclock 16 --monitor rgb \
     --gemdos-drive skip --acsi 0="$IMG" --confirm-quit no
