#!/usr/bin/env bash
# Play the patched Powermonger WW1 (Cobra #26 build) in Hatari, STE by default.
#
#   tools/play.sh                    # patched (default patch set = tick), STE, 1 MB, TOS 1.62
#   tools/play.sh --original         # the unpatched Cobra WW1.PRG, for comparison
#   tools/play.sh --machine megaste  # st, megast, ste, megaste, tt, falcon
#   tools/play.sh --ram 2048         # RAM in KiB (default 1024; 4096 on tt/falcon)
#   tools/play.sh --cpu 16           # run at N MHz (8 stock): boots at 8 and is raised at VBL 200
#   tools/play.sh --tos FILE         # another TOS image
#   tools/play.sh --only tick        # exactly these patches (tools/wwbuild.py list shows them);
#                                    #   --only with nothing after it plays the unpatched set
#   tools/play.sh --print            # only print the Hatari command line (no build)
#   tools/play.sh --fresh            # discard build/play/ and rebuild from scratch
#   tools/play.sh ... -- OPTS        # everything after -- goes to Hatari unchanged
#
# How it runs: tools/wwbuild.py depacks Cobra #26's WW1.PRG (ATOMIK), applies the patch sites
# and writes a plain PRG into build/play/; the game's data file WW1_FUZI.LFB is copied beside
# it.  Hatari boots that folder as C: (this base is a folder run, not a floppy) and the game
# autoruns.  At the title pictures press SPACE; type a name and press RETURN; the Option
# Screen is mouse-driven.  F12 opens Hatari's menu, AltGr+M toggles mouse grab.
#
# The patched build's world runs at 4.00 ticks/s on every machine (the unpatched one follows
# the frame rate: 3.60 at 8 MHz, 7.62 at 16 MHz).  Saves go to the game's own save-disk code,
# which needs a disk in A: - not wired up here yet.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
BENCH="$(cd "$ROOT/../../.." && pwd -P)"
TOSDIR="$BENCH/tos"
MACHINE=ste
RAM=""
CPU=8
VARIANT=patched
TOS=""
PRINT=0
FRESH=0
ONLY=()
ONLY_SET=0
XOPTS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --original) VARIANT=original ;;
        --machine)  MACHINE="$2"; shift ;;
        --ram)      RAM="$2"; shift ;;
        --cpu)      CPU="$2"; shift ;;
        --tos)      TOS="$2"; shift ;;
        --print)    PRINT=1 ;;
        --fresh)    FRESH=1 ;;
        --only)     ONLY_SET=1; shift
                    while [[ $# -gt 0 && "$1" != --* ]]; do ONLY+=("$1"); shift; done
                    continue ;;
        --)         shift; XOPTS=("$@"); break ;;
        -h|--help)  sed -n '2,26p' "$0"; exit 0 ;;
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

# Boot at 8 MHz and raise after TOS has initialised: TOS 2.06 with 1 MB can bomb when Hatari
# starts at 16 MHz, and a real Mega STE powers up at 8 MHz.
OPTS=(--machine "$MACHINE" --tos "$TOS" --memsize "$RAM" --cpuclock 8 --monitor rgb
      --fast-boot yes --joy1 keys --confirm-quit no --protect-floppy off)
if [[ "$CPU" != 8 ]]; then
    CLK="$ROOT/build/play-clock"
    if [[ $PRINT != 1 ]]; then
        mkdir -p "$CLK"
        printf 'setopt --cpuclock %s\n' "$CPU" > "$CLK/clk.txt"
        printf 'b VBL > 200 :trace :once :file %s\n' "$CLK/clk.txt" > "$CLK/parse.txt"
    fi
    OPTS+=(--parse "$CLK/parse.txt")
    echo "note: boots at 8 MHz, switches to $CPU MHz at VBL 200"
fi

DIR="$ROOT/build/play-$VARIANT"
# the Cobra disk has no AUTO folder (the game is launched from the desktop), so autorun it
CMD=("${HATARI:-hatari}" "${OPTS[@]}" --harddrive "$DIR" --auto "C:\\WW1.PRG" "${XOPTS[@]}")

if [[ $PRINT == 1 ]]; then printf '%q ' "${CMD[@]}"; echo; exit 0; fi

# default patch set: the tick only, for now
if [[ $VARIANT == patched && $ONLY_SET == 0 ]]; then
    ONLY=(tick noprot)
fi

rm -rf "$DIR"; mkdir -p "$DIR"
if [[ $VARIANT == patched ]]; then
    BUILD=(python3 "$ROOT/tools/wwbuild.py" build --out "$DIR")
    if (( ${#ONLY[@]} > 0 )); then BUILD+=(--only "${ONLY[@]}"); else BUILD+=(--only); fi
    "${BUILD[@]}"
    echo "patched set: ${ONLY[*]:-none}"
else
    cp "$ROOT/extracted/cobra26/WW1.PRG" "$DIR/WW1.PRG"
    echo "unpatched Cobra #26 WW1.PRG"
fi
# the game's data file must sit beside the program
for f in WW1_FUZI.LFB; do
    [[ -f "$ROOT/extracted/cobra26/$f" ]] || { echo "missing $ROOT/extracted/cobra26/$f" >&2; exit 1; }
    cp "$ROOT/extracted/cobra26/$f" "$DIR/$f"
done

echo "Powermonger WW1 ($VARIANT) on $MACHINE, ${RAM} KiB, TOS $(basename "$TOS"); folder $DIR"
exec "${CMD[@]}"
