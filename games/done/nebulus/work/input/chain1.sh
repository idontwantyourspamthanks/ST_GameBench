cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
python3 run3.py f8_jump jump 10 8 deadloop > chain1.log 2>&1
python3 run3.py b16_jump jump 8 16 none >> chain1.log 2>&1
python3 run3.py f16_jump jump 8 16 deadloop >> chain1.log 2>&1
python3 run3.py f8_walk walk 8 8 deadloop >> chain1.log 2>&1
python3 run3.py b8_walk walk 8 8 none >> chain1.log 2>&1
python3 run3.py f8_stand stand 8 8 deadloop >> chain1.log 2>&1
python3 run3.py b8_stand stand 8 8 none >> chain1.log 2>&1
echo DONE >> chain1.log
