#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
L=work/tint2/res/bus_log2.txt
DEF=$(python3 tools/msrpatch.py list | awk '$2=="yes" && $1 !~ /^pp_/ {print $1}' | tr '\n' ' ')
mk() { n=$1; shift; python3 tools/msrpatch.py build --floppy --out build/bus_$n --only "$@" >/dev/null 2>&1 || echo "BUILD FAIL $n" >> $L; }
run() { echo "== $1" >> $L; timeout 900 python3 work/tint2/bus.py build/bus_$1/disk_a.st build/bus_$1/disk_b.st ste 1024 1.62 $1 >> $L 2>&1; }
mk v2 $(echo $DEF | tr ' ' '\n' | grep -v -e '^tb_blit' | tr '\n' ' ')
mk v3 $(echo $DEF | tr ' ' '\n' | grep -v -e '^ta_nomouse$' -e '^ta_rb' | tr '\n' ' ')
mk v4 $(echo $DEF | tr ' ' '\n' | grep -v -e '^mg_' | tr '\n' ' ') mt_sync
mk v5 $(echo $DEF | tr ' ' '\n' | grep -v -e '^tb_car' | tr '\n' ' ')
run v2; run v3; run v4; run v5
echo "== HD" >> $L
echo "-- HD default" >> $L; timeout 900 python3 work/tint2/hdbus.py build/mfin_hd hd_default ste 1024 1.62 >> $L 2>&1
echo "-- HD stock (PP's unpatched release)" >> $L; timeout 900 python3 work/tint2/hdbus.py originals/MOONSHR hd_stock ste 1024 1.62 >> $L 2>&1
echo "== HD MegaSTE default" >> $L; timeout 900 python3 work/tint2/hdbus.py build/mfin_hd hd_megaste megaste 4096 2.06 >> $L 2>&1
echo ALLDONE >> $L; touch work/tint2/res/bus2.done
