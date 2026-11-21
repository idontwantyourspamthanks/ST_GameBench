#!/bin/bash
cd /tmp/msrmus
S1=/tmp/msrmus/s1/MOONSHR
python3 mus.py orig fx ste o_ste_fx > out/o_ste_fx.stdout 2>&1
python3 mus.py orig music ste o_ste_music > out/o_ste_music.stdout 2>&1
python3 mus.py $S1 fx ste v_ste_fx > out/v_ste_fx.stdout 2>&1
python3 mus.py $S1 music ste v_ste_music > out/v_ste_music.stdout 2>&1
echo ALLDONE
