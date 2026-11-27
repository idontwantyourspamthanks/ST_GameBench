#!/usr/bin/env bash
# Package Seconds Out Enhanced v1.1 for distribution (HD zip + Floppy zip + Bootable VHD zip).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BENCH_DIR="$(cd "$GAME_DIR/../../.." && pwd)"
VERSION="1.1"

python3 "$SCRIPT_DIR/build_so.py"

DIST="$GAME_DIR/dist"
STAGE="$(mktemp -d /tmp/so_pkg.XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT

# 1. Hard-Drive zip: clean SECONDS/ folder (excludes harness RUNME.TOS duplicate)
mkdir -p "$STAGE/hd/SECONDS"
for f in "$DIST/hd/"*; do
    base="$(basename "$f")"
    [[ "$base" == "RUNME.TOS" ]] && continue
    cp -p "$f" "$STAGE/hd/SECONDS/$base"
done
cp -p "$GAME_DIR/patches/PATCHES.TXT" "$STAGE/hd/SECONDS/PATCHES.TXT"
cp -p "$GAME_DIR/README.md" "$STAGE/hd/README.md"

HD_ZIP="$DIST/SecondsOut_Enhanced_v${VERSION}_HD.zip"
rm -f "$HD_ZIP"
(cd "$STAGE/hd" && zip -q -r "$HD_ZIP" SECONDS README.md)

# 2. Floppy zip: auto-booting 720 KB .st + docs
mkdir -p "$STAGE/floppy"
cp -p "$DIST/SecondsOut_Enhanced_v${VERSION}.st" "$STAGE/floppy/"
cp -p "$GAME_DIR/patches/PATCHES.TXT" "$STAGE/floppy/PATCHES.TXT"
cp -p "$GAME_DIR/README.md" "$STAGE/floppy/README.md"

FLOPPY_ZIP="$DIST/SecondsOut_Enhanced_v${VERSION}_Floppy.zip"
rm -f "$FLOPPY_ZIP"
(cd "$STAGE/floppy" && zip -q -r "$FLOPPY_ZIP" .)

# 3. Bootable 8 MB VHD zip (HDDRIVER + FAT16 BGM + DESKTOP.INF/NEWDESK.INF autorun)
VHD_ZIP="$DIST/SecondsOut_Enhanced_v${VERSION}_VHD.zip"
python3 "$BENCH_DIR/tools/make_game_vhds.py" seconds-out

echo "Packaged:"
ls -lh "$HD_ZIP" "$FLOPPY_ZIP" "$VHD_ZIP"
