#!/bin/bash
# Stage 6 release matrix on the UNZIPPED SHIPPED zips (one Hatari at a time, private HOME inside each work dir).
#   S=/tmp/pmww1s6/ship holds floppy/{PowermongerWW1_patched.st, manifest.json} and hd/{POWERMONGER_WW1/, manifest.json}  (manifest.json = the build that produced the zips,
#   members compared by md5 with the zips; the manifest only tells the gates the expected site bytes / free-RAM pattern spans).
#   usage: tools/stage06_matrix.sh [cell names...]      Logs: work/runs/s6_<name>.txt, work dirs /tmp/pmww1s6/w/<name>
set -u
cd "$(dirname "$0")/.."
export PYTHONPATH=/home/ryan/Code/AtariST/gamebench/tools
S=${S:-/tmp/pmww1s6/ship}
W=/tmp/pmww1s6/w
F=$S/floppy/PowermongerWW1_patched.st; FM=$S/floppy/manifest.json
H=$S/hd/POWERMONGER_WW1;                HM=$S/hd/manifest.json
STEPS=boot,map,hw,rate,saveload,lose,win,round3
TTX="--mmu true --cpuclock 32 --monitor vga"
FALX="--borders false"
mkdir -p work/runs "$W"
run() { local n=$1; shift; rm -rf "$W/$n"; echo "== $n: $*"; "$@" --workdir "$W/$n" > work/runs/s6_$n.txt 2>&1; grep -h "CELL DONE\|CELL FAILED\|PSGCHECK\|TOOLTIP GATE\|KEYS \|PTR \|FLIPS " work/runs/s6_$n.txt | tail -4; }
cell() { local n=$1; shift; run $n python3 tools/wwgate.py cell --disk $F --manifest $FM --tag $n --fill-hi --trace --steps $STEPS "$@"; }
hdcell() { local n=$1; shift; run $n python3 tools/wwgate.py cell --hd $H --manifest $HM --tag $n --fill-hi --trace --steps boot,map,hw,saveload,lose,win,round3 "$@"; }
want() { [[ $# == 0 ]] && return 0; for x in "$@"; do [[ $x == $CUR ]] && return 0; done; return 1; }
ARGS=("$@")
go() { CUR=$1; want "${ARGS[@]}"; }

go st      && cell st      --machine st --tos 1.04 --mem 1024 --psg
go ste     && cell ste     --machine ste --tos 1.62 --mem 1024 --psg
go mste16  && cell mste16  --machine megaste --tos 2.06 --mem 4096 --psg
go mste8   && cell mste8   --machine megaste --tos 2.06 --mem 4096 --psg --set-mhz 8
go tt      && cell tt      --machine tt --tos 3.06 --mem 4096 --extra "$TTX"
go falrgb  && cell falrgb  --machine falcon --tos 4.04 --mem 4096 --extra "$FALX"
go falvga  && cell falvga  --machine falcon --tos 4.04 --mem 4096 --extra "$FALX --monitor vga"
go keys    && run keys python3 tools/wwkeys.py --disk $F --manifest $FM --tag keys
go tt_ste  && run tt_ste python3 tools/wwtt.py gate --disk $F --manifest $FM --tag tt_ste
go tt_tt   && run tt_tt python3 tools/wwtt.py gate --disk $F --manifest $FM --quick --machine tt --tos 3.06 --mem 4096 --extra "$TTX" --tag tt_tt
go tt_fal  && run tt_fal python3 tools/wwtt.py gate --disk $F --manifest $FM --quick --machine falcon --tos 4.04 --mem 4096 --extra "$FALX" --tag tt_fal
go end     && run end python3 tools/wwend.py final --disk $F --manifest $FM --watch work/runs/end_watch_spans.txt
go ptr_tt  && run ptr_tt python3 tools/wwptr.py cold --disk $F --machine tt --tos 3.06 --mem 4096 --extra "$TTX" --flips --tag ptr_tt
go hd_ste_g   && hdcell hd_ste_g  --machine ste --tos 1.62 --mem 1024
go hd_ste_a   && hdcell hd_ste_a  --machine ste --tos 1.62 --mem 1024 --acsi
go hd_mste_g  && hdcell hd_mste_g --machine megaste --tos 2.06 --mem 4096
go hd_mste_a  && hdcell hd_mste_a --machine megaste --tos 2.06 --mem 4096 --acsi
go hd_fal_g   && hdcell hd_fal_g  --machine falcon --tos 4.04 --mem 4096 --extra "$FALX"
echo MATRIX DONE
