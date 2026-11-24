#!/usr/bin/env bash
# Play Powermonger: World War 1 Edition (enhanced) in Hatari, emulating an STE by default.
#
#   tools/play.sh                    # enhanced floppy in drive A, STE, 1 MB, TOS 1.62
#   tools/play.sh --original         # the unpatched EA game (disks/ea.st) for comparison
#   tools/play.sh --machine megaste  # st, megast, ste, megaste, tt, falcon
#   tools/play.sh --ram 4096         # RAM in KiB (default 1024; 4096 on tt/falcon)
#   tools/play.sh --mhz 8            # CPU clock for the Mega STE (Hatari starts it at 16), TT, Falcon
#   tools/play.sh --worktree         # build from the working tree (ungated patches included) instead of the last commit
#   tools/play.sh --fresh            # discard the play dir (the floppy copy, the save disk) and start clean
#
# The enhanced disk is built from the LAST COMMIT (`git archive HEAD` of patches/ and tools/), so patches that are written but
# not yet gated (uncommitted) are not in it.  The hard-disk build is not gated yet, so there is no --hd.
#
# Machines and TOS: st/megast TOS 1.04, ste 1.62, megaste 2.06, tt 3.06, falcon 4.04 (override with --tos FILE).
# TT: set the desktop to ST low first (the game never sets the screen mode; the original does the same).
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
TOSDIR="$ROOT/../../../tos"     # gamebench/tos
MACHINE=ste
RAM=""
VARIANT=patched
FRESH=0
WORKTREE=0
MHZ=""
TOS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --original) VARIANT=original ;;
        --machine)  MACHINE="$2"; shift ;;
        --ram)      RAM="$2"; shift ;;
        --mhz)      MHZ="$2"; shift ;;
        --tos)      TOS="$2"; shift ;;
        --worktree) WORKTREE=1 ;;
        --fresh)    FRESH=1 ;;
        -h|--help)  sed -n '2,23p' "$0"; exit 0 ;;
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

PLAY="$ROOT/build/play-$VARIANT"
[[ $FRESH == 1 ]] && rm -rf "$PLAY"
mkdir -p "$PLAY"

if [[ $VARIANT == original ]]; then
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
    python3 "$SRC/tools/wwpatch.py" build --floppy --out "$PLAY/build" >/dev/null
    cp "$PLAY/build/floppy.st" "$PLAY/ww1_d1.st"
fi
[[ -f "$PLAY/savedisk.st" ]] || python3 -c "
import sys; sys.path.insert(0, sys.argv[1] + '/tools')
import wwpatch
blk = wwpatch.resident_bytes(0x1C860, 512)      # the game's own 'SAVED GAME DISC' boot sector (as tools/pmww.py save_disk_image)
assert blk[:4] == b'POWE'
open(sys.argv[2], 'wb').write(blk + bytes(800 * 512 - 512))" "$SRC" "$PLAY/savedisk.st"

COMMON=(--machine "$MACHINE" --tos "$TOS" --memsize "$RAM" --monitor rgb --confirm-quit no --protect-floppy off)
[[ -n "$MHZ" ]] && COMMON+=(--cpuclock "$MHZ")
echo "Powermonger WW1 ($VARIANT, floppy) on $MACHINE, ${RAM} KiB, TOS: $(basename "$TOS")"
echo "Game disk: $PLAY/ww1_d1.st (refreshed every run); blank save disk: $PLAY/savedisk.st"
# NOT named A.st / B.st (Hatari auto-inserts those)
exec hatari "${COMMON[@]}" --disk-a "$PLAY/ww1_d1.st"
