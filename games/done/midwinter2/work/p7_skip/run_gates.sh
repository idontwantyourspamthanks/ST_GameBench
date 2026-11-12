#!/bin/bash
# final gate run: raw outputs into evidence/
cd /home/ryan/Code/AtariST/midwinter2/work/p7_skip
S=/home/ryan/Code/AtariST/midwinter2/work/snapshots
E=evidence; mkdir -p $E
echo "== (a) standing 1mb_ingame_foot: A = p4+p7 base, B = base + p7_skip" | tee $E/a_base.txt
python3 gate.py ident $S/1mb_ingame_foot.sav /tmp/sk/base /tmp/sk/basesk 10,40,100 --tag fa1 2>&1 | cut -c1-330 | tee -a $E/a_base.txt
echo "== (a) standing 1mb_ingame_foot: A = UNPATCHED, B = base + p7_skip" | tee $E/a_unpatched.txt
python3 gate.py ident $S/1mb_ingame_foot.sav - /tmp/sk/basesk 10,40,100 --tag fa2 2>&1 | cut -c1-330 | tee -a $E/a_unpatched.txt
echo "== (a) standing ingame_lobos_foot (2 MB): A = base, B = base + p7_skip" | tee $E/a_lobos.txt
python3 gate.py ident $S/ingame_lobos_foot.sav /tmp/sk/base /tmp/sk/basesk 10,40,100 --mem 2048 --tag fa3 2>&1 | cut -c1-330 | tee -a $E/a_lobos.txt
echo "== (b) walking 1mb_ingame_walking: A = base, B = base + p7_skip" | tee $E/b_walk.txt
python3 gate.py ident $S/1mb_ingame_walking.sav /tmp/sk/base /tmp/sk/basesk 10,40,100 --tag fb1 2>&1 | cut -c1-330 | tee -a $E/b_walk.txt
echo "== (b) banked turn ingame_foot_banked_turn (2 MB): A = base, B = base + p7_skip" | tee $E/b_bank.txt
python3 gate.py ident $S/ingame_foot_banked_turn.sav /tmp/sk/base /tmp/sk/basesk 10,40,100 --mem 2048 --tag fb2 2>&1 | cut -c1-330 | tee -a $E/b_bank.txt
echo "== (b) turning ingame_foot_turning (2 MB)" | tee $E/b_turn.txt
python3 gate.py ident $S/ingame_foot_turning.sav /tmp/sk/base /tmp/sk/basesk 10,40,100 --mem 2048 --tag fb3 2>&1 | cut -c1-330 | tee -a $E/b_turn.txt
echo "== stop-and-go: heading poke @18, position poke @43, restore @68 (standing snapshot)" | tee $E/stopgo.txt
python3 gate.py ident $S/1mb_ingame_foot.sav /tmp/sk/base /tmp/sk/basesk 19,20,22,25,44,45,47,69,70,72,90 --tag sg1 --poke '18:w $6742 $02 $80;w $6294 $02 $80;w $764a $02 $80' --poke '43:w $66e6 $00 $00 $67 $00' --poke '68:w $6742 $03 $00;w $6294 $03 $00;w $764a $03 $00;w $66e6 $00 $00 $64 $00' 2>&1 | cut -c1-330 | tee -a $E/stopgo.txt
echo "== (c1) NPC poked 1200 units ahead, moving, player standing" | tee $E/c_npc_near.txt
python3 gate.py ident $S/1mb_ingame_foot.sav /tmp/sk/base /tmp/sk/basesk 6,7,8,9,10,14,20,30,40 --tag npc1 --png --poke '2:w $3538 $00 $00 $5b $50;w $353c $00 $00 $64 $00;w $3560 $00 $01;w $356c $00 $00' 2>&1 | cut -c1-330 | tee -a $E/c_npc_near.txt
echo "== (c2) NPC poked 17400 units away (outside the 16-cell window), moving" | tee $E/c_npc_far.txt
python3 gate.py ident $S/1mb_ingame_foot.sav /tmp/sk/base /tmp/sk/basesk 6,10,20,30,40,60 --tag npc2 --poke '2:w $3538 $00 $00 $20 $00;w $353c $00 $00 $64 $00;w $3560 $00 $01;w $356c $00 $00' 2>&1 | cut -c1-330 | tee -a $E/c_npc_far.txt
echo "== (c3) sea in view (player moved 8 cells east, heading east)" | tee $E/c_sea.txt
python3 gate.py ident $S/1mb_ingame_foot.sav /tmp/sk/base /tmp/sk/basesk 6,7,8,9,10,11,20,21,40 --tag sea1 --png --poke '2:w $6742 $01 $00;w $6294 $01 $00;w $764a $01 $00;w $66e6 $00 $00 $75 $f8' 2>&1 | cut -c1-330 | tee -a $E/c_sea.txt
echo "== render gate \$6298 on at flip 10, off at flip 14" | tee $E/gate6298.txt
python3 gate.py ident $S/1mb_ingame_foot.sav /tmp/sk/base /tmp/sk/basesk 8,11,13,15,16,18,24,40 --tag gt1 --poke '10:w $6298 $ff $ff' --poke '14:w $6298 $00 $00' 2>&1 | cut -c1-330 | tee -a $E/gate6298.txt
echo "== HUD message timer \$7590 = 5 at flip 10 (text drawn into the window after the render)" | tee $E/msg.txt
python3 gate.py ident $S/1mb_ingame_foot.sav /tmp/sk/base /tmp/sk/basesk 8,11,12,14,16,18,24,40 --tag msg1 --png --poke '10:w $7590 $00 $05' 2>&1 | cut -c1-330 | tee -a $E/msg.txt
echo ALLDONE | tee $E/done.txt
