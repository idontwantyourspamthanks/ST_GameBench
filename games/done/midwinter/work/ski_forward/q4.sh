#!/bin/bash
D=/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/work/ski_forward
V=/home/ryan/Code/AtariST/gamebench/dist/AtariST_enhanced_games_2026-11-11.vhd
FWD_VHD=$V FWD_EXTRA="--fast-boot no" python3 $D/fwd.py vhd J tt > $D/logs/vhd_J_tt_noFastBoot.log 2>&1
FWD_VHD=$V FWD_EXTRA="--ttram 16" python3 $D/fwd.py vhd M tt > $D/logs/vhd_M_tt_ttram16.log 2>&1
