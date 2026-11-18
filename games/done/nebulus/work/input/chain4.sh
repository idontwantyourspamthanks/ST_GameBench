cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
for cfg in "j1b_stock none" "j1b_jump jump" "j1b_stock2 none" "j1b_jumpshoot jumpshoot"; do set -- $cfg; python3 s3.py $1 $2 > sc_$1.out 2>&1; done
echo DONE > chain4.done
