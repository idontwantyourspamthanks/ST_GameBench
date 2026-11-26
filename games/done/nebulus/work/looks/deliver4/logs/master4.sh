#!/bin/bash
# A/B part 2 with the corrected validator protocol; starts when the running chain (master3.sh) has written its "finished" line: one Hatari at a time
cd /tmp/nlcv/games/in_progress/nebulus; X=/tmp/nlcv/x; L=$X/logs; S=work/editor
export PYTHONUNBUFFERED=1 HOME=/tmp/nlcv/home
while ! grep -q 'chain .* finished' $L/master.progress 2>/dev/null; do sleep 10; done
run(){ n=$1; shift; "$@" > $L/$n.log 2>&1; echo "$(date +%T) $n done rc=$?" >> $L/master.progress; }
SIGN=10307e3010ffff0002080c7e0c08ffff0002; SIGO=$(printf 'Door + opposite' | xxd -p); NOS=$(printf 'Conveyor left' | xxd -p)
run ab3_old env PART=2 SIG=$SIGO NOSIG=$NOS python3 $S/e208_ab.py run $X/b_old $X/title_ste_old.sav $X/ab3/old ste
run ab3_new env PART=2 SIG=$SIGN python3 $S/e208_ab.py run $X/b_new $X/title_ste_new.sav $X/ab3/new ste
run ab3_cmp python3 $S/e208_ab.py cmp $X/ab3/old $X/ab3/new
echo "$(date +%T) chain4 done" >> $L/master.progress
