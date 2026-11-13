#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2
G="python3 -u tools/p2abtest.py --turns 130"
$G --only pop2_spr > work/scratch/g_spr_blit.log 2>&1; echo EXIT $? >> work/scratch/g_spr_blit.log
$G --only pop2_spr --poke 88200:b17e0002 > work/scratch/g_spr_cache.log 2>&1; echo EXIT $? >> work/scratch/g_spr_cache.log
$G --only pop2_ptr_a pop2_ptr_b > work/scratch/g_ptr.log 2>&1; echo EXIT $? >> work/scratch/g_ptr.log
$G --only pop2_clamp > work/scratch/g_clamp.log 2>&1; echo EXIT $? >> work/scratch/g_clamp.log
