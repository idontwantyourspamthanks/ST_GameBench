#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2
while pgrep -f batch2.sh > /dev/null; do sleep 10; done
P="python3 -u tools/p2abtest.py"
python3 -u tools/p2blit.py --trials 30000 > work/scratch/blit_30k.log 2>&1; echo EXIT $? >> work/scratch/blit_30k.log
python3 -u tools/p2blit.py --trials 3000 --neg > work/scratch/blit_neg.log 2>&1; echo EXIT $? >> work/scratch/blit_neg.log
$P --turns 60 --snapshot busy1 --only pop2_spr pop2_spr16 --poke 840b3:05 > work/scratch/n_spr.log 2>&1; echo EXIT $? >> work/scratch/n_spr.log
$P --turns 60 --snapshot busy1 --only pop2_ptr_a pop2_ptr_b --poke 8603e:4e714e71 > work/scratch/n_ptr.log 2>&1; echo EXIT $? >> work/scratch/n_ptr.log
$P --turns 40 --snapshot game_start --neg > work/scratch/n_walk.log 2>&1; echo EXIT $? >> work/scratch/n_walk.log
$P --turns 130 --mhz 16 --only pop2_spr pop2_spr16 > work/scratch/g16_spr.log 2>&1; echo EXIT $? >> work/scratch/g16_spr.log
$P --turns 130 --mhz 16 --only pop2_ptr_a pop2_ptr_b > work/scratch/g16_ptr.log 2>&1; echo EXIT $? >> work/scratch/g16_ptr.log
$P --turns 130 --mhz 8 16 --only pop2_spr pop2_spr16 pop2_ptr_a pop2_ptr_b pop2_clamp > work/scratch/g_all.log 2>&1; echo EXIT $? >> work/scratch/g_all.log
$P --turns 130 --snapshot busy1 --no-walk --only pop2_spr pop2_spr16 > work/scratch/g_static_blit.log 2>&1; echo EXIT $? >> work/scratch/g_static_blit.log
$P --turns 130 --snapshot busy1 --no-walk --only pop2_spr pop2_spr16 --poke 88200:b17e0002 > work/scratch/g_static_cache.log 2>&1; echo EXIT $? >> work/scratch/g_static_cache.log
python3 -u tools/p2blit.py --trials 6000 --neg-verify > work/scratch/blit_negverify.log 2>&1; echo EXIT $? >> work/scratch/blit_negverify.log
python3 -u tools/p2clamp.py --vbls 400 > work/scratch/clamp_proof.log 2>&1; echo EXIT $? >> work/scratch/clamp_proof.log
