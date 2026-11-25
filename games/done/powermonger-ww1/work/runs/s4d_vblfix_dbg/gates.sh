#!/usr/bin/env bash
# gates of the hd_core late-VBL fix (build /tmp/pmww1fhd2/b_fix = HEAD patches + the fixed hd_core.s; f_fix = the plain floppy build of the same set).  One Hatari at a time.
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger-ww1
export TMPDIR=/tmp/pmww1fhd2
B=/tmp/pmww1fhd2/b_fix; F=/tmp/pmww1fhd2/f_fix; W=/tmp/pmww1fhd2; R=work/runs
HD="--hd $B/hd --manifest $B/manifest.json --fill-hi --trace --steps boot,map,hw,saveload,lose,win,round3"
FAL='--machine falcon --tos 4.04 --mem 4096'
run() { n=$1; shift; echo "== $n: $*"; "$@" > $R/s4d_vblfix_$n.txt 2>&1; grep -h 'CELL DONE\|CELL FAILED\|FAIL\|Error' $R/s4d_vblfix_$n.txt | tail -6; }
for want in "$@"; do case $want in
 fal1) WW_CLICK_HOLD=0.10 run fal_hd_short1 python3 tools/wwgate.py cell $HD $FAL --extra "--borders false" --tag vf_fhd1 --workdir $W/c_fhd1 ;;
 fal2) WW_CLICK_HOLD=0.10 run fal_hd_short2 python3 tools/wwgate.py cell $HD $FAL --extra "--borders false" --tag vf_fhd2 --workdir $W/c_fhd2 ;;
 ste)  run ste_gemdos python3 tools/wwgate.py cell $HD --tag vf_ste_gemdos --workdir $W/c_ste_g ;;
 stea) run ste_acsi python3 tools/wwgate.py cell $HD --acsi --tag vf_ste_acsi --workdir $W/c_ste_a ;;
 mste) run mste_gemdos python3 tools/wwgate.py cell $HD --machine megaste --tos 2.06 --mem 4096 --tag vf_mste_gemdos --workdir $W/c_mste_g ;;
 mstea) run mste_acsi python3 tools/wwgate.py cell $HD --acsi --machine megaste --tos 2.06 --mem 4096 --tag vf_mste_acsi --workdir $W/c_mste_a ;;
 falf) run fal_floppy python3 tools/wwgate.py cell --disk $F/floppy.st --manifest $F/manifest.json $FAL --extra "--borders false" --fill-hi --trace --steps boot,map,saveload,lose --tag vf_falflop --workdir $W/c_falf ;;
 keys) run keys_ste python3 tools/wwkeys.py --disk $F/floppy.st --manifest $F/manifest.json --workdir $W/c_keys --tag vf_keys ;;
 neg)  WW_CLICK_HOLD=0.10 run NEG_fal_hd_short_oldcore python3 tools/wwgate.py cell --hd /tmp/pmww1fhd2/b_head/hd --manifest /tmp/pmww1fhd2/b_head/manifest.json --fill-hi --trace --steps boot,map,hw,saveload,lose $FAL --extra "--borders false" --tag vf_neg --workdir $W/c_neg ;;
esac; done
