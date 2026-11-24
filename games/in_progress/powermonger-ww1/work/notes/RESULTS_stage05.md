# Stage 5 results (PMWW1Stage05, 2026-11-24): master's performance patches ported to WW1, one at a time, each gated

Evidence contract: **[obs]** = raw lines from a file named here (`work/runs/s5_*.txt`, line numbers cited); **[INFERENCE]** = reasoning only; failures are listed as failures.
Hatari 2.6.1, private HOME per run (`pmww.PMW`), work dirs `/tmp/pmww1s5/*`, ONE Hatari at a time. Cycles / fps are EMULATED time (Hatari's CycleCounter, flips per emulated VBL), never host time.
"16 MHz" on the STE = master's method (`hatari-option --cpuclock 16`, no cache model); the Mega STE is its own machine (`pm_mste` writes `$ff8e21 = 3`: 16 MHz + cache), see section 9.

## 0. Harness (new in this stage)
| tool | what |
|---|---|
| `tools/wws5snap.py` | cold boot of a built floppy, memory snapshots of three scenes (`map_idle` = the first 3D view, `get_men` = zoomed view with men moving, `random` = PLAY RANDOM LAND) -> `/tmp/pmww1s5/snaps/<machine>_<scene>.sav` |
| `tools/wwab.py` | port of master's `pmab.py`: both runs restore the SAME snapshot (committed default set live: tick, p3b, snd, ...), apply `test_walk*` (pointer driver) + `--base` live, the patched run adds `--only`; frames matched by (world tick, pass kind) and compared byte for byte (`back` = the frame just rendered, `shown` = displayed frame + software pointer); cycles per rendered pass (`$13e0a` .. flip `$e0e`), fps, world ticks/s; `--state` also compares the 101 376 B world state per flip; `--c3` a third buffer; `--count` executions of patch addresses. Runs sequentially (one Hatari). A run that crashes or stalls (< half the flips) is a FAIL |
| `tools/wwptr_test.py` | offline lock-step test of the pointer patches in unicorn (68000): two machines from the same 1 MB dump, random events, whole-RAM compare after every step |
| `tools/wwfill_test.py` | port of master's `pmfill_test.py`: renderer `$fc78` original vs patched over random cameras + direct random calls of the triangle setup, whole-RAM compare |
| `tools/wwblit.py` + `patches/test_blit.s` | random differential test of `p4_spr` in the running game (blitter and cache paths, 40 000 trials each, + negative controls) |
| `tools/wwtriple.py` + `patches/test_nowait.s` | tearing trace for the three buffers (video base / draw target / pointer buffer) + negative control |
| `tools/wwstress.py` + `patches/test_ovr.s` | IKBD ACIA overrun stress (random pointer / key traffic) |
| `tools/wwdumps.py` | 1 MB RAM dumps from the snapshots for the offline tests |
| test patches (never default): `test_walk{,2,3}` (pointer driver), `test_delay` (timing control), `test_blit`, `test_nowait`, `test_ovr` | |

Snapshots are STE 1 MB TOS 1.62, built from the committed default set (`build/s5_base`, md5 `cd60bc18...`). `map_idle` of this stage is the first 3D view after the island click: it shows hardly any tree (1 sprite-blit call per pass), unlike
`profile_ww1.md`'s scene; `get_men` (45 calls per pass) is the tree-heavy one.

Two findings that shaped the ports:
* WW1's game image overwrites `$5a0` (the `_p_cookies` pointer): the machine class can only be read in an `init` routine (supervisor, before the game). `p4_spr` therefore decides blitter / cache in its own `init` (master read core.s's FLAGS; WW1's FLAGS belong to `snd_core`), a first lazy version asked the cookie jar at the first blit and crashed the game (`Address Error` in the probe) [obs: first A/B run, log tail in `/tmp/pmww1s5/ab/spr_get_men`].
* The blitter ignores bit 0 of its address registers: a negative control with destination X increment 9 does NOT fail (it equals 8); increment 10 does.

## 1. p4_ptr_a + p4_ptr_b (`$87e`, `$9b8`; blobs `$75c40`, `$75d20`, data P `$75e00`)
Re-site of master's pointer-redraw skip (VBL handler `$774`: restore 16 saved lines + redraw at EVERY VBL, ~11.7 k cycles). Differences from master: addresses (`$1c49a` -> `$1d2ba`, `$2df78` -> `$2ed98`, `$2df92/94` -> `$2edb2/b4`, rows/stride `$1d4be/$1d4c0`), and the animation word `$2cfde`
is not always 0 in WW1: it is part of the recorded inputs and a cache entry exists only for the static frames 0 / `$320` (the WW1-only `cmp.w #$320,d0 / beq.b` skips the animation step).
Gates:
* offline lock-step (`work/runs/s5_ptr_offline.txt` line 2): 5400 steps in 90 trials over 3 dumps, events incl. screen pokes under the pointer, flips, hide, frame word, VBL counter: **IDENTICAL (whole 1 MB after every step)**, skip path taken in 1063 steps. Negative control (rectangle compare removed): **68 MISMATCH** (line 5).
* Hatari A/B (`work/runs/s5_ptr_ab.txt`): STE 8 MHz `map_idle` IDENTICAL (back 124, shown+pointer 81; line 4), `get_men` (back 62 / 34; line 12), `random` (back 111 / 103; line 30); skip path in 1365 of 1483 handler runs (line 13, `$75cca + $75ce2` vs entries `$75c40`).
  Negative control `--neg` DIFFER (line 50). 16 MHz (cpuclock): `map_idle` IDENTICAL (back 242, shown 241; line 6); `get_men` / `random` differ ONLY in render-only (R) frames (lines 14-28, 32-48); with `--tonly` (T frames hard) both IDENTICAL (`s5_ptr_ab_16.txt` lines 4, 9).
  The R frames depend on pass timing alone: `test_delay` (burn 1500 iterations per VBL in the pointer code, nothing else) on the same snapshot at 16 MHz gives the same kind of R-frame difference (`s5_timing_control.txt`: `DIFFER`, rows 82-98, column 18, `BACK DIFFER key (tick 303, R)`); self test base vs base at 16 MHz: IDENTICAL, all 179 frames (`s5_ptr_ab_16.txt` line 14).
* Regression (`PFX=s5 tools/stage04b_regress.sh ptr build/s5_ptr`): `s5_ptr_ste.txt` line 87 `CELL DONE ptr/ste-1.62-1024K: OK (517s)`, `hi@...` PASS at options / map / saveload / lose / win / round3 (lines 33, 47, 58, 63, 72, 80: `0 of 267264 bytes changed`), `payload@...` unchanged, `save/load ... 0 differ` (53), `world rate 3.995/s` (51);
  `s5_ptr_keys.txt` line 50 `KEYS 39 of 39 key/click pairs identical`; `s5_ptr_tt.txt` line 123 `TOOLTIP GATE ptr_tt: 116 lines PASS, 0 FAIL`.
* Speed (work/pass, STE): `map_idle` 8 MHz -4.43 %, fps 4.844 -> 5.010; `get_men` -4.48 %, 2.883 -> 3.014 (+4.5 %); `random` -4.35 %, 3.799 -> 3.989 (+5.0 %); 16 MHz -1.8 .. -2.1 % (lines 4-6, 12-14, 30-32). Master: -4.4 .. -5.6 % at 8 MHz.

## 2. p4_spr (`$1325e`; blob `$75f20`, init `$762e0`, cache data `$df000` 62 464 B) - state: differential + A/B PASS, regression cell RUNNING
Not failing now. History: first version (lazy cookie probe) crashed in the A/B (Address Error in the probe: `$5a0` is overwritten by the game); fixed by an `init` routine; all gates below are on the fixed code.
* `tools/wwblit.py`, 40 000 trials per case (`s5_blit.txt`): blitter + random words, blitter + real sheet addresses, cache + random words, cache + sheet: 0 mismatching trials, 0 register mismatches, `BLIT ALL PASS`.
  Negative controls (`s5_blit_control.txt`): blitter dest X inc 10 -> FAIL (2000/2000, 1987/2000), cache `or.l`->`and.l` -> FAIL (1882/2000); cache + random words PASS by design (outside the sheets the original code runs).
* `tools/wwab.py` (`s5_spr_ab.txt`, STE, base = ptr patches live): blitter 8 MHz `map_idle` IDENTICAL (back 80, shown 43), `get_men` IDENTICAL (56 / 38), `random` IDENTICAL (79 / 76); cache path (BLT=2 poked) the same three IDENTICAL (80/43, 49/26, 78/75); 16 MHz `get_men`, T frames hard: blitter and cache IDENTICAL.
* Speed (work/pass, fps): blitter `get_men` -19.6 %, fps 3.040 -> 3.762 (+23.7 %) (master -12 %); `random` -2.7 %, 4.022 -> 4.137; `map_idle` -0.3 % (this start view has 1 blit call per pass); cache `get_men` -14.2 %, 3.040 -> 3.531 (+16.1 %); 16 MHz get_men blitter 6.155 -> 7.673 fps (+24.7 %), cache 7.179.
  Cache hit rate (calls at `$75ffe` vs builds at `$7610a`): get_men 3060 / 22, random 405 / 5, map_idle 99 / 1 (>= 99 %); ST-machine rate not yet measured.
* Pending: regression cell on `build/s5_spr` (running), ST + Mega STE cold-boot `hw` check (BLT word), ST speed.

(sections 3.. follow as the patches are gated)
