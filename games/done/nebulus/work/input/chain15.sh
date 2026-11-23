cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input
while [ ! -f chain14.done ]; do sleep 3; done
python3 s3.py j1b_all all > sc_j1b_all.out 2>&1
python3 s5.py k1 k1_all all > sc_k1_all.out 2>&1
python3 gate_boot.py build/defshoot ste 21 > gate4_defshoot_ste.log 2>&1
python3 gate_boot.py build/defshootbad ste 22 > gate4_defshootbad_ste.log 2>&1
python3 gate_boot.py build/defshoot megaste 23 > gate4_defshoot_mste.log 2>&1
python3 gate_boot.py build/defshootbad megaste 24 > gate4_defshootbad_mste.log 2>&1
python3 realpulse2.py build/defshoot rp6_defshoot 0 8 > rp6_defshoot.log 2>&1
echo DONE > chain15.done
