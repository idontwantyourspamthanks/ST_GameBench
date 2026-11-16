#!/bin/bash
# CrawlerApply: reruns of the cases that showed the start-one-flip-apart harness flake (NPC table 35bf-35df in A-vs-P and A-vs-L alike)
cd "$(dirname "$0")"
G() { timeout 1500 python3 gate.py "$@" 2>&1 | grep -E "^##|^GATE|^    |Error|error" ; }
{
G crawler_shore_32_rerun   raid_crawler_panao.sav 32 41 --poke 6fba=02580000 66e6=00003a00 6742=0300 6294=0300 764a=0300
G crawler_downhill_32      raid_crawler_panao.sav 32 41 --poke 6fba=02580000 66e6=00001c00 6742=0100 6294=0100 764a=0100
G speedboat_stand_32_rerun raid_speedboat_iquitos.sav 32 41
G jeep_movturn_8_rerun     raid_jeep_dhafra.sav 8 41 --poke 6fba=00c80000 6fb6=ff600000
} > logs/gates_apply2.txt
