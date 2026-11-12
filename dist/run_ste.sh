#!/usr/bin/env bash
# Boot the all-games hard disk image in Hatari as an STE (TOS 1.62, 1 MB, 8 MHz).
#   ./run_ste.sh [IMAGE [HATARI OPTIONS...]]   default image: the newest AtariST_enhanced_games_*.vhd/.img next to this script ("" = default)
# The image is used directly, so game saves (e.g. Powermonger's SAVEDISK.DAT) persist in it.
# Hatari keys: F12 menu, AltGr+M mouse grab, AltGr+Q quit.
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
TOS="$HERE/../tos/TOS_1_62.img"
IMG="${1:-$(ls -t "$HERE"/AtariST_enhanced_games_*.vhd "$HERE"/AtariST_enhanced_games_*.img 2>/dev/null | head -1)}"
[[ -f "$IMG" ]] || { echo "no hard disk image found (pass one as the first argument)" >&2; exit 1; }
[[ -f "$TOS" ]] || { echo "TOS image not found: $TOS (see gamebench/tos/README.md)" >&2; exit 1; }
echo "STE (TOS 1.62, 1 MB, 8 MHz): $IMG"
exec hatari --machine ste --tos "$TOS" --memsize 1024 --cpuclock 8 --monitor rgb \
     --gemdos-drive skip --acsi 0="$IMG" --confirm-quit no "${@:2}"
