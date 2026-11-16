#!/bin/bash
# CrawlerApply: second reruns (now with the direct P-vs-L comparison) of the cases where A (or one run) was off by the start flake; plus on foot
cd "$(dirname "$0")"
G() { timeout 1500 python3 gate.py "$@" 2>&1 | grep -E "^##|^GATE|^    |Error|error|Trace|assert" ; }
{
G foot_movturn_32          raid_onfoot_dhafra.sav 32 41 --poke 6fba=012c0000 6fb6=ff2e0000
G crawler_downhill_32_b    raid_crawler_panao.sav 32 41 --poke 6fba=02580000 66e6=00001c00 6742=0100 6294=0100 764a=0100 --at 154500
G speedboat_stand_32_b     raid_speedboat_iquitos.sav 32 41 --at 154500
G jeep_movturn_8_b         raid_jeep_dhafra.sav 8 41 --poke 6fba=00c80000 6fb6=ff600000 --at 154500
G crawler_stand_32_b       raid_crawler_panao.sav 32 41 --at 154500
} > logs/gates_apply3.txt
