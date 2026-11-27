#!/usr/bin/env bash
# Build Player Manager v1.1 and write the deterministic HD + VHD distribution zips into dist/.
#
#   tools/package.sh   # writes dist/PlayerManager_v1.1_patched_{hd,vhd}_<date>.zip
#
# Needs originals/PLAYERME, work/ko2_ram.bin, work/setup_ram.bin, work/DEMO92.DAT,
# Kick Off 2 originals/KICKOFF2/FILES/KRD, and vasmm68k_mot.
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"

VER="1.1"
DATE="${DATE:-$(date +%F)}"
STAMP="2026-01-01 00:00:00 UTC"

python3 tools/pmpatch.py

mkdir -p dist
rm -rf build/dist_stage && mkdir -p build/dist_stage/PLAYERME
cp -r build/game/. build/dist_stage/PLAYERME/
sed 's/$/\r/' patches/README_HD.TXT > build/dist_stage/PLAYERME/PATCHED.TXT

HDZIP="dist/PlayerManager_v${VER}_patched_hd_${DATE}.zip"
rm -f "$HDZIP"
find build/dist_stage -exec touch -d "$STAMP" {} +
(cd build/dist_stage && find PLAYERME -type f | LC_ALL=C sort | TZ=UTC zip -q -X -@ "$ROOT/$HDZIP")

echo "Built $HDZIP"
python3 "$ROOT/../../../tools/make_game_vhds.py" player-manager --date "$DATE"
VHDZIP="dist/PlayerManager_v${VER}_patched_vhd_${DATE}.zip"
md5sum build/game/HAGA build/game/FILES/PMLA build/game/FILES/KO2ENG.BIN build/game/FILES/KO2HND.BIN build/game/FILES/PMCODE.BIN build/game/FILES/KO2STE.BIN build/game/FILES/AMIGASND.BIN build/game/FILES/AMIGAP0.BIN "$HDZIP" "$VHDZIP"
