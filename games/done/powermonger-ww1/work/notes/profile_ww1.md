# WW1 vs Powermonger: speed, profile, and what master's performance work transfers (PMWW1Profile, 2026-11-23)

Evidence tags: **[obs]** = a number my tools produced this session (raw files in `work/profile/data/`, scripts in `work/profile/`); **[INFERENCE]** = arithmetic / reasoning from [obs] numbers, not run.
Hatari 2.6.1-devel, STE, TOS 1.62, 1 MB, private HOME, workdir `/tmp/pmww1prof/`, unpatched games (EA `ea.st` and master's `protected.st` via master's snapshots).

**Units.** Everything is EMULATED time: fps = flips of `$ff8201` per 400 emulated VBL x 50 / 400 (Hatari's VBL counter, not host time); cycles = Hatari's `e CycleCounter` (emulated CPU cycles) or `profile save` cycles. No host wall-clock figure is used anywhere (another Hatari runs on the host).
**"16 MHz"** = master's method: the same STE machine with `--cpuclock 16` (no Mega STE cache model, no 8 MHz-bus wait states beyond what Hatari does). I did not boot a TOS 2.06 Mega STE.
**Method = master's** (`baseline.md`, `hotpaths.md`): restore a snapshot, warm up 60 VBL, `fps` over 400 VBL, `profile save` over 300 VBL (+ 25 end margin), and `e CycleCounter` at the loop call sites over 300 VBL.
One departure (Hatari behaviour): in this Hatari build every debugger breakpoint stop resets the profiler (log: `Freed previous CPU profile buffers` after each hit), so profile and call-site trace are two consecutive windows of the same run, not one window as in master's `pmprof2.py`. A control: master's own scenes re-measured with my tool reproduce master's baseline table (below).

## 0. Answers in one paragraph
1. **WW1 is not slower per unit of work; the code is the same engine.** Cycles per terrain scanline `543.3` in WW1 map_idle vs `543.3` in Powermonger map_idle; per triangle setup `1442/1347` vs `1430/1375`; per 3-column sprite blit `20.0k/18.6k` vs `20.2k/17.9k`; window copy `164-175k` vs `165-176k`; sample IRQ `265` vs `264` cycles per entry. What differs is the SCENE: WW1's start view is tree-heavy (51 sprite blits per pass vs 18) and, in my get_men scene, zoomed in (14.6 scanlines per triangle vs 10.7). On the starting view WW1 runs 1.9 fps vs 2.3 fps (8 MHz); on a comparable close-up 3.1-3.9 fps vs 3.7-3.9 fps.
2. **Renderer = master's code, shifted.** 11 of the 12 hottest routines match master's mnemonic-for-mnemonic (list in section 3); the other one (pointer) is 98 % identical; the cell loop differs by one extra colour test (section 4). The DeepSeek claim "WW1 renders differently / much slower" is **refuted** for the renderer; "triangle routines do not transpose" is **refuted** (`$f342` = master `$ef62`, 234/234 instructions equal). Its claim that the YM sample IRQ at `$1bc92` is "a timer-C sequencer" is also wrong: it is master's timer-A sample player (`$1af32`), 26/26 instructions equal, 265 cycles per interrupt.
3. **All of master's performance patches apply**, by re-siting; none needs a different renderer. Biggest wins for WW1: sprite blitter (`p4_spr`) because of the trees, sound DMA (`snd_*`) while a sample plays, triangle setup+fill (`p6_*`), pointer skip (`p4_ptr_*`), triple buffering at 16 MHz.
4. Plan in section 6; the only real design question is RAM placement (master's blobs need ~110 KB, the stage-1 payload window is 22.5 KB).

## 1. Speed, same machine, master's method [obs]
Scenes. WW1 `map_idle` = the 3D view right after the protection answer (`work/profile/data/map_idle.png`); WW1 `get_men` = overview click on the island, 3-sword icon, GET MEN (a zoomed close-up of the terrain, 1-3 men moving; `get_men.png`). Powermonger scenes = master's own snapshots (`map_idle`, `get_men`, `battle_320`). **No WW1 battle scene was reached** (no enemy in reach on the start land; the PM battle is not slower than its get_men: 3.75 vs 3.875 fps, so the cost model below covers it). Scenes are NOT pixel-equal across the two games (different land, zoom), so section 2 gives per-unit costs.

fps = flips/400 VBL (`flips` shown); `cyc/pass` = mean cycles between two window copies (`$13e0a` / `$13096`) over the trace window (`data/passes.txt`); VBL/pass = mean emulated VBL between them.

| game | scene | CPU | flips/400 VBL | fps | cyc/rendered pass | VBL/pass | master's own table (baseline.md) |
|---|---|---|---:|---:|---:|---:|---|
| PM | map_idle | 8 | 18 | 2.250 | 3 468 383 | 21.6 | 2.38 fps |
| WW1 | map_idle | 8 | 15 | 1.875 | 4 235 957 | 26.5 | |
| PM | get_men | 8 | 31 | 3.875 | 2 150 217 | 13.4 | 4.00 fps |
| WW1 | get_men | 8 | 25 | 3.125 | 2 083 229 | 13.0 | |
| PM | battle_320 | 8 | 30 | 3.750 | 1 995 451 | 12.5 | 3.88 fps |
| PM | map_idle | 16 | 50 | 6.250 | 2 564 094 | 8.0 | 6.25 fps |
| WW1 | map_idle | 16 | 40 | 5.000 | 3 205 117 | 10.0 | |
| PM | get_men | 16 | 65 | 8.125 | 2 073 072 | 6.5 | 8.25 fps |
| WW1 | get_men | 16 | 57 | 7.125 | 1 935 612 | 6.0 | |
| PM | battle_320 | 16 | 66 | 8.250 | 1 923 072 | 6.0 | 8.25 fps |

Notes: a flip count of 400 VBL has +-1 flip = +-0.125 fps granularity (WW1 get_men 8: 25 flips = 3.125 fps but 13.0 VBL/pass from the trace = 3.85 fps; the trace window is the more precise one, 24 passes). The first-run PM numbers match master's (6.25/8.25/8.25 exact at 16 MHz) so the method is the same.
Summary: WW1 map_idle is 22 % more cycles per pass than PM map_idle (scene: more sprites, see below); WW1 get_men is 3 % FEWER cycles per pass than PM get_men (8 MHz trace means). There is no 2-5x slowdown anywhere.

## 2. Per-unit costs (identical code => identical unit costs) [obs, 8 MHz profile windows, `data/tables.txt`]

| quantity | WW1 map_idle | PM map_idle | WW1 get_men | PM get_men | PM battle_320 |
|---|---:|---:|---:|---:|---:|
| triangles / rendered pass | 120.2 | 124.5 | 121.3 | 127.1 | 125.4 |
| scanlines / pass | 1348 | 1907 | 1765 | 1362 | 1334 |
| span fill cycles per scanline | 543.3 | 543.3 | 524.2 | 521.8 | 521.6 |
| triangle setup cycles per triangle | 1442 | 1430 | 1347 | 1375 | 1376 |
| 3-col sprite blit calls / pass | 50.9 | 17.8 | 13.3 | 18.0 | 18.0 |
| cycles per blit call (`$1325e` / `$124a8`) | 20 037 | 20 212 | 18 609 | 17 878 | 17 823 |
| window copy cycles / pass | 175 185 | 176 513 | 164 496 | 165 060 | 165 276 |
| sample IRQ cycles per entry | 265 | 266 | 265 | 263 | 263 |

So WW1 map_idle is slow because its start view draws 51 tree sprites (1.02 M cycles/pass = 25.9 % of the profile) and a sample IRQ share of 25.9 % (a sound plays at start, as in PM: 25.9 %); PM's start view draws 18.

## 3. Where the time goes, hot blocks mapped to master [obs]
Blocks = contiguous executed addresses (gap <= 64 B) in the Hatari profile; "master" = best address shift by the 12-byte-anchor map (`tools/addrmap.py`), "equal" = capstone mnemonic sequences compared over the whole block (`data/equiv.txt`). % = share of the profiled cycles, 8 MHz.

| WW1 block | master block | role | equal mnemonics | WW1 map_idle % | WW1 get_men % | PM get_men % |
|---|---|---|---|---:|---:|---:|
| `$e7c6-$e8be` | `$e3e6` | terrain span fill, head + loop | 105/105 | 13.4 | 26.9 | 22.9 |
| `$e90a-$e98a` | `$e52a` | span fill tail | 55/55 | 5.2 | 13.6 | 11.5 |
| `$f342-$f5c2` | `$ef62` | triangle setup (6 `divu`) | 234/234 | 4.4 | 7.2 | 8.5 |
| `$1325e-$1332e` | `$124a8` | masked sprite blit, 3 columns | 96/96 | 25.9 | 10.9 | 15.6 |
| `$1bc92-$1bce8` | `$1af32` | timer-A sample IRQ (YM volume `movep`) | 26/26 | 25.9 | 12.2 | 5.1 |
| `$13a94-$13abe` | `$12ce0` | 32 000 B window copy | 13/13 | 4.4 | 7.2 | 8.0 |
| `$866-$9dc` | `$1372` | mouse pointer in VBL | 98 % (difflib on mnemonics; 2 instructions differ, `cmp.w #$320,d0 / beq.b` is WW1-only) | 7.2 | 7.1 | 7.0 |
| `$e04-$ef8` | `$1870` | VBL-flag spin | 56/56 | 3.0 | 4.2 | 4.5 |
| `$12cba-$12e94` | `$11f12` | small sprites / object positions | 208/208 | 4.4 | 1.9 | 3.6 |
| `$10118-$101da` | `$fccc` | terrain cell loop | differs, see section 4 | 1.0 | 1.7 | 2.2 |
| `$1729a-$17534` | `$163ea` | army/people list move | 232/232 | 0.7 | 1.2 | 2.3 |
| `$12ff8-$131d2` | `$12242` | sprite clip front end | 183/183 | 0.8 | 0.6 | |
| `$158b2-$15904` | `$14b62` | men sim / status bars | 19/19 | 0.4 | 0.7 | 0.9 |

Of all profiled cycles, 89.9 % (map_idle) / 88.2 % (get_men) lie in blocks with >= 90 % equal mnemonics; 98.4 % / 97.6 % lie in blocks >= 0.2 % each and every one of those is either equal or the two cases below (equal numbers include only blocks that my naive alignment matched: pointer and cell loop are the two that need the section 4 look).

Stage split (CycleCounter at the main-loop call sites, 8 MHz; `data/stages.txt`; "landscape" = `$fc78` / `$f898`):

| stage | WW1 map_idle | PM map_idle | WW1 get_men | PM get_men |
|---|---:|---:|---:|---:|
| logic | 386 k (9.1 %) | 302 k (8.7 %) | 233 k (10.6 %) | 238 k (10.2 %) |
| VBL wait | 46 k (1.1 %) | 34 k (1.0 %) | 63 k (2.8 %) | 121 k (5.2 %) |
| window copy | 266 k (6.2 %) | 254 k (7.3 %) | 187 k (8.4 %) | 196 k (8.4 %) |
| landscape + objects | 3 423 k (80.4 %) | 2 707 k (77.9 %) | 1 634 k (74.0 %) | 1 661 k (71.0 %) |
| HUD / UI / men / weather / rest | 139 k (3.3 %) | 178 k (5.1 %) | 92 k (4.2 %) | 124 k (5.3 %) |
| total / pass | 4 259 k | 3 474 k | 2 209 k | 2 340 k |

At 16 MHz the same blocks lead: WW1 get_men 16: span fill 28.4 + 14.4 %, sprite blit 11.5 %, VBL wait **10.8 %**, triangle setup 7.6 %, copy 7.4 %, sample IRQ 5.8 %; map_idle 16: sprite blit 32.8 %, fill 16.8 + 6.5 %, IRQ 13.0 %, setup 5.5 %.

## 4. Is the renderer different? The one real difference [obs]
The terrain cell loop (`$10118` vs master `$fccc`) is the same routine with one added test per triangle (WW1 disassembly vs master, `bsr.w $f342` = master `bsr.w $ef62`):

```
WW1  $10140 move.b $0(a1),d3 ; $10144 bge.b $1014a ; $10146 move.b #$1f,d3 ; $1014a cmpi.w #$c,d3 ; bge ; add.w d5,d3 ; movem.l ... ; bsr.w $f342
PM   $fcf4  move.b $0(a1),d3 ;                                                 $fcf8  cmpi.w #$c,d3  ; bge ; add.w d5,d3 ; movem.l ... ; bsr.w $ef62
```
i.e. a cell colour byte with the sign bit set is clamped to colour `$1f` (a 32nd terrain colour); WW1 therefore has more terrain colours (more pattern rings; palette/patterns are DATA, the fill code is the same). Cost: ~16 cycles per triangle, < 0.5 % of a pass. Nothing else in the 98 % of profile cycles I mapped differs. **[INFERENCE]** the visual difference between the games (grey WW1 palette, trenches/craters as extra colours, portrait background picture in the 32 000 B window image) is data, not code.
Not verified: the code/data used outside the hot paths (menus, intro, the war-specific captain/people logic).

## 5. Master's performance patches: applicability and gain for WW1
Gain estimates use master's MEASURED per-unit savings (`hotpaths2.md`: p6_tri/slope -13.2..-13.8 % of a pass = about 500 cycles per triangle + 126 per scanline; p6_cpy -35..-58 k per pass; p4_spr ~7.0 k vs ~17.9 k per blit = ~10.9 k saved per call; pointer 7.0 % -> 1.7 %; DMA sound producer 2.2-5 % instead of the IRQ's 5-26 %) applied to WW1's counts of triangles/scanlines/calls from section 2 [INFERENCE: arithmetic, not run]. "8 MHz" percentages are of the cycles of one rendered pass.

| master patch | WW1 verdict | WW1 site (addrmap, 8/8 instructions) | est. gain WW1 map_idle / get_men (8 MHz) |
|---|---|---|---|
| `p6_slope` + `p6_tri` (setup + fill, exact) | identical routine, re-site (`$ef62`->`$f342`, filler `$e3e6`->`$e7c6`, ring/table addresses re-derived; flat-top/ring-wrap logic unchanged) | `$f342` (data tables: re-derive) | -5.8 % / -12.4 % (230 k / 283 k per pass) |
| `p6_cpy` (window copy on blitter) | identical routine | `$13a94` | -1.5 % / -2.5 % (58 k) |
| `p4_spr` (blitter / pre-shifted sprite cache) | identical routine (`$124a8`->`$1325e`, 96/96) | `$1325e` | **-14 % / -6.4 %** (51 resp. 13.3 calls x ~10.9 k) |
| `p4_ptr_a`/`p4_ptr_b` (skip pointer redraw) | similar: routine 98 % equal; the 2 differing instructions are not on the skipped path | `$87e` / `$9b8` (mapped) | -5.4 % / -5 % (7.2 % share -> ~1.7 %) |
| `p7_triple_*` (3 buffers, no VBL wait) | identical logic (flip `$e0e`, wait `$e04`, flag `$2edac`); needs a 32 000 B buffer outside the game's RAM | `$145e2`, `$e2c`, `$13e04` | +3.0 % / +4.2 % at 8 MHz; **+10.8 % get_men at 16 MHz** (VBL wait share) |
| `snd_*` (STE DMA sound) | identical player (`$1bc92`, `$1bbbc`...); sample playing only | `$1c4de`, `$6de`, `$1bbbc`, `$1bb96` | -20 % of a pass while a sample plays (IRQ 25.9 % -> ~3 %) in map_idle, -10 % in get_men |
| `p3b_interp` / `p3b_delta` (men smoothing) | similar, needs tick; sites mapped | `$13e1e`, `$13e3c` | 1-2 % cost, a smoothness feature |
| `tick_*` (fixed 4 Hz world) | similar: loop head must be re-derived (addrmap: `tick_head` 0/8) | `$13da0` etc. (stage 2) | feature (speed-independence) |
| `p4_clamp`, `pm_cachecap`, `tt_ptr`, `pm_mste` | safety / platform, identical or game-independent | `$ed6`, `$e3f2`, `$e20`, init | none (needed) |
| `p4_chase` (not default) | n/a (master left it off: inexact) | | |
| **not applicable** | none found | | |

Total if all of `p6`, `p4_spr`, `ptr`, `triple`, `snd`, `cpy` are in: **[INFERENCE]** get_men 8 MHz 2.28 M -> ~1.35 M cycles per pass (-40 %), i.e. ~5.5-6 fps from 3.1-3.9; map_idle 8 MHz (while the start sample plays) 3.94 M -> ~1.9 M (-50 %), ~4.2 fps from 1.9; after the sample ends the start view is ~3.0 M -> ~2.2 M. Master's final PM numbers for reference (hotpaths2): get_men 5.4 fps, map_idle 3.4 fps at 8 MHz. So WW1 ends where PM ends, a bit better on get_men because its fill/scanline share is the same and its pointer/sprite-share gains are the same. Not measured: no patched WW1 exists yet.

## 6. Recommendation for stage 5
Order (cheapest exact win per unit effort first; all are RE-SITES of master's sources + address re-derivation, Sonnet-class work with master's gates `pmab` frame A/B, `pmfill_test.py`):
1. `snd_core/start/stop/setup` (DMA sound): -10..-20 % while a sample plays, trivial sites (4 of 4 map 8/8, payload only needs the staging buffer 16 KB).
2. `p4_ptr_a/b` + `p4_clamp`: -5 % always; one RAM block (288 B).
3. `p4_spr`: -6..-14 %; STE-blitter path needs no cache; the plain-ST pre-shifted cache (62 KB) can be left out (ST gets the original code) if RAM is short.
4. `p6_slope` + `p6_tri`: -6..-12 %; 16 KB table + 2 KB code; re-derive the filler/ring/table addresses; the unicorn differential test `pmfill_test.py` must be retargeted to the WW1 image and the 3 snapshots (the 1 extra `move.b #$1f` colour does not touch `$f342`).
5. `p6_cpy`: -1.5..-2.5 %; 200 bytes.
6. `p7_triple_*`: +3..+4 % at 8 MHz, up to +11 % at 16 MHz; needs a 32 000 B 256-aligned buffer.
7. `p3b_*`, tick: with stage 2.
**Needs the design model:** nothing in the renderer. The ONE design decision is RAM placement: master's set needs ~16 KB slope table + 2 KB p6_tri + 16 KB sound staging + 32 KB third buffer (+ 62 KB ST sprite cache) = 66-128 KB, but the stage-1 payload window `$72000-$77fff` holds 22.5 KB. Free RAM [obs, RAM dumps at the map view, `/tmp/pmww1prof/res/*.bin`]: `$a0000-$f7fff` has 10 non-zero bytes (all at `$f7fc8-$f7fff`, the supervisor stack); resource-cache cursor `$2cfda` = `$9fc58` at the map view (`$a7958` after the lose picture, `$af658` after the win picture per Stage-01 notes). Proposal: keep the small hooks/code in `$72000-$77fff`, put the big data (slope table, third buffer, sound staging, optional ST cache) above a `pm_cachecap` cap at e.g. `$b8000` (analog site `$e3f2`, mapped 8/8), exactly master's design; it needs the Retire/Win/Lose gate (`pmretire` analog) again. That is the only place the lead/design model should decide.

## 7. Evidence list
`work/profile/data/`: `chain.log` (fps lines), `passes.txt`, `stages.txt`, `tables.txt` (top-10 blocks per scene), `equiv.txt` (mnemonic comparison), `*.json` (raw `(pc, CycleCounter, VBL)` trace records + fps), `profiles_txt.tgz` (the Hatari `profile save` files), `map_idle.png`, `get_men.png`. Scripts: `boot_snap.py`, `snap_getmen.py`, `measure.py`, `analyze.py`, `report.py`, `tables.py`, `stages.py`. Snapshots and 1 MB dumps stay in `/tmp/pmww1prof/`.
Failures/limits: first chain run produced empty profiles (profiler reset by breakpoint stops; fixed by separate windows, the first runs were discarded); two PM runs failed on a 23-byte memstate path limit (workdir renamed); no WW1 battle scene; no real Mega STE (TOS 2.06 + cache) run; 16 MHz = `--cpuclock 16` only.
