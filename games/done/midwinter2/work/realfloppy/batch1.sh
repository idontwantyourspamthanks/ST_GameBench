cd /home/ryan/Code/AtariST/gamebench/games/done/midwinter2/work/realfloppy
python3 drive.py b_ste_eject ste v14 eject > b_ste_eject.out 2>&1
python3 drive.py b_ste_keyfirst ste v14 keyfirst > b_ste_keyfirst.out 2>&1
EXTRA="--cpuclock 16" DRIVEB=true python3 drive.py b_mste16_instant megaste v14 instant > b_mste16_instant.out 2>&1
python3 drive.py b_ste_orig_instant ste orig instant > b_ste_orig_instant.out 2>&1
