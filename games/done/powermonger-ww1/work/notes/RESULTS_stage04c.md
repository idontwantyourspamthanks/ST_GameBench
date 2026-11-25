# Stage 4c results (PMWW1Stage04c, 2026-11-24): campaign-end image classification, tooltip full run, then the remaining stage-4 patches gated one at a time

Evidence contract: **[obs]** = raw lines from a file named here; **[INFERENCE]** = reasoning only; failures are listed as failures.
Hatari 2.6.1 (`~/Code/AtariST/hattari/build/src/hatari`), private HOME per run (`<workdir>/home`), work dirs `/tmp/pmww1s4c/*`, one Hatari at a time. Logs `work/runs/s4c_*.txt`.
Builds (cumulative, fresh, `wwpatch.py build --floppy --only ... --out build/g_*`): `BASE` = `p4_clamp pm_cachecap pm_credit pm_mste pm_nokeydisk pm_noprot pm_noprot_box pm_tooltip qol_keys qol_keys2 tick_click tick_click2 tick_click3 tick_head tick_men tick_pass tt_ptr`;
`g_ctl` = BASE + tick_wx (= the committed default), `g_rain` = BASE + tick_rain, `g_hover` = + qol_hover qol_hover2, `g_interp` = + p3b_interp p3b_delta, `g_snd` = + snd_core snd_setup snd_start snd_stop.

