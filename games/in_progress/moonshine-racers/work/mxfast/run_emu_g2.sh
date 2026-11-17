#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/mxfast
SC=("start zig 150 1" "start zig 150 3" "start zig 100 130" "up up 150 2" "L0 rand 150 2" "L1 rand 150 2" "L2 rand 150 2" "L3 left 200 2" "L3 rand 200 3" "L4 rand 150 2" "L5 zig 150 2" "L6 rand 150 2" "L7 right 150 2" "L8 rand 150 2" "L9 rand 150 2" "L10 left 200 2" "L10 rand 200 2" "L11 rand 150 2" "L12 hard 200 2" "L13 rand 150 2" "L14 rand 200 3")
for a in "${SC[@]}"; do python3 cmpmx.py $a X G 2>&1 | grep -v "^  extras\|^  runs"; done > res/emu_X_vs_G.final3.txt
echo DONE > res/emu_g3.done
