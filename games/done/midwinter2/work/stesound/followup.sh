#!/usr/bin/env bash
# follow-up chain after run_gates.sh b: logo glyph test, Mega STE 16 MHz 1-drive cell re-run, YM A/B on Mega ST / TT
cd "$(dirname "$0")"
while pgrep -f "run_gates.sh /tmp/mw2s/c17" >/dev/null; do sleep 15; done
export MW2S_SOUND=50066
echo "== logo tests"
MW2S_EXTRA="" python3 logotest.py logo_v161 /tmp/mw2s/v161 2>&1 | grep -E "shot|Error"
MW2S_EXTRA="" python3 logotest.py logo_punct /tmp/mw2s/logot 2>&1 | grep -E "shot|Error"
echo "== LOGO DONE"
export MW2S_EXTRA="--trace fdc,psg_write"
for i in 1 2 3; do
  n=p2_b_mste206_16_d1_r$i
  timeout 1800 python3 cell16.py $n megaste 206 1024 /tmp/mw2s/c17 16 1 --soak 120 > out/$n.log 2>&1
  grep -E "^(CELL|EXC|PSGCHECK|RAMCHECK)|game type I commands|first game restore" out/$n.log | cut -c1-200
  rm -rf /tmp/mw2s/$n
  grep -q "^EXC OSError" out/$n.log || break
done
echo "== YM A/B"
export MW2S_EXTRA="--trace psg_write"
for m in "megast 104 1024" "tt 306 4096"; do
  set -- $m
  export MW2S_MEM=$3
  for v in ship:/tmp/mw2s/ship c17:/tmp/mw2s/c17; do
    n=ym_$1_${v%%:*}
    timeout 900 python3 ymab.py $n $1 $2 8 1 ${v#*:} > out/$n.log 2>&1
    echo "$n: $(grep -E 'orange prompt|RAM' out/$n.log | tr '\n' ' ' | cut -c1-200)"
  done
  python3 ymdiff.py /tmp/mw2s/ym_$1_ship/fdc.trace /tmp/mw2s/ym_$1_c17/fdc.trace > out/ymdiff_$1.txt 2>&1
  echo "--- ymdiff $1"; cat out/ymdiff_$1.txt | cut -c1-220
done
echo "== ALL DONE"
