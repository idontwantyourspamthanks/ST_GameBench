#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor
while ! grep -q ALLDONE ../gate_NebOddGateEd/logs/chain.out; do sleep 10; done
B=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateEd/build
for m in ste megaste; do timeout 1500 python3 e180.py $B /tmp/ne/oge_wx_$m $m /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/dist/example/NEBLEVEL.OVL --disk --quick --snap /tmp/ne/oge_snap_$m.sav > ../gate_NebOddGateEd/logs/e180_example_disk_$m.log 2>&1; done
echo EXDONE >> ../gate_NebOddGateEd/logs/chain.out
