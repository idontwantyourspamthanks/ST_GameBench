#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/floppy
D=Z/NEBULUS_floppy/Nebulus_game_disk.st
mkdir -p res
python3 fgate.py $D /tmp/nfc_st st 1024 1.04 patched > res/st_1mb_tos104.txt 2>&1
python3 fgate.py $D /tmp/nfc_mste megaste 4096 2.06 patched > res/megaste_4mb_tos206.txt 2>&1
python3 fgate.py $D /tmp/nfc_512 st 512 1.04 patched > res/st_512k_tos104.txt 2>&1
python3 fgate.py "../../alt/floppy/Nebulus (1988)(Hewson)[cr Atari Legend].st" /tmp/nfc_ctl ste 1024 1.62 control > res/control_ste.txt 2>&1
echo done > res/ALLDONE
