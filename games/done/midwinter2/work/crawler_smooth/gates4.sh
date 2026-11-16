#!/bin/bash
cd "$(dirname "$0")"
G() { timeout 1500 python3 gate.py "$@" 2>&1 | grep -E "^##|^GATE|^    |Error|error|Trace|assert" ; }
{
G foot_movturn_32          raid_onfoot_dhafra.sav 32 41 --poke 6fba=012c0000 6fb6=ff2e0000 --at 165000
G crawler_downhill_32_c    raid_crawler_panao.sav 32 41 --poke 6fba=02580000 66e6=00001c00 6742=0100 6294=0100 764a=0100 --at 154700
G crawler_shore_32_b       raid_crawler_panao.sav 32 41 --poke 6fba=02580000 66e6=00003a00 6742=0300 6294=0300 764a=0300 --at 154500
} > logs/gates_apply4.txt
