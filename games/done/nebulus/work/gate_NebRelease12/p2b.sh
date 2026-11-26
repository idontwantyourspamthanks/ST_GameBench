#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus; L=work/gate_NebRelease12/logs; B=/tmp/r12; R=$B/r; export PYTHONUNBUFFERED=1
FG=$B/s/fl/NEBULUS_floppy/Nebulus_game_disk.st; O=/tmp/looksgate/ne/odd; GC=work/gate_NebOddGateCore; GF=work/gate_NebFloppyEject
rl(){ python3 work/looks/run_look.py "$@"; }
step(){ echo "== $1 $(date +%T)" >> $L/p2b_steps.txt; }
md5sum $FG > $L/fl_game_md5.txt
step all12_look; rl $B/hd_all12 $R/all12_ste 12 camp ste > $L/hd_all12_look_ste.log 2>&1; python3 work/looks/check_all12.py $R/base8_ste $R/all12_ste > $L/hd_check_all12_ste.txt 2>&1
step eyes5; NOE=1 DELAY=2 rl $B/hd_eyes5 $R/eyes5_ste 5 camp ste > $L/hd_eyes5_ste.log 2>&1
step negctl; rl $B/old_looks15 $R/neg_looks15_ste 15 camp ste > $L/neg_looks15_ste.log 2>&1; python3 work/looks/check_look.py $R/base8_ste $R/neg_looks15_ste looks15 > $L/neg_check_ste.txt 2>&1
for i in 3 4 5; do step noise$i; rl $B/b_old $R/stock_old$i 8 stock ste > $L/noise_old$i.log 2>&1; done
for p in "3 4 5 3" "4 5 3 4" "3 5 4 3"; do set -- $p; python3 work/looks/check_noise.py $R old$1 old$2 old$3 old$4 8 > $L/noise_cmp_$1$2$3.txt 2>&1; done
step fgate_ste; python3 work/floppy/fgate.py $FG $B/fg_ste ste 1024 1.62 patched > $L/fl_fgate_ste.txt 2>&1
step fgate_mste; python3 work/floppy/fgate.py $FG $B/fg_mste megaste 4096 2.06 patched > $L/fl_fgate_mste.txt 2>&1
step fl_ui_ste; python3 work/floppy/fl_ui.py $FG $B/flui_ste $R/base8_ste ste > $L/fl_ui_ste.log 2>&1
step fl_ui_mste; python3 work/floppy/fl_ui.py $FG $B/flui_mste $R/base8_megaste megaste > $L/fl_ui_mste.log 2>&1
step fo180_ste; python3 $GC/fo180.py $FG $B/fo_ste ste $O/odd2.ovl $O/looks.ovl $O/stress05.ovl $O/stress01.ovl --quick > $L/fl_fo_ste.txt 2>&1
step fo180_mste; python3 $GC/fo180.py $FG $B/fo_mste megaste $O/odd2.ovl $O/looks.ovl --quick > $L/fl_fo_mste.txt 2>&1
step fge_ste; python3 $GC/fge.py $FG $B/fge_ste ste fuzzsubset > $L/fl_fge_ste.txt 2>&1
step fl_look; python3 work/floppy/fl_look.py $FG $B/fllook /tmp/looksgate/fx/looks15.ovl $R/base8_ste 0,4,9,12 > $L/fl_look_ste.log 2>&1
step f161_fuzz; python3 $GC/f161_nfe.py $FG $B/f161_ste ste > $L/fl_f161_fuzz_ste.txt 2>&1
echo done > $L/p2b.done
