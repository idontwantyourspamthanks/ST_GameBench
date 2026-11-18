#!/bin/bash
# collects the raw outputs quoted by work/notes/mxfast.md into res/RAW.txt
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/mxfast
{
echo "##### Hatari profile categories (prof_mx.py + prof_ana2.py; 8 MHz, race_drive, X_TEST=1 = one extra per racing tick, 150 VBL)"
for v in X M G; do python3 prof_ana2.py res/prof_${v}_x1.txt $v; done
echo; echo "##### model (Musashi) whole tick with 1 extra, start scene, zig, passes 30/31/60 (mxcost.py)"
for v in X M G; do echo "--- $v"; python3 mxcost.py $v start zig 1 30 31 60 2>&1 | grep -E "segment|blob:(saveundo|restoreundo|prerestore|slotreset)|mx_pre|all"; done
echo; echo "##### extra frame by routine, G, start scene (mxcost.py ... game)"
python3 mxcost.py G start zig 1 30 31 60 game 2>&1 | sed -n '/segment 1/,/segment 2/p' | head -24
echo; echo "##### steered 8 MHz racing windows (ext_sum2.py)"
python3 ext_sum2.py res/ext_X_8.json res/ext_M8_s0.json res/ext_M8_sm3.json res/ext_M8_sm6.json res/ext_M8_sm9.json res/ext_G8_sm6.json res/ext_G8_sm3.json res/ext_G8_s0.json res/ext_G8_sp3.json res/ext_G8_sp6.json res/ext_X_16.json res/ext_M16_s0.json res/ext_G16_s0.json 2>/dev/null
echo; echo "##### emulator X vs M (every flip, whole RAM)"; cat res/emu_X_vs_M.final.txt | sed -E 's/\[\(.*\)\]/[...]/' | cut -c1-300
echo; echo "##### emulator X vs G"; cat res/emu_X_vs_G.final2.txt 2>/dev/null | sed -E 's/\[\(.*\)\]/[...]/' | cut -c1-520
echo; echo "##### negative controls M"; cat res/neg_M.txt | cut -c1-240
echo "##### negative controls G"; cat res/neg_G.txt | cut -c1-240
echo; echo "##### main frames vs the default set without pacer (pixmain.py)"; cat res/pixmain_M.txt res/pixmain_G.txt
echo; echo "##### Hatari per-pass state gates (gate_report.py)"
for s in start drive up; do for c in "M 16" "M 32" "G 16" "G 32"; do python3 gate_report.py $s $c 2>&1 | cut -c1-420; done; done
echo; echo "##### Hatari state run counts"; grep hits res/state_log.txt res/state_log_G.txt res/state_log_T.txt 2>/dev/null
echo; echo "##### cold boots"; cat res/cold_hd.txt 2>/dev/null
echo; echo "##### 2-minute drives"; cat res/play2.txt 2>/dev/null
} > res/RAW.txt 2>&1
wc -l res/RAW.txt
