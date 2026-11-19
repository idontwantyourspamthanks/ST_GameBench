#!/bin/bash
# usage: dbgbuild.sh OUTGAMEDIR [SOURCE.s]   private build (default source patches/ed_editor.s) into OUTGAMEDIR; patches dir /tmp/ne/dbgpatches
set -e
G=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
P=/tmp/ne/dbgpatches; rm -rf $P; mkdir -p $P
cp $G/patches/*.nep $P/
python3 $G/work/editor/gen_ed.py "${2:-$G/patches/ed_editor.s}" $P/ed_overlay.nep
NEP_PATCHES=$P python3 $G/work/editor/nepatch_priv.py build --out "$1" | tail -1
