# Raids: starting vehicle per island

Surveyed 2026-11-10 with `tools/mw2raids.py`, Hatari STE 2 MB, level of play NOVICE, mouse mode. All numbers observed (RAM reads and screenshots under `work/raids/`, git-ignored), not read from the game data.

## Result in one paragraph
The Raids island map has **41 selectable islands** (ids `$eb9c` = 2..42). Each starts the player in a fixed vehicle. 15 of the 22 vehicle types occur. **Not found on any island: Tank (0), Train (4), Minisub (8), Frogman (11, only reached by Esc), Zeppelin (14), Rocket Pack (16), Flying Sub (20).** The 3D view is identical in layout to a campaign mission (HUD at the top, `$700a == 2`).

**Labelling question settled:** `$6220 = 13` is the **Helicopter**. The old `1mb_ingame_foot` / `walking` snapshots (Lobos campaign start) show a green helicopter canopy and cockpit, not a person. A raid on Lobos gives the same state (`$6220 = 13`, HUD distance 1272, compass W). The real on-foot state is `$6220 = 5`: Esc out of a Jeep shows the parachute-less standing player and the pistol in the weapon box (`work/snapshots/raid_onfoot_dhafra.sav`), and island 20 (Zafriya) starts on foot. The name table at `$1642f` is correct; the "foot" label of the old snapshots was wrong.

## How the flow works
1. After the M/J/K key: corridor. Doors: WAR ROOM (top-left), RAIDS (about (300,230), left door), CONTROL (middle), TRAINING, PERSONNEL (top-right). RAIDS needs no agent or campaign.
2. RAIDS opens "SELECT LEVEL OF PLAY": NOVICE button at (175,390).
3. "SELECT MISSION" island map (`work/ref`-style screenshot in `work/raids/map.png`). Only Lobos, Dhafra, Camargo, Agora and Africa carry labels on the map; every other island is selectable too, and its name appears as the title of the island text page.
4. **Hover an island and press SPACE** (not click). `$eb9c` becomes the island id at once (`$ffff` before). Un-selectable areas leave it `$ffff` (Agora, Africa and 4 small islands: (120,88) (175,108) (671,430) (711,429)).
5. The island text/picture page loads (about 25 s). Then click the `?` icon (140,415): the "boss" screen with the thumbs up/down icons appears (`work/ref/boss_thumbs.png`). Clicks are lost while a page loads, so retry until the boss screen matches.
6. Click the thumbs-up (625,92). Blue screen, then a wireframe model of the starting vehicle (here `$6220` is already set), then the 3D view after about 40-60 s. There was no separate "In" button: the thumbs-up goes straight to the load.
7. 3D view gate: `$6220 != $ffff` and the HUD frame in the screenshot (pixel (100,100) sky blue, (730,100) dark blue).

## Reproduce
```
# cold boot, Dhafra -> Jeep, about 4 min (verified: prints {'island': 3, 'vehicle': 1, 'view': 2})
python3 tools/mw2raids.py cold 446 177
# save the map-screen state (used by the surveys; work/snapshots/raids_map.sav is such a state)
python3 tools/mw2raids.py map
```
```python
import sys; sys.path.insert(0, 'tools')
from mw2harness import Hatari
from mw2raids import enter_raid, cold_to_raid_map, warroom_to_raid_map
h = Hatari(snapshot='work/snapshots/raids_map.sav', memsize_kb=2048)  # starts on the island map
print(enter_raid(h, 446, 177))      # {'island': 3, 'vehicle': 1, 'view': 2}  Dhafra: Jeep
# parachute starts (islands 10, 39): settle=0, then save at once; the player is Swimming 4-5 s later
# enter_raid(h, 388, 201, settle=0); h.savemem('work/snapshots/raid_parachute_calabar.sav')
```
`cold_to_raid_map(h)` does the cold boot part (Hatari(snapshot=None, memsize_kb=1024, game_dir=GAME_DIR/'build/game')); `warroom_to_raid_map(h)` starts from `warroom_campaign.sav`. `survey(points, ...)` restores the map snapshot per island and optionally saves shots and snapshots. The (x,y) pairs are screenshot coordinates of a point inside each island (island centroid, listed below; `work/raids/points.json` has all 50 land blobs).

