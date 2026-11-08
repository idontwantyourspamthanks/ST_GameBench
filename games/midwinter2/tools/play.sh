#!/usr/bin/env bash
# Play the patched Midwinter 2 in Hatari, emulating a Mega ST by default.
#
#   tools/play.sh                  # patched default build, Mega ST, 1 MB, TOS 1.04
#   tools/play.sh --original       # unpatched game, for comparison
#   tools/play.sh --machine ste    # any Hatari machine: st, megast, ste, megaste, tt, falcon
#   tools/play.sh --ram 2048       # RAM in KiB (the game needs at least 1024)
#   tools/play.sh --fresh          # discard the play dir (saves, campaign) and start clean
#
# The game is copied to build/play-<variant>/ so its saves and campaign disk persist
# between runs, while the originals and build/ stay untouched. The campaign disk
# made during testing (work/disk_overlay) is pre-installed, so War Room ->
# Control works straight away. The default STE/Mega STE TOS is 1.62, ST/Mega ST
# uses TOS 1.04; override with --tos FILE.
#
# In-game:
# - Choose M, J or K at the start screen.
# - Hatari's joystick is mapped to the cursor keys plus right Ctrl (--joy1 keys).
# - Numpad * exits to the desktop and numpad / saves the gamestate (PP's HAGA keys).
# - F12 opens the Hatari menu; AltGr+M toggles mouse grab.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
TOSDIR="$ROOT/../../tos"     # gamebench/tos
MACHINE=megast
RAM=1024
VARIANT=patched
FRESH=0
TOS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --original) VARIANT=original ;;
        --machine)  MACHINE="$2"; shift ;;
        --ram)      RAM="$2"; shift ;;
        --tos)      TOS="$2"; shift ;;
        --fresh)    FRESH=1 ;;
        -h|--help)  sed -n '2,23p' "$0"; exit 0 ;;
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
            for t in "$TOSDIR"/TOS_3_0*.img "$TOSDIR"/TOS_4_0*.img "$TOSDIR"/EmuTOS_1024k.img; do
                [[ -f "$t" ]] || continue
                case "$MACHINE:$(basename "$t")" in tt:TOS_4_*|falcon:TOS_3_*) continue ;; esac
                TOS="$t"; break
            done ;;
        *) echo "no default TOS for --machine $MACHINE; pass --tos FILE" >&2; exit 2 ;;
    esac
fi
[[ -f "$TOS" ]] || { echo "TOS image not found: $TOS" >&2; exit 1; }

PLAY="$ROOT/build/play-$VARIANT"
[[ $FRESH == 1 ]] && rm -rf "$PLAY"

# (Re)build the selected variant. --only with no names = zero patches (original game).
if [[ $VARIANT == patched ]]; then
    python3 "$ROOT/tools/mw2patch.py" build --out "build/stage-$VARIANT" >/dev/null
else
    python3 "$ROOT/tools/mw2patch.py" build --only --out "build/stage-$VARIANT" >/dev/null
fi
STAGE="$ROOT/build/stage-$VARIANT"

# The program files are refreshed on every run; FILES/ (disks, campaign, saves) only on first run.
mkdir -p "$PLAY"
for f in RUNME.TOS HAGA FF240R.BMP FFF273.HST LFF273.HST; do cp "$STAGE/$f" "$PLAY/"; done
if [[ ! -d "$PLAY/FILES" ]]; then
    cp -r "$STAGE/FILES" "$PLAY/FILES"
    cp "$ROOT/work/disk_overlay/FILES/FFD" "$PLAY/FILES/FFD"
fi

echo "Midwinter 2 ($VARIANT) on $MACHINE, ${RAM} KiB, TOS: $(basename "$TOS")"
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
    --confirm-quit no
