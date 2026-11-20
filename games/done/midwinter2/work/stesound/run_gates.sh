#!/usr/bin/env bash
# Phase 2 gate matrix, sound ON (--sound 50066) + PSG trace (psgcheck.py: reg 7 bit 6 = port A direction) on every gate.  One Hatari at a time.
#   run_gates.sh DISKDIR PREFIX [a|c|b|all]
cd "$(dirname "$0")"
D=$1; P=$2; WHAT=${3:-all}
export MW2S_SOUND=${MW2S_SOUND:-50066} MW2S_EXTRA="--trace fdc,psg_write"
OUT=out; mkdir -p $OUT
runa() { n=$1; shift; timeout 800 python3 bootgate.py "$n" "$@" > $OUT/$n.log 2>&1; grep -E "^(GATE|PSGCHECK|VERDICT)|FRAMES" $OUT/$n.log; rm -rf /tmp/mw2s/$n; }
runc() { n=$1; shift; timeout 900 python3 swapgate.py "$n" "$@" > $OUT/$n.log 2>&1; grep -E "SWAP|PSGCHECK|RAMCHECK|FRAMES" $OUT/$n.log; rm -rf /tmp/mw2s/$n; }
runb() { n=$1; shift; timeout 1800 python3 cell16.py "$n" "$@" > $OUT/$n.log 2>&1; grep -E "^(CELL|EXC|PSGCHECK|RAMCHECK)|FRAMES|first game restore|game type I commands" $OUT/$n.log | cut -c1-240; rm -rf /tmp/mw2s/$n; }
if [[ $WHAT == n || $WHAT == all ]]; then      # fix-invariant gate: candidate must PASS, the shipped v1.6 (negative control) must FAIL; STE and Mega STE, boot + first check + FFB swap
runc ${P}_n_ste_fix     ste     162 8  1 $D B
runc ${P}_n_mste_fix    megaste 206 8  1 $D B
runc ${P}_n_mste16_fix  megaste 206 16 1 $D B
MW2S_EXPECT_3392C=103c00c0 runc ${P}_n_ste_v16    ste     162 8  1 /tmp/mw2s/ship B
MW2S_EXPECT_3392C=103c00c0 runc ${P}_n_mste_v16   megaste 206 8  1 /tmp/mw2s/ship B
fi
if [[ $WHAT == a || $WHAT == all ]]; then
runa ${P}_a_ste8   ste 8 $D --expect pass
runa ${P}_a_mste8  megaste 8 $D --expect pass
runa ${P}_a_mste16 megaste 16 $D --expect pass
fi
if [[ $WHAT == c || $WHAT == all ]]; then
runc ${P}_c_ste_d1  ste 162 8 1  $D A B
runc ${P}_c_ste_d1c ste 162 8 1  $D C CB
runc ${P}_c_ste_d2  ste 162 8 2  $D A B
runc ${P}_c_ste_d2f ste 162 8 2f $D D
fi
if [[ $WHAT == b || $WHAT == all ]]; then
runb ${P}_b_ste162_8_d2    ste     162 1024 $D 8  2 --soak 120
runb ${P}_b_ste162_8_d1    ste     162 1024 $D 8  1
runb ${P}_b_mste206_8_d1   megaste 206 1024 $D 8  1
runb ${P}_b_mste206_16_d1  megaste 206 1024 $D 16 1 --soak 120
runb ${P}_b_mste206_16_d2  megaste 206 1024 $D 16 2
runb ${P}_b_st104_8_d1     st      104 1024 $D 8  1
runb ${P}_b_tt306_d1       tt      306 4096 $D 8  1
fi
