#!/usr/bin/env bash
# As run_falcon_emutos.sh (Falcon, EmuTOS, 4 MB, 16 MHz, the all-games hard disk image on IDE), but records video with sound:
# an AVI (PNG frames + 44.1 kHz PCM audio) in ~/Videos/AtariST/ (set ATARI_VIDEO_DIR to change it), named falcon_emutos_<date>_<time>.avi.
#   ./rec_falcon_emutos.sh [IMAGE] [HATARI OPTIONS...]
# Recording starts at power-on and the file is closed when Hatari quits (AltGr+Q); one run = one clip.
# Frame rate: a fixed 60 fps (VGA ST modes); set AVI_FPS=50 if the status bar shows 50 Hz.
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
source "$HERE/_hatari.sh"   # HATARI (exported: run_falcon_emutos.sh uses the same binary) and AVIREC
OUT="${ATARI_VIDEO_DIR:-$HOME/Videos/AtariST}"
mkdir -p "$OUT"
FILE="$OUT/falcon_emutos_$(date +%Y-%m-%d_%H%M%S).avi"
echo "recording to $FILE"
IMG=(); if [[ $# -gt 0 && "$1" != -* ]]; then IMG=("$1"); shift; fi   # optional IMAGE first
exec "$HERE/run_falcon_emutos.sh" "${IMG[@]}" --sound 44100 "${AVIREC[@]}" --avi-fps "${AVI_FPS:-60}" --avi-vcodec png --png-level 3 --avi-file "$FILE" "$@"
