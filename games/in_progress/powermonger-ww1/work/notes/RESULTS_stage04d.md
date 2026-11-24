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
