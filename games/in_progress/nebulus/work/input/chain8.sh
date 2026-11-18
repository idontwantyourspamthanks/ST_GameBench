cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
while [ ! -f chain7.done ]; do sleep 3; done
python3 realpulse.py build/both rp_both 20 10 > rp_both.log 2>&1
python3 realpulse.py build/nolatch rp_nolatch 20 10 > rp_nolatch.log 2>&1
python3 gate_boot.py build/both ste 5 > gate2_both_ste.log 2>&1
python3 gate_boot.py build/bad ste 6 > gate2_bad_ste.log 2>&1
python3 holdfire.py build/nolatch nolatch > hold_nolatch.log 2>&1
python3 holdfire.py build/both both > hold_both.log 2>&1
python3 gate_boot.py build/both megaste 7 > gate2_both_mste.log 2>&1
python3 gate_boot.py build/bad megaste 8 > gate2_bad_mste.log 2>&1
echo DONE > chain8.done
