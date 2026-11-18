cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
while [ ! -f chain15.done ]; do sleep 3; done
for cfg in "k4b k4b_stock none" "k4b k4b_shoot shoot"; do set -- $cfg; python3 s6.py $1 $2 $3 > sc_$2.out 2>&1; done
echo DONE > chain16.done
