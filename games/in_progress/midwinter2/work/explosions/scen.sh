#!/bin/bash
# usage: scen.sh TAG "args"   -> stock + display(fixed) in parallel, compare
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2
T=$1; shift; SNAP=${SNAP:-work/explosions/jeep_fired.sav}
rm -rf /tmp/ex/${T}_st /tmp/ex/${T}_fx
python3 work/explosions/expseq.py $SNAP stock /tmp/ex/${T}_st "$@" > /tmp/ex/${T}_st.log 2>&1 &
python3 work/explosions/expseq.py $SNAP display /tmp/ex/${T}_fx "$@" > /tmp/ex/${T}_fx.log 2>&1 &
wait
echo "== $T $*"; python3 work/explosions/cmpdirs.py /tmp/ex/${T}_st /tmp/ex/${T}_fx $N | tail -1
