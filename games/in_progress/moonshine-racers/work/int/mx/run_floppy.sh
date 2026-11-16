#!/usr/bin/env bash
cd "$(dirname "$0")/../../.."
D=build/mx_floppy
for spec in "ste 1024 1.62 ste_1024" "ste 4096 1.62 ste_4096" "megaste 4096 2.06 megaste_4096" "st 1024 1.04 st_1024"; do set -- $spec
  echo "=== floppy gate $spec (16 MHz extras count)"; python3 tools/msrfloppy.py gate $D/disk_a.st --disk-b $D/disk_b.st --machine $1 --mem $2 --tos $3 --name mx_$4 --cpu 16 2>&1 | tail -14
done
echo DONE
