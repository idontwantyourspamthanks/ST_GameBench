#!/usr/bin/env bash
# Launch Flood v1.0 auto-booting 720 KB floppy image in Hatari.
# Usage: ./run_floppy.sh <ste|megaste|tt|falcon> [extra hatari args...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLOOD_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BENCH_DIR="$(cd "$FLOOD_DIR/../../.." && pwd)"
TOS_DIR="$BENCH_DIR/tos"
ZIP="$FLOOD_DIR/dist/Flood_floppy_v1.0.zip"
HATARI="${HATARI:-/home/ryan/Code/AtariST/hattari/build/src/hatari}"
if [[ ! -x "$HATARI" ]]; then
    HATARI="$(command -v hatari)"
fi

if [[ ! -f "$ZIP" ]]; then
    echo "Missing $ZIP — run: python3 $SCRIPT_DIR/package_flood.py --version v1.0" >&2
    exit 1
fi

MACHINE="${1:-ste}"
shift || true

TMPDIR_IMG="$(mktemp -d /tmp/flood_run.XXXXXX)"
trap 'rm -rf "$TMPDIR_IMG"' EXIT
unzip -q -o "$ZIP" '*.st' -d "$TMPDIR_IMG"
IMG="$(ls "$TMPDIR_IMG"/*.st | head -n 1)"

COMMON=(
    --disk-a "$IMG"
    --fastfdc yes
    --joy1 keys
    --sound 50066
    --confirm-quit no
)

case "$MACHINE" in
    ste)
        "$HATARI" --machine ste --memsize 1024 --tos "$TOS_DIR/TOS_1_62.img" \
            --monitor rgb --fast-boot yes "${COMMON[@]}" "$@"
        ;;
    megaste)
        "$HATARI" --machine megaste --memsize 2048 --cpuclock 16 --tos "$TOS_DIR/TOS_2_06.img" \
            --monitor rgb --fast-boot no "${COMMON[@]}" "$@"
        ;;
    tt)
        "$HATARI" --machine tt --memsize 4096 --tos "$TOS_DIR/TOS_3_06_uk.img" \
            --monitor vga --fast-boot yes "${COMMON[@]}" "$@"
        ;;
    falcon)
        "$HATARI" --machine falcon --memsize 4096 --tos "$TOS_DIR/TOS_4_04.img" \
            --monitor rgb --fast-boot yes "${COMMON[@]}" "$@"
        ;;
    *)
        echo "Usage: $0 <ste|megaste|tt|falcon> [extra hatari args...]" >&2
        exit 1
        ;;
esac
