#!/usr/bin/env bash
# Check that the release zips hold exactly a fresh build of the current patches (md5 for md5, member lists equal).
#
#   tools/packcheck.sh [floppy.zip hd.zip]        # default: dist/Powermonger_v<ver>_patched_{floppy,hd}_<newest date>.zip
#
# A fresh build is made into build/packcheck (independent of tools/package.sh's build/dist_build), the zips are unzipped into a scratch dir.
# Prints one line per member; exit 1 on any difference.  Also checks the credit line version and the README stamp.
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
cd "$ROOT"
VER=$(sed -n 's/^TXT:.*"v\([^ ]*\) enhanced by .*".*/\1/p' patches/pm_credit.s)
FL=${1:-$(ls -1 dist/Powermonger_v${VER}_patched_floppy_*.zip | tail -1)}
HDZ=${2:-$(ls -1 dist/Powermonger_v${VER}_patched_hd_*.zip | tail -1)}
python3 tools/pmpatch.py build --out build/packcheck >/dev/null
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
[[ "$(cd "$S/fl" && find . -type f | LC_ALL=C sort | tr '\n' ' ')" == "./Powermonger_patched.st ./README.TXT " ]] || { echo "DIFF  floppy member list"; bad=1; }
cmpf Powermonger_patched.st "$S/fl/Powermonger_patched.st" build/packcheck/floppy/powermonger.st
echo "hd zip: $HDZ"
want=$(cd build/packcheck/hd && find AUTO DATA -type f | sed 's|^|POWERMONGER/|'; echo POWERMONGER/PMLATE.DAT; echo POWERMONGER/SAVEDISK.DAT; echo POWERMONGER/README.TXT)
have=$(cd "$S/hd" && find POWERMONGER -type f)
[[ "$(echo "$want" | LC_ALL=C sort)" == "$(echo "$have" | LC_ALL=C sort)" ]] || { echo "DIFF  hd member list"; diff <(echo "$want" | LC_ALL=C sort) <(echo "$have" | LC_ALL=C sort) || true; bad=1; }
while read -r f; do
    [[ $f == POWERMONGER/README.TXT ]] && continue
    cmpf "$f" "$S/hd/$f" "build/packcheck/hd/${f#POWERMONGER/}"
done < <(echo "$want" | LC_ALL=C sort)
for r in "$S/fl/README.TXT" "$S/hd/POWERMONGER/README.TXT"; do
    grep -q "v$VER" "$r" && grep -q "^Build: v$VER, git " "$r" && echo "ok    $(basename "$(dirname "$r")")/README.TXT: version $VER, $(grep '^Build:' "$r" | tr -d '\r')" || { echo "DIFF  README version / build stamp: $r"; bad=1; }
done
python3 - "$S/fl/Powermonger_patched.st" "$VER" <<'EOF' || bad=1
import sys
# the credit line text is in the payload (stored in the clear inside WAR.PRG's records, which the .st holds uncompressed)
d = open(sys.argv[1], "rb").read()
need = f"v{sys.argv[2]} enhanced by dad_prg".encode()
print(("ok    credit text %r in the floppy image" % need.decode()) if need in d else "DIFF  credit text missing")
sys.exit(0 if need in d else 1)
EOF
[[ $bad == 0 ]] && echo "PACKCHECK OK" || { echo "PACKCHECK FAILED"; exit 1; }
