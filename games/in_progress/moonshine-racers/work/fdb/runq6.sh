cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
F=work/fdb/fdb.py
V2=work/fdb/build_v2
python3 $F v2_empty_ste $V2/disk_a.st $V2/disk_b.st swapA --tos 1.62 --presses 3 --tail 30 --vars bb52e > work/fdb/out/v2_empty_ste.out 2>&1
python3 $F v2_nob_ste $V2/disk_a.st $V2/disk_b.st swapA --tos 1.62 --presses 3 --tail 30 --nob --vars bb52e > work/fdb/out/v2_nob_ste.out 2>&1
python3 $F v2_insB_ste $V2/disk_a.st $V2/disk_b.st insB --tos 1.62 --tail 30 --vars bb52e > work/fdb/out/v2_insB_ste.out 2>&1
python3 $F v2_startB_ste $V2/disk_a.st $V2/disk_b.st startB --tos 1.62 --tail 30 --vars bb52e > work/fdb/out/v2_startB_ste.out 2>&1
