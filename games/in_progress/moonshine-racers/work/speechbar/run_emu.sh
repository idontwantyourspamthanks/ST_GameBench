#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
R=work/speechbar/res; V=work/speechbar/live
ALL=0,1,2,3,4,5,6,7,8,9,10,11,12,13,14
python3 work/speechbar/gate_emu_sb.py $V/F $V/S $ALL up,zig 200 res=$R/emu_main.json > $R/emu_main.txt 2>&1
python3 work/speechbar/gate_emu_sb.py $V/X $V/XS $ALL up,zig 200 xtest=3 res=$R/emu_x3.json > $R/emu_x3.txt 2>&1
python3 work/speechbar/gate_emu_sb.py $V/F $V/S 0,5 up,zig 120 poke=b6306=7e1a > $R/emu_neg_tall.txt 2>&1
python3 work/speechbar/gate_emu_sb.py $V/F $V/S 0,5 up,zig 120 poke=b6074=4e714e71 > $R/emu_neg_nowipe.txt 2>&1
python3 work/speechbar/gate_emu_sb.py $V/X $V/XS 0,5 up,zig 120 xtest=3 poke=b6074=4e714e71 > $R/emu_x3_neg_nowipe.txt 2>&1
# race_grid / race_up dumps (standing time-out state, race_up)
python3 work/speechbar/gate_emu_sb.py $V/F $V/S 0 up,zig 300 dumps=/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/speechbar/dumps/G%d.bin > $R/emu_grid.txt 2>&1
python3 work/speechbar/gate_emu_sb.py $V/F $V/S 0 up,zig 300 dumps=/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/speechbar/dumps/U%d.bin > $R/emu_up.txt 2>&1
echo DONE > $R/emu.done
