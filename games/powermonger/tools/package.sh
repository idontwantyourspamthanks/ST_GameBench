#!/usr/bin/env bash
# Verify, build the default patch set and write the distribution zips into dist/.
#
#   tools/package.sh      # floppy zip (patched .st + README.TXT) and HD zip (AUTO\WAR.PRG, DATA\*, SAVEDISK.DAT, PMLATE.DAT + README.TXT)
#
# Needs the user's original floppy image disks/protected.st (nothing of the game is in git).
# Zips: dist/Powermonger_v<ver>_patched_floppy_<date>.zip, dist/Powermonger_v<ver>_patched_hd_<date>.zip; md5s are printed.
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"
DATE=$(date +%F)
# release version: one line in patches/pm_credit.s (`TXT: dc.b "v1.0 enhanced by ..."`)
VER=$(sed -n 's/^TXT:.*"v\([^ ]*\) enhanced by .*".*/\1/p' patches/pm_credit.s)
[[ -n "$VER" ]] || { echo "version not found in patches/pm_credit.s" >&2; exit 1; }
PM="python3 tools/pmpatch.py"

[[ -f disks/protected.st ]] || { echo "disks/protected.st (the original floppy image) is missing" >&2; exit 1; }
$PM verify >/dev/null
$PM build --out build/dist_build >/dev/null
FLOPPY=build/dist_build/floppy/powermonger.st
HD=build/dist_build/hd
[[ -f $FLOPPY && -f $HD/AUTO/WAR.PRG && -f $HD/DATA/SPRITE40.DAT && -f $HD/SAVEDISK.DAT && -f $HD/PMLATE.DAT ]] \
    || { echo "build output incomplete" >&2; exit 1; }

mkdir -p dist
rm -rf build/dist_stage && mkdir -p build/dist_stage/floppy build/dist_stage/hd

# floppy: the patched disk (a bootable AUTO-folder disk, one drive) + README.TXT (CRLF)
cp "$FLOPPY" build/dist_stage/floppy/Powermonger_patched.st
sed "s/@VER@/$VER/g; s/\$/\r/" patches/README_FLOPPY.TXT > build/dist_stage/floppy/README.TXT
FLZIP="dist/Powermonger_v${VER}_patched_floppy_${DATE}.zip"
rm -f "$FLZIP"
(cd build/dist_stage/floppy && zip -q -X "$ROOT/$FLZIP" Powermonger_patched.st README.TXT)

# hard disk: a folder to copy to the root of the boot partition (AUTO\ is run by TOS at boot, DATA\ is read by name)
STAGE=build/dist_stage/hd/POWERMONGER
mkdir -p "$STAGE"
cp -r "$HD/AUTO" "$HD/DATA" "$STAGE/"
cp "$HD/SAVEDISK.DAT" "$HD/PMLATE.DAT" "$STAGE/"
sed "s/@VER@/$VER/g; s/\$/\r/" patches/README_HD.TXT > "$STAGE/README.TXT"
HDZIP="dist/Powermonger_v${VER}_patched_hd_${DATE}.zip"
rm -f "$HDZIP"
(cd build/dist_stage/hd && zip -q -X -r "$ROOT/$HDZIP" POWERMONGER)

md5sum "$FLOPPY" "$HD/AUTO/WAR.PRG" "$HD/DATA/SPRITE40.DAT" "$FLZIP" "$HDZIP"
