#!/bin/bash
# Re-runs the pixel/self-check gates of p7_skip; raw output in evidence/.  Needs /tmp/p7s/{base,sk}.{img,json} and /tmp/p7s/enemy.sav:
#   D=$(python3 tools/mw1patch.py list | awk '$2=="yes" && $1!~/^(floppy|pp_)/ {print $1}')
#   python3 tools/mw1patch.py live --only $D --out /tmp/p7s/base ; python3 tools/mw1patch.py live --only $D p7_skip_sky p7_skip_render --out /tmp/p7s/sk
#   python3 work/p7_skip/mkenemy.py /tmp/p7s/enemy.sav x          # cold boot, Training/Mortars/Bombers OFF, snapshot when the enemy object is active
cd /home/ryan/Code/AtariST/gamebench/games/done/midwinter/work/p7_skip
E=evidence
for s in stand walk turn busy; do python3 match.py $s /tmp/p7s/base /tmp/p7s/sk --batches 3 > $E/match_$s.txt 2>&1; done
python3 match.py /tmp/p7s/enemy.sav /tmp/p7s/base /tmp/p7s/sk --batches 3 > $E/match_enemy.txt 2>&1
python3 verify.py stand /tmp/p7s/sk 30 > $E/verify_stand.txt 2>&1
python3 verify.py stand /tmp/p7s/sk 40 --pre 'w $12c98 $00 $ba;w $15114 $00 $ba;w $b370a $00 $ba;w $b370e $00 $ba' > $E/verify_stand_heading.txt 2>&1
for s in walk busy turn; do python3 verify.py $s /tmp/p7s/sk 25 --settle 300 > $E/verify_$s.txt 2>&1; done
python3 verify.py /tmp/p7s/enemy.sav /tmp/p7s/sk 30 --settle 20 --maxwait 30 > $E/verify_enemy.txt 2>&1
