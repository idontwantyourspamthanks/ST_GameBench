#!/usr/bin/env bash
# Build the default patch set and write both distribution zips into dist/.
#
#   tools/package.sh            # HD zip (MW2PATCH/ folder) + floppy zip
#
# The HD zip: MW2PATCH/ with patched RUNME.TOS + HAGA, the original disks
# (blank campaign disk FFD), PP's text files and PATCHES.TXT (patches/PATCHES.TXT).
# The floppy zip comes from `mw2patch.py build --floppy --zip`.
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"
DATE=$(date +%F)

python3 tools/mw2patch.py verify >/dev/null
python3 tools/mw2patch.py build --out build/game >/dev/null

STAGE=build/dist/MW2PATCH
rm -rf build/dist && mkdir -p "$STAGE" dist
cp build/game/{RUNME.TOS,HAGA,FF240R.BMP,FFF273.HST,LFF273.HST} "$STAGE/"
cp README.TXT LOG.TXT SOLUTION.TXT "$STAGE/"
cp -r FILES "$STAGE/FILES"              # originals: FFD stays the blank campaign disk
cp patches/PATCHES.TXT "$STAGE/PATCHES.TXT"
HDZIP="dist/Midwinter2_patched_${DATE}.zip"
rm -f "$HDZIP"
(cd build/dist && zip -qr -X "$ROOT/$HDZIP" MW2PATCH)
python3 tools/mw2patch.py build --floppy --zip "dist/Midwinter2_patched_floppies_${DATE}.zip" >/dev/null

md5sum build/game/RUNME.TOS build/game/HAGA dist/*"${DATE}"*.zip
