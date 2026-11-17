#!/bin/bash
# Measurements (STE 1 MB, Hatari): cycles per pass (tick OFF), extras per tick / fps / late ticks (tick ON, steered 2-minute drives)
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2
while [ ! -f res/pix.done ]; do sleep 10; done
unset TINT_SHOW
R=res; L=res/meas_log.txt
S="python3 steer_fin.py"
run() { echo "== $*" >> $L; timeout 3000 "$@" >> $L 2>&1; }
# extras per tick (race_drive: time-out sequence, restart, standing start, then racing; 1300 passes = 130 s emulated)
run $S race_drive X 8 1300 $R/ext_X_8.json steer=zig mode=pass
run $S race_drive XM 8 1300 $R/ext_XM_8.json steer=zig mode=pass
run $S race_drive P 8 1300 $R/ext_P_8.json steer=zig mode=pass
run $S race_drive X 8 1300 $R/ext_X_8_s3.json steer=zig mode=pass poke=b8f6c=0003
run $S race_drive X 16 1300 $R/ext_X_16.json steer=zig mode=pass
run $S race_drive X 32 1300 $R/ext_X_32.json steer=zig mode=pass
run $S race_drive X 16 1300 $R/ext_X_16_s3.json steer=zig mode=pass poke=b8f6c=0003
# cycles per pass, tick OFF, matched passes (steered zig from the same key)
run $S race_start F 8 520 $R/cyc_start_F.json steer=zig zigk=140 mode=cyc
run $S race_start PF 8 520 $R/cyc_start_PF.json steer=zig zigk=140 mode=cyc
run $S race_up F 8 400 $R/cyc_up_F.json steer=zig zigk=470 mode=cyc
run $S race_up PF 8 400 $R/cyc_up_PF.json steer=zig zigk=470 mode=cyc
for d in "tb_blit,tb_blit11,tb_blit13,tb_blit15:noblit" "ta_nomouse:nomouse" "ta_rb,ta_rb0:norb"; do
  v=${d%%:*}; n=${d##*:}
  echo "== drop $v" >> $L
  TINT_TAG=_$n TINT_DROP=$v timeout 3000 $S race_start F 8 520 $R/cyc_start_F_$n.json steer=zig zigk=140 mode=cyc >> $L 2>&1
done
echo "== no facestat (ta_face instead)" >> $L
TINT_TAG=_face TINT_DROP=ta_facestat TINT_ADD=ta_face timeout 3000 $S race_start F 8 520 $R/cyc_start_F_face.json steer=zig zigk=140 mode=cyc >> $L 2>&1
echo ALLDONE >> $L; touch res/meas.done
