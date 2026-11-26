#!/bin/bash
# usage: man.sh  (starts Xvfb :77 + Mega STE hatari on a copy of the image; fifo /tmp/pmig.fifo)
cd /home/ryan/Code/AtariST/gamebench
(Xvfb :77 -screen 0 1024x768x24 >/dev/null 2>&1 & echo $! > /tmp/pmig_xvfb.pid); sleep 1
rm -rf /tmp/pmig.fifo /tmp/pmigshots; mkdir -p /tmp/pmigshots /tmp/pmighome/.config/hatari
cp dist/AtariST_enhanced_games_2026-11-19.img /tmp/pmig.img
DISPLAY=:77 SDL_AUDIODRIVER=dummy HOME=/tmp/pmighome nohup hatari --machine megaste --tos tos/TOS_2_06.img --memsize 4096 --cpuclock 16 --monitor rgb --gemdos-drive skip --acsi 0=/tmp/pmig.img --fast-boot no --sound off --cmd-fifo /tmp/pmig.fifo --screenshot-dir /tmp/pmigshots --screenshot-format png > work/gate_PMImageGate/manual3.log 2>&1 &
echo $! > /tmp/pmig_h.pid
