#!/bin/bash
# CrawlerApply: P = shipped-before (HEAD), L = new shipped build; sequential, one Hatari at a time
# all L-vs-A (and P-vs-A) group-end gates of the level-rule experiment; output logs/gates_apply.txt
cd "$(dirname "$0")"
G() { timeout 1500 python3 gate.py "$@" 2>&1 | grep -E "^##|^GATE|^    |Error|error" ; }
{
G crawler_sea_movturn_32_N raid_crawler_panao.sav 32 41 --sets A L N --poke 6fba=02580000 6fb6=fed40000
G crawler_sea_movturn_32   raid_crawler_panao.sav 32 41 --poke 6fba=02580000 6fb6=fed40000
G crawler_sea_movturn_16   raid_crawler_panao.sav 16 41 --poke 6fba=02580000 6fb6=fed40000
G crawler_shore_32         raid_crawler_panao.sav 32 41 --poke 6fba=02580000 66e6=00003a00 6742=0300 6294=0300 764a=0300
G crawler_land_downhill_32 raid_crawler_panao.sav 32 41 --poke 6fba=01d20000 66e6=00001c00 6742=0100 6294=0100 764a=0100
G crawler_sea_movturn_8    raid_crawler_panao.sav 8 41 --poke 6fba=02580000 6fb6=fed40000
G jeep_movturn_8           raid_jeep_dhafra.sav 8 41 --poke 6fba=00c80000 6fb6=ff600000
G crawler_stand_32         raid_crawler_panao.sav 32 41
G jeep_movturn_32          raid_jeep_dhafra.sav 32 41 --poke 6fba=00c80000 6fb6=ff600000
G foot_movturn_32          raid_onfoot_dhafra.sav 32 41 --poke 6fba=012c0000 6fb6=ff2e0000
G speedboat_movturn_32     raid_speedboat_iquitos.sav 32 41 --poke 6fba=00fa0000 6fb6=ff600000
G speedboat_stand_32       raid_speedboat_iquitos.sav 32 41
G hovercraft_movturn_32    raid_hovercraft_thar.sav 32 41 --poke 6fba=00fa0000 6fb6=ff600000
G swimming_movturn_32      raid_swimming_vitoria.sav 32 41 --poke 6fba=00fa0000 6fb6=ff600000
G ship_movturn_32          raid_ship_bourem.sav 32 41 --poke 6fba=00fa0000 6fb6=ff600000
G truck_movturn_32         raid_truck_aledo.sav 32 41 --poke 6fba=00c80000 6fb6=ffa60000
G tanktype_movturn_32      raid_jeep_dhafra.sav 32 41 --type 0 --poke 6fba=00fa0000 6fb6=ff600000
G heli_movturn_32          raid_helicopter_lobos.sav 32 41 --poke 6fba=00fa0000 6fb6=ff380000
G submarine_movturn_32     raid_submarine_jebba.sav 32 41 --poke 6fba=00fa0000 6fb6=ff600000
} > logs/gates_apply.txt
