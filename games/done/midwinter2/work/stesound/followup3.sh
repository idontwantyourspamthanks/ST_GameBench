#!/usr/bin/env bash
cd "$(dirname "$0")"
while pgrep -f "followup2.sh|followup.sh" >/dev/null; do sleep 15; done
export MW2S_EXTRA="--trace fdc,psg_write" MW2S_SOUND=50066
for i in 1 2; do
n=p2_b_st104_8_d1_v16c$i; MW2S_EXPECT_3392C=102b0014 timeout 1800 python3 cell16.py $n st 104 1024 /tmp/mw2s/ship 8 1 > out/$n.log 2>&1
echo "$n (shipped v1.6, sound on): $(grep -E '^(CELL|EXC)' out/$n.log | tr '\n' ' ' | cut -c1-200)"; rm -rf /tmp/mw2s/$n
done
echo "== ALL3 DONE"
