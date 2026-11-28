#!/usr/bin/env bash
# Launch Entombed (STe Enhanced) in Hatari.
# Usage: ./run.sh <ste|megaste|orig> [extra hatari args...]
# Controls: Arrow keys + Right Ctrl (Joystick 1), H = toggle 50/60 Hz, P = pause, 0-9 = hourglass delay.
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

OVERLAY_DIR="$GAME_DIR/work/disk_overlay"
ORIG_DIR="$GAME_DIR/work/extracted/disk/SIDE_2/ENTOMBED"

if [[ "$MACHINE" == "orig" ]]; then
    if [[ ! -f "$ORIG_DIR/ENTOMBED.PRG" ]]; then
        python3 "$SCRIPT_DIR/unpack_entombed.py" >/dev/null
    fi
    DRIVE="$ORIG_DIR"
    MACHINE="ste"
else
    if [[ ! -f "$OVERLAY_DIR/ENTOMBED.PRG" ]]; then
        python3 "$SCRIPT_DIR/build_entombed.py"
    fi
    DRIVE="$OVERLAY_DIR"
fi

COMMON=(
    --harddrive "$DRIVE"
    --auto 'C:\ENTOMBED.PRG'
    --joy1 keys
    --sound 50066
    --confirm-quit no
)

case "$MACHINE" in
    ste)
        exec "$HATARI" --machine ste --memsize 1024 --cpuclock 8 --tos "$TOS_DIR/TOS_1_62.img" \
            --monitor rgb --fast-boot yes "${COMMON[@]}" "$@"
        ;;
    megaste)
        exec "$HATARI" --machine megaste --memsize 2048 --cpuclock 16 --tos "$TOS_DIR/TOS_2_06.img" \
            --monitor rgb --fast-boot no "${COMMON[@]}" "$@"
        ;;
    *)
        echo "Usage: $0 <ste|megaste|orig> [extra hatari args...]" >&2
        exit 1
        ;;
esac
