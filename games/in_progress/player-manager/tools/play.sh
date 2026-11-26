#!/usr/bin/env bash
# Play the patched Player Manager (PLAYERME) in Hatari, emulating an STE by default.
#
#   tools/play.sh                   # patched build, STE, 1 MB, TOS 1.62
#   tools/play.sh --original        # unpatched PLAYERME, for comparison
#   tools/play.sh --machine megaste # any Hatari machine: st, megast, ste, megaste, tt, falcon
#   tools/play.sh --ram 2048        # RAM in KiB (1024 minimum)
#   tools/play.sh --tos FILE        # override TOS image
#   tools/play.sh --fresh           # discard build/play-<variant>/ (saves) and start clean
#   tools/play.sh --fast-forward    # start Hatari with fast-forward enabled (AltGr+X toggles)
#
# The game is staged to build/play-<variant>/ so your saved games persist between
# runs while originals/ stay untouched. FILES/PMLA is refreshed from the latest build
# on every launch.
#
# In-game (patched 92-team build):
# - League Names: click the active Division tab or press Space / Up / Down to flip pages 1 <-> 2.
# - Division Tables: click the active Division tab or press Space to toggle Top 12 / Bottom 12;
#   Up / Down scroll 4 rows at a time; Esc or Done exits.
# - Weekly Fixtures & Results: click or press any key to advance Page 1 -> Page 2 -> Page 3 -> exit.
# - Joystick 1 is mapped to the cursor keys + Right Ctrl (--joy1 keys).
# - Numpad * exits to desktop, Numpad / opens HAGA statesave, F12 opens Hatari menu, AltGr+M grabs mouse.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
TOSDIR="$ROOT/../../../tos"
MACHINE=ste
RAM=1024
VARIANT=patched
FRESH=0
TOS=""
EXTRA=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --original)     VARIANT=original ;;
        --machine)      MACHINE="$2"; shift ;;
        --ram)          RAM="$2"; shift ;;
        --tos)          TOS="$2"; shift ;;
        --fresh)        FRESH=1 ;;
        --fast-forward) EXTRA+=(--fast-forward true) ;;
        -h|--help)      sed -n '2,22p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

if [[ -z "$TOS" ]]; then
    case "$MACHINE" in
        st|megast) TOS="$TOSDIR/TOS_1_04.img" ;;
        ste)       TOS="$TOSDIR/TOS_1_62.img" ;;
        megaste)   TOS="$TOSDIR/TOS_2_06.img" ;;
        tt|falcon)
            if [[ $MACHINE == tt ]]; then prefs=(TOS_3_06_uk TOS_3_05_us); else prefs=(TOS_4_04 TOS_4_02 TOS_4_01); fi
            for t in "${prefs[@]/#/$TOSDIR/}" "$TOSDIR/EmuTOS_1024k"; do
                [[ -f "$t.img" ]] && { TOS="$t.img"; break; }
            done ;;
        *) echo "no default TOS for --machine $MACHINE; pass --tos FILE" >&2; exit 2 ;;
    esac
fi
[[ -f "$TOS" ]] || { echo "TOS image not found: $TOS" >&2; exit 1; }

if [[ $MACHINE == tt ]]; then
    EXTRA+=(--mmu true)
fi

PLAY="$ROOT/build/play-$VARIANT"
[[ $FRESH == 1 ]] && rm -rf "$PLAY"

if [[ $VARIANT == patched ]]; then
    (cd "$ROOT" && python3 "$ROOT/tools/pmpatch.py" >/dev/null)
    SRC="$ROOT/build/game"
else
    SRC="$ROOT/originals/PLAYERME"
fi

if [[ ! -d "$PLAY" ]]; then
    cp -r "$SRC" "$PLAY"
else
    # Refresh program files on every run while preserving any saved games in FILES/
    for f in RUNME.TOS HAGA PLAYMA.PCH; do
        [[ -f "$SRC/$f" ]] && cp "$SRC/$f" "$PLAY/$f"
    done
    cp "$SRC/FILES/PMLA" "$PLAY/FILES/PMLA"
    for f in DEMO92.DAT KO2ENG.BIN KO2HND.BIN PMMATCH.BIN KRD; do
        [[ -f "$SRC/FILES/$f" ]] && cp "$SRC/FILES/$f" "$PLAY/FILES/$f"
    done
fi

echo "Player Manager ($VARIANT) on $MACHINE, ${RAM} KiB, TOS: $(basename "$TOS")"
echo "Game dir: $PLAY"
exec hatari \
    --machine "$MACHINE" \
    --tos "$TOS" \
    --memsize "$RAM" \
    --monitor rgb \
    --harddrive "$PLAY" \
    --auto 'C:\RUNME.TOS' \
    --fast-boot yes \
    --joy1 keys \
    --confirm-quit no \
    "${EXTRA[@]}"
