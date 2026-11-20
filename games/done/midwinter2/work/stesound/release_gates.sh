#!/usr/bin/env bash
# Release gates on the SHIPPED zips: build twice (identical md5), unzip, gate with sound on + PSG check.   work/stesound/release_gates.sh
R=/home/ryan/Code/AtariST/gamebench/games/done/midwinter2; cd $R
VER=$(python3 tools/mw2patch.py version); DATE=$(date +%F)
echo "version $VER date $DATE"
tools/package.sh > /tmp/mw2s/pkg1.log 2>&1; echo "build 1 exit $?"; tail -4 /tmp/mw2s/pkg1.log
cp dist/Midwinter2_v${VER}_patched_floppies_${DATE}.zip /tmp/mw2s/fl1.zip; cp dist/Midwinter2_v${VER}_patched_${DATE}.zip /tmp/mw2s/hd1.zip
tools/package.sh > /tmp/mw2s/pkg2.log 2>&1; echo "build 2 exit $?"; tail -4 /tmp/mw2s/pkg2.log
md5sum /tmp/mw2s/fl1.zip /tmp/mw2s/hd1.zip dist/Midwinter2_v${VER}_patched_floppies_${DATE}.zip dist/Midwinter2_v${VER}_patched_${DATE}.zip
cmp /tmp/mw2s/fl1.zip dist/Midwinter2_v${VER}_patched_floppies_${DATE}.zip && cmp /tmp/mw2s/hd1.zip dist/Midwinter2_v${VER}_patched_${DATE}.zip && echo "BUILD TWICE: IDENTICAL"
rm -rf /tmp/mw2s/rel && mkdir -p /tmp/mw2s/rel && (cd /tmp/mw2s/rel && unzip -oq $R/dist/Midwinter2_v${VER}_patched_floppies_${DATE}.zip && md5sum * )
cd work/stesound
python3 - <<'P'
import sys; sys.path.insert(0, '../../tools')
import mw2patch as M
for n in ('FFA_boot', 'FFB_graphics', 'FFC_missions', 'FFD_campaign_blank'):
    assert M.msa_to_st(open(f'/tmp/mw2s/rel/{n}.msa', 'rb').read()) == open(f'/tmp/mw2s/rel/{n}.st', 'rb').read(), n
print('shipped .msa == shipped .st: 4/4')
P
export MW2S_SOUND=50066 MW2S_EXTRA="--trace fdc,psg_write"
D=/tmp/mw2s/rel
echo "== swap STE 1 drive A+B"; python3 swapgate.py rel_ste_d1 ste 162 8 1 $D A B 2>&1 | grep -E "SWAP|PSGCHECK|RAMCHECK" | cut -c1-230
echo "== swap Mega STE 8 / 16 MHz"; for c in 8 16; do python3 swapgate.py rel_mste_$c megaste 206 $c 1 $D B 2>&1 | grep -E "SWAP|PSGCHECK|RAMCHECK" | cut -c1-230; done
echo "== boot gates (first restore + PSG): Mega STE 8/16, .msa on STE"
for spec in "rel_a_mste8 megaste 8" "rel_a_mste16 megaste 16"; do set -- $spec; python3 bootgate.py $1 $2 $3 $D --expect pass 2>&1 | grep -E "^(GATE|PSGCHECK|VERDICT)" | cut -c1-230; done
python3 bootgate.py rel_a_ste8_msa ste 8 $D --expect pass --ext msa 2>&1 | grep -E "^(GATE|PSGCHECK|VERDICT)" | cut -c1-230
echo "== boot to the orange prompt + PSG check: Mega ST, TT"
for spec in "rel_b_megast megast 104 1024" "rel_b_tt tt 306 4096"; do set -- $spec; MW2S_MEM=$4 python3 ymab.py $1 $2 $3 8 1 $D 2>&1 | grep -E "orange|RAM|Error"; python3 psgcheck.py /tmp/mw2s/$1/fdc.trace $1 | tail -1 | cut -c1-230; done
echo "== RELEASE GATES DONE"
