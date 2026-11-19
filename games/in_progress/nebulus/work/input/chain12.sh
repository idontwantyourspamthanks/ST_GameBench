cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
python3 realpulse2.py build/both rp4_both 0 12 > rp4_both.log 2>&1
python3 realpulse2.py build/nolatch rp4_nolatch 0 12 > rp4_nolatch.log 2>&1
python3 gate_boot.py build/both ste 11 > gate3_both_ste.log 2>&1
python3 gate_boot.py build/bad ste 12 > gate3_bad_ste.log 2>&1
python3 gate_boot.py build/default ste 13 > gate3_default_ste.log 2>&1
python3 gate_boot.py build/both megaste 14 > gate3_both_mste.log 2>&1
python3 gate_boot.py build/bad megaste 15 > gate3_bad_mste.log 2>&1
echo DONE > chain12.done
