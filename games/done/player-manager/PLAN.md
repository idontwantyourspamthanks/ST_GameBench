# Player Manager — Master Plan (Task 1: 1989–90 92-Team Expansion & Task 2: Kick Off 2 Match Engine Port)

Target: `originals/PLAYERME` (English PP HAGA conversion, 1 MB RAM minimum target where feasible).
Status: **v1.0 complete & packaged** (`dist/PlayerManager_v1.0_patched_hd_2026-11-26.zip`, 1 MB STE 50 FPS verified). Next: **v1.1 — Amiga tiled pitch graphics port**.

---

## 0. Architectural Findings Summary

Both **Player Manager** (`FILES/PMLA` + `FILES/PRD`) and **Kick Off 2** (`games/queue/kick-off-2/originals/KICKOFF2/FILES/K2LA` + `FILES/KRD`) were written by Dino Dini in the same 68000 assembler/toolchain and converted by PP with the same loader architecture:

| Property | Player Manager (`PLAYERME`) | Kick Off 2 (`KICKOFF2`) |
|---|---|---|
| Depacked code address | `$010000..$02169c` (71.3 KB) | `$010000..$0204ac` (66.7 KB) |
| Data base (`a4 - $7ffe`) | `$02169c` (`a4 = $02969a`) | `$0204ac` (`a4 = $0284aa`) |
| Management code | `$010000..$018e7f` (~36 KB) | Menus/UI (~25 KB) |
| Match engine code | `$018e80..$0213bb` (~34 KB, `football.asm`) | ~40 KB (same family, extended) |
| Management→Match boundary | **2 calls** (`$0166cc`, `$016716`) → **`$018e86`** (`a0..a3`, `d0..d2`) + init `$018e80` (`$01030a`) | Standalone match entry |
| Asset archive | `FILES/PRD` (160 KB, `C3` packed) | `FILES/KRD` (299 KB, IFF/raw + `sprites.dat`, `SAMPLES.DAT`, `CORNSEL1/2.IFF`) |
| Free RAM in 1 MB STE | `$b0000..$cbfff` (**112 KB free**) | `$24000..$34000` (64 KB), `$4c000..$64000` (96 KB), `$b4000..$cc000` (96 KB) |

### 1 MB RAM Feasibility Analysis
- **Task 1 (92 teams + ~2,600 players):**
  - Team array: `44 × $64 = 4.4 KB` → `92 × $64 = 9.2 KB` (**+4.8 KB**).
  - Player pool: `1,500 × $2a = 63 KB` → `~2,600 × $2a = 109 KB` (**+46 KB**).
  - Fixture/cup tables + scrolling code: **~8–12 KB**.
  - Total extra RAM for Task 1: **~60 KB** — **fits comfortably inside 1 MB RAM** (112 KB free at `$b0000..$cbfff`!).
- **Task 2 (Kick Off 2 match engine in 1 MB RAM):**
  - PM's match engine (`$018e80..$0213bb`, 34 KB) and its match-only `Malloc`s (`$0187c6`: 72 KB graphics/samples, `$01d042`: 120 KB pitch/screen buffers = **192 KB**) are replaced by KO2's match engine + KO2's assets (`sprites.dat`, `SAMPLES.DAT`, pitch/replays).
  - Because management UI and the match engine never execute simultaneously, we can keep PM's 100 KB player/team/season data safe in RAM and **overlay/swap** match-only graphics/buffers if needed — making **1 MB RAM achievable** (and 2 MB+ effortless).

---

## 1. Task 1 — 1989–90 Football League Expansion (44 → 92 Teams)

### Goal
Expand Player Manager from its 44-team league (`[10, 10, 12, 12]`) to the full **1989–90 English Football League** (**92 teams**: `[20, 24, 24, 24]`), with scrolling league tables and fixture lists, and cleanly scaled cup competitions, fitting in 1 MB RAM.

### Key Touchpoints Identified in Disassembly
- **Division sizes table** (`a4-$70b2`, 6 refs: `$012ff4, $013366, $013568, $0135e0, $013718, $014af4`): `[10, 10, 12, 12]` → `[20, 24, 24, 24]`.
- **Team allocation & division pointers** (`$010150` `Malloc($1130)` → `$23f0`; `$0101c4..$0101ee` division boundaries `10/20/32/44` → `20/44/68/92`; ~14 hardcoded `44`/`43` loops across `$010a46..$01756a`).
- **1989–90 team names, kits, finances & squad-count table (`a4-$77f4`)**: replace the 44-team roster with all 92 real 1989–90 clubs (Div 1: 20, Div 2: 24, Div 3: 24, Div 4: 24).
- **Player pool & New Game quotas**:
  - Expand `Malloc($f618)` (`$0102ee`) and pool scans (`$014c3a, $014c48, $014c62`) from 1,500 players → ~2,600 players (109 KB).
  - Scale bucket quotas at `a4-$7d22` proportionally (~1,800–2,000 starting players); keep our fast setup optimisations (and revisit Option B if setup time grows back over ~3 min with 2× players).
  - Update Save/Load (`$014658..$0146c6`) for the larger team & player buffers.
- **Season calendar & fixture generator**:
  - Currently 18 weeks (Div 1/2) / 22 weeks (Div 3/4). Expand to **38 weeks (Div 1)** / **46 weeks (Div 2/3/4)** using a proper Berger round-robin generator (or expanded fixture table), aligning season length, end-of-season trigger, wages/finances, and promotion/relegation counts (3 up / 3 down between Div 1↔2, 2↔3, 3↔4).