Takes: about 2 min per island from the map snapshot, load is slower with several Hatari running.

## Table (all 41 islands)
Columns: id (`$eb9c`), island name (title of the island page; there is no other raid/mission name: the raid is "the island"), hover point, start vehicle, `$6220`, snapshot of that vehicle type, 3D-view screenshot of the island (`work/raids/`).

| id | island | point | vehicle | `$6220` | snapshot (`work/snapshots/`) | screenshot |
|---|---|---|---|---|---|---|
| 2 | Lobos | (149,271) | Helicopter | 13 | `raid_helicopter_lobos.sav` (this island) | `raid_02.png` |
| 3 | Dhafra | (446,177) | Jeep | 1 | `raid_jeep_dhafra.sav` (this island) | `raid_03.png` |
| 4 | Camargo | (402,420) | Jeep | 1 | `raid_jeep_dhafra.sav` | `raid_04.png` |
| 5 | Panao | (126,159) | Crawler | 7 | `raid_crawler_panao.sav` (this island) | `raid_05.png` |
| 6 | Vicenza | (172,207) | FlyingBoat | 18 | `raid_flyingboat_vicenza.sav` (this island) | `raid_06.png` |
| 7 | Gamboa | (239,241) | Jeep | 1 | `raid_jeep_dhafra.sav` | `raid_07.png` |
| 8 | Iquitos | (275,249) | Speedboat | 6 | `raid_speedboat_iquitos.sav` (this island) | `raid_08.png` |
| 9 | Maracay | (344,230) | Biplane | 12 | `raid_biplane_maracay.sav` (this island) | `raid_09.png` |
| 10 | Calabar | (388,201) | Parachute | 17 | `raid_parachute_calabar.sav` (this island) | `raid_10.png` |
| 11 | Aledo | (393,140) | Truck | 2 | `raid_truck_aledo.sav` (this island) | `raid_11.png` |
| 12 | Corozal | (377,94) | Balloon | 15 | `raid_balloon_corozal.sav` (this island) | `raid_12.png` |
| 13 | Jebba | (452,98) | Submarine | 9 | `raid_submarine_jebba.sav` (this island) | `raid_13.png` |
| 14 | Qamar | (502,83) | Truck | 2 | `raid_truck_aledo.sav` | `raid_14.png` |
| 15 | Maji | (507,150) | Jeep | 1 | `raid_jeep_dhafra.sav` | `raid_15.png` |
| 16 | Cubango | (584,157) | Helicopter | 13 | `raid_helicopter_lobos.sav` | `raid_16.png` |
| 17 | Gau | (636,125) | Helicopter | 13 | `raid_helicopter_lobos.sav` | `raid_17.png` |
| 18 | Vitoria | (536,214) | Swimming | 21 | `raid_swimming_vitoria.sav` (this island) | `raid_18.png` |
| 19 | Sikasso | (470,224) | Helicopter | 13 | `raid_helicopter_lobos.sav` | `raid_19.png` |
| 20 | Zafriya | (591,231) | foot | 5 | `raid_foot_zafriya.sav` (this island) | `raid_20.png` |
| 21 | Djoum | (674,86) | Helicopter | 13 | `raid_helicopter_lobos.sav` | `raid_21.png` |
| 22 | Satara | (664,172) | Jeep | 1 | `raid_jeep_dhafra.sav` | `raid_22.png` |
| 23 | Thar | (659,231) | Hovercraft | 19 | `raid_hovercraft_thar.sav` (this island) | `raid_23.png` |
| 24 | Gran Paradiso | (442,284) | Helicopter | 13 | `raid_helicopter_lobos.sav` | `raid_24.png` |
| 25 | Bourem | (377,309) | Ship | 10 | `raid_ship_bourem.sav` (this island) | `raid_25.png` |
| 26 | Maghar | (395,343) | Submarine | 9 | `raid_submarine_jebba.sav` | `raid_26.png` |
| 27 | Jerez | (331,334) | foot | 5 | `raid_foot_zafriya.sav` | `raid_27.png` |
| 28 | Beni Mazar | (496,320) | Helicopter | 13 | `raid_helicopter_lobos.sav` | `raid_28.png` |
| 29 | Ghazal | (556,358) | Hovercraft | 19 | `raid_hovercraft_thar.sav` | `raid_29.png` |
| 30 | Ndola | (645,289) | Helicopter | 13 | `raid_helicopter_lobos.sav` | `raid_30.png` |
| 31 | Makat | (605,334) | foot | 5 | `raid_foot_zafriya.sav` | `raid_31.png` |
| 32 | Khash | (497,371) | Biplane | 12 | `raid_biplane_maracay.sav` | `raid_32.png` |
| 33 | Mocorito | (448,369) | Biplane | 12 | `raid_biplane_maracay.sav` | `raid_33.png` |
| 34 | Hemet | (405,374) | Jeep | 1 | `raid_jeep_dhafra.sav` | `raid_34.png` |
| 35 | Cajamarca | (355,362) | Ship | 10 | `raid_ship_bourem.sav` | `raid_35.png` |
| 36 | Nicobar | (297,297) | FlyingBoat | 18 | `raid_flyingboat_vicenza.sav` | `raid_36.png` |
| 37 | Almirante | (187,308) | Speedboat | 6 | `raid_speedboat_iquitos.sav` | `raid_37.png` |
| 38 | Cristobal | (223,352) | Hovercraft | 19 | `raid_hovercraft_thar.sav` | `raid_38.png` |
| 39 | Aosta | (287,361) | Parachute | 17 | `raid_parachute_calabar.sav` | `raid_39.png` |
| 40 | Galva | (151,412) | Bus | 3 | `raid_bus_galva.sav` (this island) | `raid_40.png` |
| 41 | Andara | (201,420) | Jeep | 1 | `raid_jeep_dhafra.sav` | `raid_41.png` |
| 42 | Muar | (280,398) | Speedboat | 6 | `raid_speedboat_iquitos.sav` | `raid_42.png` |

