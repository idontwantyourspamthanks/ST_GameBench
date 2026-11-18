cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
python3 gate_boot.py build/both megaste 3 > gate_both_mste.log 2>&1
python3 gate_boot.py build/bad megaste 4 > gate_bad_mste.log 2>&1
echo DONE > chain3.done
