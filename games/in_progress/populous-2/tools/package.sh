#!/usr/bin/env bash
# Build the default patch set and write both distribution zips into dist/.
#
#   tools/package.sh            # HD zip + floppy zip
#
# Zips are named Populous2_v<VERSION>_patched_<date>.zip and
# Populous2_v<VERSION>_patched_floppy_<date>.zip.  VERSION is the one release version, the `; version:`
# header of patches/pop2_credit.s (`pop2patch.py version`); it is also the "v<VERSION> enhanced by dad_prg"
# line on the main menu and @VERSION@ in PATCHES.TXT / FLOPPY.TXT.
#
# The HD zip: POPS2/ with the patched RUNME.TOS, the untouched HAGA, FILES\ and the pictures plus
# PATCHES.TXT.  The floppy zip: Populous2_boot.st plus FLOPPY.TXT.
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"
DATE=$(date +%F)
VER=$(python3 tools/pop2patch.py version)     # the release version: `; version:` of patches/pop2_credit.s

python3 tools/pop2patch.py verify >/dev/null
python3 tools/pop2patch.py build --out build/hd >/dev/null
python3 tools/pop2patch.py build --floppy --out build/floppy >/dev/null

STAGE=build/dist/POPS2
rm -rf build/dist && mkdir -p "$STAGE" dist
cp build/hd/RUNME.TOS build/hd/HAGA build/hd/*.HST build/hd/*.BMP build/hd/*.TXT "$STAGE/"
cp -r build/hd/FILES "$STAGE/FILES"
python3 tools/pop2patch.py doc patches/PATCHES.TXT | sed "s/{DATE}/$DATE/" > "$STAGE/PATCHES.TXT"
HDZIP="dist/Populous2_v${VER}_patched_${DATE}.zip"
rm -f "$HDZIP"
(cd build/dist && zip -qr -X "$ROOT/$HDZIP" POPS2)

FSTAGE=build/dist/floppy
rm -rf "$FSTAGE" && mkdir -p "$FSTAGE"
cp build/floppy/Populous2_boot.st "$FSTAGE/"
python3 tools/pop2patch.py doc patches/FLOPPY.TXT | sed "s/{DATE}/$DATE/" > "$FSTAGE/FLOPPY.TXT"
FZIP="dist/Populous2_v${VER}_patched_floppy_${DATE}.zip"
rm -f "$FZIP"
(cd build/dist/floppy && zip -qr -X "$ROOT/$FZIP" .)

md5sum build/hd/RUNME.TOS dist/*"_v${VER}_"*"${DATE}"*.zip
