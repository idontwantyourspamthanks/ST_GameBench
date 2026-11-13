#!/usr/bin/env bash
# Build the default patch set and write the distribution zips into dist/.
#
#   tools/package.sh            # HD zip + floppy zip + low-RAM floppy zip
#   tools/package.sh lowram     # only the low-RAM floppy zip (the other two are not rebuilt)
#
# Zips are named Populous2_v<VERSION>_patched_<date>.zip, Populous2_v<VERSION>_patched_floppy_<date>.zip and
# Populous2_v<VERSION>_patched_floppy_lowram_<date>.zip.  VERSION is the one release version, the `; version:`
# header of patches/pop2_credit.s (`pop2patch.py version`); it is also the "v<VERSION> enhanced by dad_prg"
# line on the main menu and @VERSION@ in PATCHES.TXT / FLOPPY.TXT / FLOPPY_LOWRAM.TXT.
#
# The HD zip: POPS2/ with the patched RUNME.TOS, the untouched HAGA, FILES\ and the pictures plus
# PATCHES.TXT.  The floppy zip: Populous2_boot.st, the blank formatted save disk Populous2_save.st (pop2_save asks for it) plus FLOPPY.TXT.
# The low-RAM floppy zip (ICS crack's game, `pop2patch.py build --base ics`): Populous2_lowram.st plus README.TXT (from patches/FLOPPY_LOWRAM.TXT).
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"
DATE=$(date +%F)
VER=$(python3 tools/pop2patch.py version)     # the release version: `; version:` of patches/pop2_credit.s

MODE="${1:-all}"
if [ "$MODE" != lowram ]; then
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
cp build/floppy/Populous2_boot.st build/floppy/Populous2_save.st "$FSTAGE/"
python3 tools/pop2patch.py doc patches/FLOPPY.TXT | sed "s/{DATE}/$DATE/" > "$FSTAGE/FLOPPY.TXT"
FZIP="dist/Populous2_v${VER}_patched_floppy_${DATE}.zip"
rm -f "$FZIP"
(cd build/dist/floppy && zip -qr -X "$ROOT/$FZIP" .)
fi

python3 tools/pop2patch.py verify --base ics >/dev/null
python3 tools/pop2patch.py build --base ics --out build/ics >/dev/null
LSTAGE=build/dist_lowram
rm -rf "$LSTAGE" && mkdir -p "$LSTAGE" dist
cp build/ics/Populous2_lowram.st "$LSTAGE/"
python3 tools/pop2patch.py doc --base ics patches/FLOPPY_LOWRAM.TXT | sed "s/{DATE}/$DATE/" > "$LSTAGE/README.TXT"
LZIP="dist/Populous2_v${VER}_patched_floppy_lowram_${DATE}.zip"
rm -f "$LZIP"
(cd "$LSTAGE" && zip -qr -X "$ROOT/$LZIP" .)

md5sum build/ics/Populous2_lowram.st dist/*"_v${VER}_"*"${DATE}"*.zip
