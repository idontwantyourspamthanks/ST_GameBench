#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
GAME="$ROOT/games/in_progress/seconds-out"
HATARI="${HATARI:-/home/ryan/Code/AtariST/hattari/build/src/hatari}"
[[ -x "$HATARI" ]] || HATARI="$(command -v hatari)"
exec "$HATARI" --machine ste --tos "$ROOT/tos/TOS_1_62.img" --memsize 1024 \
  --monitor rgb --fast-boot yes --fastfdc yes --sound 50066 --confirm-quit no \
  --disk-a "$GAME/dist/SecondsOut_Enhanced_v1.1.st" --joy1 keys "$@"
