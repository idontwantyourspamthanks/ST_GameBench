#!/usr/bin/env bash
cd "$(dirname "$0")"
G=build/mx_hd
for spec in "ste 1024 1.62" "ste 4096 1.62" "megaste 4096 2.06" "st 1024 1.04" "tt 4096 3.06"; do set -- $spec
  echo "=== HD cold boot $spec"; python3 cold.py $1 $2 $3 $G 500 native 0,16,32 2>&1 | tail -6
done
echo DONE
