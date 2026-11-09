#!/usr/bin/env bash
# Play the patched Hunter in Hatari, emulating a Mega ST by default.
#
#   tools/play.sh                  # patched build from a hard disk image, Mega ST, 1 MB, TOS 1.04
#   tools/play.sh --floppy         # the patched one-disk floppy (82x11) in drive A instead of the hard disk
#   tools/play.sh --original       # unpatched game (HD: PP's files; --floppy: the Paper Bag disk), for comparison
#   tools/play.sh --machine ste    # any Hatari machine: st, megast, ste, megaste, tt, falcon
#   tools/play.sh --ram 4096       # RAM in KiB (the game needs at least 1024)
#   tools/play.sh --fresh          # discard the play dir (saves) and start clean
#
# The hard-disk run builds an ACSI image (tools/hunter.py build_hd: HDDRIVER from gamebench/hd/, see hd/README.md)
# in build/play-<variant>/hd.img and rebuilds it every run (saves on it are lost; use --floppy for saves, the
# floppy copy in build/play-floppy*/ persists).  ST/Mega ST use TOS 1.04, STE 1.62, Mega STE 2.06, TT 3.06 and
# Falcon 4.04 if present in tos/ (else EmuTOS); override with --tos FILE.  The STE sound plays on every machine
# except st and megast (plain ST keeps the YM).  On a Falcon the ACSI image is not visible to TOS: use --floppy.
#
# In-game: the HW-detect screen counts down ~25 s, SPACE skips it; SPACE again at each picture.
# Hatari's joystick is mapped to the cursor keys plus right Ctrl (--joy1 keys).
# F12 opens the Hatari menu; AltGr+M toggles mouse grab.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
TOSDIR="$ROOT/../../tos"     # gamebench/tos
MACHINE=megast
RAM=1024
VARIANT=patched
MEDIA=hd
FRESH=0
TOS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --original) VARIANT=original ;;
        --floppy)   MEDIA=floppy ;;
        --machine)  MACHINE="$2"; shift ;;
        --ram)      RAM="$2"; shift ;;
        --tos)      TOS="$2"; shift ;;
        --fresh)    FRESH=1 ;;
        -h|--help)  sed -n '2,19p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

if [[ -z "$TOS" ]]; then
    case "$MACHINE" in
        st|megast)   TOS="$TOSDIR/TOS_1_04.img" ;;
        ste)         TOS="$TOSDIR/TOS_1_62.img" ;;
        megaste)     TOS="$TOSDIR/TOS_2_06.img" ;;
        tt|falcon)
            # Real TOS 3.06 (TT) / 4.04 (Falcon) if dropped into tos/, else EmuTOS.
            if [[ $MACHINE == tt ]]; then prefs=(TOS_3_06_uk TOS_3_05_us); else prefs=(TOS_4_04 TOS_4_02 TOS_4_01); fi
            for t in "${prefs[@]/#/$TOSDIR/}" "$TOSDIR/EmuTOS_1024k"; do
                [[ -f "$t.img" ]] && { TOS="$t.img"; break; }
            done ;;
        *) echo "no default TOS for --machine $MACHINE; pass --tos FILE" >&2; exit 2 ;;
    esac
fi
[[ -f "$TOS" ]] || { echo "TOS image not found: $TOS" >&2; exit 1; }

PLAY="$ROOT/build/play-$VARIANT-$MEDIA"
[[ $FRESH == 1 ]] && rm -rf "$PLAY"
mkdir -p "$PLAY"

COMMON=(--machine "$MACHINE" --tos "$TOS" --memsize "$RAM" --monitor rgb --joy1 keys --confirm-quit no)

if [[ $MEDIA == floppy ]]; then
    # NOT named A.st / B.st (Hatari auto-inserts those)
    if [[ $VARIANT == original ]]; then
        BASE=$(ls "$ROOT"/alt/floppy/*"Paper Bag"*.st | head -n 1)
        [[ -f "$BASE" ]] || { echo "Paper Bag floppy image not found in alt/floppy/" >&2; exit 1; }
        [[ -f "$PLAY/hunter_d1.st" ]] || cp "$BASE" "$PLAY/hunter_d1.st"
    else
        [[ -f "$ROOT/build/hunter_snd.bin" ]] || python3 "$ROOT/tools/snd_build.py" >/dev/null
        python3 "$ROOT/tools/huntpatch.py" build --floppy --samples "$ROOT/build/hunter_snd.bin" --out "build/stage-floppy" >/dev/null
        # the disk is refreshed on every run only when the play copy does not exist (saves go to the copy)
        [[ -f "$PLAY/hunter_d1.st" ]] || cp "$ROOT/build/stage-floppy/HUNTER_disk1.st" "$PLAY/hunter_d1.st"
    fi
    echo "Hunter ($VARIANT, floppy) on $MACHINE, ${RAM} KiB, TOS: $(basename "$TOS")"
    echo "Disk: $PLAY/hunter_d1.st (delete or --fresh to rebuild; the game saves to it)"
    exec hatari "${COMMON[@]}" --disk-a "$PLAY/hunter_d1.st"
fi

# Hard disk: stage the game files (patched or not), then build the ACSI image from them.
if [[ $VARIANT == patched ]]; then
    [[ -f "$ROOT/build/hunter_snd.bin" ]] || python3 "$ROOT/tools/snd_build.py" >/dev/null
    python3 "$ROOT/tools/huntpatch.py" build --samples "$ROOT/build/hunter_snd.bin" --out "build/stage-patched" >/dev/null
else
    python3 "$ROOT/tools/huntpatch.py" build --only --out "build/stage-original" >/dev/null
fi
python3 - "$ROOT" "$ROOT/build/stage-$VARIANT" "$PLAY/hd.img" <<'PY'
import sys
from pathlib import Path
root = sys.argv[1]
sys.path.insert(0, root + "/tools")
from hunter import build_hd
build_hd(Path(sys.argv[3]), game=Path(sys.argv[2]))
PY
echo "Hunter ($VARIANT, hard disk) on $MACHINE, ${RAM} KiB, TOS: $(basename "$TOS")"
echo "Disk image: $PLAY/hd.img"
exec hatari "${COMMON[@]}" --gemdos-drive skip --acsi "0=$PLAY/hd.img"
