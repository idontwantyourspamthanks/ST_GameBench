#!/bin/bash
# bus/address error forensics: default floppy build vs a zero-patch floppy build, then the bisect variants
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
L=work/tint2/res/bus_log.txt
DEF=$(python3 tools/msrpatch.py list | awk '$2=="yes" && $1 !~ /^pp_/ {print $1}' | tr '\n' ' ')
build() { python3 tools/msrpatch.py build --floppy --out build/bus_$1 --only $2 >/dev/null 2>&1 || echo "BUILD FAIL $1"; }
run() { echo "== $1" >> $L; timeout 900 python3 work/tint2/bus.py $2 $3 $4 $5 $6 $1 >> $L 2>&1; }
# V0: no patch at all (fl_hook is always in a floppy build; fl_deprot only skips the manual question)
build v0 "fl_deprot"
run v0 build/bus_v0/disk_a.st build/bus_v0/disk_b.st ste 1024 1.62
# V1: the shipped default set
run v1 build/mfin_floppy/disk_a.st build/mfin_floppy/disk_b.st ste 1024 1.62
echo ALLDONE >> $L; touch work/tint2/res/bus.done