Count: Helicopter 8, Jeep 7, Speedboat 3, On foot 3, Biplane 3, Hovercraft 3, Flying Boat 2, Parachute 2, Truck 2, Submarine 2, Ship 2, Balloon 1, Swimming 1, Bus 1, Crawler 1.

## Start states (from snapshots at HUD-up, `$66e6/$66ea` = x/y long)
| vehicle | start x, y | HUD distance (`$6888`) | notes |
|---|---|---|---|
| Jeep | 25856, 25600 | 70 | green body, steering wheel. Land |
| Truck | 25600, 25600 | 90 | green cab, red steering wheel |
| Bus | 25600, 25600 | 80 | sand-coloured bus windscreen |
| On foot | 26563, 25856 | 50 | pistol (30) in the weapon box |
| Speedboat | 25600, 25856 | 50 | yellow deck, ship wheel; water start |
| Crawler | 25600, 25600 | 50 | |
| Submarine | 25600, 25600 | 564 | periscope binocular view (yellow ring + crosshair); underwater |
| Ship | 25600, 25600 | 50 | yellow bridge, wheel |
| Biplane | 25600, 30650 | 2030 | red cockpit, wing struts; airborne |
| Helicopter | 25600, 25600 | 1272 | green canopy; airborne; compass W |
| Balloon | 25339, 26086 | 12003 | the first screen says OUTSIDE RAID AREA; pistol 30 in the weapon box; airborne |
| Parachute | 26654, 24484 | 50 | airborne, descending; the type becomes Swimming 4-5 s later over water; weapon box shows a grapple item (6) |
| Flying Boat | 25600, 18200 | 2053 | airborne |
| Hovercraft | 25856, 25856 | 70 | |
| Swimming | 25600, 25600 | 50 | in water, no cockpit |

