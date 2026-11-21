#!/bin/bash
cd /tmp/msrmus
S1=/tmp/msrmus/s1/MOONSHR; FX=/tmp/msrmus/fixroot/MOONSHR
python3 mus.py orig fx megaste o8_ms_fx --clocks 8 --nonative > out/o8_ms_fx.stdout 2>&1
python3 mus.py orig music megaste o8_ms_music --clocks 8 --nonative > out/o8_ms_music.stdout 2>&1
python3 mus.py $S1 fx megaste v8_ms_fx --clocks 8 --nonative > out/v8_ms_fx.stdout 2>&1
python3 mus.py $S1 music megaste v8_ms_music --clocks 8 --nonative > out/v8_ms_music.stdout 2>&1
python3 mus.py $FX music megaste f8_ms_music --clocks 8 --nonative > out/f8_ms_music.stdout 2>&1
echo ALLDONE3
