cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
for cfg in "j2_stock none" "j2_jump jump"; do set -- $cfg; python3 s4.py $1 $2 > sc_$1.out 2>&1; done
echo DONE > chain5.done
