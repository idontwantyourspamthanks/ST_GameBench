cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
F=work/fdb/fdb.py
A=work/fdb/build_db/disk_a.st; B=work/fdb/build_db/disk_b.st
python3 $F db_insB_ste $A $B insB --tos 1.62 --tail 40
python3 $F db_swapA_ste $A $B swapA --tos 1.62 --tail 40
python3 $F db_startB_ste $A $B startB --tos 1.62 --tail 40
python3 $F db_none_ste $A $B none --tos 1.62 --tail 60
python3 $F db_none_nob_ste $A $B none --tos 1.62 --tail 60 --nob
python3 $F db_swapA_nob_ste $A $B swapA --tos 1.62 --tail 40 --nob
python3 $F db_insB_ste4m $A $B insB --tos 1.62 --mem 4096 --tail 40
python3 $F db_swapA_ste4m $A $B swapA --tos 1.62 --mem 4096 --tail 40
python3 $F db_startB_ste4m $A $B startB --tos 1.62 --mem 4096 --tail 40
python3 $F db_insB_mste4m $A $B insB --machine megaste --tos 2.06 --mem 4096 --tail 40
python3 $F db_swapA_mste4m $A $B swapA --machine megaste --tos 2.06 --mem 4096 --tail 40
python3 $F db_startB_mste4m $A $B startB --machine megaste --tos 2.06 --mem 4096 --tail 40
python3 $F db_insB_st104 $A $B insB --machine st --tos 1.04 --tail 40
python3 $F db_swapA_st104 $A $B swapA --machine st --tos 1.04 --tail 40
python3 $F db_startB_st104 $A $B startB --machine st --tos 1.04 --tail 40
