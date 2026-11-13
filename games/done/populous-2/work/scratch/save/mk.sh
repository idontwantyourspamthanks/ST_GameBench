#!/usr/bin/env bash
# build the default set + the three save patches: mk.sh hd|floppy|zero OUTDIR
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2
kind=$1; out=$2
names=$(python3 tools/pop2patch.py list | awk 'NR>1 && $2=="yes"{print $1}' | grep -v pop2_floppy_head | tr '\n' ' ')
case $kind in
 hd)     python3 tools/pop2patch.py build --only $names pop2_save pop2_save_w pop2_save_d --out $out ;;
 floppy) python3 tools/pop2patch.py build --floppy --only $names pop2_floppy_head pop2_save pop2_save_w pop2_save_d --out $out ;;
 ref)    python3 tools/pop2patch.py build --only $names --out $out ;;
 reff)   python3 tools/pop2patch.py build --floppy --only $names pop2_floppy_head --out $out ;;
esac
