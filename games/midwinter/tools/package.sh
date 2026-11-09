#!/usr/bin/env bash
# Build the default patch set and write both distribution zips into dist/.
#
#   tools/package.sh            # HD zip (MW1PATCH/ folder) + floppy zip
#
# The HD zip: MW1PATCH/ with patched RUNME.TOS + HAGA, the original disks
# (blank campaign disk FFD), PP's text files and PATCHES.TXT (patches/PATCHES.TXT).
# The floppy zip comes from `mw1patch.py build --floppy --zip`.
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"
DATE=$(date +%F)

python3 tools/mw1patch.py verify >/dev/null
python3 tools/mw1patch.py build --out build/game >/dev/null

STAGE=build/dist/MW1PATCH
rm -rf build/dist && mkdir -p "$STAGE" dist
cp build/game/{RUNME.TOS,HAGA,MW240R.BMP,FMW273.HST,LMW273.HST} "$STAGE/"
cp README.TXT LOG.TXT "$STAGE/"
cp -r FILES "$STAGE/FILES"              # original disk images (MWC = data disk)
cp patches/PATCHES.TXT "$STAGE/PATCHES.TXT"
HDZIP="dist/Midwinter_patched_${DATE}.zip"
rm -f "$HDZIP"
(cd build/dist && zip -qr -X "$ROOT/$HDZIP" MW1PATCH)
python3 tools/mw1patch.py build --floppy --zip "dist/Midwinter_patched_floppies_${DATE}.zip" >/dev/null

md5sum build/game/RUNME.TOS build/game/HAGA dist/*"${DATE}"*.zip
