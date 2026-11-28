#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
GAME="$ROOT/games/done/seconds-out"
HATARI="${HATARI:-/home/ryan/Code/AtariST/hattari/build/src/hatari}"
[[ -x "$HATARI" ]] || HATARI="$(command -v hatari)"
exec "$HATARI" --machine megaste --cpuclock 16 --tos "$ROOT/tos/TOS_2_06.img" --memsize 2048 \
  --monitor rgb --fast-boot no --sound 50066 --confirm-quit no \
  --harddrive "$GAME/dist/hd" --joy1 keys "$@" "$GAME/dist/hd/SECONDS.PRG"
