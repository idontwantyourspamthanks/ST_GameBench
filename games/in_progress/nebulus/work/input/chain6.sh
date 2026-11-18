cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
while [ ! -f chain5.done ]; do sleep 3; done
for cfg in "j1noen_stock none" "j1noen_jump jump" "j1noen_stock2 none"; do set -- $cfg; python3 s3.py $1 $2 > sc_$1.out 2>&1; done
echo DONE > chain6.done
