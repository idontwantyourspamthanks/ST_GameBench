#!/usr/bin/env bash
# HAGA swap-area record on 2 MB / 4 MB Mega STE (haga_loc.py after the offset fix).  Output /tmp/mw2tail/loc2_*.out
R=/home/ryan/Code/AtariST/gamebench/games/done/midwinter2; cd $R
for c in "loc2_ms2 megaste 206 2048" "loc2_ms4 megaste 206 4096" "loc2_ms1 megaste 206 1024" "loc2_ste1 ste 162 1024"; do
  set -- $c; n=$1; shift
  echo "== $n $*"; timeout 900 python3 work/banktail/haga_loc.py $n "$@" > /tmp/mw2tail/$n.out 2>&1; grep "^$n" /tmp/mw2tail/$n.out; done
