cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
while [ ! -f chain9.done ]; do sleep 3; done
python3 realpulse2.py build/nolatch rp2_nolatch 0 14 > rp2_nolatch.log 2>&1
python3 realpulse2.py build/both rp2_both 0 14 > rp2_both.log 2>&1
echo DONE > chain10.done
