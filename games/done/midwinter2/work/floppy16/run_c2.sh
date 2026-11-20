#!/usr/bin/env bash
cd "$(dirname "$0")"
while pgrep -f "[r]un_final.sh" >/dev/null; do sleep 15; done
for spec in "sc_ste_d1_v16 ste 162 8 1 /tmp/mw2f/ship A B" "sc_ste_d1_v16c ste 162 8 1 /tmp/mw2f/ship C CB"; do
  set -- $spec; n=${1}r; shift; set -- $n "$@"
  timeout 900 python3 swapgate.py "$@" > out/$n.log 2>&1
done
