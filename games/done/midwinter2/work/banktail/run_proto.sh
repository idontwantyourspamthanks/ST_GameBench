#!/usr/bin/env bash
# Prototype of the proposed guard (work/notes/banktail.md section 7): a copy of tools/ + patches/ in /tmp/mw2tail/proto with the 'ASNE' end canary
# (asn_build.py appends it, blob.s asn_init0 checks it).  Build: see notes.  Cells: pr_ms (Mega STE 1 MB TOS 2.06), pr_ste (STE 1 MB TOS 1.62), pr_ms4 (Mega STE 4 MB)
R=/home/ryan/Code/AtariST/gamebench/games/done/midwinter2; cd $R
export BT_BANK=/tmp/mw2tail/proto/build/asn_bank.bin
G=/tmp/mw2tail/proto/build/game
run() { n=$1; shift; echo "== $n $*"; timeout 2400 python3 work/banktail/walk.py $n "$@" > /tmp/mw2tail/$n.out 2>&1; echo "exit $?"; }
case "$1" in
  pr_ms)  run pr_ms  megaste 206 1024 hd $G --to hall ;;
  pr_ste) run pr_ste ste     162 1024 hd $G --to hall ;;
  pr_ms4) run pr_ms4 megaste 206 4096 hd $G --to hall ;;
  *) echo "usage: run_proto.sh pr_ms|pr_ste|pr_ms4" ;;
esac
