#!/usr/bin/env bash
# Verify, build the default patch set and write the distribution zips into dist/.
#   tools/package.sh   # HD zip (patched PP folder) and floppy zip (Populous_boot.st, Populous_save.st) + README.TXT each
# Needs the user's originals/POPULOUS (nothing of the game is in git).
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"
DATE=$(date +%F)
PP="python3 tools/poppatch.py"
VER=$($PP version)
$PP verify >/dev/null
$PP build --hd --out build/dist_hd >/dev/null
$PP build --floppy --out build/dist_floppy >/dev/null
mkdir -p dist
rm -rf build/dist_stage && mkdir -p build/dist_stage/POPULOUS build/dist_stage/floppy
cp -r build/dist_hd/. build/dist_stage/POPULOUS/
$PP doc patches/README_HD.TXT | sed 's/$/\r/' > build/dist_stage/POPULOUS/PATCHED.TXT
cp build/dist_floppy/Populous_boot.st build/dist_floppy/Populous_save.st build/dist_stage/floppy/
$PP doc patches/README_FLOPPY.TXT | sed 's/$/\r/' > build/dist_stage/floppy/README.TXT
HDZIP="dist/Populous_v${VER}_patched_hd_${DATE}.zip"; FLZIP="dist/Populous_v${VER}_patched_floppy_${DATE}.zip"
rm -f "$HDZIP" "$FLZIP"
(cd build/dist_stage && zip -q -X -r "$ROOT/$HDZIP" POPULOUS)
(cd build/dist_stage/floppy && zip -q -X "$ROOT/$FLZIP" Populous_boot.st Populous_save.st README.TXT)
md5sum build/dist_hd/RUNME.TOS build/dist_hd/FILES/POLA build/dist_hd/HAGA build/dist_floppy/*.st "$HDZIP" "$FLZIP"
