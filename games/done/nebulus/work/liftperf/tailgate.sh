#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/liftperf
cat > titlef10.py <<'PY'
from lp import *
h = mk('/tmp/lp/patched2', '/tmp/lp/w_tf10', snapshot=str(NEB / 'work/snapshots/hiscores.sav'))
try:
    time.sleep(2.0)
    n0 = len(h._logtext())
    h.cmd('hatari-debug b pc = $7574c :trace'); time.sleep(0.3)
    h.key('F10', hold=0.5); time.sleep(1.5)
    print('F10 on the title -> editor title-poll hook hits:', h._logtext()[n0:].count('matched'))
    print('rsEd $77c86 =', int.from_bytes(rd(h, 0x77c86, 2), 'big'), 'ed marker $75740..', rd(h, 0x75740, 8).hex())
    h.shot('/tmp/lp/title_editor.png')
finally:
    h.close()
PY
python3 titlef10.py > /tmp/lp/titlef10.log 2>&1
python3 mksnap2.py /tmp/lp/patched2 /tmp/lp/mste_s megaste 1 6 > /tmp/lp/mksnap_mste.log 2>&1
for t in 1 6; do
  PRE=0.2 python3 ride2.py /tmp/lp/mste_s_t$t.sav ms${t}_base 24 1 megaste /tmp/lp/patched2 > /tmp/lp/ms${t}_base.out 2>&1
  python3 ana.py /tmp/lp/tr_ms${t}_base/log.txt | grep "state6\|^all" > /tmp/lp/ms${t}_base.ana
  LIVE=np_lift PRE=0.2 python3 ride2.py /tmp/lp/mste_s_t$t.sav ms${t}_lift 24 1 megaste /tmp/lp/patched2 > /tmp/lp/ms${t}_lift.out 2>&1
  python3 ana.py /tmp/lp/tr_ms${t}_lift/log.txt | grep "state6\|^all" > /tmp/lp/ms${t}_lift.ana
done
python3 tick.py /tmp/lp/mste_s_t1.sav megaste m1 > /tmp/lp/tick_mste.log 2>&1
python3 tick.py /tmp/lp/ste_s_t1.sav ste s1 > /tmp/lp/tick_ste.log 2>&1
echo done > /tmp/lp/tail.done
