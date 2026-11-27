#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
GAME="$ROOT/games/in_progress/seconds-out"
HATARI="${HATARI:-/home/ryan/Code/AtariST/hattari/build/src/hatari}"
[[ -x "$HATARI" ]] || HATARI="$(command -v hatari)"

VHD_ZIP="$GAME/dist/SecondsOut_Enhanced_v1.2_VHD.zip"
VHD="${VHD:-$GAME/work/SecondsOut_v1.2.vhd}"
if [[ ! -f "$VHD" || "$VHD_ZIP" -nt "$VHD" ]]; then
  mkdir -p "$(dirname "$VHD")"
  unzip -qo "$VHD_ZIP" SecondsOut_v1.2.vhd -d "$(dirname "$VHD")"
fi

exec "$HATARI" --machine ste --tos "$ROOT/tos/TOS_1_62.img" --memsize 4096 \
  --monitor rgb --sound 50066 --confirm-quit no \
  --gemdos-drive skip --acsi 0="$VHD" --joy1 keys "$@"
