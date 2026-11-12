#!/bin/bash
# runq.sh QUEUEFILE : each line "BUILD MODE MACHINE TAG"; BUILD = a | b | stock | vhd | vhdorig ; runs sequentially
B=/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/build/MW1Ski
V=/home/ryan/Code/AtariST/gamebench/dist/AtariST_enhanced_games_2026-11-11.vhd
D=/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/work/ski_forward
while read -r build mode mach tag; do
  case $build in
    stock) path=stock ;;
    vhd) export FWD_VHD=$V; path=vhd ;;
    vhdorig) export FWD_VHD=$V FWD_ORIG=1; path=vhdorig ;;
    *) path=$B/$build ;;
  esac
  python3 $D/fwd.py $path $mode $mach > $D/logs/${tag}.log 2>&1
  unset FWD_VHD FWD_ORIG
done < "$1"
