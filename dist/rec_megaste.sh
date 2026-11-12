#!/usr/bin/env bash
# As run_megaste.sh (Mega STE (TOS 2.06, 4 MB, 16 MHz)), but records video with sound: an AVI (PNG frames + 44.1 kHz PCM audio) in
# ~/Videos/AtariST/ (set ATARI_VIDEO_DIR to change it), named megaste_<date>_<time>.avi.
#   ./rec_megaste.sh [IMAGE] [HATARI OPTIONS...]
# Recording starts at power-on and the file is closed when Hatari quits (AltGr+Q); one run = one clip.
# Hatari's AltGr+A toggles recording; run the script again for a new file.
# Frame rate: the AVI is written at a fixed 60 fps (TOS 2.06 (US) runs the desktop at 60 Hz); Hatari otherwise takes the rate at power-on,
# before TOS sets it. If a game switches the refresh (the status bar shows 50/60 Hz), set AVI_FPS=50 or 60 to match,
# or the video runs fast/slow against the sound.
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
OUT="${ATARI_VIDEO_DIR:-$HOME/Videos/AtariST}"
mkdir -p "$OUT"
FILE="$OUT/megaste_$(date +%Y-%m-%d_%H%M%S).avi"
echo "recording to $FILE"
IMG=(); if [[ $# -gt 0 && "$1" != -* ]]; then IMG=("$1"); shift; fi   # optional IMAGE first
exec "$HERE/run_megaste.sh" "${IMG[@]}" --sound 44100 --avirecord --avi-fps "${AVI_FPS:-60}" --avi-vcodec png --png-level 3 --avi-file "$FILE" "$@"
