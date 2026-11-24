#!/usr/bin/env bash
# Launch Overlander floppy image in Hatari/Hattari.
# Usage: ./run_floppy.sh <st|ste|megaste|tt|falcon> [extra hatari args...]
# Set OVERLANDER_IMG=/path/to/image.st to override the default image.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BENCH_DIR="$(cd "$GAME_DIR/../../.." && pwd)"
TOS_DIR="$BENCH_DIR/tos"
HATARI="${HATARI:-/home/ryan/Code/AtariST/hattari/build/src/hatari}"
if [[ ! -x "$HATARI" ]]; then
    HATARI="$(command -v hatari)"
fi

MACHINE="${1:-ste}"
shift || true

TMPDIR_IMG=""
cleanup() {
    if [[ -n "$TMPDIR_IMG" ]]; then
        rm -rf "$TMPDIR_IMG"
    fi
}
trap cleanup EXIT

LATEST_ZIP="$(ls -1v "$GAME_DIR"/dist/Overlander_floppy_*.zip 2>/dev/null | tail -n 1 || true)"
if [[ -n "${OVERLANDER_IMG:-}" ]]; then
    IMG="$OVERLANDER_IMG"
elif [[ -n "$LATEST_ZIP" && -f "$LATEST_ZIP" ]]; then
    TMPDIR_IMG="$(mktemp -d /tmp/overlander_run.XXXXXX)"
    unzip -q -o "$LATEST_ZIP" '*.st' -d "$TMPDIR_IMG"
    IMG="$(ls "$TMPDIR_IMG"/*.st | head -n 1)"
elif [[ -f "$GAME_DIR/work/extracted/overlander.stx" ]]; then
    IMG="$GAME_DIR/work/extracted/overlander.stx"
elif [[ -f "$GAME_DIR/originals/overlander_elite.zip" ]]; then
    TMPDIR_IMG="$(mktemp -d /tmp/overlander_run.XXXXXX)"
    unzip -q -o "$GAME_DIR/originals/overlander_elite.zip" '*.stx' -d "$TMPDIR_IMG"
    IMG="$(ls "$TMPDIR_IMG"/*.stx | head -n 1)"
else
    echo "Missing Overlander floppy image in $GAME_DIR" >&2
    exit 1
fi

FASTFDC="yes"
if [[ "$IMG" == *.stx ]]; then
    FASTFDC="no"
fi

COMMON=(
    --disk-a "$IMG"
    --fastfdc "$FASTFDC"
    --joy1 keys
    --sound 50066
    --confirm-quit no
)

case "$MACHINE" in
    st)
        "$HATARI" --machine st --memsize 1024 --tos "$TOS_DIR/TOS_1_04.img" \
            --monitor rgb --fast-boot yes "${COMMON[@]}" "$@"
        ;;
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
        echo "Usage: $0 <st|ste|megaste|tt|falcon> [extra hatari args...]" >&2
        exit 1
        ;;
esac
