#!/bin/bash
export HOME=/tmp/nld/home PYTHONUNBUFFERED=1
cd /tmp/nld/games/in_progress/nebulus/work/editor
X=/tmp/nld/x; L=$X/logs; B=$X/b_new
SE=446f6f72202b206f70706f73697465     # "Door + opposite"
python3 e203.py $B $X/g203_ste ste > $L/e203_ste.log 2>&1
python3 e170.py $B $X/g170_ste ste > $L/e170_ste.log 2>&1
python3 e150.py $B $X/g150_ste ste > $L/e150_ste.log 2>&1
SNAP_EXPECT=$SE python3 e180.py $B $X/g180_ste ste $X/ne/odd/odd2.ovl $X/ne/odd/stress01.ovl $X/ne/odd/stress05.ovl --snap $X/title_ste_new.sav --quick > $L/e180_ste.log 2>&1
echo ste done > $L/chain1.ste.done
python3 $X/mksnap.py $B $X/title_megaste_new.sav megaste $X/wdsnap_mste > $L/snap_megaste.log 2>&1
python3 e203.py $B $X/g203_mste megaste > $L/e203_megaste.log 2>&1
python3 e170.py $B $X/g170_mste megaste > $L/e170_megaste.log 2>&1
echo megaste done > $L/chain1.mste.done
python3 $X/mksnap.py $B $X/title_st_new.sav st $X/wdsnap_st > $L/snap_st.log 2>&1
python3 e203.py $B $X/g203_st st > $L/e203_st.log 2>&1
echo st done > $L/chain1.st.done
