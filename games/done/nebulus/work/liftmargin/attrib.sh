#!/bin/bash
# usage: attrib.sh NAME [NAME...]   (build dirs /tmp/nlm/b_NAME): snapshot tower 6 + ride (enemies on) + per-loop analysis
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/liftmargin
for n in "$@"; do
  G=/tmp/nlm/b_$n
  [ -f /tmp/nlm/s_${n}_t6.sav ] || python3 mksnap2.py $G /tmp/nlm/s_$n ste 6 > /tmp/nlm/out/mk_$n.txt 2>&1
  python3 ride2.py /tmp/nlm/s_${n}_t6.sav ${n}_r1 24 1 ste $G > /tmp/nlm/out/ride_${n}_r1.txt 2>&1
  python3 ana.py /tmp/nlm/tr_${n}_r1/log.txt > /tmp/nlm/out/ana_${n}_r1.txt 2>&1
  echo "== $n"; grep -E "ride" /tmp/nlm/out/ana_${n}_r1.txt
done
echo done > /tmp/nlm/out/attrib.done
