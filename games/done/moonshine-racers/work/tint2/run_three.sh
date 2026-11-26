#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
L=work/tint2/res/three_log.txt
rm -rf /tmp/loneA; mkdir -p /tmp/loneA; cp build/mfin_floppy/disk_a.st /tmp/loneA/disk_a.st
echo "=== LONE-A gate ste 1024 1.62 16" >> $L
timeout 900 python3 tools/msrfloppy.py gate /tmp/loneA/disk_a.st --disk-b build/mfin_floppy/disk_b.st --machine ste --mem 1024 --tos 1.62 --cpu 16 --name three_ste 2>&1 | cut -c1-320 >> $L
echo "=== bus, rebuilt default (lone A)" >> $L
timeout 900 python3 work/tint2/bus.py /tmp/loneA/disk_a.st build/mfin_floppy/disk_b.st ste 1024 1.62 v1c 2>&1 | grep -E '^(v1c|  \[phase)' >> $L
echo ALLDONE >> $L; touch work/tint2/res/three.done
