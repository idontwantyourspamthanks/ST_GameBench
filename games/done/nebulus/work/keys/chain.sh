#!/bin/bash
export IMG=/tmp/nf/img_new.img
python3 g1.py fin ste keys > /tmp/nf/fin_g1_ste.log 2>&1
WD=/tmp/nf/fa python3 t3.py /tmp/nf/fin_f10.json ste xdo 20 4 0,1,2 > /tmp/nf/fin_f10.log 2>&1
WD=/tmp/nf/fb KEY=d SC=32 python3 t3.py /tmp/nf/fin_d.json ste xdo 100 4 0,1,2 > /tmp/nf/fin_d.log 2>&1
python3 t7.py ste > /tmp/nf/fin_t7_ste.log 2>&1
python3 g1.py finm megaste keys > /tmp/nf/fin_g1_mste.log 2>&1
python3 ../editor/e97.py > /tmp/nf/fin_e97.log 2>&1
touch /tmp/nf/chain.done
