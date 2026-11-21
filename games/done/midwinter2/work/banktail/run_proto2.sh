#!/usr/bin/env bash
# Prototype guard, sound check: the Mega STE 1 MB run with the YM audible at the intro (rms per second of the capture) and the DMA off; STE 1 MB for comparison (DMA on).
R=/home/ryan/Code/AtariST/gamebench/games/done/midwinter2; cd $R
export BT_BANK=/tmp/mw2tail/proto/build/asn_bank.bin
G=/tmp/mw2tail/proto/build/game
run() { n=$1; shift; echo "== $n $*"; timeout 2400 python3 work/banktail/walk.py $n "$@" > /tmp/mw2tail/$n.out 2>&1; echo "exit $?"; }
run pr_ms_w  megaste 206 1024 hd $G --to logo --intro 25 --wav 15
run pr_ste_w ste     162 1024 hd $G --to logo --intro 25 --wav 15
