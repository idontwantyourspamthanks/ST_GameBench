#!/usr/bin/env bash
# HAGA location / swap area / bank survival for other RAM sizes (one Hatari at a time).  Output /tmp/mw2tail/loc_*.out
R=/home/ryan/Code/AtariST/gamebench/games/done/midwinter2; cd $R
for c in "loc_ms4 megaste 206 4096" "loc_ms2 megaste 206 2048" "loc_ste2 ste 162 2048" "loc_ste1 ste 162 1024" "loc_ms1 megaste 206 1024" "loc_ste4 ste 162 4096"; do
  set -- $c; n=$1; shift
  echo "== $n $*"; timeout 900 python3 work/banktail/haga_loc.py $n "$@" > /tmp/mw2tail/$n.out 2>&1; grep "^$n" /tmp/mw2tail/$n.out; done
