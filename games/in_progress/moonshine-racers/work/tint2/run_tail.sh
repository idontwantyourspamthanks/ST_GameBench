#!/bin/bash
# after the cold boots: tick-on/no-extras state references (is a difference due to the extras or to a patch?), raster/palette traces (ta_rb + tb_blit), blitter use
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2
while [ ! -f res/cold.done ]; do sleep 10; done
./run_bisect.sh
L=res/tail_log.txt
run() { echo "== $*" >> $L; timeout 3000 "$@" >> $L 2>&1; }
run python3 exp_state_fin.py T ste1m_race_start.sav 8 230 res/st_start_T8.json
run python3 exp_state_fin.py T ste1m_race_drive.sav 8 320 res/st_drive_T8.json
run python3 exp_state_fin.py T ste1m_race_start.sav 8 260 res/st_zig_start_T8.json zig=140
run python3 exp_state_fin.py T ste1m_race_up.sav 8 260 res/st_zig_up_T8.json zig=470
TINT_TAG=_nrb TINT_DROP=ta_rb,ta_rb0 run python3 exp_state_fin.py T ste1m_race_start.sav 8 230 res/st_start_T8_nrb.json
run python3 rastercheck.py A ste1m_race_start.sav 3000 res/ras_A.txt trace=video_color zig=140
run python3 rastercheck.py X ste1m_race_start.sav 6000 res/ras_X.txt trace=video_color zig=140
run python3 rastercheck.py NB ste1m_race_start.sav 6000 res/ras_NB.txt trace=video_color zig=140
run python3 rastercheck.py NRB ste1m_race_start.sav 3000 res/ras_NRB.txt trace=video_color zig=140
run python3 rastercheck.py X ste1m_race_start.sav 400 res/blit_X.txt trace=blitter zig=140
python3 rb2_cmp.py res/ras_A.txt res/ras_X.txt res/ras_NB.txt res/ras_NRB.txt > res/ras_cmp.txt 2>&1
echo ALLDONE >> $L; touch res/tail.done
