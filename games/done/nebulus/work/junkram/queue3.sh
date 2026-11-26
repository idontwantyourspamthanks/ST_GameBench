#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus
J=$PWD/work/junkram
while [ ! -f $J/queue2.done ]; do sleep 5; done
cd work/editor
python3 e170.py $J/build/after /tmp/strun-jr-g170s ste > $J/gates/e170_ste.log 2>&1
python3 ../junkram/gates/e91_jr.py > $J/gates/e91.log 2>&1
python3 e150.py $J/build/after /tmp/strun-jr-g150 ste > $J/gates/e150_ste.log 2>&1
python3 e161.py $J/build/after /tmp/strun-jr-g161s ste > $J/gates/e161_ste.log 2>&1
python3 e170.py $J/build/after /tmp/strun-jr-g170m megaste > $J/gates/e170_megaste.log 2>&1
python3 e161.py $J/build/after /tmp/strun-jr-g161m megaste skipfuzz > $J/gates/e161_megaste.log 2>&1
echo done > $J/queue3.done
