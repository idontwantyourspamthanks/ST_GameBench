cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
for cfg in "k1 k1_stock none" "k1 k1_stock2 none" "k1 k1_shoot shoot" "k1 k1_turn turn" "k1 k1n_stock none noen" "k1 k1n_shoot shoot noen" "k1 k1n_turn turn noen" "k2 k2n_stock none noen" "k2 k2n_shoot shoot noen" "k3 k3_stock none" "k3 k3_jump jump"; do set -- $cfg; python3 s5.py $1 $2 $3 $4 > sc_$2.out 2>&1; done
echo DONE > chain13.done
