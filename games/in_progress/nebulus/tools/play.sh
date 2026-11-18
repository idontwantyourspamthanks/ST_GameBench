#!/usr/bin/env bash
# Play the patched Nebulus in Hatari (a visible window), STE by default.
#
#   tools/play.sh                    # patched build (default patch set + the level editor), STE, 1 MB, TOS 1.62
#   tools/play.sh --original         # PP's unpatched Gamex build, for comparison
#   tools/play.sh --machine megaste  # st, megast, ste, megaste (TT/Falcon: pass --tos FILE and expect nothing: untested)
#   tools/play.sh --ram 4096         # RAM in KiB (1024 minimum)
#   tools/play.sh --cpu 16           # run at N MHz (8 stock): the machine BOOTS at 8 MHz and is raised to N after TOS init (Hatari --parse)
#   tools/play.sh --tos FILE         # another TOS image
#   tools/play.sh --no-editor        # the release default set only (no level editor / campaign hooks)
#   tools/play.sh --only A B ...     # exactly these patches (tools/nepatch.py list shows them)
#   tools/play.sh --keep-ovl         # keep the campaign / level file between runs (see below)
#   tools/play.sh --print            # only print the Hatari command line (no build, no image)
#   tools/play.sh ... -- OPTS        # everything after -- goes to Hatari unchanged (e.g. -- --disk-b x.st); $HATARI picks the binary
#
# How it runs: tools/nebrelease.py builds the patched folder (build/play-patched/; START.TOS + NEPATCH.BIN + PP's files + NEBLEVEL.OVL),
# tools/nebulus.py build_hd makes a 16 MB ACSI image with HDDRIVER's boot code from it (build/play-<variant>.img; needs the user-supplied
# gamebench/hd/ files, as the test harness), and Hatari boots it: HDDRIVER banner, then DESKTOP.INF autoruns C:\START.TOS.  At the screens press
# SPACE.  Joystick = cursor keys + Right Ctrl (Hatari --joy1 keys).  F10 on the title = the level editor.  F12 opens Hatari's menu.
#
# NEBLEVEL.OVL (the campaign / custom levels the in-game editor saves) lives INSIDE the image, which is rebuilt on every run.  --keep-ovl makes
# it persist: before the build the file is taken from $NEBULUS_OVL, else ~/.nebulus/NEBLEVEL.OVL, else work/play/NEBLEVEL.OVL (first that exists;
# none = the empty file the build writes) and copied into the image; after Hatari exits the image's NEBLEVEL.OVL is copied BACK to the first
# of those paths that exists, else to ~/.nebulus/NEBLEVEL.OVL (created).  Use "Save to disk" in the editor before you quit Hatari.  Without
# --keep-ovl the saved levels die with the image.
set -euo pipefail

ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd -P)"
BENCH="$(cd "$ROOT/../../.." && pwd -P)"
TOSDIR="$BENCH/tos"
MACHINE=ste
RAM=1024
CPU=8
VARIANT=patched
TOS=""
PRINT=0
KEEP=0
EDITOR=1
ONLY=()
XOPTS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --original)  VARIANT=original ;;
        --machine)   MACHINE="$2"; shift ;;
        --ram)       RAM="$2"; shift ;;
        --cpu)       CPU="$2"; shift ;;
        --tos)       TOS="$2"; shift ;;
        --print)     PRINT=1 ;;
        --keep-ovl)  KEEP=1 ;;
        --no-editor) EDITOR=0 ;;
        --only)      shift; while [[ $# -gt 0 && "$1" != --* ]]; do ONLY+=("$1"); shift; done; continue ;;
        --)          shift; XOPTS=("$@"); break ;;
        -h|--help)   sed -n '2,26p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

if [[ -z "$TOS" ]]; then
    case "$MACHINE" in
        st|megast)  TOS="$TOSDIR/TOS_1_04.img" ;;
        ste)        TOS="$TOSDIR/TOS_1_62.img" ;;
        megaste)    TOS="$TOSDIR/TOS_2_06.img" ;;
        *) echo "no default TOS for --machine $MACHINE; pass --tos FILE" >&2; exit 2 ;;
    esac
