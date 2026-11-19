# Powermonger VBL pointer bus error (PMBusErr): IKBD ACIA overrun caused by `p6_cpy`'s blitter chunks

Tags: **[obs]** observed in Hatari 2.6.1 (raw output reproducible with the command given); **[disasm]** read from `work/dumps/get_men.bin` with `tools/m68dis.py`; **[INFERENCE]** not run.
Tool: `tools/pmbuserr.py` (`repro`, `stress`; test patches `test_cpyx`, `test_cpyold`, `test_ovr`; `tools/pmbuserr_rows.py` = histogram of the sprite row counts). Everything: 1 MB STE, TOS 1.62, 8 MHz unless a row says otherwise. Raw output kept in `work/buserr/` (`repro_crash_state.txt`, `trace_acia_blitter_excerpt.txt`, `latency_summary.txt` + `lat.py`, `gate_*.txt`, `stress_st*.log`); every number below is the output of the command shown.

## 0. Result

* **Root cause [obs]: the hypothesis was right.** `p6_cpy` copied the window picture with the STE blitter in HOG mode in 10-row chunks (6 400 cycles each). In Hatari an interrupt raised during a chunk is taken after up to TWO chunks, not at the first gap, so the keyboard ACIA interrupt waited up to 21 HBL = 10 750 cycles, longer than one IKBD byte (20 HBL = 10 240 cycles at 7812.5 baud). The ACIA holds one received byte: the next byte overwrote it (**OVRN**), the 6-byte mouse reply lost a byte, and the game's packet parser built a garbage position (`x = $0000, y = $adfd`). The VBL pointer draw (`$13c4`..`$147c`) adds `y * 160` to the buffer address: `move.w (a4),(a6)+` at `$147c` -> **Bus Error reading at address $6f0220** (A4 = `$006f0220`).
* **Not a snapshot artefact [obs].** A COLD BOOT of the floppy build with the 10-row chunks and the original sound path (no `snd_*` patches, as in the snapshots) takes the same bus error at `$147e` while the game enters the 3D view (`Bus Error reading at address $a06e00 / $a06e08, PC=$147e`, two runs). The default set WITH the `snd_*` patches (the shipped v1.0) did not crash in 6-minute cold-boot stress runs (0 overruns in 215 000 bytes): the DMA-sound patches change the VBL handler's timing and with it the phase between the ACIA bytes and the chunk boundaries. So v1.0 was exposed to a timing coincidence; real hardware has other timings [INFERENCE].
* **Fix (two parts, both default):**
  1. `p6_cpy`: **50 chunks of 4 rows (2 560 cycles of blitter, 2 660 per chunk with the setup)** instead of 20 of 10. Peak ACIA interrupt latency after the fix 11-12 HBL of 20 (8 MHz), 0 overruns in every run.
  2. new `p4_clamp` (site `$1942`, 10 bytes, code `$BD400`, 52 B): a packet whose position is out of range (x > 319 or y > 199: the range the game sets with `$09 $013f $00c7`) is dropped (the last committed position is kept). Safety net for anything that still loses an IKBD byte (a longer IRQ-off section on a real machine, other patches); inert in normal use (0 hits in the 800-VBL run of the shipped set; pmab IDENTICAL).
* **Gates (all section 5):** pmab IDENTICAL x6 for the new `p6_cpy` and x6 for `p4_clamp`; fps effect of the 4-row chunks: -2.0 to -4.4 % of the pass at 8 MHz (old 10 rows: -2.7 to -4.3 %); cold-boot stress runs: shipped set 0 overruns / 0 bus errors, old chunks without clamp crash, old chunks with the clamp survive 4 165 overruns.

## 1. Reproduction [obs]

`python3 tools/pmbuserr.py repro get_men` (live set `tick_* p4_ptr_a p4_ptr_b p4_spr p6_cpy` with the OLD 10-row chunks, applied at the first flip after VBL 12 500, no `test_walk*`): 32 VBL later

