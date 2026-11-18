cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
python3 realpulse2.py build/nolatch rp3_nolatch 0 14 > rp3_nolatch.log 2>&1
python3 realpulse2.py build/both rp3_both 0 14 > rp3_both.log 2>&1
echo DONE > chain11.done
