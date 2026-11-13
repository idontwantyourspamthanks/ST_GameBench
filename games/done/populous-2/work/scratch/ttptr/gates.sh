#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2
G=work/gates
python3 tools/p2abtest.py --only pop2_spr pop2_spr16 pop2_ptr_a pop2_ptr_b pop2_clamp pop2_tt_ptr --mhz 8 > $G/tt_ptr_abtest.txt 2>&1
echo "EXIT $?" >> $G/tt_ptr_abtest.txt
python3 tools/p2tick.py ab busy1 16 130 --extra pop2_tt_ptr > $G/tt_ptr_tickab_busy1.txt 2>&1
echo "EXIT $?" >> $G/tt_ptr_tickab_busy1.txt
python3 tools/p2abtest.py --only pop2_tt_ptr --poke 86fa0:02 --snapshot game_start --turns 60 --mhz 8 > $G/tt_ptr_abtest_neg.txt 2>&1
echo "EXIT $?" >> $G/tt_ptr_abtest_neg.txt
