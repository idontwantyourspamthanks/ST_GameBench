#!/usr/bin/env bash
# Build the default patch set and write both distribution zips into dist/.
#
#   tools/package.sh            # HD zip (MW2PATCH/ folder) + floppy zip
#
# Zips are named Midwinter2_v<VERSION>_patched_<date>.zip and Midwinter2_v<VERSION>_patched_floppies_<date>.zip.  VERSION is the one
# release version, the `; version:` header of patches/mw2_credit.s (`mw2patch.py version`); it is also the "v<VERSION> enhanced by
# dad_prg" line on the logo screen and @VERSION@ in PATCHES.TXT / README.TXT.
#
# The HD zip: MW2PATCH/ with patched RUNME.TOS + HAGA, the original disks
# (blank campaign disk FFD), the Amiga sample bank FILES\ASNBANK.BIN, PP's text files and PATCHES.TXT (patches/PATCHES.TXT).
# The floppy zip comes from `mw2patch.py build --floppy --zip`.
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"
DATE=$(date +%F)
VER=$(python3 tools/mw2patch.py version)       # the release version: `; version:` of patches/mw2_credit.s (one place)

# The Amiga sound effects + music (asn_* patches) are part of the release: the sample bank is converted from the Amiga disk 1.
[[ -f alt/amiga/disk1.adf ]] || { echo "package.sh: alt/amiga/disk1.adf is missing: the release must ship the Amiga sample bank (FILES\\ASNBANK.BIN), refusing to package without it" >&2; exit 1; }
python3 tools/asn_build.py >/dev/null
[[ -f build/asn_bank.bin ]] || { echo "package.sh: tools/asn_build.py did not produce build/asn_bank.bin" >&2; exit 1; }
export MW2_BANK="$ROOT/build/asn_bank.bin"

python3 tools/mw2patch.py verify >/dev/null
python3 tools/mw2patch.py build --out build/game >/dev/null
[[ -f build/game/FILES/ASNBANK.BIN ]] || { echo "package.sh: the default build has no FILES/ASNBANK.BIN" >&2; exit 1; }

STAGE=build/dist/MW2PATCH
rm -rf build/dist && mkdir -p "$STAGE" dist
cp build/game/{RUNME.TOS,HAGA,FF240R.BMP,FFF273.HST,LFF273.HST} "$STAGE/"
cp README.TXT LOG.TXT SOLUTION.TXT "$STAGE/"
cp -r FILES "$STAGE/FILES"              # originals: FFD stays the blank campaign disk
cp build/game/FILES/ASNBANK.BIN "$STAGE/FILES/ASNBANK.BIN"      # Amiga sample bank + sound/music code (asn_* patches)
python3 tools/mw2patch.py doc patches/PATCHES.TXT > "$STAGE/PATCHES.TXT"
HDZIP="dist/Midwinter2_v${VER}_patched_${DATE}.zip"
rm -f "$HDZIP"
(cd build/dist && zip -qr -X "$ROOT/$HDZIP" MW2PATCH)
python3 tools/mw2patch.py build --floppy --zip "dist/Midwinter2_v${VER}_patched_floppies_${DATE}.zip" >/dev/null

md5sum build/game/RUNME.TOS build/game/HAGA dist/*"_v${VER}_"*"${DATE}"*.zip
