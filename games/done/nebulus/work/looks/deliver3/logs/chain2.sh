#!/bin/bash
export HOME=/tmp/nld/home PYTHONUNBUFFERED=1
while [ ! -f /tmp/nld/x/logs/chain1.st.done ]; do sleep 10; done
cd /tmp/nld/games/in_progress/nebulus/work/editor
X=/tmp/nld/x; L=$X/logs; B=$X/b_new
SE=446f6f72202b206f70706f73697465
ONLY=STUCK python3 e203_study2.py $X/b_base $X/study2s_ste ste $X/title_ste_base.sav > $L/study2_stuck_ste.log 2>&1
python3 e150.py $B $X/g150b_ste ste > $L/e150b_ste.log 2>&1
SNAP_EXPECT=$SE python3 e180.py $B $X/g180_mste megaste $X/ne/odd/odd2.ovl $X/ne/odd/stress05.ovl --snap $X/title_megaste_new.sav --quick > $L/e180_megaste.log 2>&1
python3 e150.py $B $X/g150_mste megaste > $L/e150_megaste.log 2>&1
echo done > $L/chain2.done
