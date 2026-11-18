#!/bin/sh
# per-pass state gate for tb_car(+tb_carph): reference vs patched, tick (T) and tick+extras (X) at 8/16/32 MHz
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
P=tb_car+tb_carph; R=work/tightB/res
run() { python3 work/tightB/exp_state_tb.py "$@"; }
for scene in start:200 drive:270; do
  s=${scene%%:*}; n=${scene##*:}; snap=ste1m_race_$s.sav
  run T $snap 8 $n $R/car_${s}_T8_ref.json
  run T+$P $snap 8 $n $R/car_${s}_T8_tb.json
  for mhz in 8 16 32; do
    run X $snap $mhz $n $R/car_${s}_X${mhz}_ref.json
    run X+$P $snap $mhz $n $R/car_${s}_X${mhz}_tb.json
  done
done
echo DONE
