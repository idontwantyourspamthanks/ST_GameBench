#!/usr/bin/env bash
# Build the bank and the HD + floppy test builds of the default set (includes the asn_* group) into build/mus/{hd,fl}.
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 tools/asn_build.py | cut -c1-220
MW2_BANK=build/asn_bank.bin python3 tools/mw2patch.py build --out build/mus/hd | grep "^built"
MW2_BANK=build/asn_bank.bin python3 tools/mw2patch.py build --floppy --out build/mus/fl | grep "^built"
