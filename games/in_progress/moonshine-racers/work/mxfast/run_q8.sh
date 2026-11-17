#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while [ ! -f work/mxfast/res/q7.done ]; do sleep 20; done
R=work/mxfast/res; M=work/mxfast
echo "=== FLOPPY gate mg ste 1024 1.62 16 (repeat)"  > $R/floppy2.txt
timeout 1500 python3 tools/msrfloppy.py gate $M/build/mg_fl/disk_a.st --disk-b $M/build/mg_fl/disk_b.st --machine ste --mem 1024 --tos 1.62 --cpu 16 --name mxf_mg_ste_b 2>&1 | cut -c1-300 >> $R/floppy2.txt
echo "=== FLOPPY gate control (build/tight_floppy = today's default) ste 1024 1.62 16" >> $R/floppy2.txt
timeout 1500 python3 tools/msrfloppy.py gate build/tight_floppy/disk_a.st --disk-b build/tight_floppy/disk_b.st --machine ste --mem 1024 --tos 1.62 --cpu 16 --name mxf_ctl_ste 2>&1 | cut -c1-300 >> $R/floppy2.txt
echo DONE > $R/q8.done
