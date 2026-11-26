#!/bin/bash
# assemble conveyor_notes.md (hand-written parts + tables generated from the logs) and (re)write the delivery
X=/tmp/nlcv/x; L=$X/logs; D=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/looks/deliver4; N=/tmp/nlcv/deliver4
res(){ [ -f $L/$1.log ] && grep -h '^checkpoints\|^bytes compared\|^RESULT\|^FAIL' $L/$1.log | cut -c1-300 || echo "(not run yet)"; }
{
cat $N/conveyor_notes.md
echo
echo "**Result** (\`logs/ab_cmp.log\`, session part 1, 116 checkpoints):"
echo '```'; res ab_cmp; echo '```'
cat $N/notes_ab_mid.md
echo '```'; res ab3_cmp; echo '```'
[ -f $L/ab3_new.log ] && { echo "Validator parity, new build (\`logs/ab3_new.log\`: name, the game keeps the magic, \`ovl.py validate\` accepts):"; echo '```'; grep -h 'validator (\|PARITY\|title vbl' $L/ab3_new.log | cut -c1-200; echo '```'; }
echo
echo "### 6.4 Regression gates on the build with the conveyors [obs] (\`logs/<gate>_<machine>.log\`; generated from the logs by \`mktable.py\`)"
python3 $X/mktable.py
cat $N/notes_64_tail.md
cat $N/notes_tail.md
} > $X/conveyor_notes_final.md
cp $X/conveyor_notes_final.md $X/cn_tmp.md
mkdir -p $D
# mkdeliver copies /tmp/nlcv/deliver4/conveyor_notes.md: give it the assembled file
sed -e "s#cp /tmp/nlcv/deliver4/conveyor_notes.md#cp $X/conveyor_notes_final.md#" $X/mkdeliver.sh > $X/mkdeliver_final.sh; chmod +x $X/mkdeliver_final.sh
$X/mkdeliver_final.sh $D
mv $D/conveyor_notes_final.md $D/conveyor_notes.md
cp $L/size_by_label.py $X/master.sh $X/master3.sh $X/master4.sh $X/mktable.py $X/mkdeliver.sh $X/finalize.sh $D/logs/ 2>/dev/null
ls $D $D/logs | head -80
