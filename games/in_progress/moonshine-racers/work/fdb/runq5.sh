cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
F=work/fdb/fdb.py
A=work/fdb/build_def/disk_a.st; B=work/fdb/build_def/disk_b.st
python3 tools/msrfloppy.py gate $A --disk-b $B --machine ste --mem 1024 --tos 1.62 --name fdb_ste_1024 > work/fdb/out/def_msrfloppy_gate_ste_1024.out 2>&1
python3 $F def_insB_mste4m $A $B insB --machine megaste --tos 2.06 --mem 4096 --tail 30 --vars b8e9e --drive
python3 $F def_startB_st104 $A $B startB --machine st --tos 1.04 --tail 30 --vars b8e9e --drive
