#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
GAME="$ROOT/games/in_progress/seconds-out"
HATARI="${HATARI:-/home/ryan/Code/AtariST/hattari/build/src/hatari}"
[[ -x "$HATARI" ]] || HATARI="$(command -v hatari)"
exec "$HATARI" --machine ste --tos "$ROOT/tos/TOS_1_62.img" --memsize 1024 \
  --monitor rgb --fast-boot yes --sound 50066 --confirm-quit no \
  --harddrive "$GAME/dist/hd" --joy1 keys "$@" "$GAME/dist/hd/SECONDS.PRG"
