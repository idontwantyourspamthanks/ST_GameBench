#!/usr/bin/env bash
# Boot the all-games hard disk image in Hatari as a TT (TOS 3.06, 4 MB ST-RAM, 32 MHz).
#   ./run_tt.sh [IMAGE]          default: the newest AtariST_enhanced_games_*.vhd/.img next to this script
# The image is used directly, so game saves (e.g. Powermonger's SAVEDISK.DAT) persist in it.
# --mmu true: Midwinter 1/2 (PP's HAGA) remap low RAM through the 68030 PMMU on TOS 3.x; without it TOS state is trashed (games/midwinter/work/notes/tt.md).
# Hatari keys: F12 menu, AltGr+M mouse grab, AltGr+Q quit.
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
TOS="$HERE/../tos/TOS_3_06_uk.img"
IMG="${1:-$(ls -t "$HERE"/AtariST_enhanced_games_*.vhd "$HERE"/AtariST_enhanced_games_*.img 2>/dev/null | head -1)}"
[[ -f "$IMG" ]] || { echo "no hard disk image found (pass one as the first argument)" >&2; exit 1; }
[[ -f "$TOS" ]] || { echo "TOS image not found: $TOS (see gamebench/tos/README.md)" >&2; exit 1; }
echo "TT (TOS 3.06, 4 MB ST-RAM, 32 MHz): $IMG"
exec hatari --machine tt --tos "$TOS" --memsize 4096 --cpuclock 32 --monitor vga --mmu true \
     --gemdos-drive skip --acsi 0="$IMG" --confirm-quit no
