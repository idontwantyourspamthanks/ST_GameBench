#!/bin/bash
cd /tmp/looksgate/games/in_progress/nebulus; L=/tmp/looksgate/logs; R=/tmp/looksgate/r; B=/tmp/looksgate; export PYTHONUNBUFFERED=1
while pgrep -f "work/gate_NebFloppyEject" >/dev/null; do sleep 3; done
rl(){ python3 work/looks/run_look.py "$@"; }
FG=$B/fl_new/Nebulus_game_disk.st
python3 work/editor/e170.py $B/b_new $B/wd170_mega megaste > $L/e170_mega.log 2>&1
python3 work/editor/e150.py $B/b_new $B/wd150_mega megaste > $L/e150_mega.log 2>&1
rl $B/b_new_looks15 $R/looks15_mega 15 camp megaste > $L/c2_looks15_mega.log 2>&1
python3 work/looks/check_look.py $R/base8_ste $R/looks15_mega looks15 > $L/c2_check_mega.txt 2>&1
python3 work/editor/e170.py $B/b_new $B/wd170_st st > $L/e170_st.log 2>&1
python3 work/editor/e150.py $B/b_new $B/wd150_st st > $L/e150_st.log 2>&1
rl $B/b_new_st6 $R/st6_st 6 camp st > $L/c2_st6_st.log 2>&1
python3 work/looks/check_look.py $R/base8_ste $R/st6_st st6 > $L/c2_check_st.txt 2>&1
python3 work/floppy/fl_ui.py $FG $B/wdflui_mega $R/base8_ste megaste > $L/c7_fl_ui_mega.log 2>&1
REFDIR=$R/base8_ste python3 work/editor/e190.py $B/b_new $B/wd190_mega megaste > $L/e190_mega.log 2>&1
echo done > $L/m.done
