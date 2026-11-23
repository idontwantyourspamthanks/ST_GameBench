cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
while [ ! -f chain13.done ]; do sleep 3; done
for cfg in "k4 k4_stock none" "k4 k4_stock2 none" "k4 k4_shoot shoot" "k5 k5_stock none" "k5 k5_shoot shoot"; do set -- $cfg; python3 s6.py $1 $2 $3 > sc_$2.out 2>&1; done
echo DONE > chain14.done
