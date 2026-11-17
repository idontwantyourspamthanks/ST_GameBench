#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/mxfast
SC=("start zig 150 1" "start zig 150 3" "start zig 100 130" "up up 150 2" "L0 rand 150 2" "L1 rand 150 2" "L2 rand 150 2" "L3 left 200 2" "L3 rand 200 3" "L4 rand 150 2" "L5 zig 150 2" "L6 rand 150 2" "L7 right 150 2" "L8 rand 150 2" "L9 rand 150 2" "L10 left 200 2" "L10 rand 200 2" "L11 rand 150 2" "L12 hard 200 2" "L13 rand 150 2" "L14 rand 200 3")
for c in M G; do
  for a in "${SC[@]}"; do python3 cmpmx.py $a X $c 2>&1 | grep -v "^  extras"; done > res/emu_X_vs_$c.final.txt
done
for c in M G; do
  for a in "start zig 120 2" "up up 120 2" "L3 left 120 2" "L5 rand 120 3" "L10 rand 120 2" "L12 rand 120 2" "L14 zig 120 2"; do python3 pixmain.py $c $a 2>&1; done > res/pixmain_$c.txt
done
echo DONE > res/emu_final.done
