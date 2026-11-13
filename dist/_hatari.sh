# Sourced (not run) by run_tt.sh, run_falcon*.sh and rec_tt/rec_falcon*.sh: picks the Hatari binary for TT/Falcon.
# Default: the system `hatari`. Stock Hatari (2.6.x) draws a TT/Falcon screen with one palette per frame, so raster palette
# changes (Midwinter 2's panel, Hunter's sky) don't show; a Hatari with per-scanline TT/Videl palettes does. To use one:
#   HATARI=/path/to/hatari ./run_tt.sh            (one run), or
#   echo 'HATARI_TTF=/path/to/hatari' > dist/hatari.local      (git-ignored; also read by the test harnesses)
# AVIREC: the option that starts AVI recording (2.6.1 takes `--avirecord`, newer builds `--avirecord <bool>`).
[[ -f "$HERE/hatari.local" ]] && source "$HERE/hatari.local"
HATARI="${HATARI:-${HATARI_TTF:-hatari}}"
export HATARI
AVIREC=(--avirecord)
if [[ "$("$HATARI" --help 2>/dev/null || true)" == *"--avirecord <bool>"* ]]; then AVIREC=(--avirecord true); fi
