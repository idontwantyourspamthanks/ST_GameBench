#!/bin/bash
cd "$(dirname "$0")"
./env.sh python3 probe_type.py --game ../camphd/b5 --machine ste --mem 2048 --out snap/b5_ste2m > boot_b5_ste2m.txt 2>&1
./env.sh python3 gate.py finish --machine ste --mem 2048 --build b5 --tag real_ste2m > log_real_ste2m.txt 2>&1
echo DONE > log_real_done.txt
