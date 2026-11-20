#!/usr/bin/env bash
# after followup.sh: Mega ST cell re-runs (sound on; then sound off if it fails again), psgcheck vs shared tools/psgcheck.py on one v1.6 negative + one candidate swap trace
cd "$(dirname "$0")"
while pgrep -f "followup.sh" >/dev/null; do sleep 15; done
export MW2S_EXTRA="--trace fdc,psg_write"
ok=0
for i in 1 2; do
  n=p2_b_st104_8_d1_r$i; MW2S_SOUND=50066 timeout 1800 python3 cell16.py $n st 104 1024 /tmp/mw2s/c17 8 1 > out/$n.log 2>&1
  echo "$n (sound on): $(grep -E '^(CELL|EXC)' out/$n.log | tr '\n' ' ' | cut -c1-200)"; rm -rf /tmp/mw2s/$n
  grep -q "^CELL.*: PASS" out/$n.log && { ok=1; break; }
done
if [ $ok = 0 ]; then
  n=p2_b_st104_8_d1_off; MW2S_SOUND=off timeout 1800 python3 cell16.py $n st 104 1024 /tmp/mw2s/c17 8 1 > out/$n.log 2>&1
  echo "$n (sound OFF): $(grep -E '^(CELL|EXC)' out/$n.log | tr '\n' ' ' | cut -c1-200)"; rm -rf /tmp/mw2s/$n
  n=p2_b_st104_8_d1_v16; MW2S_SOUND=50066 timeout 1800 python3 cell16.py $n st 104 1024 /tmp/mw2s/ship 8 1 > out/$n.log 2>&1
  echo "$n (shipped v1.6, sound on): $(grep -E '^(CELL|EXC)' out/$n.log | tr '\n' ' ' | cut -c1-200)"; rm -rf /tmp/mw2s/$n
fi
echo "== psgcheck both tools"
export MW2S_SOUND=50066
for v in ship:/tmp/mw2s/ship c17:/tmp/mw2s/c17; do
  n=pc_ste_${v%%:*}; timeout 900 python3 swapgate.py $n ste 162 8 1 ${v#*:} B > out/$n.log 2>&1
  echo "-- $n: mine"; python3 psgcheck.py /tmp/mw2s/$n/fdc.trace $n | tail -2 | cut -c1-240
  echo "-- $n: shared tools/psgcheck.py"; python3 ../../../../tools/psgcheck.py /tmp/mw2s/$n/fdc.trace --name $n 2>&1 | tail -4 | cut -c1-240
  rm -rf /tmp/mw2s/$n
done
echo "== ALL2 DONE"
