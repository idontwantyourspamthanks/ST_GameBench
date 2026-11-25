#!/usr/bin/env bash
# Play Powermonger: World War 1 Edition (enhanced) in Hatari, emulating an STE by default.
#
#   tools/play.sh                    # enhanced floppy in drive A, STE, 1 MB, TOS 1.62
#   tools/play.sh --hd               # the hard-disk build (ACSI image + HDDRIVER, see ../../../hd/README.md); Hatari's GEMDOS folder on a Falcon
#   tools/play.sh --hd --gemdos      # with --hd: Hatari's GEMDOS folder as drive C instead of an ACSI image (no driver needed)
#   tools/play.sh --original         # the unpatched EA game (disks/ea.st) for comparison (--hd: the HD loader + pm_nokeydisk only)
#   tools/play.sh --machine megaste  # st, megast, ste, megaste, tt, falcon
#   tools/play.sh --ram 4096         # RAM in KiB (default 1024; 4096 on tt/falcon)
#   tools/play.sh --mhz 8            # CPU clock for the Mega STE (Hatari starts it at 16), TT, Falcon
#   tools/play.sh --worktree         # build from the working tree (ungated patches included) instead of the last commit
#   tools/play.sh --fresh            # discard the play dir (the floppy copy, the save disk) and start clean
#
# The enhanced disk is built from the LAST COMMIT (`git archive HEAD` of patches/ and tools/), so patches that are written but
# not yet gated (uncommitted) are not in it.  The hard-disk build keeps its saves in SAVEDISK.DAT (rebuilt, so lost, on every run of the
# ACSI image; with --gemdos or on a Falcon they persist in build/play-*-hd/hdfolder).  Hatari's Falcon has no ACSI: --hd falls back to
# the GEMDOS folder there.
#
# Machines and TOS: st/megast TOS 1.04, ste 1.62, megaste 2.06, tt 3.06, falcon 4.04 (override with --tos FILE).
# TT / Falcon: any desktop mode works (the loader sets ST low / an ST-compatible mode itself).
#
# Saves go to a SECOND disk: a blank save disk (the game's own "SAVED GAME DISC" boot sector + zeros; Hatari can't run the
# game's own FORMAT) is created next to the game disk (savedisk.st).  Swap it into drive A through Hatari's menu
# (F12 -> Floppy disks -> A:) when the game asks for the save disk, and the game disk back afterwards.
# --original: the unpatched game asks for the original Powermonger disk on the first START NEW CONQUEST (key-disk check);
# swap in ../../done/powermonger/disks/protected.st, then the WW1 disk back.
#
# In-game: F12 opens the Hatari menu; AltGr+M toggles mouse grab.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
export PYTHONPATH="$ROOT/../../../tools${PYTHONPATH:+:$PYTHONPATH}"   # stharness, for the git-archive export in build/play-src
TOSDIR="$ROOT/../../../tos"     # gamebench/tos
MACHINE=ste
RAM=""
VARIANT=patched
FRESH=0
WORKTREE=0
MEDIA=floppy
GEMDOS=0
HDDIR="$ROOT/../../../hd"       # gamebench/hd (HDDRIVER, not in git)
MHZ=""
TOS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --original) VARIANT=original ;;
        --floppy)   MEDIA=floppy ;;
        --hd)       MEDIA=hd ;;
        --gemdos)   GEMDOS=1 ;;
        --machine)  MACHINE="$2"; shift ;;
        --ram)      RAM="$2"; shift ;;
        --mhz)      MHZ="$2"; shift ;;
        --tos)      TOS="$2"; shift ;;
        --worktree) WORKTREE=1 ;;
        --fresh)    FRESH=1 ;;
        -h|--help)  sed -n '2,28p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

if [[ -z "$RAM" ]]; then
    case "$MACHINE" in tt|falcon) RAM=4096 ;; *) RAM=1024 ;; esac
fi
if [[ -z "$TOS" ]]; then
    case "$MACHINE" in
        st|megast) TOS="$TOSDIR/TOS_1_04.img" ;;
        ste)       TOS="$TOSDIR/TOS_1_62.img" ;;
        megaste)   TOS="$TOSDIR/TOS_2_06.img" ;;
        tt)        TOS="$TOSDIR/TOS_3_06_uk.img" ;;
        falcon)    TOS="$TOSDIR/TOS_4_04.img" ;;
        *) echo "no default TOS for --machine $MACHINE; pass --tos FILE" >&2; exit 2 ;;
    esac
fi
[[ -f "$TOS" ]] || { echo "TOS image not found: $TOS" >&2; exit 1; }
[[ -f "$ROOT/disks/ea.st" ]] || { echo "disks/ea.st not found (README: tools/stx2st.py from the EA .stx)" >&2; exit 1; }