- **Scrolling UI**:
  - **League tables** (`$012fe0..$013030` currently hardcoded to 12 visible rows): add Up/Down scroll controls (and auto-scroll to player's team) to view all 20 / 24 teams cleanly.
  - **Fixture lists & results screens**: add paging/scrolling for 10–12 matches per division per week and 38–46 week club fixture lists.
- **Cup competition (`The Cup`)**:
  - Expand from 44 teams to 92 teams with authentic staggered entry:
    - **1st Round:** 48 Div 3 & Div 4 teams (24 ties → 24 winners; or 28 ties with 8 byes → clean 64-team 3rd Round with all 44 Div 1 & Div 2 teams entering in Round 3? Note: 48 Div 3/4 → R1 (48→24), R2 (24→12)? Wait: `20 + 24 = 44` Div 1/2 teams, `64 - 44 = 20` spots! So R1 = 48 Div 3/4 → 24 winners, R2 = 8 ties (16 teams) + 8 byes → 16? Even cleaner: **R1 = 56 teams** (all 48 Div 3/4 + 8 Div 2, or 48 Div 3/4 with 16 byes → 16 ties = 32 teams → 16 winners + 16 byes = 32 in R2 → 16 winners + 44 Div 1/2 + 4 Div 2 byes = 64? Or simply: **R1: 48 Div 3/4 → 24 winners; R2: 8 of those 24 play 4 ties (20 left) + 44 Div 1/2 = 64 teams in Round 3 → R4 (32) → R5 (16) → QF (8) → SF (4) → Final (2)**!). We will inspect PM's existing cup draw & round-tracking code first to make the cleanest possible fit.

### Phased Milestones for Task 1
1. **1A — Deep-dive PM's league, fixture, cup, save, and UI routines** (disassemble all 6 `div_sizes` refs, fixture generator, cup draw, and table/fixture screens).
2. **1B — Data & Memory Expansion**: 92 teams (1989–90 lineup), 2,600-player pool, scaled quotas, updated 14 team-count loops, updated Save/Load.
3. **1C — Fixtures, Calendar & Promotion/Relegation**: 38/46-game round-robin schedule, 3 up / 3 down, end-of-season rollover verified.
4. **1D — Scrolling League Tables & Fixture Lists**: interactive scrolling on Division Tables and Fixtures screens.
5. **1E — 92-Team Cup Competition**: staggered entry, draw, results, and cup UI verified through a full season.

---

## 2. Task 2 — Porting the Kick Off 2 Match Engine into Player Manager

### Goal
Replace Player Manager's match engine (`$018e80..$0213bb`, "Kick Off 1.5") with **Kick Off 2's** match engine (`K2LA` + `KRD` assets), preserving Player Manager's unique features (**player stats feeding into the pitch, tactics/formations, play-as-player-manager-in-position vs play-as-team, goals/scorers/bookings/injuries/subs flowing back into management**) while gaining Kick Off 2's full gameplay & feature set (aftertouch, banana shots, pitch types, referees, replays, improved AI/passing/tackling/throw-ins/corners/graphics/sound).

### Architectural Approach (To Be Finalised After Deep-Dive)
Because `$018e86` is a **single, clean boundary** between PM's management half and its match engine:
1. **Reverse-engineer `$018e86`'s exact contract**: every input (`a0` home team, `a1` away team, `a2` tactics/match struct, `a3` player pool, `d0/d1/d2` mode/cup/player-manager flags) and every output written back to RAM (score, scorers, minute, yellow/red cards, injuries, fatigue, substitutions, extra time/penalties).
2. **Reverse-engineer Kick Off 2's match engine (`$010000..$0204ac`)**:
   - Locate KO2's match-init and match-loop entry points, its internal player/team structs (notice Dino Dini almost certainly reused the same 22-player pitch struct layout with extensions!), its pitch/referee/weather/replay/aftertouch options, and how `KRD` assets (`sprites.dat`, `SAMPLES.DAT`, `CORNSEL1/2.IFF`) are loaded.
3. **Design the 1 MB RAM Co-Residency / Overlay Bridge**:
   - Build a unified asset pack (PM's management assets from `PRD` + KO2's match assets from `KRD`).
   - Either relocate KO2's match engine code (~40 KB) into PM's freed `$018e80..$0213bb` + `$b3000+` space (or load KO2's match engine overlay on match entry into match RAM, run the match with KO2's own `a4`, then translate match outcomes back into PM's structs and restore PM's screen/VDI/vectors!).
   - **Overlaying KO2's match engine on match entry** is especially compelling for 1 MB RAM and reliability: KO2's code can run at its **native addresses** (or a single clean relocated base) with minimal instruction patching, while a thin **PM↔KO2 Adapter** maps:
     - PM's 11-player lineup + bench + 0..200 player attributes (pace, stamina, passing, shooting, tackling, keeping, aggression) → KO2's match player structs
     - PM's "Play in Position" (lock camera/control to the player-manager's player ID!) vs "Play as Team" (standard KO2 nearest-player switching)
     - PM's kit colours, team names, tactics (`4-4-2`, `4-3-3`, `4-2-4`, `5-3-2`, etc.), cup extra-time/penalties
     - KO2's match results (goals, scorers, bookings, injuries, substitutions) → PM's post-match structs.

### Phased Milestones for Task 2
1. **2A — Document `$018e86` (PM match contract)** and **KO2's match entry & player/team structs**.
2. **2B — Proof-of-concept bridge**: launch a live KO2 match from PM's "Play Match" button and return cleanly to PM's management screen with the final score recorded.
3. **2C — Full PM↔KO2 stat, tactic, kit, scorer/booking/injury, and Play-in-Position integration**.
4. **2D — KO2 features polish**: pitch conditions (dry/normal/soggy/wet), referee selection/strictness, action replays, aftertouch, cup extra time & penalties, verified on 1 MB STE / Mega STE / TT / Falcon.
