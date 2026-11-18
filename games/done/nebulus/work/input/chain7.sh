cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
while [ ! -f chain6.done ]; do sleep 3; done
python3 s4.py j2_jump1 jump > sc_j2_jump1.out 2>&1
python3 run_en.py en_b_jump jump 10 none > en_b_jump.log 2>&1
python3 run_en.py en_f_jump jump 10 jump > en_f_jump.log 2>&1
python3 run_en.py en_b_stand stand 10 none > en_b_stand.log 2>&1
python3 run_en.py en_f_stand stand 10 shoot > en_f_stand.log 2>&1
echo DONE > chain7.done
