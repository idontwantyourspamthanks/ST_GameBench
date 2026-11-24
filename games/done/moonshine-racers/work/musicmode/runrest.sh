#!/bin/bash
cd /tmp/msrmus
S1=/tmp/msrmus/s1/MOONSHR; FX=/tmp/msrmus/fixroot/MOONSHR
python3 mus.py $FX music ste f_ste_music > out/f_ste_music.stdout 2>&1
python3 mus.py $FX fx ste f_ste_fx > out/f_ste_fx.stdout 2>&1
python3 mus.py orig fx megaste o_ms_fx --clocks 16 > out/o_ms_fx.stdout 2>&1
python3 mus.py orig music megaste o_ms_music --clocks 16 > out/o_ms_music.stdout 2>&1
python3 mus.py $S1 fx megaste v_ms_fx --clocks 16 > out/v_ms_fx.stdout 2>&1
python3 mus.py $S1 music megaste v_ms_music --clocks 16 > out/v_ms_music.stdout 2>&1
python3 mus.py $FX music megaste f_ms_music --clocks 16 > out/f_ms_music.stdout 2>&1
python3 mus.py $FX fx megaste f_ms_fx --clocks 16 > out/f_ms_fx.stdout 2>&1
echo ALLDONE2
