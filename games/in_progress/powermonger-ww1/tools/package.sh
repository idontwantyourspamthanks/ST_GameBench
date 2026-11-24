#!/usr/bin/env bash
# Build the default patch set from the LAST COMMIT and write the distribution zips into dist/.
#
#   tools/package.sh              # export HEAD (patches/ + tools/) with git archive, build, write both zips; refuses if patches/ or tools/ differ from HEAD
#   tools/package.sh --worktree   # dry run from the working tree (README stamp says +dirty): NOT a release
#
# Needs disks/ea.st (the EA floppy image; nothing of the game is in git) and vasmm68k_mot.
# Zips (master's naming): dist/PowermongerWW1_v<ver>_patched_floppy_<date>.zip   PowermongerWW1_patched.st, README.TXT, PATCHES.TXT
#                         dist/PowermongerWW1_v<ver>_patched_hd_<date>.zip       POWERMONGER_WW1/{AUTO/WW1.PRG, data files, SAVEDISK.DAT, README.TXT, PATCHES.TXT}
# Deterministic: fixed file times, sorted members.  DATE=YYYY-MM-DD overrides the date in the names.
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"
WORKTREE=0
[[ "${1:-}" == "--worktree" ]] && WORKTREE=1
DATE=${DATE:-$(date +%F)}
STAMP="2026-01-01 00:00:00 UTC"
TOP="$(git rev-parse --show-toplevel)"
PFX="$(git rev-parse --show-prefix)"
GIT=$(git rev-parse --short HEAD)
DIRTY=0
git diff --quiet HEAD -- patches tools || DIRTY=1
if [[ $WORKTREE == 1 ]]; then
    SRC="$ROOT"; [[ $DIRTY == 1 ]] && GIT="$GIT+dirty"
    echo "(DRY RUN from the working tree: not a release)"
else
    [[ $DIRTY == 0 ]] || { echo "patches/ or tools/ differ from HEAD: commit first (or --worktree for a dry run)" >&2; exit 1; }
    SRC="$ROOT/build/pkg_src"
    rm -rf "$SRC" && mkdir -p "$SRC"
    git -C "$TOP" archive --format=tar "HEAD:${PFX}" patches tools | tar -x -C "$SRC"
    ln -s "$ROOT/disks" "$SRC/disks"
fi
echo "(building from commit $GIT)"
[[ -f disks/ea.st ]] || { echo "disks/ea.st (the EA floppy image, tools/stx2st.py) is missing" >&2; exit 1; }
# release version: one line in patches/pm_credit.s (`TXT: dc.b "v1.0 enhanced by dad_prg"`)
VER=$(sed -n 's/^TXT:.*"v\([^ ]*\) enhanced by .*".*/\1/p' "$SRC/patches/pm_credit.s")
[[ -n "$VER" ]] || { echo "version not found in patches/pm_credit.s" >&2; exit 1; }
WP="python3 $SRC/tools/wwpatch.py"
$WP verify >/dev/null
OUT="$ROOT/build/dist_build"
rm -rf "$OUT"
$WP build --floppy --out "$OUT/floppy" >/dev/null
$WP build --hd --out "$OUT/hd" >/dev/null
$WP checkdisk "$OUT/floppy/floppy.st" | tail -1
FLOPPY=$OUT/floppy/floppy.st
HD=$OUT/hd/hd
[[ -f $FLOPPY && -f $HD/AUTO/WW1.PRG && -f $HD/FX.PAK && -f $HD/SAVEDISK.DAT ]] || { echo "build output incomplete" >&2; exit 1; }

mkdir -p dist
rm -rf build/dist_stage && mkdir -p build/dist_stage/floppy build/dist_stage/hd/POWERMONGER_WW1
txt() { sed "s/@VER@/$VER/g; s/@GIT@/$GIT/g; s/\$/\r/" "$SRC/patches/$1" > "$2"; }

cp "$FLOPPY" build/dist_stage/floppy/PowermongerWW1_patched.st
txt README_FLOPPY.TXT build/dist_stage/floppy/README.TXT
txt PATCHES.TXT build/dist_stage/floppy/PATCHES.TXT
FLZIP="dist/PowermongerWW1_v${VER}_patched_floppy_${DATE}.zip"
S=build/dist_stage/hd/POWERMONGER_WW1
cp -r "$HD"/. "$S/"
txt README_HD.TXT "$S/README.TXT"
txt PATCHES.TXT "$S/PATCHES.TXT"
HDZIP="dist/PowermongerWW1_v${VER}_patched_hd_${DATE}.zip"
rm -f "$FLZIP" "$HDZIP"
find build/dist_stage -exec touch -d "$STAMP" {} +      # fixed file times, sorted member order: the same input gives the same zip bytes
(cd build/dist_stage/floppy && TZ=UTC zip -q -X "$ROOT/$FLZIP" PowermongerWW1_patched.st README.TXT PATCHES.TXT)
(cd build/dist_stage/hd && find POWERMONGER_WW1 -type f | LC_ALL=C sort | TZ=UTC zip -q -X -@ "$ROOT/$HDZIP")

md5sum "$FLOPPY" "$HD/AUTO/WW1.PRG" "$FLZIP" "$HDZIP"