Most starts are at the island centre (25600, 25600). Nearby boardable vehicles were NOT surveyed (none visible in the start views).

## Esc behaviour (scratch runs, key held 0.6 s; a 0.15 s press was missed three times)
`$6220` after Esc (after about 3 s, after about 13 s, after about 33 s):
| from | after Esc | later |
|---|---|---|
| Jeep (1) | on foot (5) | stays 5 |
| Truck (2) | on foot (5) | |
| Bus (3) | on foot (5) | |
| Hovercraft (19) | on foot (5) at 3 s | Swimming (21) at 13 s (it was over water) |
| Ship (10) | on foot (5) at 3 s | Swimming (21) at 13 s |
| Speedboat (6) | Frogman (11) | Swimming (21) at 13 s |
| Crawler (7) | Frogman (11) | stays 11 |
| Submarine (9) | Frogman (11) | stays 11 |
| Helicopter (13) | **Parachute (17)** | on foot (5) at 13 s (landed) |
| Biplane (12) | Parachute (17) | Frogman (11) after landing in water |
| Balloon (15) | Parachute (17) (needed 3 presses) | |
| Flying Boat (18) | Parachute (17) | Swimming (21) |
| Foot (5), Swimming (21), Parachute (17) | no change | |
Esc from a flying vehicle is therefore safe: the player drops by parachute (type 17), the HUD shows the parachute figure. Esc cannot be used to reach on-foot in the middle of the sea (Swimming).

True on-foot snapshot: `work/snapshots/raid_onfoot_dhafra.sav` (Jeep at Dhafra, Esc, `$6220 = 5`, mouse mode); `raid_foot_zafriya.sav` is the island 20 start on foot.

## Snapshots
Per distinct vehicle (15 types), taken 3 s after the HUD appears, 2 MB STE, mouse mode (`$eb76..7a = 0 0 ffff`):
`raid_jeep_dhafra`, `raid_truck_aledo`, `raid_bus_galva`, `raid_foot_zafriya`, `raid_speedboat_iquitos`, `raid_crawler_panao`, `raid_submarine_jebba`, `raid_ship_bourem`, `raid_biplane_maracay`, `raid_helicopter_lobos`, `raid_balloon_corozal`, `raid_parachute_calabar` (taken at once; the player lands within 4-5 s of running), `raid_flyingboat_vicenza`, `raid_hovercraft_thar`, `raid_swimming_vitoria`.
Moving snapshots (mouse mode): `raid_jeep_dhafra_moving`, `raid_helicopter_lobos_moving`, `raid_biplane_maracay_moving`, `raid_speedboat_iquitos_moving`. Controls: the pointer in the centre, then `h.rel(0,-200)` twice (mouse Y forward = throttle). Positions changed in 4-6 s: Jeep (25856,25600) -> (27038,24275) in 8 s; Helicopter x 25600 -> 25084; Biplane y 31250 -> 36598; Speedboat (25600,25856) -> (25194,25370).
`work/snapshots/raids_map.sav` is the island-map state used by the surveys.
Snapshots restore at 2 MB (`memsize_kb=2048`).

## Gotchas
- Pressing SPACE on an island once is final: there is no way back to the map from the island page, so every island needs a fresh restore of `raids_map.sav`.
- The Hatari instance time budget: the load is 40-60 s alone, 90+ s with another Hatari running. Do not gate on fixed sleeps; use `enter_raid`.
- The name-table location for the HUD is not shown on screen in the raid: the vehicle name appears only implicitly (cockpit graphics). The mapping `$6220` -> type was confirmed by cockpit graphics for all 15 types (`work/raids/raid_NN.png`).