```
WARN : Bus Error reading at address $6f0220, PC=$147e addr_e3=147e op_e3=3cd4
  A4 006F0220   A5 FFFFFFFF   A6 0001C49E   D5 00310000   D6 00000090   D7 0000000F        (0000147c: move.w (a4),(a6)+)
> m $2df78 24                      $2df78 = 00024400 (L), $2df7c = 0001c700 (D): both fine
> m $1c48e 8                       00 00 02 00 00 00 ad fd          $1c48e = 0 (parser state), $1c490 = 02 (a phantom key), $1c492.w = 0000 (x), $1c494.w = adfd (y)
```
`a4 = L + y * 160 + (x / 16) * 8`: `$24400 + 44 541 * 160 = $6f0220` exactly (x = 0): the pointer address is garbage because the position word is.

## 2. How the position gets garbage [obs + disasm]

* The game talks to the IKBD in **absolute mouse mode, polled every VBL** [disasm]: start-up sends `$15` (joystick interrogation mode), `$09 $013f $00c7` (absolute, max 319 x 199), `$0C 1 1` (`$1b1e/$1b24`); the VBL handler writes `$0D` (read absolute position) at `$1380` and `$16` (joystick interrogate) at `$14cc`. The reply is **9 bytes back to back per VBL, one every 20 HBL (10 240 cycles)**: `f7 btn xh xl yh yl | fd j0 j1`. `--trace acia`, VBL 12 509:
  `read rdr data=0xf7 (HBL 59) 0x00 (93) 0x00 (113) 0xe5 (133) 0x00 (153) 0xad (173) 0xfd (193) 0x00 (213) 0x02 (233)`, i.e. mouse (229, 173) = `$00e5, $00ad`, button 0, joystick `fd 00 02`.
* The ACIA handler `$18be` reads status (`$18c6`), `bsr $18e4` reads the byte and runs the state machine [disasm]: state `$1c48e` = 0: byte < `$f6` = scancode (`$1992`: key table `$2de6c + code`, `st`/`sf`), `$f7` = state 5, other `$f6+` (the `$fd` joystick header) = state `$fe`; state > 0 stores the byte at `$1c491 + (5 - state)` and at 0 copies `$1c491 -> $1c48f` (buttons, an index into the 16-entry jump table at `$12ac`) and `$1c492 -> $2df92`, `$1c494 -> $2df94` (`$1942-$1960`).
* The first overrun of the repro [obs, `--trace acia`]: the CPU had not yet read byte `0x00` (the x high byte, IRQ at HBL 113) when the next byte `0xe5` finished: `acia ikbd clock_rx overrun rsr=0xe5 unread rdr=0x00  VBL=12511 HBL=133` (the 6850 keeps the old byte and drops the new one) then `read rdr data=0x00 new sr=0x22 overrun=yes  HBL=137` (the read at 137 returns the x high byte, `e5` is gone). The stream the parser saw: `f7 00 00 [e5 lost] 00 ad | fd 00 02` -> button 0, x = `$00` `$00`, y = `$ad` `$fd` (the joystick header `fd` eaten as the last position byte), then `00` and `02` as key codes (`$1c490 = 02`). `test_ovr` (a counter in the ACIA handler, status read after the data read, which is where the 6850 flags OVRN) agreed with the trace: 5 overruns at the first crash.
* **Resync [disasm + obs]:** the parser has no timeout, it resynchronises at the next byte >= `$f6` seen in state 0, i.e. the next VBL's `f7`. A bad packet therefore corrupts one VBL: the position (garbage, fatal in the pointer draw), phantom key codes (a make code without a break code leaves a key flag set in `$2de6c+code` until its break arrives [disasm]; not examined further), and for a lost `fd` packet byte the following `f7` is eaten as data. With `p4_clamp` the old-chunk build ran 800 VBL with 83 overruns and 32 dropped positions (first: `$1c492 = 0000, $1c494 = adfd`, `$2df92/94` kept) without a bus error; the cold boot with the clamp and old chunks ran 5 minutes through get_men with **4 165 overruns, 0 bus errors** (section 4).

## 3. Why the chunk is the cause [obs]

