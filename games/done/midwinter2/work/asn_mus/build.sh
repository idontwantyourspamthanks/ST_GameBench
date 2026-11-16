#!/usr/bin/env bash
# Build the bank and the HD + floppy test builds of the default set + the whole asn_* group into build/mus/{hd,fl}.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 tools/asn_build.py | cut -c1-220
ASN="asn_core asn_wd asn_lvc asn_lv1 asn_lv2 asn_mus"
DEFAULTS=$(python3 tools/mw2patch.py list | awk '$2=="yes" && $3!="(floppy)"{printf "%s ",$1}')
MW2_BANK=build/asn_bank.bin python3 tools/mw2patch.py build --out build/mus/hd --only $DEFAULTS $ASN | grep "^built"
FDEF=$(python3 tools/mw2patch.py list | awk '$2=="yes" && $4!="(file"{printf "%s ",$1}' | sed 's/pp_bigram_cache//;s/pp_nofade//')
MW2_BANK=build/asn_bank.bin python3 tools/mw2patch.py build --floppy --out build/mus/fl --only $FDEF $ASN | grep "^built"