## 1. Campaign-end image FAIL: classification and the corrected gate
**What the FAIL was.** `wwgate.imgcheck` compared the resident image `$576-$1d2ad` after the ending with the hand-over dump and failed on any differing span >= 256 B. The game keeps variables, tables and buffers inside that range, so a run always differs.
**Method.** (a) the same scenario on the CORE-ONLY build (`build/core_only`: only the loader, the game's own protection question and disk swap, `wwend.py final --orig-flow`), the image listed at the map view (before the ending) and after it;
(b) the differing spans are disassembled / dumped (`work/dumps/entry576.bin` against `img_final_end.bin`); (c) a code-execution watch: a `b pc > lo-1 && pc < hi+1 :trace :file` breakpoint per differing span from the first instruction after the title (Hatari 2.6.1 has no `>=`: the first try printed `Unrecognized number prefix` and
the positive control caught it: 0 hits at the win routine; Hatari's CPU `profile` is not usable from the remote debugger: the file stays empty). The gate now FAILS if (1) the control breakpoint over the win routine `$1b182-$1b19f` does NOT fire, (2) a differing span is not in the watch list, (3) any instruction is fetched from a watched span.
**Result [obs]** (`work/runs/s4c_end_final.txt`, `s4c_end_core_final.txt`, list `work/runs/end_watch_spans.txt`).
```
build/core_only, original flow (disk swap + protection answered), campaign table forced to ones, RETIRE won  (work/runs/s4c_end_core_final.txt):
GATE end_final image@final_map (listed) PASS 2288 B differ in 33 span(s) ...                                  <- the same kind of spans BEFORE the ending
GATE end_final image@final_end span watch positive control (pc breakpoint over $1b182-$1b19f sees the win routine) PASS 7 distinct pc(s) $1b182, $1b186, $1b188, $1b18e, $1b194, $1b19a, $1b19c
GATE end_final image@final_end every differing span was watched for execution PASS 33 of 33 spans inside the watch list; unwatched: none
GATE end_final image@final_end no instruction was executed inside the watched spans (nothing was loaded as code later) PASS executed pcs inside the watched spans: none; 2291 B differ in 33 span(s)
GATE end_final only resource 15 (WIN.PAK) was requested at the end PASS resources [15]       CELL DONE end_final: OK
patched build (build/s4c_mste = committed set + mste), same scenario (work/runs/s4c_end_final.txt): 30 spans, 2284 B (the number of the earlier FAIL), watch PASS, CELL DONE end_final: OK  (see the file for the exact lines)
```
**Classification of the differing spans** (hand-over image `work/dumps/entry576.bin` against `img_final_end.bin` of the core-only run; xrefs = 4-byte absolute operands in the image):
* **Zero in the hand-over image = run-time tables / buffers inside the file's range (BSS-like): about 2 100 of the 2 284 bytes.** `$763c-$793d` (770 B: the open window's instance text / button buffer, `WTEXT $7640`, starts `...ABOUT ...`), `$dbd5-$dd68` (404 B: a resource descriptor / name record `WIN     PAK` plus decoder state),
  `$120fa-$12425` (812 B: a table of 8-byte records `ffff 0000 0000 0000` x 101), `$e431-$e45d`, `$e46f-$e473`, `$e4bf-$e501`, `$e51f-$e53d`, `$e573-$e585` (the resource directory's slots: sizes `0x1fa800`, `0x35b400` and the TOS ROM pointer values `00e59400`..), `$74bb-$74c7`, `$d41f-$d42d`, `$f5c2-$f5da`, `$1af96-$1afb3` (15 words), `$fade-$faf6`, `$fba9-$fbbb`.
* **Non-zero in the hand-over image, 1-5 bytes: single variables / flags** `$2073 $82c5-6 $a389-b $e2d6-7 $e7c3-5 $fc70-7 $1025b-$10273 $1040b-$10414 $1b8fe-$1b900 $1d0d0-5` and the one-byte slots in front of function entries (`$10335 $1194d $1243f $12483 $13ccd`: the byte before `47f9...` / `48e7...` = an odd-aligned flag byte, never an instruction); `$1bc9b-$1bc9d` is the pointer variable `$1bc9a` (`snd_stop` writes its constant there).
* **One CODE slot: `$15998-$1599b`** (two `bra.w $16f84` of the protection flow): in the ORIGINAL flow (core-only: the game's own protection question answered) the game overwrites it with the flag `$0000002c` (`wwgate` logs `flag $15998 after the correct answer`), the patched build's `pm_noprot` site is the same place and is masked. The slot is self-modified data, never executed afterwards (the watch).
**Answer to the question: no code is loaded later** [obs: 0 instructions fetched in any of the 33 differing spans from the first instruction after the title to the end picture, with a positive control that sees the win routine; the same spans exist at the map view, before the ending; the loader after the retire click requests resource 15 only] -
the "dead END_PIC1 / END loader" conclusion stands: nothing of the ending needs a resource other than WIN.PAK. The orphan run (`work/runs/s4c_end_orphan.txt`): the rewritten dispatch calls `$1b3a6`, the loader asks for resource 12 and the disk requester `PLEASE INS...` appears (the game would wait for END_PIC1 for ever): `GATE end_orphan the orphan routine ran PASS`, `GATE ... WW1 disk only: the requester for the missing file appears PASS`
(its image check is list-only: the test itself rewrites `$d6de` and the win routine does not run).
The span set varies by a few bytes between runs (timing-dependent variables: `$fade`, `$fba9`, `$1b828`, `$11dc8`): the watch list is the union (`work/runs/end_watch_spans.txt`) and the gate fails on any span that is not in it.
Tools: `tools/wwend.py --watch FILE --orig-flow`, `wwgate.imgcheck(info / executed / ctl / watch)`.

## 2. Tooltip gate, full run, committed default incl. the new Build wording
`build/g_ctl` = the committed default set (BASE + tick_wx), STE TOS 1.62 1 MB, `wwtt.py gate` (no `--quick`; `work/runs/s4c_tt_full_ste.txt`):
```
TOOLTIP GATE tt_ctl: 584 lines PASS, 0 FAIL
CELL DONE tt_ctl: OK
GATE tt_ctl id  7 Build level 3 swords pixels == reference rendering PASS text 'Build (I): a town workshop makes tanks': 0 of 624 bytes differ
GATE tt_ctl id  7 Build level 2 swords pixels == reference rendering PASS text 'Build (I): a town workshop makes planes': 0 of 624 bytes differ
GATE tt_ctl id  7 Build level 1 sword pixels == reference rendering PASS text 'Build (I): a town workshop makes rifles': 0 of 624 bytes differ
```
(the line is composed live, compared with the Python rendering of the same text byte for byte, in the displayed buffer and in a screenshot; also every other id, levels, the erase, the key labels).

## 3. Patch gates (cumulative builds, STE 1 MB unless stated)
### 3.1 tick_rain (replaces tick_wx)  build/g_rain
Smoke `work/runs/s4c_rain_smoke.txt`: `CELL DONE rain_smoke/ste-1.62-1024K: OK (135s)`.  Own gate `wwrain.py` (rain on the actual screen pixels at every main-loop top, 16 MHz so that render-only passes exist), control = the committed tick_wx build:
```
s4c_rain_gate.txt     RAIN tick_rain 16 MHz: rain on 40 of 40 consecutive frames; ... 21 distinct world ticks in the window      GATE rain tick_rain 16 MHz rain on every frame PASS 40 of 40 (clock on in 40)
s4c_rain_control.txt  RAIN tick_wx_control 16 MHz: rain on 21 of 41 consecutive frames                                         GATE rain tick_wx_control 16 MHz rain on every frame FAIL 21 of 41 (clock on in 41)   (the gate can fail)
```
Regression `tools/stage04b_regress.sh rain build/g_rain` (`s4c_rain_summary.txt`): `GATE rain/ste-1.62-1024K world rate = 4.00/s (+-5 %) PASS 3.995 world steps per emulated second`, `CELL DONE rain/ste-1.62-1024K: OK (521s)` (fill-hi + loader trace: every checkpoint 0 bytes changed), `KEYS 39 of 39 key/click pairs identical`, `CELL DONE rain_keys: OK`, `TOOLTIP GATE rain_tt: 116 lines PASS, 0 FAIL`.
**tick_rain: PASS** (all four gates).  `tick_wx.s` stays in the tree as `; default: no` (rain replaces it).

### 3.2 qol_hover / qol_hover2  build/g_hover
Smoke `s4c_hover_smoke.txt`: `CELL DONE hover_smoke/ste-1.62-1024K: OK (136s)`. Own gate `wwhover.py` (`s4c_hover_gate.txt`): first run FAIL `HIT $0, RES 1, ARM 0`: **a debugger poke of `$2edb2/$2edb4` does not hold** [obs: `w` reports "Wrote 2 'b' values", the next read returns the old `$3c / $18`, `/tmp/pmww1s4c/hvp2`]; the gate now moves the real pointer (`goto_st`). Re-run: `GATE hover a house under the resting pointer is picked (HIT) PASS HIT $542fa`, `BUF == reference rendering of SB PASS 0 of 624 bytes differ`, `pointer away: the hover text is gone from both buffers PASS`, `Build icon selected: ... PASS got 'Build here: no workshop here'`, `CELL DONE hover hover: OK`.
**Gap:** that town has no workshop, so `making <item> (NN%)` was not exercised. The gate now also pokes the settlement record (item `$c`, countdown `$10`) and checks the text: **written, NOT run** (re-run `tools/wwhover.py cold --disk build/g_hover/floppy.st ...`).
Regression `s4c_hover_*`: `CELL DONE hover/ste-1.62-1024K: OK (525s)`, `CELL DONE hover_keys: OK`, `TOOLTIP GATE hover_tt: 116 lines PASS, 0 FAIL`.

### 3.3 p3b_interp / p3b_delta  build/g_interp
Smoke `CELL DONE interp_smoke/ste-1.62-1024K: OK (137s)`. `wwinterp.py` 16 MHz (`s4c_interp_gate16.txt`): 231 of 231 passes people table restored, 231 of 231 with offsets, 0 records with other bytes changed, 94 distinct drawn x low bytes, `CELL DONE ... OK`.
**8 MHz (`s4c_interp_gate8.txt`): FAIL `people table restored ... T1 == T0: 46 of 103`** (NMOV 0, no offsets: those checks PASS). [INFERENCE] at 8 MHz a pass contains the world step, so T1 != T0 may be legitimate; NOT confirmed: the gate now prints which records / bytes differ (`s4c_interp_gate8b` was queued, not run). Open: run it, then decide whether the check is only valid for render-only passes or the patch has a bug.
Regression `s4c_interp_*`: `CELL DONE interp/ste-1.62-1024K: OK (526s)`, keys OK, `TOOLTIP GATE interp_tt: 116 lines PASS, 0 FAIL`.

### 3.4 snd_*  build/g_snd (DMA sound)
```
STE   s4c_snd_smoke_ste.txt: CELL DONE snd_smoke/ste-1.62-1024K: OK (259s); FLAGS $3; DMA plays a chunk PASS; PSGCHECK snd_smoke: PASS (violations 0, warnings 0; reg-7 writes 2, reg-14 writes 329, FDC commands 874, ...)  (saveload = disk access in the cell)
Mega STE 4 MB s4c_snd_smoke_megaste.txt: CELL DONE ... OK (243s); PSGCHECK snd_mega: PASS (violations 0, warnings 0; ... FDC commands 884 ...)
ST    s4c_snd_smoke_st.txt: FLAGS $6, `plain ST path (no DMA, original YM player) PASS`, CELL DONE OK (202s)
WAV effect 47, YM build (g_interp) vs DMA build, STE:  CMP rho = +0.9630 at lag +0.0 ms; durations 0.443 / 0.439 s; rms 4158 / 5436   (master: +0.963, 0.443 / 0.439)
WAV effect 47 on ST, YM build vs snd build: CMP rho = +0.9978; durations 0.443 / 0.443 s; rms 4111 / 4116   (the ST path is the original player)
regression (--psg): CELL DONE snd/ste-1.62-1024K: OK (519s); PSGCHECK snd_ste: PASS (violations 0, warnings 0; reg-14 writes 454, FDC commands 1081 ...); keys OK; TOOLTIP GATE snd_tt: 116 lines PASS, 0 FAIL
```
**snd_*: PASS on STE / Mega STE / ST** (Falcon: see 4).

## 4. Falcon (lead's correction): fal_ym for WW1's own sample player
`patches/fal_ym.s` (new, `; falcon: yes`, site `$1bcb8`, 8 B `movep.l d1,-$720f(a0) ; movep.w d0,...` -> `jsr $75bd0 ; nop`, blob = two `movep.w` through $ff8800/02 + swap d1 twice) and the Falcon class in `core.s` (`FALCON` byte `$727f4` set by `init` from `_MCH` high word 3; the hook applies class-4 sites only then; `wwpatch.py` header `; falcon: yes`, manifest `falcon`; `wwgate` expects the ORIGINAL bytes at a falcon site on other machines and has a `core: FALCON flag` line in `hw`). Builds assemble and `checkdisk` PASS (`build/g_ymfal` = no DMA, `build/g_snd2` = with snd): **NO Falcon run has been made** (queued script killed at the budget). Not done: (1) boot the committed default on the Falcon (record where it stops), (2) gate `g_ymfal` to the map with YM sound (cell + `wwsnd wav --machine falcon` vs STE YM wav `/tmp/pmww1s4c/e47_ym.wav`), (3) `g_snd2` Falcon, Falcon pointer cell (tt_ptr; the Falcon desktop mode may not be ST low: look at the first screenshot), (4) ST/STE/Mega STE regression of the new core (FALCON flag 0, fal_ym site original). README: mirror master (Falcon HD untestable in Hatari: `--acsi` ignored by TOS 4.04; GEMDOS folder only). Do not claim "WW1 only runs on a Falcon with DMA sound".

## 5. Not started
HD gates (`build/g_hd`: `wwpatch.py build --hd`, built, never booted), orphan end re-run with the list-only mode, a final cell of the full default set with the new core.
