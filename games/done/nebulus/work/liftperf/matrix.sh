#!/bin/bash
# STE 1 MB: baseline (default patched set) vs +np_lift (live pokes), END=24
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/liftperf
run() { en=$1; t=$2; v=$3
    tag=m_${v}_t${t}_e${en}
    [ -f /tmp/lp/$tag.ana ] && return
    if [ $v = lift ]; then export LIVE=np_lift; else unset LIVE; fi
    PRE=0.2 python3 ride2.py /tmp/lp/ste_s_t$t.sav $tag 24 $en > /tmp/lp/$tag.out 2>&1
    python3 ana.py /tmp/lp/tr_$tag/log.txt | grep "state6\|^all" > /tmp/lp/$tag.ana
}
for t in 6 8 4 3 5 7 2 1; do for v in base lift; do run 1 $t $v; done; done
for t in 1 6 8; do for v in base lift; do run 0 $t $v; done; done
echo done > /tmp/lp/matrix.done
