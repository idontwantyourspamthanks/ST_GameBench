#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2
while pgrep -f 'floppy_fin.py' >/dev/null; do sleep 10; done
L=res/isr_log.txt
r() { echo "== $*" >> $L; timeout 2600 "$@" >> $L 2>&1; }
r python3 isr2.py A ste1m_race_start.sav 3000 res/isr_A.json
r python3 isr2.py X ste1m_race_start.sav 6000 res/isr_X.json
r python3 isr2.py NB ste1m_race_start.sav 6000 res/isr_NB.json
E=res/ext8; mkdir -p $E
r python3 steer_fin.py race_start X 8 700 $E/ext8_start_X8.json steer=zig mode=pass
r python3 steer_fin.py race_up X 8 700 $E/ext8_up_X8.json steer=zig mode=pass
r python3 joy2.py ste1m_race_drive.sav res/joy_final.txt
r python3 menus.py build/mfin_hd final_race
echo ALLDONE >> $L; touch res/final.done
