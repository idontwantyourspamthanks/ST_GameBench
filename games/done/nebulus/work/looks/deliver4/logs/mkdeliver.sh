#!/bin/bash
# NebConveyor delivery: mirror files (real-tree paths), PATCH.diff against the gate2-merged tree, logs, shots, dadprg.diff.   usage: mkdeliver.sh OUTDIR
set -e
R=/home/ryan/Code/AtariST/gamebench; N=games/in_progress/nebulus; C=/tmp/nlcv/$N; BASE=/tmp/nlcv/basetree/$N; D=$1
rm -rf $D/patches $D/work $D/logs $D/shots $D/PATCH.diff $D/dadprg.diff; mkdir -p $D/logs $D/shots
# files whose content is path-free
for f in patches/ed_editor.s patches/ed_overlay.nep patches/README_HD.TXT patches/README_FLOPPY.TXT work/editor/gen_ed.py work/editor/ovl.py work/notes/editor.md; do mkdir -p $D/$(dirname $f); cp $C/$f $D/$f; done
# pre-existing gate scripts: back to the gate2 form of their paths (real tree for games/tools, /tmp/nlg scratch), so the diff shows only this round's edits
for f in work/editor/e150.py work/editor/e200.py; do mkdir -p $D/$(dirname $f); sed -e "s#/tmp/nlcv/games#$R/games#g" -e "s#/tmp/nlcv/tools#$R/tools#g" -e "s#/tmp/nlcv#/tmp/nlg#g" $C/$f > $D/$f; done
# new gate scripts: real tree for games/tools, own scratch /tmp/nlcv/x
for f in work/editor/e208.py work/editor/e208_ab.py; do sed -e "s#/tmp/nlcv/games#$R/games#g" -e "s#/tmp/nlcv/tools#$R/tools#g" $C/$f > $D/$f; done
(cd $D; for f in $(find patches work -type f | sort); do if [ -f $BASE/$f ]; then diff -u --label a/$f --label b/$f $BASE/$f $f; else diff -u --label /dev/null --label b/$f /dev/null $f; fi; done) > $D/PATCH.diff || true
# the diff applies to the base
T=$(mktemp -d); cp -a $BASE/. $T/; (cd $T && patch -p1 -s < $D/PATCH.diff) && (cd $D; for f in $(find patches work -type f); do cmp -s $f $T/$f || echo "PATCH MISMATCH $f"; done); rm -rf $T
# dadprg: this round only (base = HEAD + deliver3/dadprg.diff)
(cd /tmp/nlcv; for f in README.md api/app/services/hub/ncmp/legend.rb api/test/controllers/api/hub_browse_test.rb api/test/services/hub/ncmp_test.rb; do diff -u --label a/$f --label b/$f dadbase/$f /home/ryan/Code/dadprg/$f; done) > $D/dadprg.diff || true
cp /tmp/nlcv/x/logs/*.log /tmp/nlcv/x/logs/*.txt /tmp/nlcv/x/logs/master.progress $D/logs/ 2>/dev/null || true
for d in /tmp/nlcv/x/user/e208_*_out; do [ -d $d ] && mkdir -p $D/shots/$(basename $d _out) && cp $d/*.png $D/shots/$(basename $d _out)/; done
cp /tmp/nlcv/deliver4/conveyor_notes.md $D/
(cd $D; find . -type f | sort | xargs md5sum) > /tmp/nlcv/x/deliver_md5.txt; wc -l $D/PATCH.diff $D/dadprg.diff; du -sh $D
