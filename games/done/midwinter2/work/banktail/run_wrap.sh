#!/usr/bin/env bash
# Resident-driver stand-in (mkwrap.py) in front of RUNME: STE TOS 1.62 1 MB with KEEP = $4100 (16 KB), $2000 (8 KB) and $1000 (4 KB); one Hatari at a time.
R=/home/ryan/Code/AtariST/gamebench/games/done/midwinter2; cd $R
HD=/tmp/mw2tail/rel/hd/MW2PATCH
for k in 4100 2100 1100; do n=wrap$k; echo "== $n"; timeout 1200 python3 work/banktail/walk.py $n ste 162 1024 hd $HD --to logo --wrap $k > /tmp/mw2tail/$n.out 2>&1; echo "exit $?"; done
