# Stage 4d results (PMWW1Stage04d, 2026-11-24): Falcon, new-core regression, hover item path, interp 8 MHz, HD

Evidence contract: **[obs]** = raw lines from a file named here; **[INFERENCE]** = reasoning only; failures are listed as failures.
Hatari 2.6.1, private HOME per run, work dirs `/tmp/pmww1s4d/*`, one Hatari at a time. Logs `work/runs/s4d_*.txt`. Falcon cells: `--machine falcon --tos 4.04 --mem 4096 --extra "--borders false"` (screenshots 640 x 436, picture at 0,0).
Builds (`wwpatch.py build --floppy`): `s4d_old` = the COMMITTED tree (HEAD patches via `WW_PATCHDIR`, old core, snd_* on, no fal_ym / hover / interp); `s4d_new` = the working tree default set; `s4d_nosnd` = new default minus `snd_*`;
`s4d_nofalym` = `s4d_nosnd` minus `fal_ym`; `s4d_nocac` = `s4d_nosnd` with the `bsr.w cacroff` in core.s `init` replaced by two `nop` (scratch patch dir); `s4d_nointerp` = new default minus `p3b_*`.

## 1. Falcon
### 1a. committed default (old core, snd_* DMA) on the Falcon
`work/runs/s4d_fal_old.txt`: cold boot -> option screen (marker PMPO, every site PASS, payload unchanged) -> map view with the world counter ticking:
```
GATE fal_old/falcon-4.04-4096K boot PASS 51s
  [fal_old] [   73s vbl 6436] 3D map view, world counter ticking
GATE fal_old/falcon-4.04-4096K map view PASS counter 65, flag $15998 = $0000002c
GATE fal_old/falcon-4.04-4096K payload@map PASS unchanged
```
(the one FAIL line of that run, `credit visible`, was the gate's crop: it assumed an ST-family 832 x 588 screenshot; fixed in `wwgate.py`: 640-wide TT / Falcon shots use the picture at (0,0). The `fal_nofalym` run shows `credit visible PASS`.)
`s4d_fal_old_wav.txt` (effect 47 started as the game does, emulated sound on): `FLAGS $3, effect 47 sequence pointer $5e264` / `CPU exceptions in the Hatari log: 0 []` / `WAV ...e47_old.wav: 3.50 s at 50066 Hz, sound 0.82-1.25 s, rms 3247.3, peak 8192`.
**The committed default already boots to the map view on the Falcon and plays the DMA effect with no CPU exception** (the committed core has `cacroff`; snd_* replaces the game's sample player, so the YM movep site is never reached).

### 1b. new core.s + fal_ym WITHOUT DMA sound (`s4d_nosnd`) on the Falcon: YM audio, no bus error
`s4d_fal_nosnd.txt` (cell boot,map,hw,saveload) and `s4d_fal_nosnd_wav.txt`:
```
GATE fal_nosnd/falcon-4.04-4096K marker PASS $727f8 = b'PMPO' (want b'PMPO')
GATE fal_nosnd/falcon-4.04-4096K credit visible PASS rows 194-199: 7680 px of colours [(255, 255, 255)]
GATE fal_nosnd/falcon-4.04-4096K map view PASS counter 63, flag $15998 = $0000002c
GATE fal_nosnd/falcon-4.04-4096K tt_ptr: LIVE flag PASS $ff
GATE fal_nosnd/falcon-4.04-4096K core: FALCON flag ($727f4, _MCH cookie high word 3) PASS $ff on falcon
GATE fal_nosnd/falcon-4.04-4096K save/load: loaded state == saved state PASS 101376 B: 0 differ
GATE fal_nosnd/falcon-4.04-4096K payload@saveload PASS unchanged            CELL DONE fal_nosnd/falcon-4.04-4096K: OK (265s)
  FLAGS $0, effect 47 sequence pointer $5e264 / CPU exceptions in the Hatari log: 0 [] / WAV /tmp/pmww1s4d/e47_fal_nosnd.wav: 3.50 s at 50066 Hz, sound 0.88-1.32 s, rms 3324.8, peak 9207
```
Hatari log of the cell: 0 `Bus Error` lines (`grep -c`). The sample is the game's own YM player (FLAGS $0 = no DMA), written through `$ff8800/02` by `fal_ym`.
Sound check: Falcon YM (fal_ym) against the STE YM of the original player (`/tmp/pmww1s4c/e47_ym.wav`, `s4d_fal_cmp_all.txt`): `CMP rho = +0.8671 at lag +0.0 ms; durations 0.443 / 0.445 s` (STE DMA vs Falcon YM +0.8482). The sample content is the original's.
**Negative control, same set WITHOUT fal_ym (`s4d_nofalym`, `s4d_fal_nofalym.txt`):** the cell fails at the chart (`RuntimeError: island click never started the land generation`, `CELL FAILED`), the Hatari log (`/tmp/pmww1s4d/c_fal_nofalym/log.txt`) is full of
`WARN : Bus Error writing at address $ffff8804, PC=$1bcb8 addr_e3=1bcb8 op_e3=3c8` (10192 lines incl. the repeat counters, up to `16384 repeats of:`): the game's sample player `movep.l d1,-$720f(a0)` at `$1bcb8` bus-errors on the Falcon exactly as the master's stage-1 player did. fal_ym is needed whenever snd_* is not in the build.
(Its wav run never reached the map view and hung in the harness; killed by me, PIDs mine.)

### 1c. full default (new core + fal_ym + snd_*, `s4d_new`) on the Falcon: DMA to the map
`s4d_fal_new.txt`: `snd_core: FLAGS (DMA sound probe) PASS $3`, `snd_core: the DMA plays a chunk ... PASS bit seen True, SV busy ff, sequencer active 01, chunk busy ff`, `map view PASS counter 65`, save/load PASS (`101376 B: 0 differ`, `244 differ` world moved), `CELL DONE fal_new/falcon-4.04-4096K: OK (271s)`; wav: `FLAGS $3 / CPU exceptions in the Hatari log: 0 [] / WAV e47_fal_new.wav: 3.52 s, sound 0.90-1.33 s, rms 3264.8`; Hatari log 0 `Bus Error`.
**Observation (not a gate failure):** the Falcon's DMA output of effect 47 is the STE's waveform with inverted sign and a ~75 ms quiet lead-in: unaligned `CMP rho = -0.4474 / -0.3782`; aligned on the first 25 ms window above half of the maximum (`s4d_fal_dma_align.txt`): falcon DMA vs STE DMA rho -0.9505, falcon DMA vs falcon YM -0.8650, falcon YM vs STE DMA +0.8503. [INFERENCE] Hatari's Falcon crossbar DMA path; an inverted waveform is inaudible; real Falcon behaviour untested.
Sound output on the Falcon: both the YM path (1b) and the DMA path (1c) play effect 47 with the same duration (0.43-0.45 s) and spectrum; **no gate shows that DMA sound is required on the Falcon.**

### 1e. is `cacroff` needed? (`s4d_nocac` = the nosnd set with the `bsr.w cacroff` in `init` replaced by `nop nop`)
`s4d_fal_nocac.txt`: `RuntimeError: name prompt not reached` / `CELL FAILED fal_nocac/falcon-4.04-4096K`; log: `WARN : Bus Error writing at address $ffffffff, PC=$5d0` then `Bus Error reading at address $c945cb56, PC=$e0fbd2` (repeating). **Yes: without cacroff the game does not get to the name prompt on the Falcon** (stale 68030 instruction cache after the in-place depackers, as the master's section 9). Already in the committed core.

## 2. The NEW core.s regression: default set (`build/s4d_new`: all `; default: yes` patches incl. fal_ym, qol_hover(2), p3b_*, snd_*, tick_rain, tt_ptr) on ST 1 MB, STE 1 MB, Mega STE 4 MB
Cell per machine = `wwgate.py cell --fill-hi --trace --psg --steps boot,map,hw,rate,saveload,lose,win,round3` (boot, name prompt, option screen, markers / all site bytes, payload `$72000-$77fff` unchanged, high-area pattern `$b0000-$bbfff, $c1c00-$f6fff` [+ `$f7000-$fffff` at 4 MB] unchanged at every checkpoint,
cache cursor <= `$b0000`, noprot flow, map view, world rate, DMA / plain-ST sound, save / load, RETIRE lose (picture stays), START NEW + RETIRE win (picture stays), round 3, loader trace, strict-PSG gate), `wwkeys.py` (39 key/click pairs), `wwtt.py gate` (STE: full; ST, Mega STE: `--quick`), `wwend.py final --watch work/runs/end_watch_spans.txt` (the end-image watch list).
Logs `work/runs/s4d_{ste,st,mste}_{cell,keys,tt,end}.txt`.
| | STE TOS 1.62 1 MB | ST TOS 1.04 1 MB | Mega STE TOS 2.06 4 MB |
|---|---|---|---|
| cell | `CELL DONE ste/ste-1.62-1024K: OK (527s)` | `CELL DONE st/st-1.04-1024K: OK (594s)` | `CELL DONE mste/megaste-2.06-4096K: OK (504s)` |
| world rate | 3.933 / s PASS | 3.995 / s PASS | 3.970 / s PASS |
| sound | FLAGS $3, DMA plays a chunk; `PSGCHECK cell: PASS (violations 0, warnings 0; ... FDC commands 1083 ...)` | FLAGS $6 plain ST path; PSGCHECK PASS (violations 0, warnings 0, FDC commands 1081) | FLAGS $3; PSGCHECK PASS (violations 0, warnings 0, FDC commands 1091) |
| `$ff8e21` | `$ff` (STE: unmapped) | `$00` | `$03` (16 MHz + cache) |
| FALCON flag `$727f4` | `$00` PASS | (hw line is machine-gated) | (same) |
| keys | `KEYS 39 of 39 key/click pairs identical`, `CELL DONE ste_keys: OK` | same, `CELL DONE st_keys: OK` | same, `CELL DONE mste_keys: OK` |
| tooltips | `TOOLTIP GATE ste_tt: 584 lines PASS, 0 FAIL` (full) | `st_tt: 116 lines PASS, 0 FAIL` (quick) | `mste_tt: 116 lines PASS, 0 FAIL` (quick) |
| end image | `end_final ... no instruction was executed inside the watched spans ... PASS ... 2284 B differ in 30 span(s)`, `win picture shown and stable PASS`, `CELL DONE end_final: OK` | `... 13 colours, stable x3`, `CELL DONE end_final: OK` | `... 15 colours`, `CELL DONE end_final: OK` |
Each cell: `hi@...` PASS at every checkpoint (`0 of 267264 bytes changed`; 4 MB: more bytes), `lose picture PASS ... still there after 8 s PASS`, `win picture PASS ... still there after 8 s PASS`, `loader: every cacheable resource ... at most once PASS`, `cap normal: no skip (M3a) PASS`, `save/load: loaded state == saved state PASS 101376 B: 0 differ`, `save disk slot A == saved state PASS`.
(Grep `FAIL` over the 12 files: none. The first chain run was killed by me and restarted (my mistake with a background job); the files above are from the clean re-runs.)
**New core.s: PASS on ST, STE, Mega STE** (on top of the Falcon cells in section 1).

### 1d. Falcon pointer cell (tt_ptr)
Flip check (`wwptr.py cold --flips`, new: at every return of the flip routine `$e34` the pointer's saved-screen address `[$1d2ba]` against the buffer now displayed `[$2ed98]`, master's `ptr_buffer`), Falcon TOS 4.04, 6 s of map view [obs `s4d_fal_flips.txt`, `s4d_fal_flips_control.txt`]:
```
FLIPS fal_ttptr falcon: at 69 flip returns the pointer record [$1d2ba] lies inside the new displayed buffer [$2ed98] in 69 (video base register == [$2ed98] in 69)
FLIPS fal_nottptr falcon: at 70 flip returns the pointer record [$1d2ba] lies inside the new displayed buffer [$2ed98] in 0 (video base register == [$2ed98] in 70)    (control: new default minus tt_ptr, LIVE $00)
```
The Falcon's video follows the base register live (as the TT): with tt_ptr 69 of 69, without 0 of 70. The screenshot gate (`wwptr.py` spots) is NOT decisive on the WW1 Falcon: `PTR fal_ttptr falcon: visible in 29 of 60 screenshots (LIVE $ff)` vs control `39 of 60` (`s4d_fal_ptr*.txt`): the area compare is disturbed by the map's animation / rain, so I do not use it for the Falcon verdict (failure recorded plainly; TT gate needed ST low, 4b).
README: `## Machines` section added (Falcon works with and without DMA; HD on Falcon untestable in Hatari).

## 3. qol_hover / qol_hover2: extended item-path gate (`wwhover.py`, STE 1 MB, `s4d_hover_gate.txt`)
`wwhover.py` now prefers a drawn town whose settlement chain has a workshop house (kind byte 7). **No drawn town had one** (`houses drawn 1; of towns with a workshop: 0`), so the gate sets the kind byte of the settlement's chain head to 7 and prints it (`TEST SETUP: ... house $542fa ... set to 7 (was 11)`): the workshop is a test setup, not a natural one. [obs]
```
GATE hover hover_ws the hovered town has a workshop (house kind 7 in the chain) PASS 1 town(s)
GATE hover hover_ws a house under the resting pointer is picked (HIT) PASS HIT $542fa, RES 1, ARM 0, house $542fa at pointer (205,81)
GATE hover hover_ws text equals the settlement record (no item: workshop idle / none) PASS 'workshop idle', item word 0
GATE hover hover_ws BUF == reference rendering of SB (wwtt composer) PASS 0 of 624 bytes differ
GATE hover hover_ws pointer away: the hover text is gone from both buffers PASS HIT $0
GATE hover hover_ws item 0x6 in the making: the text follows the record PASS got 'Ranatey: making rifles (50%)', want making rifles ([50] %), record item 0x6 countdown 7 (T 14)
GATE hover hover_ws item 0x6: BUF == reference rendering of the text PASS 0 of 624 bytes differ
GATE hover hover_ws item 0xe in the making: the text follows the record PASS got 'Ranatey: making planes (24%)', want making planes ([24] %), record item 0xe countdown 779 (T 1038)
GATE hover hover_ws item 0xe: BUF == reference rendering of the text PASS 0 of 624 bytes differ
GATE hover hover_ws Build icon selected: the hover says what Build would make here PASS got 'Build here: planes (2 swords)' want 'Build here: planes (2 swords)' (posture word 3, workshop True)
CELL DONE hover hover_ws: OK
```
`making <item> (NN%)` is pixel-exact (0 of 624 bytes) for two item kinds (rifles, planes). The default-set regressions of section 2 (ST / STE / Mega STE, keys, tooltips) ran with qol_hover(2) loaded and passed.

## 4. p3b_interp / p3b_delta at 8 MHz: the T1 != T0 difference is the game's world step (legitimate), not a restore bug
The gate now saves the world clock (`$2ed90`, +1 per world step) with each people-table snapshot (`it_*.bin`, written just before the table). 8 MHz, patched (`s4d_interp_gate8b.txt`) and the control without any p3b_* (`s4d_interp_gate8b_control.txt`), same scene:
```
patched : passes where the world clock ITER advanced between T0 and T1: 45 of 115; table changed: 45; both: 45; byte columns that changed: ['0x0','0x1','0x2','0x3','0x8','0x9','0xa','0xb','0xc','0xd','0xe','0x11','0x13','0x14','0x15','0x16','0x17','0x1e','0x1f','0x29']
control : passes where the world clock ITER advanced between T0 and T1: 45 of 116; table changed: 45; both: 45; byte columns that changed: [the same 20 columns]
```
The table changes in exactly the passes that contain the world step (45 of 45 both ways), with the same columns in the UNPATCHED game; at 8 MHz T0 == TMID (no offset applied). At 16 MHz no pass contains a world step (0 of 250) and 250 of 250 are restored. Gate corrected: T1 == T0 is required in the passes where the clock did not advance, plus the two cross checks. Final runs (`s4d_interp_gate8c.txt`, `s4d_interp_gate16c.txt`):
```
GATE interp interp8 8 MHz people table restored after the render in every pass without a world step (T1 == T0, clock not advanced) PASS 72 of 72 (passes with a world step: 44)
GATE interp interp8 8 MHz every pass whose people table changed during the call is a pass in which the world clock advanced ... PASS 44 of 44 ...
GATE interp interp8 8 MHz every pass in which the clock advanced changed the table PASS 44 of 44        CELL DONE interp interp8 8 MHz: OK
GATE interp interp16 16 MHz people table restored ... PASS 250 of 250 (passes with a world step: 0)         CELL DONE interp interp16 16 MHz: OK
GATE interp interp16 16 MHz passes with offsets applied (T0 != TMID) PASS 250 of 250   (from 16b: offsets touch only the low bytes of x / z PASS 0 records with other bytes changed; 118 distinct drawn x low bytes)
```
Default-set regressions (section 2, with p3b_* loaded) passed on ST / STE / Mega STE.

## 5. HD build (`build/s4d_hd`: `wwpatch.py build --hd --floppy`, hd_* + default set; AUTO\WW1.PRG 86259 B, SAVEDISK.DAT)
Cell = `wwgate.py cell --hd build/s4d_hd/hd [--acsi] --fill-hi --trace --steps boot,map,hw,saveload,lose,win,round3`, cold boot -> name prompt -> map -> save/load (SAVEDISK.DAT via hd_sector) -> RETIRE lose -> win -> round 3. `work/runs/s4d_hd_*.txt`:
```
CELL DONE ste_gemdos/ste-1.62-1024K-hd: OK (443s)          (Hatari GEMDOS folder)
CELL DONE ste_acsi/ste-1.62-1024K-hd-acsi: OK (448s)       (real ACSI image + HDDRIVER, TOS's own GEMDOS)
CELL DONE mste_gemdos/megaste-2.06-4096K-hd: OK (429s)
CELL DONE mste_acsi/megaste-2.06-4096K-hd-acsi: OK (507s)
```
each with `save/load: loaded state == saved state PASS 101376 B: 0 differ`, lose / win pictures stable and still there after 8 s, `hi@...` PASS (STE: `0 of 148480 bytes changed in $b0000-$bbfff, $c1c00-$c1fff, $df000-$f6fff`), loader checks. (`grep FAIL` on the four files: see the run files; the CELL lines are OK.)
**Falcon HD via the GEMDOS folder: NOT passing** [obs `s4d_hd_fal_gemdos.txt`]: boot, map view, `snd_core` DMA PASS, then `RuntimeError: the load never returned` in `saveload_hd` / `CELL FAILED fal_gemdos/falcon-4.04-4096K-hd`. Not investigated (Falcon HD through a real disk is untestable in Hatari, `--acsi` ignored by TOS 4.04; whether this is the harness's Falcon click geometry or the game's load is unknown [INFERENCE: harness]).

## 6. TT / Falcon video mode (lead's request after a user report: TT shows the 2 x 2 tiled picture from the TOS 3.06 desktop)
core.s `init` now calls `ttlow` (TT: `clr.b $ffff8262.w` = ST low, `_MCH` high word 2) and, in `falcon` (Falcon only), `Vsetmode(-1)` then `Vsetmode((old & $30) | $82)` (keep VGA / PAL bits; ST compatible, 4 planes, 40 columns). Build `build/s4d_tt2` (default set); `s4d_tt` = TT part only.
* Before (build `s4d_tt` on the Falcon with `--monitor vga`, `work/shots/stage02/fal_vga_falcon_map.png` of the first run): the map view is noise (tiled / garbled picture) although the old cell said `map view PASS` / `CELL DONE ... OK`: **the cells do not judge the picture; the screenshots do.**
* TT 4 MB TOS 3.06 `--mmu true --cpuclock 32 --monitor vga`, default TT-medium desktop (`s4d2_tt_cell.txt`): `CELL DONE tt_low/tt-3.06-4096K: OK (130s)` (boot, credit, map, hw: `tt_ptr: LIVE flag PASS $ff`, DMA plays); screenshots `tt_low_tt_options.png` / `tt_low_tt_map.png`: correct picture, credit line, pointer, status panel (read by me). Pointer (`s4d_tt_ptr.txt`): `FLIPS tt_low tt: at 120 flip returns ... inside the new displayed buffer in 120`, `PTR tt_low tt TOS 3.06: visible in 24 of 24 screenshots`.
* TT tooltips pixel-exact (`wwtt.py` now handles 640-wide TT / Falcon shots and has `--extra`; `s4d2_tt_tt.txt`): `TOOLTIP GATE tt_low_tt: 116 lines PASS, 0 FAIL`, `CELL DONE tt_low_tt: OK`.
* Falcon VGA (`--monitor vga`) and RGB (`s4d2_fal_vga.txt`, `s4d2_fal_rgb.txt`): both `CELL DONE ...: OK (137s)`; map screenshots after the fix are pixel-identical between RGB and VGA (0 of 256000 px differ over the 640 x 400 picture area; `fal_vga_falcon_map.png` read by me: correct picture) and match the TT picture except 328 px (animation / pointer).
* ST / STE / Mega STE unaffected: quick cells on `s4d_tt2` below (s4d2_q_*.txt).
* ST / STE / Mega STE unaffected (quick cells on s4d_tt2: boot,map,hw,saveload,lose): CELL DONE q_st/st-1.04-1024K: OK (397s), q_ste/ste-1.62-1024K: OK (328s), q_mste/megaste-2.06-4096K: OK (312s) (s4d2_q_*.txt; FALCON flag $00 on each, save/load 0 differ, lose picture stable).
* **User confirmation (2026-11-24):** after `489b187` the user ran WW1 on a TT and reported "works great on a TT" (the user's own run; the report doesn't say whether it was Hatari or real hardware).

## 7. Falcon HD hang: OPEN (PMWW1FalconHD, 2026-11-24; stopped by the lead at the stall limit, cause not found)
Build: `wwpatch.py build --hd --floppy` of the committed tree (`f78bebf`), WW1.PRG byte-identical to `build/s4d_hd2` (`cmp`: same, 86331 B). Cell: `wwgate.py cell --hd .../hd --manifest .../manifest.json --machine falcon --tos 4.04 --mem 4096 --extra "--borders false" --fill-hi --trace --steps boot,map,hw,saveload,lose,win,round3` (NB: without `--manifest` the `--fill-hi` pattern spans cover the HD variables `$c2000`: first two runs died in `hd_core` `.cb` copy loop, `Bus Error writing at address $400000, PC=$7775a`; my mistake, not a finding). Logs `work/runs/s4d_fhd_cell1.txt`, `s4d_fhd_cell2.txt`; debug scripts / logs `work/runs/s4d_fhd_dbg/`.
**Result (2 runs, identical): Falcon HD GEMDOS cell FAILS ("back to option screen"; the load itself works in these runs), and the failure is lost clicks in the game, not a GEMDOS error.**
```
fhd1/2: GATE ... save/load: loaded state == saved state PASS 101376 B: 0 differ
        GATE ... save/load: save disk slot A == saved state PASS sectors 1-198 equal: True, slot flag $ff, image 409600 B
        GATE ... lose picture PASS non-black 0.63, 19 colours, seen stable x3
        GATE ... back to option screen FAIL
        ... map view (2nd land) PASS / win picture PASS / back to option screen (after win) PASS ... CELL DONE fhd1/falcon-4.04-4096K-hd: FAIL (462s)   (fhd2 the same, 462s)
```
* **The "lose picture PASS" is false** (the cells do not judge pictures): I read `work/shots/stage02/fhd1_falcon_lose.png` / `fhd2_falcon_lose.png`: they show the 3D map view (officer, table, water), NOT the lose picture (the explosion picture of `fal_flop_full_falcon_lose.png`). The Retire never happened: the Option / Game / Retire clicks after the load were ignored. `win` / `round3` shots (`fhd1_falcon_win.png` "WELL DONE YOU HAVE WON THE BATTLE", `after_win_start.png` confirm dialog, `map.png`, `options.png`) are correct pictures.
* The "load never returned" of the old runs reproduces without the trace breakpoints (`dbg.py`, 3 of 4 runs; 1 run passed all: save/load, retire picture). Cause of that error: the harness's one-shot breakpoint at `$1cb2a` is never reached because **the LOAD click does nothing**: Hatari log of a failing run (`w_m1`, breakpoints on `hd_sector` `$7740c`): 3 `hd_sector` calls (the save: sector 0 read `D1 00020000 D2 1 D3 0`, write `D2 $c6 D3 $8001`, write sector 0 `D3 1`), then NO further call; the game keeps ticking (`ticking True WINDOW_OPEN 0x0`), `HDSW` ready, `SAVEDISK.DAT` flag byte `$ff` == RAM `$1c964` (`disk flag@104 255 ... sector0 on disk == RAM block: True ram flag 255`), RLEN `$fc64`. In passing runs the load does call `hd_sector` (`D1 1 D2 $c6 D3 $8000`, d0 = 0 at the return `$1cb2a`, `s4d_fhd_dbg/n1_hatari_log.txt`). **So the failing click never enters the game's load routine; no GEMDOS call fails (the clicks are lost AFTER earlier `hd_*` calls; see the control below).**
* Button packets of a run where the load worked but the NEXT clicks were lost (`dbg9.py`, bp `$ef4` with `($1d2af).b > 0`, `n1_hatari_log.txt`): press `04` / release `08` with the pointer at the right place for every click, e.g.
```
vbl 8505 btn 04 pos 43,15 window 017c  -> vbl 8521 btn 08 pos 43,15 window 0000     (LOAD: worked)
vbl 9974 btn 04 pos 69,137 window 0000 -> vbl 9984 btn 08 pos 69,137 window 0000    (OPTION after the load: window stays 0; GAME 47,26 and RETIRE 25,50 clicks likewise nothing)
```
  the same OPTION click at the same coordinates opened the window 3 times before the save (`vbl 5138..5148`, `7478..7487`: `window 017c`). So the IKBD packets reach the game; the game does not act. The same flow with every click held 0.6 s (`dbg12`) passed (save/load, option, game, retire: picture, `ticking=False`); `dbg11` (clicks held 0.2 s but different timing) also passed. It is therefore a timing / race: deterministic for identical emulated timing (n1, n2 failed identically), different with other timing. A controlled test (`dbg16.py`, OPTION click held 0.1 / 0.2 / 0.3 / 0.8 s, 4x each, before and after the load) showed clicks mostly working at every hold; one miss: `after load ... hold 0.1: ['MISS', 'open', ...]` (first click after the load). My close-the-window step was wrong (OPTION toggles; the `STUCK-OPEN` entries are my bug), so that table is weak.
* Falcon timing (tick_head data `$72a80`, 8 s on the map): `falcon VBL 465 {'ticks': 37, 'rpass': 70, 'spass': 0, 'pas': 107} VBL/pass = 4.35` vs `ste VBL 465 {'ticks': 37, 'rpass': 8, 'spass': 0, 'pas': 45} VBL/pass = 10.33` (`$2ed90` is the 4 Hz world clock, not the pass counter). After the load on the Falcon: 3.42 VBL/pass. Clicks are dated by PASS (tick_click*: lifetime one pass), so a Falcon pass is 2.4x shorter than an STE pass.
* Falcon-only oddity seen on the way (floppy and HD alike; not examined further): opening the FILE window turns the 3D view from land into water (`/tmp` shots `e_file.png` vs `e_opt.png`; Falcon floppy `dbg3.py floppy falcon` and Falcon HD both; STE HD keeps the land). No stuck keys (`$2ec8c` table empty at every step). Not explained; the saved / loaded state compares equal.
* **Ruled out:** GEMDOS / Hatari's GEMDOS on a Falcon (no call made when the click is lost; calls that are made return 0); `hd_core` swap / R region (RLEN `$fc64`, state equal, `0 differ`, `hi@...` all PASS); a stale slot flag (`$ff` in RAM and on disk); phantom / stuck keys; the hang itself (every run got through save, load, win, round 3). Not done: master's Powermonger HD on the Falcon (`tools/play.sh --hd --machine falcon`) for the comparison; a patch bisect (`WW_PATCHDIR` copies of the committed patches in `/tmp/pmww1fhd/pd_*`, `b_notick`, `b_nottptr`, `b_noqol`, `b_nop3b` built, never run).
* **Retraction:** `s4d_fhd_hdfloppy1.txt` (a Falcon "floppy" cell that failed 2/2 at "save-disk requester not shown") used the floppy.st of the `--hd --floppy` build, i.e. the HD patches on a floppy: it is NOT evidence about the plain floppy build, and my earlier line "floppy too" is withdrawn.
* **Control (proper floppy, same Falcon options, same `--fill-hi --trace`, committed patches built with `WW_PATCHDIR` = `git archive HEAD patches`, no hd_*; `work/runs/s4d_fhd_floppy_control1.txt`, steps boot,map,saveload,lose): PASSES**
```
GATE fbase1/falcon-4.04-4096K-... save/load: loaded state == saved state PASS 101376 B: 0 differ
GATE fbase1/falcon-4.04-4096K lose picture PASS non-black 0.52, 19 colours, seen stable x3; cache cursor $9fc58 -> $a7958
GATE fbase1/falcon-4.04-4096K back to option screen PASS
CELL DONE fbase1/falcon-4.04-4096K: OK (319s)
```
  Second control run `s4d_fhd_floppy_control2.txt`: `CELL DONE fbase2/falcon-4.04-4096K: OK (318s)`. Differences between that and `s4d_fal_flop_full.txt` (also OK): the earlier control ran without `--fill-hi` / `--trace` (no `hi@` / `LOADER` lines) and more steps; mine passes with both, so they are not the cause. Same harness (`wwgate.py cell`, `pmww.PMW`), tos 4.04, mem 4096, `--borders false`, click timing (`click_st`, hold 0.2). The only difference between the passing floppy cell and the failing HD cell is the HD build + `PMWHD` (GEMDOS folder as C:). **So the lost clicks are specific to the HD build on the Falcon (STE / Mega STE HD, GEMDOS and ACSI, pass: section 5).**
* [INFERENCE] best explanation (revised): the game ignores clicks after the HD build's GEMDOS excursions (`tos_in` / `tos_out`: the VBL is masked and `_hz_200` / timer C reprogrammed while a call runs, the keyboard bytes are queued and replayed through `$e7c`), on the Falcon only because its passes are short (3.4 to 4.4 VBL vs 10 on the STE) and a click lives one PASS (tick_click*, `$2ed94` stamp cleared at `$144b2`). A state the excursion leaves behind (click flags `$2edb6` / `$2edb8` / `$2edbc` / `$2edbe`, the IKBD packet state `$1d2ae`, the latched stamp, or the tick_head ACC / LAST after a long gap: tick_head resyncs only after more than 4 ticks) would explain "first click after a save / load is lost" and "LOAD click lost right after the save's three calls". Not tested. Next steps: (1) dump `$2edb6 $2edb8 $2edbc $2edbe $2ed94 $1d2ae` and tick_head D `$72a80..` right after a save and after a load in a failing run vs a passing one; (2) HD build without tick_click* / tick_head (`b_notick` style, with hd_*); (3) master's Powermonger HD on a Falcon (`tools/play.sh --hd --machine falcon`) as the comparison asked for.
* Harness suggestions: `lose` / `win` must check the picture (RAM / screenshot) and not just `non-black 0.6`; clicks that must change the window state should be verified and repeated.
