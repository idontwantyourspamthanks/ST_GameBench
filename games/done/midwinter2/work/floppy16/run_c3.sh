#!/usr/bin/env bash
cd "$(dirname "$0")"
while pgrep -f "[r]un_final.sh|[r]un_c2.sh" >/dev/null; do sleep 15; done
timeout 1500 python3 cell16.py sb_ste162_8_d2r ste 162 1024 /tmp/mw2f/ship 8 2 --ext st > out/sb_ste162_8_d2r.log 2>&1
timeout 1500 python3 cell16.py ctl_v15_ste162_8_d2a ste 162 1024 /tmp/mw2f/v15 8 2 --ext st > out/ctl_v15_ste162_8_d2a.log 2>&1
timeout 1500 python3 cell16.py ctl_v15_ste162_8_d2b ste 162 1024 /tmp/mw2f/v15 8 2 --ext st > out/ctl_v15_ste162_8_d2b.log 2>&1
