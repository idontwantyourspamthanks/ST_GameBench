#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2
python3 work/fire/from_map.py ste14 build/MW2Fire ste 1024 446 177 jeep > work/fire/c_ste14_jeep.log 2>&1
python3 work/fire/from_map.py tt14 build/MW2Fire tt 4096 446 177 jeep > work/fire/c_tt14_jeep.log 2>&1
python3 work/fire/cold_fire.py ms0 build/MW2FireStock megaste 4096 > work/fire/c_ms0.log 2>&1
python3 work/fire/from_map.py ms0 build/MW2FireStock megaste 4096 446 177 jeep > work/fire/c_ms0_jeep.log 2>&1
python3 work/fire/cold_fire.py tt0 build/MW2FireStock tt 4096 > work/fire/c_tt0.log 2>&1
python3 work/fire/from_map.py tt0 build/MW2FireStock tt 4096 446 177 jeep > work/fire/c_tt0_jeep.log 2>&1
echo done > work/fire/c_all.done
