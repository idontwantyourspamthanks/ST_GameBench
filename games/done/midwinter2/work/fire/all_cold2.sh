#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2
while [ ! -f work/fire/c_all.done ]; do sleep 10; done
python3 work/fire/cold_fire.py ste14fix build/MW2FireFix ste 1024 > work/fire/c_ste14fix.log 2>&1
python3 work/fire/from_map.py ste14fix build/MW2FireFix ste 1024 446 177 jeep > work/fire/c_ste14fix_jeep.log 2>&1
python3 work/fire/cold_fire.py tt14fix build/MW2FireFix tt 4096 > work/fire/c_tt14fix.log 2>&1
python3 work/fire/from_map.py tt14fix build/MW2FireFix tt 4096 446 177 jeep > work/fire/c_tt14fix_jeep.log 2>&1
echo done > work/fire/c_all2.done
