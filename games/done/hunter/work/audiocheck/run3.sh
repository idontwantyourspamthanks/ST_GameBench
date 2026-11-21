#!/usr/bin/env bash
# Narrowed set (lead's request): Mega STE 4 MB HD, Mega STE 1 MB floppy.  Waits for a running cell (pid in $1) first.
cd "$(dirname "$(readlink -f "$0")")/../../../../.." || exit 1
while [ -n "$1" ] && kill -0 "$1" 2>/dev/null; do sleep 5; done
C=games/done/hunter/work/audiocheck/cell.py
run() { n=$1; shift; timeout 2700 python3 $C "$n" "$@" > /tmp/huntbank/log_$n.txt 2>&1; echo "DONE $n rc=$? $(grep -c 'FAILED' /tmp/huntbank/log_$n.txt) failures"; }
run hd_ms4 --kind hd --machine ms4 --play 60 --saveload --fx
run fl_ms1 --kind fl --machine ms1 --play 90 --saveload --fx
echo "ALLDONE run3"