fi
[[ -f "$TOS" ]] || { echo "TOS image not found: $TOS" >&2; exit 1; }

# TOS 2.06 with 1 MB can bomb when Hatari starts at 16 MHz; a real Mega STE powers up at 8 MHz.  Always boot at 8 MHz and switch after TOS init.
OPTS=(--machine "$MACHINE" --tos "$TOS" --memsize "$RAM" --cpuclock 8 --monitor rgb --fast-boot yes --joy1 keys --confirm-quit no)
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

IMG="$ROOT/build/play-$VARIANT.img"
DIR="$ROOT/build/play-$VARIANT"
CMD=("${HATARI:-hatari}" "${OPTS[@]}" --gemdos-drive skip --acsi "0=$IMG" "${XOPTS[@]}")

ovl_in() {      # the persistent campaign file to start from (first that exists), or nothing
    local c
    for c in "${NEBULUS_OVL:-}" "$HOME/.nebulus/NEBLEVEL.OVL" "$ROOT/work/play/NEBLEVEL.OVL"; do
        [[ -n "$c" && -f "$c" ]] && { echo "$c"; return; }
    done
}

if [[ $PRINT == 1 ]]; then printf '%q ' "${CMD[@]}"; echo; exit 0; fi

rm -rf "$DIR"; mkdir -p "$DIR" "$ROOT/build"
if [[ $VARIANT == patched ]]; then
    if (( ${#ONLY[@]} == 0 )); then
        mapfile -t ONLY < <(python3 "$ROOT/tools/nepatch.py" list | awk '/ default=yes/{print $1}')
        if [[ $EDITOR == 1 ]]; then
            printf '%s\n' "${ONLY[@]}" | grep -qx ed_overlay || ONLY+=(ed_overlay)
        else
            mapfile -t ONLY < <(printf '%s\n' "${ONLY[@]}" | grep -vx ed_overlay)
        fi
    fi
    python3 "$ROOT/tools/nebrelease.py" build --out "$DIR" --only "${ONLY[@]}" > /dev/null
    echo "patched set: ${ONLY[*]}"
else
    cp -r "$ROOT/originals/NEBULGX/." "$DIR/"
fi
SRC=""
if [[ $KEEP == 1 && $VARIANT == patched ]]; then
    SRC="$(ovl_in)"
    if [[ -n "$SRC" ]]; then cp "$SRC" "$DIR/NEBLEVEL.OVL"; echo "campaign file in: $SRC"; else echo "campaign file: none yet (a new empty one is used; it is kept after this run)"; fi
fi
python3 - "$ROOT/tools" "$IMG" "$DIR" <<'PY'
import sys; from pathlib import Path
sys.path.insert(0, sys.argv[1])
from nebulus import build_hd
build_hd(sys.argv[2], game=Path(sys.argv[3]))
PY
echo "Nebulus ($VARIANT) on $MACHINE, ${RAM} KiB, ${CPU} MHz, TOS $(basename "$TOS"); image $IMG"

back() {        # image -> the persistent file
    local dst="${SRC:-$HOME/.nebulus/NEBLEVEL.OVL}" tmp
    tmp="$(mktemp)"
    if MTOOLS_SKIP_CHECK=1 mcopy -n -i "$IMG@@1024" ::NEBLEVEL.OVL "$tmp" 2>/dev/null && [[ "$(stat -c %s "$tmp")" == 8192 ]]; then
        if [[ ! -f "$dst" ]] || ! cmp -s "$tmp" "$dst"; then mkdir -p "$(dirname "$dst")"; cp "$tmp" "$dst"; echo "campaign file saved: $dst"; else echo "campaign file unchanged"; fi
    else
        echo "could not read NEBLEVEL.OVL back from the image" >&2
    fi
    rm -f "$tmp"
}
if [[ $KEEP == 1 && $VARIANT == patched ]]; then
    "${CMD[@]}" || true
    back
else
    exec "${CMD[@]}"
fi
