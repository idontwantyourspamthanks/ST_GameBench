#!/bin/bash
# two chains, each runs its cells sequentially (max 2 Hatari at once)
cd /home/ryan/Code/AtariST/midwinter2
R() { python3 work/bigram/run_cell.py "$@" > work/bigram/$1.out 2>&1; }
( R mste206_4mb_fixonly megaste 206 4096 build/bigram_only timing
  R mste206_1mb_fix megaste 206 1024 build/game
  R st104_4mb_fix st 104 4096 build/game
  R mste206_14mb_fix megaste 206 14336 build/game ) &
( R mste206_2mb_fix megaste 206 2048 build/game
  R ste162_4mb_fix ste 162 4096 build/game
  R mste206_8mb_fix megaste 206 8192 build/game
  R mste206_1mb_pristine megaste 206 1024 /tmp/bigram/pristine_ov timing ) &
wait
