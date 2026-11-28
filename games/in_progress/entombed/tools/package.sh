#!/usr/bin/env bash
# Package Entombed STe Enhanced v1.0 for distribution:
#   - Entombed_Enhanced_v1.0_HD.zip     (C:\ENTOMBED\ folder)
#   - Entombed_Enhanced_v1.0_Floppy.zip (auto-booting 720 KB .st floppy + docs)
#   - Entombed_Enhanced_v1.0_VHD.zip    (auto-booting 8 MB HDDRIVER .vhd + README.TXT)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BENCH_DIR="$(cd "$GAME_DIR/../../.." && pwd)"
VERSION="1.0"

python3 "$SCRIPT_DIR/build_entombed.py"

DIST="$GAME_DIR/dist"
mkdir -p "$DIST"
STAGE="$(mktemp -d /tmp/entombed_pkg.XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT

ORIG_DOC="$GAME_DIR/work/extracted/disk/SIDE_2/ENTOMBED/ENTOMBED.DOC"
PRG="$GAME_DIR/work/disk_overlay/ENTOMBED.PRG"
PATCHES_TXT="$GAME_DIR/patches/PATCHES.TXT"

# 1. Hard-Drive zip: clean 8.3 ENTOMBED/ folder
mkdir -p "$STAGE/hd/ENTOMBED"
cp -p "$PRG" "$STAGE/hd/ENTOMBED/ENTOMBED.PRG"
if [[ -f "$ORIG_DOC" ]]; then
    cp -p "$ORIG_DOC" "$STAGE/hd/ENTOMBED/ENTOMBED.DOC"
fi
cp -p "$PATCHES_TXT" "$STAGE/hd/ENTOMBED/PATCHES.TXT"

HD_ZIP="$DIST/Entombed_Enhanced_v${VERSION}_HD.zip"
rm -f "$HD_ZIP"
(cd "$STAGE/hd" && zip -q -9 -r "$HD_ZIP" ENTOMBED)

# 2. Auto-booting 720 KB FAT12 Floppy (.st) + Floppy zip
FLOPPY_ST="$DIST/Entombed_Enhanced_v${VERSION}.st"
rm -f "$FLOPPY_ST"
truncate -s 737280 "$FLOPPY_ST"
mkfs.fat -F 12 -s 2 -S 512 -R 1 -f 2 -r 112 -M 0xF9 -n "ENTOMBED" "$FLOPPY_ST" >/dev/null
# Write canonical Atari ST 68000 boot jump ($6038) + non-$1234 checksum so TOS boots \AUTO\ENTOMBED.PRG cleanly
python3 -c '
import struct, sys
p = sys.argv[1]
with open(p, "r+b") as f:
    b = bytearray(f.read(512))
    b[0:2] = b"\x60\x38"
    b[510:512] = b"\x00\x00"
    if sum(struct.unpack(">256H", b)) & 0xFFFF == 0x1234:
        b[511] = 1
    f.seek(0)
    f.write(b)
' "$FLOPPY_ST"
MTOOLS_SKIP_CHECK=1 mmd -i "$FLOPPY_ST" ::AUTO
MTOOLS_SKIP_CHECK=1 mcopy -i "$FLOPPY_ST" -m "$PRG" ::AUTO/ENTOMBED.PRG
if [[ -f "$ORIG_DOC" ]]; then
    MTOOLS_SKIP_CHECK=1 mcopy -i "$FLOPPY_ST" -m "$ORIG_DOC" ::ENTOMBED.DOC
fi
MTOOLS_SKIP_CHECK=1 mcopy -i "$FLOPPY_ST" -m "$PATCHES_TXT" ::PATCHES.TXT

mkdir -p "$STAGE/floppy"
cp -p "$FLOPPY_ST" "$STAGE/floppy/"
cp -p "$PATCHES_TXT" "$STAGE/floppy/PATCHES.TXT"
cp -p "$GAME_DIR/README.md" "$STAGE/floppy/README.md"

FLOPPY_ZIP="$DIST/Entombed_Enhanced_v${VERSION}_Floppy.zip"
rm -f "$FLOPPY_ZIP"
(cd "$STAGE/floppy" && zip -q -9 -r "$FLOPPY_ZIP" .)

# 3. Standalone auto-booting 8 MB VHD zip (HDDRIVER + FAT16 BGM + DESKTOP.INF/NEWDESK.INF)
VHD_ZIP="$DIST/Entombed_Enhanced_v${VERSION}_VHD.zip"
rm -f "$VHD_ZIP"
python3 "$BENCH_DIR/tools/make_game_vhds.py" entombed

echo "Packaged Entombed v${VERSION}:"
ls -lh "$HD_ZIP" "$FLOPPY_ST" "$FLOPPY_ZIP" "$VHD_ZIP"
