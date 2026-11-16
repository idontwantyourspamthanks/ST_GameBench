#!/usr/bin/env bash
# Play the patched Moonshine Racers in Hatari (a visible window), STE by default.
#
#   tools/play.sh                    # patched default build from the hard disk, STE, 1 MB, TOS 1.62
#   tools/play.sh --original         # PP's unpatched HD release, for comparison
#   tools/play.sh --floppy           # the patched FLOPPY set (disk A in drive A; the game asks for disk 2: see below)
#   tools/play.sh --floppy --original   # the original floppy release converted to plain .ST (the manual question appears)
#   tools/play.sh --machine megaste  # st, megast, ste, megaste, tt, falcon
#   tools/play.sh --ram 4096         # RAM in KiB (1024 minimum)
#   tools/play.sh --cpu 16           # CPU clock in MHz (8 stock; 16/32 show the fixed game speed)
#   tools/play.sh --extrap           # EXPERIMENT (HD only): extra in-between frames on fast machines (mx_sync instead of mt_sync)
#   tools/play.sh --road             # no-op (kept for old command lines): the faster road is part of the default set now
#   tools/play.sh --print            # only print the Hatari command line
#
# HD: the build is copied to build/play-<variant>/ (RUNME.TOS autostarts). Press SPACE at the screens to reach the race
# (the start of a race needs one SPACE after the position table). Hatari's joystick is the cursor keys plus right Ctrl
# (--joy1 keys). F12 opens Hatari's menu.
# Floppy: when the game shows "Insert Disk 2 and press a key", press F12 -> Floppy -> Drive A and choose
# build/play-floppy*/disk_b.st (the file name differs per variant, see the echo below), then press SPACE.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
TOSDIR="$ROOT/../../../tos"
MACHINE=ste
RAM=1024
CPU=8
VARIANT=patched
MEDIA=hd
TOS=""
PRINT=0
EXTRAP=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --original) VARIANT=original ;;
        --floppy)   MEDIA=floppy ;;
        --machine)  MACHINE="$2"; shift ;;
        --ram)      RAM="$2"; shift ;;
        --cpu)      CPU="$2"; shift ;;
        --tos)      TOS="$2"; shift ;;
        --print)    PRINT=1 ;;
        --extrap)   EXTRAP=1 ;;
        --road)     ;;                      # no-op alias
        -h|--help)  sed -n '2,17p' "$0"; exit 0 ;;
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
            if [[ $MACHINE == tt ]]; then prefs=(TOS_3_06_uk TOS_3_05_us); else prefs=(TOS_4_04 TOS_4_02 TOS_4_01); fi
            for t in "${prefs[@]/#/$TOSDIR/}" "$TOSDIR/EmuTOS_1024k"; do
                [[ -f "$t.img" ]] && { TOS="$t.img"; break; }
            done ;;
        *) echo "no default TOS for --machine $MACHINE; pass --tos FILE" >&2; exit 2 ;;
    esac
fi
[[ -f "$TOS" ]] || { echo "TOS image not found: $TOS" >&2; exit 1; }

OPTS=(--machine "$MACHINE" --tos "$TOS" --memsize "$RAM" --cpuclock "$CPU" --monitor rgb --fast-boot yes --joy1 keys --confirm-quit no)

bld() { [[ $PRINT == 1 ]] || "$@"; }      # --print only prints the command line: no build, no copying
if [[ $MEDIA == hd ]]; then
    PLAY="$ROOT/build/play-hd-$VARIANT"
    bld rm -rf "$PLAY"; bld mkdir -p "$PLAY"
    if [[ $VARIANT == patched && $EXTRAP == 1 ]]; then
        # default HD set (without the floppy-only fl_* patches) with mt_sync swapped for the extra-frame pacer (mt_sync and mx_sync declare a conflict: the tool refuses both)
        SET=$(python3 "$ROOT/tools/msrpatch.py" list | awk '$2=="yes" && $1 !~ /^fl_/ {print $1}')
        SET=$(echo "$SET" | grep -v '^mt_sync$'); SET="$SET mx_pre mx_sync"
        bld python3 "$ROOT/tools/msrpatch.py" build --out "$PLAY" --only $SET >/dev/null
    elif [[ $VARIANT == patched ]]; then
        bld python3 "$ROOT/tools/msrpatch.py" build --out "$PLAY" >/dev/null
    else
        bld cp -r "$ROOT/originals/MOONSHR/." "$PLAY/"
    fi
    echo "Moonshine Racers HD ($VARIANT) on $MACHINE, ${RAM} KiB, ${CPU} MHz, TOS $(basename "$TOS"); game dir $PLAY"
    CMD=(hatari "${OPTS[@]}" --harddrive "$PLAY" --auto 'C:\RUNME.TOS')
else
    PLAY="$ROOT/build/play-floppy-$VARIANT"
    bld rm -rf "$PLAY"; bld mkdir -p "$PLAY"
    if [[ $VARIANT == patched ]]; then
        bld python3 "$ROOT/tools/msrpatch.py" build --floppy --out "$PLAY" >/dev/null
        A="$PLAY/disk_a.st"; B="$PLAY/disk_b.st"
    else
        bld cp "$ROOT/work/floppy/disk_a.st" "$PLAY/disk_a.st"; bld cp "$ROOT/work/floppy/disk_b.st" "$PLAY/disk_b.st"
        A="$PLAY/disk_a.st"; B="$PLAY/disk_b.st"
    fi
    echo "Moonshine Racers FLOPPY ($VARIANT) on $MACHINE, ${RAM} KiB, ${CPU} MHz, TOS $(basename "$TOS")"
    echo "Disk A is in drive A. When the game asks for disk 2: F12 -> Floppy -> Drive A -> choose $B, then SPACE."
    CMD=(hatari "${OPTS[@]}" --disk-a "$A")
fi
if [[ $PRINT == 1 ]]; then printf '%q ' "${CMD[@]}"; echo; exit 0; fi
exec "${CMD[@]}"
