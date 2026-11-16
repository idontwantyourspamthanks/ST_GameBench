#!/usr/bin/env bash
cd "$(dirname "$0")"
for L in 3 4 6 7 8 9 10 11 13 14; do python3 dumplevel.py $L dumps/L$L.bin 2>&1 | tail -1; done
echo DONE
