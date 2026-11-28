#!/usr/bin/env bash
# Launch Gods (STe Tier 2 Enhanced + Copylock Fixed) in Hatari.
# Usage: ./run.sh <ste|st|megaste|orig> [extra hatari args...]
# Controls: Space past Gamex screen, Arrow keys + Right Ctrl (Joystick 1), F12 = Hatari menu.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BENCH_DIR="$(cd "$GAME_DIR/../../.." && pwd)"
TOS_DIR="$BENCH_DIR/tos"

HATARI="${HATARI:-/home/ryan/Code/AtariST/hattari/build/src/hatari}"
if [[ ! -x "$HATARI" ]]; then
    HATARI="$(command -v hatari)"
fi

TARGET="${1:-ste}"
shift || true

VARIANT="patched"
MACHINE="$TARGET"
if [[ "$TARGET" == "orig" ]]; then
    VARIANT="orig"
    MACHINE="ste"
    GAME_SRC="$GAME_DIR/originals/GODS"
else
    python3 "$SCRIPT_DIR/godspatch.py" >/dev/null
    GAME_SRC="$GAME_DIR/build/game"
fi

mkdir -p "$GAME_DIR/build"
IMG="$GAME_DIR/build/play-$VARIANT.img"
python3 - "$SCRIPT_DIR" "$IMG" "$GAME_SRC" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from gods import build_hd
build_hd(sys.argv[2], game=Path(sys.argv[3]))
PY

COMMON=(
    --gemdos-drive skip
    --acsi "0=$IMG"
    --joy1 keys
    --sound 50066
    --confirm-quit no
)

case "$MACHINE" in
    ste)
        exec "$HATARI" --machine ste --memsize 1024 --cpuclock 8 --tos "$TOS_DIR/TOS_1_62.img" \
            --monitor rgb --fast-boot yes "${COMMON[@]}" "$@"
        ;;
    st)
        exec "$HATARI" --machine st --memsize 1024 --cpuclock 8 --tos "$TOS_DIR/TOS_1_04.img" \
            --monitor rgb --fast-boot yes "${COMMON[@]}" "$@"
        ;;
    megaste)
        exec "$HATARI" --machine megaste --memsize 2048 --cpuclock 8 --tos "$TOS_DIR/TOS_2_06.img" \
            --monitor rgb --fast-boot no "${COMMON[@]}" "$@"
        ;;
    *)
        echo "Usage: $0 <ste|st|megaste|orig> [extra hatari args...]" >&2
        exit 1
        ;;
esac
