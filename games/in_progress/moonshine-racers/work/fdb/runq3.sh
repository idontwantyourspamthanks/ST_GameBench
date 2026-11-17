cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
F=work/fdb/fdb.py
A=work/fdb/build_db/disk_a.st; B=work/fdb/build_db/disk_b.st
python3 $F db_startB_ste $A $B startB --tos 1.62 --tail 40 --vars b8e9e
python3 $F db_insB_ste_v $A $B insB --tos 1.62 --tail 40 --vars b8e9e
python3 $F db_swapA_ste_v $A $B swapA --tos 1.62 --tail 40 --vars b8e9e
python3 $F db_wrongB_ste $A $B wrongB --tos 1.62 --tail 40 --vars b8e9e
python3 $F db_none_ste_v $A $B none --tos 1.62 --tail 60 --vars b8e9e
python3 $F our_none_ste work/fdb/build/disk_a.st work/fdb/build/disk_b.st none --tos 1.62 --tail 60
