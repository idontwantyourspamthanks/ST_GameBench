#!/usr/bin/env bash
# Play the patched Powermonger in Hatari, emulating an STE by default.
#
#   tools/play.sh                  # patched one-disk floppy in drive A, STE, 1 MB, TOS 1.62
#   tools/play.sh --hd             # patched hard-disk build (ACSI image + HDDRIVER, see ../../hd/README.md)
#   tools/play.sh --original       # the unpatched game for comparison (floppy: disks/protected.st; --hd: the HD loader with no patches)
#   tools/play.sh --machine megaste  # st, megast, ste, megaste, tt, falcon
#   tools/play.sh --ram 4096       # RAM in KiB (default 1024; 4096 on tt/falcon)
#   tools/play.sh --mhz 8          # CPU clock for the Mega STE (Hatari starts it at 16), TT, Falcon
#   tools/play.sh --gemdos         # with --hd: Hatari's GEMDOS folder as drive C instead of an ACSI image (no driver needed)
#   tools/play.sh --fresh          # discard the play dir (the floppy copy, the save disk) and start clean
#
# Machines and TOS: st/megast TOS 1.04, ste 1.62, megaste 2.06, tt 3.06, falcon 4.04 (override with --tos FILE).  The STE-class
# machines (everything except st/megast) play the samples through the DMA sound chip; plain ST keeps the YM.  Hatari's Falcon has no
# ACSI, so --hd on a Falcon falls back to the GEMDOS folder.
#
# The floppy build is rebuilt and copied to build/play-*/ on every run (the game never writes to it); the game writes saves to a SECOND disk (the game formats it
# itself: "FORMAT THE POWERMONGER DISK?").  A blank save disk is created next to the play disk (savedisk.st); swap it into drive A
# through Hatari's menu (F12 -> Floppy disks -> A:) when the game asks for the SAVE GAME DISK, and the game disk back afterwards.
# The hard-disk build keeps its saves in SAVEDISK.DAT (rebuilt, so they are lost, on every run of the ACSI image; with --gemdos
# they persist in build/play-*/hdfolder).
#
# In-game: SPACE skips the title pictures.  F12 opens the Hatari menu; AltGr+M toggles mouse grab.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
TOSDIR="$ROOT/../../tos"     # gamebench/tos
HDDIR="$ROOT/../../hd"       # gamebench/hd (HDDRIVER, not in git)
MACHINE=ste
RAM=""
VARIANT=patched
MEDIA=floppy
GEMDOS=0
FRESH=0
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
        --fresh)    FRESH=1 ;;
        -h|--help)  sed -n '2,22p' "$0"; exit 0 ;;
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

PLAY="$ROOT/build/play-$VARIANT-$MEDIA"
[[ $FRESH == 1 ]] && rm -rf "$PLAY"
mkdir -p "$PLAY"

COMMON=(--machine "$MACHINE" --tos "$TOS" --memsize "$RAM" --monitor rgb --confirm-quit no --protect-floppy off)
[[ -n "$MHZ" ]] && COMMON+=(--cpuclock "$MHZ")

if [[ $MEDIA == floppy ]]; then
    # NOT named A.st / B.st (Hatari auto-inserts those)
    if [[ $VARIANT == original ]]; then
        [[ -f "$ROOT/disks/protected.st" ]] || { echo "disks/protected.st not found" >&2; exit 1; }
        cp "$ROOT/disks/protected.st" "$PLAY/pm_d1.st"
    else
        python3 "$ROOT/tools/pmpatch.py" build --floppy --out "$ROOT/build/stage-floppy" >/dev/null
        cp "$ROOT/build/stage-floppy/floppy/powermonger.st" "$PLAY/pm_d1.st"
    fi
    [[ -f "$PLAY/savedisk.st" ]] || head -c 819200 /dev/zero > "$PLAY/savedisk.st"
    echo "Powermonger ($VARIANT, floppy) on $MACHINE, ${RAM} KiB, TOS: $(basename "$TOS")"
    echo "Game disk: $PLAY/pm_d1.st (refreshed every run); blank save disk: $PLAY/savedisk.st"
    exec hatari "${COMMON[@]}" --disk-a "$PLAY/pm_d1.st"
fi

# Hard disk: stage the folder (patched or not), then give Hatari an ACSI image with HDDRIVER or the folder itself.
if [[ $VARIANT == patched ]]; then
    python3 "$ROOT/tools/pmpatch.py" build --hd --out "$ROOT/build/stage-patched" >/dev/null
    SRC="$ROOT/build/stage-patched/hd"
else
    python3 "$ROOT/tools/pmpatch.py" build --hd --only hd_core --out "$ROOT/build/stage-original" >/dev/null
    SRC="$ROOT/build/stage-original/hd"
fi
if [[ $GEMDOS == 1 || $MACHINE == falcon || ! -f "$HDDIR/HDDRIVER.SYS" ]]; then
    [[ $GEMDOS == 1 ]] || echo "(no ACSI + HDDRIVER here: $MACHINE or $HDDIR/HDDRIVER.SYS missing; using Hatari's GEMDOS folder as C:)"
    rm -rf "$PLAY/hdfolder" && cp -r "$SRC" "$PLAY/hdfolder"
    echo "Powermonger ($VARIANT, hard disk, GEMDOS folder) on $MACHINE, ${RAM} KiB, TOS: $(basename "$TOS")"
    exec hatari "${COMMON[@]}" --harddrive "$PLAY/hdfolder" --fast-boot yes
fi
python3 - "$ROOT" "$SRC" "$PLAY/hd.img" <<'PY'
import sys
from pathlib import Path
root = sys.argv[1]
sys.path.insert(0, root + "/../hunter/tools")
from hunter import build_hd
build_hd(Path(sys.argv[3]), game=Path(sys.argv[2]), autorun="C:\\NONE.TOS")
PY
echo "Powermonger ($VARIANT, hard disk, ACSI + HDDRIVER) on $MACHINE, ${RAM} KiB, TOS: $(basename "$TOS")"
echo "Disk image: $PLAY/hd.img (rebuilt every run)"
exec hatari "${COMMON[@]}" --gemdos-drive skip --acsi "0=$PLAY/hd.img" --fast-boot yes
