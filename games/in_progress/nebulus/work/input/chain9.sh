cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
while [ ! -f chain8.done ]; do sleep 3; done
python3 run_en.py en_b_turn turn 8 none > en_b_turn.log 2>&1
python3 run_en.py en_f_turn turn 8 turn > en_f_turn.log 2>&1
echo DONE > chain9.done