### 3.1 Controls (`pmbuserr.py repro get_men --set <names> --trace acia`, 150-300 VBL after the apply; latency = IRQ raised -> RDR read, in HBL, from the trace; 20 HBL = one byte)

| live set | overruns | max latency |
|---|---|---|
| `tick_*` only | 0 | 1 HBL |
| `+ p6_cpy` (no `p4_spr`: the blitter probe is never taken, the CPU copy runs) | 0 | 1 HBL |
| `+ p4_spr` (blitter sprites, ~900-1 150 cycles per pass) | 0 | 3 HBL |
| `+ p6_cpy + p4_spr` (10-row blitter chunks) | 9 in 150 VBL | 22 HBL |

(That `p6_cpy` alone is harmless is exactly what the first look at the problem saw; it only uses the blitter when `p4_spr`'s probe chose it, `$bdc04 = $b17e0001`.)

### 3.2 The two-chunk latency (trace blitter + acia, `--vbls 25`, VBL 12 511; cycle = position in the frame)

```
blitter ctrl=c0 start  29324        (chunk of 6 400)   IRQ raised ~30208 (HBL 59)   -> RDR read 36172  (taken at the chunk end: +350 for the exception + handler prologue)
blitter start          36628, 43128, 49628                IRQ ~47616 (HBL 93)           -> RDR read 56476  (NOT taken in the 100-cycle gap before the chunk at 49628)
blitter start          56880, 63380, 70640                IRQ ~57856 (HBL 113)          -> RDR read 70228  (NOT taken in the gap before 63380)
                                                          acia ikbd clock_rx overrun rsr=0xe5 unread rdr=0x00  HBL=133, read at 137
```
A chunk start is 6 500 cycles after the previous one (6 400 + ~100 setup); an interrupt raised inside a chunk was served right after it in some cases and only after the next one in others. [INFERENCE: Hatari's blitter runs the whole HOG chunk inside the instruction that starts it and handles the CPU / MFP interrupt timing afterwards; I did not find which sub-phase decides.] **Worst case in Hatari = two chunks + ~700 cycles.** Real hardware: [INFERENCE] one chunk is the architectural bound (the 68000 samples the interrupt at the end of the instruction that started the blit, and the blitter then hogs the bus), but the gap between chunks is only the 5-6 setup instructions, so 6 400-cycle chunks leave 6 400 + 700 against 10 240, and a Mega STE (blitter at 8 MHz while the CPU runs 16: 0.8 ms per 10-row chunk of real time against a 1.28 ms byte) is much worse than 8 MHz STE. The change below is the right fix for both.

### 3.3 Chunk size sweep (`test_cpyx`, rows poked at the apply flip, `p4_ptr_a/b + p4_spr + tick_*`, 600 VBL; reads = bytes read in the trace window incl. the start-up part)

```
get_men     rows 10 : bus errors, overruns (see 3.1)
get_men     rows  8 : bus errors 28, overruns 7,  max latency 21 HBL
get_men     rows  5 : bus errors 0,  overruns 0,  max latency 14 HBL
get_men     rows  4 : bus errors 0,  overruns 0,  max latency 11 HBL
get_men     rows  2 : max latency 4 HBL            (map-view run, 300 VBL)
battle_320  rows  8 : bus errors 25, overruns 7,  max latency 21 HBL
battle_320  rows  5 : 0 / 0 / 13 HBL
battle_320  rows  4 : 0 / 0 / 11 HBL
```
Two chunks of 4 rows = 5 320 cycles + ~450 = 11 HBL, as measured. 4 rows keeps a ratio of 55-60 % of the byte time. Cost: 50 chunks x 2 660 = 133 k cycles for the copy instead of 130 k (10 rows) or 163 k (CPU).

## 4. Cold boot, the real-user test (`pmbuserr.py stress`: `build --floppy` of the default set + `test_ovr`, cold boot to the map view, `get_men`, then 2-3 `xdotool` threads: random relative mouse moves (+-60 x, +-40 y per step, the pointer is re-centred every 40 steps) and, at 2-5 % of the steps, Shift / Ctrl / cursor keys, for the wall-clock time shown; `OVC` = `test_ovr` counter; absolute IKBD mode means the reply length does not depend on how fast the mouse moves: 9 bytes per VBL whatever the motion)

| run | patch set | result |
|---|---|---|
| st1 | shipped defaults (4-row `p6_cpy`, `p4_clamp`, `snd_*`), mouse still | 6 min, get_men + battle: **0 overruns / 215 080 bytes**, 0 bus errors |
| st2 | old 10-row chunks, `snd_*`, no clamp, mouse still | 6 min: 0 overruns / 214 820 bytes, 0 bus errors (the exposure is phase-dependent) |
| st4 | old 10-row chunks, `snd_*`, no clamp, moving mouse | 6 min: 0 overruns / 214 582 bytes, 0 bus errors, pointer wandering over the full 0..319 x 0..199 range |
| st5, st3 | old chunks, **no `snd_*`**, no clamp | **Bus Error reading at address $a06e08 (st5) / $a06e00, PC=$147e** right after the harness's "protection removed" line, i.e. while the game entered the 3D view (the harness: "no screenshot", game dead) |
| st7 | old chunks, no `snd_*`, **with `p4_clamp`** | 5 min, get_men: **4 165 overruns / 181 561 bytes, 0 bus errors**, game iterating (`iter` 214 -> 1 367), pointer sane |
| st6 | 4-row chunks, no `snd_*`, clamp, moving mouse | 6 min: **0 overruns / 214 948 bytes**, 0 bus errors |
| st8 | shipped defaults, 3 threads, 5 % keys | 267 s: 0 overruns / 165 712 bytes, 0 bus errors (then a harness read error, not a game failure) |
| st9 | shipped defaults, 2 threads, 3 % keys, 8 MHz | 6 min: **0 overruns / 219 756 bytes**, 0 bus errors, pointer over the full range, get_men + battle (`iter` 218 -> 1 601) |
| st10 | same, `set_cpuclock(16)` after the boot | 6 min: **0 overruns / 220 231 bytes**, 0 bus errors (`iter` is the world tick counter, 4 / s at either clock, so it does not show the clock change; the bytes are 9 per VBL: 24.5 k VBL in 6 + 2.4 min, real time) |

## 5. Gates

### 5.1 `p6_cpy`, 4-row chunks, against the same set without it (`python3 tools/pmab.py --base p4_ptr_a p4_ptr_b p4_spr p6_slope p6_tri pm_tooltip --only p6_cpy --snapshot map_idle get_men battle_320 --mhz 8 16 --vbls 700 --walk`; both runs carry `tick_*` and `test_walk*`)

```
map_idle   @8  MHz: IDENTICAL (back 33, shown+pointer 20) | work/pass 2474065 -> 2362750 (-4.50 %) | paired -4.40 % | fps 3.101 -> 3.238 (+4.4 %)
map_idle   @16 MHz: IDENTICAL (back 108, shown+pointer 103) | 1858700 -> 1804426 (-2.92 %) | paired -2.87 % | fps 8.043 -> 8.212 (+2.1 %)
get_men    @8  MHz: IDENTICAL (back 60, shown+pointer 41) | 1487635 -> 1453090 (-2.32 %) | paired -2.55 % | fps 5.126 -> 5.201 (+1.4 %)
get_men    @16 MHz: IDENTICAL (back 130, shown+pointer 129) | 1385377 -> 1351057 (-2.48 %) | paired -2.39 % | fps 10.116 -> 10.450 (+3.3 %)
battle_320 @8  MHz: IDENTICAL (back 59, shown+pointer 33) | 1474460 -> 1440009 (-2.34 %) | paired -2.02 % | fps 5.213 -> 5.279 (+1.3 %)
battle_320 @16 MHz: IDENTICAL (back 152, shown+pointer 151) | 1299771 -> 1268406 (-2.41 %) | paired -2.32 % | fps 11.354 -> 11.572 (+1.9 %)
ALL IDENTICAL
```
For comparison the OLD 10-row version (`--only test_cpyold`, same command): paired -4.33 / -3.54 / -3.27 / -2.67 / -3.56 / -2.70 %, fps +5.0 / +2.2 / +3.1 / +4.3 / +1.9 / +2.6 % (ALL IDENTICAL). So the safe chunking gives up 0.1-1.5 % of a pass at 8 MHz (0.3-0.7 % at 16 MHz), about a third of the original window-copy gain; the fps columns are +-1 flip per 700 VBL (1.4 %) and should be read through the cycles. The expected cost from the arithmetic alone is ~3 k cycles (30 more chunk set-ups of ~100); the 8 MHz excess of the old version [obs, not explained] is part of the gap.

### 5.2 `p4_clamp` on top of the defaults (`--base p4_ptr_a p4_ptr_b p4_spr p6_slope p6_tri pm_tooltip p6_cpy --only p4_clamp`, same snapshots / MHz / `--walk`)

```
ALL IDENTICAL (6 of 6); work/pass +0.04 .. +0.23 % (the 52 B routine runs once per IKBD packet: +460 .. +3 300 cycles in the mean of a pass, 1 packet per VBL)
```
(`test_walk2/3` replace the two position copies behind the hook, so pmab cannot exercise the drop path; section 2 does.) Normal use never takes the drop path: breakpoint at `.bad` (`$bd41e`), shipped set (new chunks), get_men, 800 VBL: **0 hits**, 0 overruns, 7 117 bytes.

### 5.3 Latency of the shipped set (`repro --trace acia --vbls 800`, no `test_walk`)

```
get_men    @8  MHz: 0 overruns, 0 bus errors, max latency 12 HBL        get_men    @16 MHz: 0 / 0 / 6 HBL
battle_320 @8  MHz: 0 / 0 / 11 HBL                                      battle_320 @16 MHz: 0 / 0 / 3 HBL
map_idle   @8  MHz: 0 / 0 / 12 HBL                                      map_idle   @16 MHz: 0 / 0 / 5 HBL
```

## 6. Other bus holders [obs + disasm]

* The only code that starts the blitter is `p6_cpy` and `p4_spr` (`grep 8a3c patches/*.s`; `test_copy` is test-only). `p4_spr`'s sprite blits are 8 HOG passes of `rows x 3 words x 12 cycles` = 864 cycles at 24 rows (the `$124a8` variant; get_men: 34 of 37 calls 24 rows, max 24; the `p4_spr` cache path allows <= 32 rows = 1 152 cycles) with the CPU in between: two passes = 2.3 k cycles = 4.5 HBL worst case, far below a byte time. `p4_spr` alone: max latency 3 HBL.
* `$124a8`'s blitter path has no row limit; a call with more than ~60 rows (>= 2 160 cycles a pass, two passes 4.3 k + chunk effects) would need splitting [INFERENCE: no caller gets there, the sprite sheets are 16/24/32 rows].
* VBL handler: runs at IPL 4, the ACIA (MFP, IPL 6) preempts it; the pointer restore + redraw in the original is 11.7 k cycles but never delayed the ACIA.

## 7. Limits

* Real hardware not run. The 2-chunk behaviour and the exact byte-time margin are Hatari's; the conclusions that hold on a real STE / Mega STE are the byte-time arithmetic and the safe margin of 4-row chunks (0.32 ms of bus per chunk against a 1.28 ms byte).
* Phantom keys after a desync (make code without break) are not guarded by `p4_clamp`; with the overruns gone they do not occur [obs: no overrun, no phantom key in the shipped runs; not examined for a stuck-key effect].
* 16 MHz machines other than Hatari's model (a Mega STE: blitter at 8 MHz, CPU at 16) were not run; the blit durations are the same in wall time and the margin is 4 rows x 80 us = 0.32 ms per chunk against 1.28 ms.
* The first overrun can also be seen during the start-up path of a cold boot with old chunks (34 overruns before the map view in st7); this was the original game start (the game's loader code is untouched), only visible with the old chunk size.
