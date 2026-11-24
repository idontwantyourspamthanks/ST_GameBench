#!/usr/bin/env bash
# Check that the release zips hold exactly a fresh build of the current patches (md5 for md5, member lists equal).
#
#   tools/packcheck.sh [floppy.zip hd.zip]     # default: the newest dist/PowermongerWW1_v<ver>_patched_{floppy,hd}_*.zip
#
# A fresh build is made into build/packcheck (independent of tools/package.sh's build/dist_build) from the working tree; the zips are
# unzipped into a scratch dir.  One line per member; exit 1 on any difference.  Also checks the README version / stamp and the credit text.
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"
VER=$(sed -n 's/^TXT:.*"v\([^ ]*\) enhanced by .*".*/\1/p' patches/pm_credit.s)
FL=${1:-$(ls -1 dist/PowermongerWW1_v${VER}_patched_floppy_*.zip | tail -1)}
HDZ=${2:-$(ls -1 dist/PowermongerWW1_v${VER}_patched_hd_*.zip | tail -1)}
python3 tools/wwpatch.py build --floppy --out build/packcheck/floppy >/dev/null
python3 tools/wwpatch.py build --hd --out build/packcheck/hd >/dev/null
S=$(mktemp -d /tmp/packcheck.XXXXXX)
trap 'rm -rf "$S"' EXIT
mkdir "$S/fl" "$S/hd"
unzip -q "$FL" -d "$S/fl"
unzip -q "$HDZ" -d "$S/hd"
bad=0
cmpf() { # label zipfile freshfile
    local a b
    a=$(md5sum < "$2" | cut -d' ' -f1); b=$(md5sum < "$3" | cut -d' ' -f1)
    if [[ $a == "$b" ]]; then echo "same  $a  $1"; else echo "DIFF  zip $a fresh $b  $1"; bad=1; fi
}
echo "floppy zip: $FL"
[[ "$(cd "$S/fl" && find . -type f | LC_ALL=C sort | tr '\n' ' ')" == "./PATCHES.TXT ./PowermongerWW1_patched.st ./README.TXT " ]] || { echo "DIFF  floppy member list"; bad=1; }
cmpf PowermongerWW1_patched.st "$S/fl/PowermongerWW1_patched.st" build/packcheck/floppy/floppy.st
echo "hd zip: $HDZ"
want=$(cd build/packcheck/hd/hd && find . -type f | sed 's|^\./|POWERMONGER_WW1/|'; echo POWERMONGER_WW1/README.TXT; echo POWERMONGER_WW1/PATCHES.TXT)
have=$(cd "$S/hd" && find POWERMONGER_WW1 -type f)
[[ "$(echo "$want" | LC_ALL=C sort)" == "$(echo "$have" | LC_ALL=C sort)" ]] || { echo "DIFF  hd member list"; diff <(echo "$want" | LC_ALL=C sort) <(echo "$have" | LC_ALL=C sort) || true; bad=1; }
while read -r f; do
    [[ $f == POWERMONGER_WW1/README.TXT || $f == POWERMONGER_WW1/PATCHES.TXT ]] && continue
    cmpf "$f" "$S/hd/$f" "build/packcheck/hd/hd/${f#POWERMONGER_WW1/}"
done < <(echo "$want" | LC_ALL=C sort)
for r in "$S/fl/README.TXT" "$S/hd/POWERMONGER_WW1/README.TXT"; do
    grep -q "v$VER" "$r" && grep -q "^Build: v$VER, git " "$r" && echo "ok    $(basename "$(dirname "$r")")/README.TXT: version $VER, $(grep '^Build:' "$r" | tr -d '\r')" || { echo "DIFF  README version / build stamp: $r"; bad=1; }
done
python3 - "$S/fl/PowermongerWW1_patched.st" "$VER" <<'PY' || bad=1
import sys
d = open(sys.argv[1], "rb").read()
need = f"v{sys.argv[2]} enhanced by dad_prg".encode()
print(("ok    credit text %r in the floppy image" % need.decode()) if need in d else "DIFF  credit text missing")
sys.exit(0 if need in d else 1)
PY
[[ $bad == 0 ]] && echo "PACKCHECK OK" || { echo "PACKCHECK FAILED"; exit 1; }
