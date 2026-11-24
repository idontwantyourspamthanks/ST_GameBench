cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
F=work/fdb/fdb.py; B=work/fdb/build_def2; O=work/fdb/out
python3 tools/msrfloppy.py gate /tmp/msr_lone2/disk_a.st --disk-b $B/disk_b.st --machine ste --mem 1024 --tos 1.62 --name fdb2_lone_ste_1024 > $O/f_msrfloppy_gate_lone_ste_1024.out 2>&1
python3 $F f_insB_ste_drive $B/disk_a.st $B/disk_b.st insB --tos 1.62 --tail 30 --vars bb52e --drive > $O/f_insB_ste_drive.out 2>&1
python3 $F f_startB_ste_drive $B/disk_a.st $B/disk_b.st startB --tos 1.62 --tail 30 --vars bb52e --drive > $O/f_startB_ste_drive.out 2>&1
python3 $F f_swapA_ste $B/disk_a.st $B/disk_b.st swapA --tos 1.62 --tail 30 --vars bb52e > $O/f_swapA_ste.out 2>&1
python3 $F f_swapA_nob_ste $B/disk_a.st $B/disk_b.st swapA --tos 1.62 --tail 30 --nob --vars bb52e > $O/f_swapA_nob_ste.out 2>&1
python3 $F f_wrongB_ste $B/disk_a.st $B/disk_b.st wrongB --tos 1.62 --tail 30 --vars bb52e > $O/f_wrongB_ste.out 2>&1
python3 $F f_insB_ste4m $B/disk_a.st $B/disk_b.st insB --tos 1.62 --mem 4096 --tail 30 --vars bb52e > $O/f_insB_ste4m.out 2>&1
for t in insB startB swapA; do
python3 $F f_${t}_mste4m $B/disk_a.st $B/disk_b.st $t --machine megaste --tos 2.06 --mem 4096 --tail 30 --vars bb52e > $O/f_${t}_mste4m.out 2>&1
python3 $F f_${t}_st104 $B/disk_a.st $B/disk_b.st $t --machine st --tos 1.04 --tail 30 --vars bb52e > $O/f_${t}_st104.out 2>&1
done
