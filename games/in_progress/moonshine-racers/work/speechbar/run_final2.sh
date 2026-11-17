#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
R=work/speechbar/res; S=work/speechbar
while ! grep -q ALLDONE $R/all_log.txt 2>/dev/null; do sleep 15; done
rm -rf /tmp/sbdrv_F /tmp/sbdrv_S /tmp/sbup_F /tmp/sbup_S
for v in F S; do timeout 1500 python3 $S/cap_sb.py $v ste1m_race_drive.sav 8 330 /tmp/sbdrv_$v 40 hold >> $R/final2_log.txt 2>&1; done
python3 $S/drive_other.py /tmp/sbdrv_F /tmp/sbdrv_S > $R/drive_other.txt 2>&1
python3 $S/mask_sb.py /tmp/sbdrv_F /tmp/sbdrv_S > $R/mask_race_drive_rerun.txt 2>&1
for v in F S; do timeout 1500 python3 $S/cap_sb.py $v ste1m_race_up.sav 8 250 /tmp/sbup_$v 40 hold >> $R/final2_log.txt 2>&1; done
python3 $S/mask_sb.py /tmp/sbup_F /tmp/sbup_S > $R/mask_race_up_rerun.txt 2>&1
rm -rf /tmp/sbup_F /tmp/sbup_S
echo FINAL2DONE >> $R/all_log.txt
