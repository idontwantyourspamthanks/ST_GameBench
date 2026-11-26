#!/bin/bash
# serial regression matrix on the relocated rd_* map; waits for gates_ab.sh (one Hatari at a time)
cd "$(dirname "$0")/../.."
while pgrep -f gates_ab.sh >/dev/null; do sleep 10; done
M=work/mste
for c in "megaste 1024 2.06 0,16" "ste 1024 1.62 0,16" "megaste 4096 2.06 0,16" "ste 4096 1.62 0,16" "megaste 2048 2.06 0,16" "st 1024 1.04 0,16" "tt 4096 3.06 0" "falcon 4096 4.04 0"; do
  set -- $c
  echo "=== HD cold $c"; timeout 1500 python3 $M/cold.py $1 $2 $3 build/mste_hd hd_$1_$2 $4 2>&1 | grep -v "^$" | cut -c1-420
done > $M/m_hd.txt 2>&1
for c in "megaste 1024 2.06 16" "megaste 4096 2.06 16" "ste 1024 1.62 16" "ste 4096 1.62 16" "st 1024 1.04 16"; do
  set -- $c
  echo "=== FLOPPY gate $c"; timeout 900 python3 tools/msrfloppy.py gate build/mste_floppy/disk_a.st --disk-b build/mste_floppy/disk_b.st --machine $1 --mem $2 --tos $3 --cpu $4 --name mste_$1_$2 2>&1 | cut -c1-300
done > $M/m_floppy.txt 2>&1
echo done > $M/matrix.done
