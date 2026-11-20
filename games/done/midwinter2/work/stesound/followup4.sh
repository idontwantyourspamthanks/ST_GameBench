#!/usr/bin/env bash
cd "$(dirname "$0")"
while pgrep -f "followup3.sh" >/dev/null; do sleep 15; done
export MW2S_EXTRA="--trace fdc,psg_write" MW2S_SOUND=50066
SH=/home/ryan/Code/AtariST/gamebench/tools/psgcheck.py
for v in ship:/tmp/mw2s/ship c17:/tmp/mw2s/c17; do
  n=pc2_ste_${v%%:*}; timeout 900 python3 swapgate.py $n ste 162 8 1 ${v#*:} B > out/$n.log 2>&1
  echo "-- $n: MINE (work/stesound/psgcheck.py)"; python3 psgcheck.py /tmp/mw2s/$n/fdc.trace $n | tail -1 | cut -c1-260
  echo "-- $n: SHARED (tools/psgcheck.py)"; python3 $SH /tmp/mw2s/$n/fdc.trace --name $n 2>&1 | tail -3 | cut -c1-260; echo "   exit code $?"
  rm -rf /tmp/mw2s/$n
done
echo "== ALL4 DONE"
