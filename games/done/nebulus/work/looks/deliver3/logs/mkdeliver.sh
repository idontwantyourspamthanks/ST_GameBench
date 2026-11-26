#!/bin/bash
# mirror + PATCH.diff for deliver3 (base = deliver2-merged tree: real tree HEAD + deliver2 files)
R=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus; D=$R/work/looks/deliver3; M=/tmp/nld/games/in_progress/nebulus; D2=$R/work/looks/deliver2
mkdir -p $D/patches $D/work/editor $D/work/notes
: > $D/PATCH.diff
for f in patches/ed_editor.s patches/ed_overlay.nep patches/README_HD.TXT patches/README_FLOPPY.TXT work/notes/editor.md; do
  mkdir -p $D/$(dirname $f); cp $M/$f $D/$f
  diff -u --label a/$f --label b/$f $D2/$f $M/$f >> $D/PATCH.diff
done
for f in work/editor/e150.py; do cp $M/$f $D/$f; diff -u --label a/$f --label b/$f $R/$f $M/$f >> $D/PATCH.diff; done
for f in work/editor/e203.py work/editor/e203_study.py work/editor/e203_study2.py; do cp $M/$f $D/$f; diff -u --label /dev/null --label b/$f /dev/null $M/$f >> $D/PATCH.diff; done
cp $M/work/editor/ulib_ui.py $D/work/editor/ulib_ui.py     # mirror only (deliver2's with /tmp/nld paths and mk_snap for machine 'st')
