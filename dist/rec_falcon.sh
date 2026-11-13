#!/usr/bin/env bash
# As run_falcon.sh (Falcon, TOS 4.04, 4 MB, 16 MHz, floppy builds), but records video with sound: an AVI (PNG frames +
# 44.1 kHz PCM audio) in ~/Videos/AtariST/ (set ATARI_VIDEO_DIR to change it), named falcon_<date>_<time>.avi.
#   ./rec_falcon.sh DISK1.st [DISK2.st] [HATARI OPTIONS...]
# Recording starts at power-on and the file is closed when Hatari quits (AltGr+Q); one run = one clip.
# Hatari's AltGr+A toggles recording; run the script again for a new file.
# Frame rate: the AVI is written at a fixed 60 fps (the Falcon drives its VGA monitor at 60 Hz in ST modes). If a game switches
# the refresh (the status bar shows 50/60 Hz), set AVI_FPS=50 or 60 to match, or the video runs fast/slow against the sound.
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
source "$HERE/_hatari.sh"   # HATARI (exported: run_falcon.sh uses the same binary) and AVIREC
OUT="${ATARI_VIDEO_DIR:-$HOME/Videos/AtariST}"
mkdir -p "$OUT"
FILE="$OUT/falcon_$(date +%Y-%m-%d_%H%M%S).avi"
echo "recording to $FILE"
DISKS=(); while [[ $# -gt 0 && "$1" != -* && ${#DISKS[@]} -lt 2 ]]; do DISKS+=("$1"); shift; done
exec "$HERE/run_falcon.sh" "${DISKS[@]}" --sound 44100 "${AVIREC[@]}" --avi-fps "${AVI_FPS:-60}" --avi-vcodec png --png-level 3 --avi-file "$FILE" "$@"
