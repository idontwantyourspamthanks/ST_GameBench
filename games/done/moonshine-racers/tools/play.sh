#!/usr/bin/env bash
# Play the patched Moonshine Racers in Hatari (a visible window), STE by default.
#
#   tools/play.sh                    # patched default build from the hard disk, STE, 1 MB, TOS 1.62
#   tools/play.sh --original         # PP's unpatched HD release, for comparison
#   tools/play.sh --floppy           # the patched FLOPPY set (disk A in drive A; the game asks for disk 2: see below)
#   tools/play.sh --floppy --original   # the original floppy release converted to plain .ST (the manual question appears)
#   tools/play.sh --machine megaste  # st, megast, ste, megaste, tt, falcon
#   tools/play.sh --ram 4096         # RAM in KiB (1024 minimum)
#   tools/play.sh --cpu 16           # run at N MHz (8 stock; 16/32 show the fixed game speed): the machine BOOTS at 8 MHz and is raised to N after TOS init (Hatari --parse, below)
#   tools/play.sh --extrap           # no-op (kept for old command lines): the extra in-between frames on fast machines are part of the default set now
#   tools/play.sh --noextrap         # the fixed-tick-only variant for comparison (mt_sync instead of mg_sync + mg_pace; same game speed, no extra frames)
#   tools/play.sh --safex N          # extra-frame deadline margin, 1/300 s units (build time: msrpatch.py build --set SAFE=N): 0 = default (most extras, more uneven frame spacing), 3 = smoother (fewer late ticks, fewer extras), negative = looser
#   tools/play.sh --no-nomouse       # real-hardware A/B switches, each takes ONE default patch out: --no-nomouse = ta_nomouse (the IKBD mouse query keeps running in the race)
#   tools/play.sh --no-blit          #   --no-blit = tb_blit* (no STE blitter sprites, no Timer-B guard)
#   tools/play.sh --no-rb            #   --no-rb = ta_rb + ta_rb0 (the stock Timer B raster list)
#   tools/play.sh --no-facestat      #   --no-facestat = ta_facestat (the talking face moves its mouth again: ta_face instead)
#   tools/play.sh --no-driveb        #   --no-driveb = fl_driveb (floppy only: no second-drive support)
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
DROP=(); ADD=(); BUILDARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --original) VARIANT=original ;;
        --floppy)   MEDIA=floppy ;;
        --machine)  MACHINE="$2"; shift ;;
        --ram)      RAM="$2"; shift ;;
        --cpu)      CPU="$2"; shift ;;
        --tos)      TOS="$2"; shift ;;
        --print)    PRINT=1 ;;
        --extrap)   ;;                      # no-op alias
        --noextrap) DROP+=(mg_sync mg_pace); ADD+=(mt_sync) ;;
        --fast|--2x) BUILDARGS+=(--fast); VARIANT="${VARIANT}-2x" ;;
        --safex)    BUILDARGS+=(--set "SAFE=$2"); shift ;;
        --no-nomouse)  DROP+=(ta_nomouse) ;;
        --no-blit)     DROP+=(tb_blit tb_blit11 tb_blit13 tb_blit15) ;;
        --no-rb)       DROP+=(ta_rb ta_rb0) ;;
        --no-facestat) DROP+=(ta_facestat); ADD+=(ta_face) ;;
        --no-driveb)   DROP+=(fl_driveb) ;;
        --road)     ;;                      # no-op alias
        -h|--help)  sed -n '2,24p' "$0"; exit 0 ;;
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

# TOS 2.06 (Mega STE) with 1 MB bombs in its own init (2 bombs, bus error at $f00000) when Hatari starts it at 16 MHz (--cpuclock 16 at power-on); a real
# Mega STE powers up at 8 MHz and software raises the clock.  So Hatari always boots at 8 MHz here and --cpu N switches after TOS init (VBL 200; TOS
# is done at VBL ~120) through a debugger command file: work/notes/integration.md section 10.1/10.2.
OPTS=(--machine "$MACHINE" --tos "$TOS" --memsize "$RAM" --cpuclock 8 --monitor rgb --fast-boot yes --joy1 keys --confirm-quit no)
if [[ "$CPU" != 8 ]]; then
    CLK="$ROOT/build/play-clock"
    if [[ $PRINT != 1 ]]; then
        mkdir -p "$CLK"
        printf 'setopt --cpuclock %s\n' "$CPU" > "$CLK/clk.txt"
        printf 'b VBL > 200 :trace :once :file %s\n' "$CLK/clk.txt" > "$CLK/parse.txt"
    fi
    OPTS+=(--parse "$CLK/parse.txt")
    echo "note: boots at 8 MHz, switches to $CPU MHz at VBL 200 ($CLK/parse.txt: b VBL > 200 :trace :once :file $CLK/clk.txt; clk.txt: setopt --cpuclock $CPU)"
fi

bld() { [[ $PRINT == 1 ]] || "$@"; }      # --print only prints the command line: no build, no copying
# The patched build: the tool's default set, or (any switch above) the default set minus DROP plus ADD, with the build-time equates BUILDARGS (--set SAFE=N).
# The tool declares every conflict/requirement and refuses an invalid selection.
patched_build() {                          # $1 = hd | floppy
    local flt='$1 !~ /^fl_/' fl=() sel
    [[ $1 == floppy ]] && { flt='$1 !~ /^pp_/'; fl=(--floppy); }
    if (( ${#DROP[@]} + ${#ADD[@]} )); then
        sel=$(python3 "$ROOT/tools/msrpatch.py" list | awk "\$2==\"yes\" && $flt {print \$1}" | grep -v -x -F -f <(printf '%s\n' "${DROP[@]}" '-') | tr '\n' ' ')
        bld python3 "$ROOT/tools/msrpatch.py" build "${fl[@]}" --out "$PLAY" "${BUILDARGS[@]}" --only $sel "${ADD[@]}" >/dev/null
    else
        bld python3 "$ROOT/tools/msrpatch.py" build "${fl[@]}" --out "$PLAY" "${BUILDARGS[@]}" >/dev/null
    fi
    echo "patched set: default${DROP[*]:+ minus ${DROP[*]}}${ADD[*]:+ plus ${ADD[*]}}${BUILDARGS[*]:+ ; ${BUILDARGS[*]}}"
}
if [[ $MEDIA == hd ]]; then
    PLAY="$ROOT/build/play-hd-$VARIANT"
    bld rm -rf "$PLAY"; bld mkdir -p "$PLAY"
    if [[ $VARIANT == patched* ]]; then
        patched_build hd
    else
        bld cp -r "$ROOT/originals/MOONSHR/." "$PLAY/"
    fi
    echo "Moonshine Racers HD ($VARIANT) on $MACHINE, ${RAM} KiB, ${CPU} MHz, TOS $(basename "$TOS"); game dir $PLAY"
    CMD=(hatari "${OPTS[@]}" --harddrive "$PLAY" --auto 'C:\RUNME.TOS')
else
    PLAY="$ROOT/build/play-floppy-$VARIANT"
    bld rm -rf "$PLAY"; bld mkdir -p "$PLAY"
    if [[ $VARIANT == patched* ]]; then
        patched_build floppy
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
