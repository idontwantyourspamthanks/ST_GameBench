cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
python3 short.py s_base 14 8 base > chain2.log 2>&1
python3 short.py s_latch 14 8 latch >> chain2.log 2>&1
echo DONE >> chain2.log