PLAY="$ROOT/build/play-$VARIANT"; [[ $MEDIA == hd ]] && PLAY="$PLAY-hd"
[[ $FRESH == 1 ]] && rm -rf "$PLAY"
mkdir -p "$PLAY"

if [[ $VARIANT == original && $MEDIA == floppy ]]; then
    cp "$ROOT/disks/ea.st" "$PLAY/ww1_d1.st"
    SRC="$ROOT"
else
    if [[ $WORKTREE == 1 ]]; then
        SRC="$ROOT"
        echo "(building from the working tree: ungated patches included)"
    else
        SRC="$ROOT/build/play-src"
        rm -rf "$SRC" && mkdir -p "$SRC"
        TOP="$(git -C "$ROOT" rev-parse --show-toplevel)"
        git -C "$TOP" archive --format=tar "HEAD:$(git -C "$ROOT" rev-parse --show-prefix)" patches tools | tar -x -C "$SRC"
        ln -s "$ROOT/disks" "$SRC/disks"
        echo "(building from commit $(git -C "$ROOT" rev-parse --short HEAD))"
    fi
    if [[ $MEDIA == floppy ]]; then
        python3 "$SRC/tools/wwpatch.py" build --floppy --out "$PLAY/build" >/dev/null
        cp "$PLAY/build/floppy.st" "$PLAY/ww1_d1.st"
    elif [[ $VARIANT == original ]]; then
        python3 "$SRC/tools/wwpatch.py" build --hd --only pm_nokeydisk --out "$PLAY/build" >/dev/null
    else
        python3 "$SRC/tools/wwpatch.py" build --hd --out "$PLAY/build" >/dev/null
    fi
fi
if [[ $MEDIA == floppy ]]; then
    [[ -f "$PLAY/savedisk.st" ]] || python3 -c "
import sys; sys.path.insert(0, sys.argv[1] + '/tools')
import wwpatch
blk = wwpatch.resident_bytes(0x1C860, 512)      # the game's own 'SAVED GAME DISC' boot sector (as tools/pmww.py save_disk_image)
assert blk[:4] == b'POWE'
open(sys.argv[2], 'wb').write(blk + bytes(800 * 512 - 512))" "$SRC" "$PLAY/savedisk.st"
fi

COMMON=(--machine "$MACHINE" --tos "$TOS" --memsize "$RAM" --monitor rgb --confirm-quit no --protect-floppy off)
[[ -n "$MHZ" ]] && COMMON+=(--cpuclock "$MHZ")
if [[ $MEDIA == floppy ]]; then
    echo "Powermonger WW1 ($VARIANT, floppy) on $MACHINE, ${RAM} KiB, TOS: $(basename "$TOS")"
    echo "Game disk: $PLAY/ww1_d1.st (refreshed every run); blank save disk: $PLAY/savedisk.st"
    # NOT named A.st / B.st (Hatari auto-inserts those)
    exec hatari "${COMMON[@]}" --disk-a "$PLAY/ww1_d1.st"
fi

# Hard disk: the built folder (AUTO\WW1.PRG, the data files, SAVEDISK.DAT) as Hatari's GEMDOS drive C or on an ACSI image with HDDRIVER.
HDSRC="$PLAY/build/hd"
if [[ $GEMDOS == 1 || $MACHINE == falcon || ! -f "$HDDIR/HDDRIVER.SYS" ]]; then
    [[ $GEMDOS == 1 ]] || echo "(no ACSI + HDDRIVER here: $MACHINE or $HDDIR/HDDRIVER.SYS missing; using Hatari's GEMDOS folder as C:)"
    rm -rf "$PLAY/hdfolder" && cp -r "$HDSRC" "$PLAY/hdfolder"
    echo "Powermonger WW1 ($VARIANT, hard disk, GEMDOS folder) on $MACHINE, ${RAM} KiB, TOS: $(basename "$TOS")"
    exec hatari "${COMMON[@]}" --harddrive "$PLAY/hdfolder" --fast-boot yes
fi
python3 - "$ROOT" "$HDSRC" "$PLAY/hd.img" <<'PY'
import sys
from pathlib import Path
root = sys.argv[1]
sys.path.insert(0, root + "/../../done/hunter/tools")
from hunter import build_hd
build_hd(Path(sys.argv[3]), game=Path(sys.argv[2]), autorun="C:\\NONE.TOS")
PY
echo "Powermonger WW1 ($VARIANT, hard disk, ACSI + HDDRIVER) on $MACHINE, ${RAM} KiB, TOS: $(basename "$TOS")"
echo "Disk image: $PLAY/hd.img (rebuilt every run)"
exec hatari "${COMMON[@]}" --gemdos-drive skip --acsi "0=$PLAY/hd.img" --fast-boot yes
