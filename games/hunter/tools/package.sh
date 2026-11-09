#!/usr/bin/env bash
# Build the default patch set and write the distribution zips into dist/.
#
#   tools/package.sh      # HD zip (HUNTER/ folder) + one-disk floppy zip + two-disk floppy zip
#
# Needs the user's files: the original game files in the game dir, alt/amiga/*.adf (sample bank) and
# alt/floppy/*Paper Bag*.st (floppy base).  The HD zip: HUNTER/ with PP's files, the patched START.TOS,
# FILES\P (patch code + sample bank) and PATCHES.TXT.  The floppy zips come from `huntpatch.py build --floppy`.
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"
DATE=$(date +%F)

python3 tools/huntpatch.py verify >/dev/null
python3 tools/snd_build.py --out build/hunter_snd.bin >/dev/null
python3 tools/huntpatch.py build --samples build/hunter_snd.bin --out build/game >/dev/null

STAGE=build/dist/HUNTER
rm -rf build/dist && mkdir -p "$STAGE" dist
cp -r build/game/. "$STAGE/"
cp patches/PATCHES.TXT "$STAGE/PATCHES.TXT"
rm -f dist/Hunter_patched_hd_test.zip
HDZIP="dist/Hunter_patched_hd_${DATE}.zip"
rm -f "$HDZIP"
(cd build/dist && zip -qr -X "$ROOT/$HDZIP" HUNTER)

FLZIP="dist/Hunter_patched_floppy_${DATE}.zip"
python3 tools/huntpatch.py build --floppy --samples build/hunter_snd.bin --out build/floppy --zip "$FLZIP" >/dev/null

# standard-format alternative: original-geometry disk 1 + 720 KB sound disk 2
python3 tools/huntpatch.py build --floppy --two-disk --samples build/hunter_snd.bin --out build/floppy2 >/dev/null
FL2ZIP="dist/Hunter_patched_floppy_2disk_${DATE}.zip"
rm -f "$FL2ZIP"
STAGE2=build/dist2
rm -rf "$STAGE2" && mkdir -p "$STAGE2"
cp build/floppy2/HUNTER_disk1.st build/floppy2/HUNTER_disk2_sound.st "$STAGE2/"
sed 's/$/\r/' patches/FLOPPY2.TXT > "$STAGE2/README.TXT"
(cd "$STAGE2" && zip -q -X "$ROOT/$FL2ZIP" HUNTER_disk1.st HUNTER_disk2_sound.st README.TXT)
rm -rf "$STAGE2"

md5sum build/game/START.TOS build/game/FILES/P "$HDZIP" "$FLZIP" "$FL2ZIP"
