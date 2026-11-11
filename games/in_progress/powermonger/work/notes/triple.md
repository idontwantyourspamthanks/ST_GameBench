# Powermonger triple buffering (PMTriple): `p7_triple_wait` + `p7_triple_flip` + `p7_triple_tail`

Tags: **[obs]** observed in Hatari 2.6.1 (raw output in `work/triple/*.txt`, reproducible with the command given); **[disasm]** read from `work/dumps/get_men.bin` with `tools/m68dis.py` (addresses given); **[INFERENCE]** not run.
Patches (**`; default: yes` since 2026-11-10, the combined set: `combined.md`**; all three are needed together): `patches/p7_triple_wait.s` (site `$13090`, carries the data block), `p7_triple_flip.s` (site `$1386c`), `p7_triple_tail.s` (site `$1898`); code and data `$DB000-$DB3FF` (new prefix `p7_` = `$DB000-$DBFFF` in `pmpatch.py PREFIX_RANGES`).
Third screen buffer C = `$70000-$77CFF` (32 000 B of RAM that nothing reserves; no `; data:` line, the patch never needs it zeroed).
Gate tools: `tools/pmtriple.py` (`trace`, `state`, `fill`, `boot`), `tools/pmab.py --c3 70000` (third capture region), negative control `patches/test_nowait.s`. Conflicts: `p4_chase` and `test_nowait` (same site `$13090`).
Everything: 1 MB STE / TOS 1.62 snapshots unless a row says otherwise; the default set below = `tick_* p4_ptr_a p4_ptr_b p4_spr p6_slope p6_tri p6_cpy pm_tooltip p3b_interp p3b_delta` (+ `test_walk*`, the pointer driver, in the pmab runs; `snd_*` is not part of any snapshot gate: its init runs at boot).

## 0. Result

| gate | result |
|---|---|
| Pixel gate `pmab.py` (per presented frame, matched by (world tick, pass kind)), defaults vs defaults + p7, map_idle / get_men / battle_320 at 8 and 16 MHz, `--walk` | **IDENTICAL in all 6**, without p3b in both runs every frame (section 4.1), with p3b every tick-pass frame and every render-only frame that has a partner (4.2); "shown + pointer" frames matched 31 / 158 / 55 / 212 / 55 / 230 |
| State equality `pmtriple.py state` (RAM `$0-$60000` at every loop top, per world tick, masks of `pmtick.py` + the three sites + key table) | **IDENTICAL in all 6** (4.3), negative control (tick k against k+1) differs in every loop top, RNG `$2df84` identical, 17-36 men records moved |
| World-tick rate (`pmtriple.py rate`) | 4.0 ticks/s with and without p7: 8 and 16 MHz at 50 Hz, 16 MHz at 60 Hz (4.6) |
| fps (pmab, 3000 VBL windows, defaults with p3b, same pointer walk) | 8 MHz **+2.2 % / +2.8 % / +3.9 %** (map_idle / get_men / battle_320); 16 MHz **+7.9 % / +9.1 % / +10.5 %** (4.4) |
| No tearing, from a trace of the video base against the draw target (`pmtriple.py trace`) | **0 violations** in 6 scenes x 8/16 MHz + the paused game (4.5); the negative control (the loop-head wait removed on the double buffer) gives 106 |
| Free RAM, `$6F30C-$77FFF` (36 084 B pattern) | **0 changed bytes** after boot, map view, get_men, query window, battle, save, load: floppy STE 1 MB, floppy Mega STE 4 MB, HD GEMDOS STE 1 MB, HD `--acsi` STE 1 MB (twice) and Mega STE 4 MB (section 2). One earlier ACSI run failed (below) |
| Cold boots with p7 (floppy) | STE 1 MB TOS 1.62, ST 1 MB TOS 1.04, Mega STE 4 MB TOS 2.06 (60 Hz): map view, get_men, query window, 16 MHz, all three buffers rotate (section 5) |
| HD `--acsi` boot on STE | map view, get_men, query window, save + load through the game's menus (a plain-flip loop in the middle), back in the 3-buffer loop (section 5) |

How it works in one line: **the wait for the VBL moves from the top of the pass to the flip at its end, where it never waits in a real scene**, because the pass draws into a third buffer that neither the display nor the pointer is using.

## 1. The current scheme (double buffer), mapped

**Buffers** [disasm `$1174-$1192`]: `A = ($1c6b8 + $ff) & -256 = $1c700`, `B = A + $7d00 = $24400`; `$2df78` = L (latest flipped = shown after the next VBL = where the VBL handler draws the pointer), `$2df7c` = D (the buffer being drawn); at game start L = A, D = B. Both are 256-aligned (STE video base `$ff8201/03`), 32 000 B each, contiguous. Above B (`$2c100-$2cc00`) is stack scratch.
**Flip `$187a`** [disasm]: swap `$2df7c` and `$2df78`, `move.l d0,$8200.w` (`d0 = old D >> 8`, written as the two words `$ff8200` / `$ff8202`: high and mid byte, so any 256-aligned address works on ST and STE), then `move.w #0,$2df8c` (`$1898`).
**The wait** [disasm]: `$1870` = `tst.w $2df8c / beq`. `$2df8c` is set at the very end of the VBL handler (`$14d2`, after the IKBD packet and after the pointer restore + redraw of `$13c4-$14c0`), and on the disk-busy path (`$1278`, `$126e != 0`); the VBL counter `$6f304` is bumped at the start (`$1286`). The loop waits at `$13090` (before the window copy), so each pass starts on a VBL boundary: the buffer the last flip just stopped showing is still scanned until that VBL and holds the pointer, which the same VBL handler restores out of it. Idle share of a pass (hotpaths2.md): 4.4-6.9 % at 8 MHz, 6.1-7.2 % at 16 MHz. [obs, this work, 8 MHz get_men] flip return -> first draw: 99 849 cycles in the original, 46 448 with p7 (= the logic stage alone): **53 400 cycles of idle per pass removed**.
**The frame picture** `$78000` (`[$e0d4]`, QAZ.DAT unpacked, 32 000 B) is copied by `$12ce0` (`p6_cpy`: STE blitter in 20 chunks) **over the whole back buffer at the start of every rendered pass** (`$13096`, a0 = `[$e0d4]`, a1 = `[$2df7c]` set at `$1305e`). Everything else (3D window, HUD, windows, tooltip) is then drawn on top, so **the previous content of D never matters**; this is why a third buffer (older content) is invisible.
**Writers** (everything that touches a screen buffer, [disasm] `grep` of the `$2df7c` / `$2df78` operands over `$1000-$1c400`):

| writer | target | with 3 buffers |
|---|---|---|
| window copy `$12ce0` (`p6_cpy`, `$188d4`, `$7818`), terrain + objects `$f898` / `$115e0` (about 25 sites), sprite blits (`p4_spr`), HUD `$17878 $165b2`, windows `$7a56` (clip limit `[$8834] = D + $7d00`: a bound, not an assumption about the other buffer), UI `$6a3a $d23a $7202` | D = `[$2df7c]`, read at the time of the draw | unchanged: D is still "the buffer being drawn" |
| `pm_tooltip` (`$130a4`, `blit: movea.l $2df7c.l,a1`), `qol_hover` (blits through the tooltip's routine) | D, immediate every pass | unchanged |
| men interpolation `p3b_interp/delta` | none: it moves the people records around the call of `$f898` | unchanged |
| mouse pointer: VBL handler `$13c4-$14c0`, `p4_ptr_a/b` (cache keyed on `[$2df78]` + the inputs + the pixels under the pointer) | L = `[$2df78]` at the VBL, restore into the buffer of the previous draw (`$1c49a`) | unchanged: L is still "latest flipped"; the first VBL after a flip is the full path (the key changed) |
| army icon `$3f14` (in `$3e06`, T passes), fade text `$1a254`, `$188c8` (copies L to D) | L | unchanged (L = the frame the previous pass finished) |
| modal loops with plain flips: `$cce2` (message / requester; ends with two flips, `$cd16/$cd28`), `$cf1e`, `$d2cc`, `$11392`, `$13d8e/$13dfa/$13e30` (the main menu loop `$13e1e-$13e36`, which `pm_credit` hooks),  fade / transition screens `$1a496 $1a510 $1a5ce $1a6ce` | D and L with their own `$1870` waits | untouched (`$187a` / `$1870` themselves are unpatched); p7 detects them (section 3) |

The `$57ff0` speed-slider skip, the tick patch's S passes (no copy, no flip) and the pause (copy, no landscape, flip) all keep the same flip site and the same flag.

## 2. The third buffer is free: pattern proof of `$70000-$77CFF`

`$70000-$77FFF` reads zero in `work/dumps/{get_men,map_idle,battle_320}.bin`, the resource table `$e0c4` has no destination there (QAZ at `$78000`, TEXTURES `$2e000`, CAPGRAPH = the back buffer, WIN / LOSE / END_PIC1 = `[$2df78]`; the preloads `e040[]` are above `$80000`), and no operand of the disassembled game points into it. Those are hints; the proof is dynamic (`pmtriple.py fill`, a copy of the method of loading.md section 5): at the stage 1 hand-over (floppy) or the stage 2 hand-over (HD) the debugger loads the position-dependent pattern `fill_byte(a)` (never 0) into **`$6F30C-$77FFF` (36 084 B: the FX.DAT / VBL counter words end at `$6f30b`, the frame picture starts at `$78000`)** of a build WITHOUT p7 (`build/triple/base`), then the harness plays the game through the stages and compares all bytes after each.

| build / machine | boot + map | get_men (16-17 moving) | query window (house window) | battle (iteration 346-350) | save | load |
|---|---|---|---|---|---|---|
| floppy, STE 1 MB TOS 1.62 | 0 / 36 084 | 0 | 0 | 0 | n/a | n/a |
| floppy, Mega STE 4 MB TOS 2.06 | 0 | 0 | 0 | 0 | n/a | n/a |
| HD GEMDOS (Hatari `--harddrive`), STE 1 MB | 0 | 0 | not run | 0 | 0 | 0 (+10 s: 0) |
| HD `--acsi` + HDDRIVER (TOS swap), STE 1 MB, run 1 | 0 | 0 | 0 | 0 | 0 | 0 (+10 s: 0) |
| HD `--acsi`, STE 1 MB, run 2 | 0 | 0 | not run | 0 | 0 | 0 (+10 s: 0) |
| HD `--acsi`, Mega STE 4 MB TOS 2.06 (R 87 760 B, S `$dd000..$f26cf`) | 0 | 0 | not run | 0 | 0 | 0 (+10 s: 0) |

(save/load = Option -> FILE -> SAVE / LOAD, slot A, through the game's own menu with `pmpatch.run_saveload`'s breakpoints: saved state == loaded state, 0 of 101 376 B differ; the harness reports the pattern after the save, after the load and 10 s later. Raw: `work/triple/fill_*.txt`.)
Real-HD swap ranges: the TOS world that `hd_core` exchanges (R, at most `[$8, $156d8)`) and its swap buffer S (`$DD000-$F5FFF`) are far from `$70000`; the `$B8800-$EFFFF` / `$F0000-$F5FFF` proofs of loading.md section 7.1 are untouched by this patch (C is outside them).
**One failed run, not explained:** the first HD `--acsi` fill run (while a floppy run and other agents' emulators shared the host) ended with `saveload: the load never returned` and 35 329 of 36 084 pattern bytes changed afterwards (`fill[after save + load]`). Three later ACSI runs (STE x2, Mega STE) and the GEMDOS run went through save and load with 0 changes, and the harness was changed to report after the save and after the load separately; the first run's memory was not kept. Treat `$70000` as proven for the paths above and this as an open question of the harness (a mis-click in the file dialog would restart a level, [INFERENCE]), not as evidence against; a pattern change after a real load would make the buffer unsafe only while the menus run, because the main loop redraws the whole buffer before it is shown (section 3).
Not proven: that the game never READS the region expecting a value (the debugger has no read watch; it is zero in every dump), and the floppy save / load (needs a second formatted disk; the HD runs cover the game's own save / load code, the floppy driver only adds DMA into `$3f768`) [INFERENCE]. 512 KB machines do not matter: the payload at `$B8000` needs 1 MB anyway.

## 3. Design (3 sites, 144 bytes of code)

```
$13090  jsr $1870          -> jsr twait   (p7_triple_wait,  $DB200)   loop-head wait
$1386c  jsr $187a          -> jsr tflip   (p7_triple_flip,  $DB100)   the main loop's flip
$1898   move.w #0,$2df8c   -> jsr ttail   (p7_triple_tail,  $DB300)   the last action of EVERY flip (6 B + nop, the rts at $18a0 stays)
T = $DB000: +0 IN.w  +2 OURS.w   (zeroed at boot by the `; data:` line of p7_triple_wait)
```
Three buffers A = `$1c700`, B = `$24400`, C = `$70000`; D drawing, L latest, X spare. **tflip**: (1) `jsr $1870` (wait for the flag = one VBL since the previous flip); (2) check D != L and both are members of {A, B, C}, otherwise `jmp $187a` unchanged; (3) X = A + B + C - D - L; IN := 1; `jsr $187a` (the plain flip: it swaps D / L, writes `$ff8201/03`, clears `$2df8c`, so a breakpoint or capture at `$187a` still sees every flip); (4) `[$2df7c] := X`. After the flip: L' = D, D' = X, X' = L (rotation A,B,C: D takes the buffer that was shown BEFORE the one shown now). X is computed, not stored, so it works from any pair a modal loop with plain flips leaves behind. **ttail** (inside `$187a`, so for every caller): `OURS := IN; IN := 0` = "the last flip was tflip's". **twait**: `OURS != 0` -> return without waiting, else the original `jmp $1870`.

Why this is safe, in terms of the three things a buffer must not be while it is drawn into: (a) *scanned*: the displayed buffer is the base register as latched at the last VBL; (b) *holding the pointer*: the VBL handler restores the pointer out of `$1c49a`'s buffer and draws into `[$2df78]`, once per VBL; (c) *pending* (flipped but not yet shown): a flipped frame must be shown before it is replaced. tflip's flag wait guarantees that a VBL handler has run completely since the previous flip, so at the flip the last VBL already showed L_prev, restored the pointer out of everything else and drew it into L_prev; D' = X is neither L_prev nor the new L. Flips are therefore at least one VBL apart (every flipped frame is shown, as in the original). In a real scene (a pass of 4-15 VBL) the flag is long set and the wait costs 16 + 12 cycles; in a short pass (paused game: copy + HUD only) it is the pacing the loop-head wait was (4.5). After a *plain* flip (any modal loop or fade) the tail hook clears OURS, so the first pass back in the main loop waits for the VBL as the original did (a double plain flip would restore the pair `(D, L)` and fool a pair check; the hook cannot be fooled).
Unchanged by design: pass order, `$12f58`, the tick head / pass / wx / men hooks (R and S passes never touch world state; the only thing that moved is WHEN a pass starts relative to the VBL, which the tick accumulator already measured in VBLs), `$2df70` and the click lifetime counter, the sound IRQ, the pointer code (`p4_ptr_a/b` keep their `[$2df78]` key).

## 4. Gates (raw output in `work/triple/`)

### 4.1 Pixel gate, no p3b (every frame comparable) `ab_nop3b.txt`
`python3 tools/pmab.py --base p4_ptr_a p4_ptr_b p4_spr p6_slope p6_tri p6_cpy pm_tooltip --only p7_triple_wait p7_triple_flip p7_triple_tail --c3 70000 --snapshot map_idle get_men battle_320 --mhz 8 16 --vbls 1000 --walk`
Both runs carry `tick_*` + `test_walk*` + the base; `--c3 70000` adds the third buffer to the per-flip capture. Frames are the buffer just rendered (`[$2df7c]` at the flip entry) and the shown buffer + pointer, matched by (world tick, pass kind).
```
map_idle   @8  MHz: IDENTICAL (back frames matched 50,  shown+pointer matched 31)  fps 3.241 -> 3.271 (+0.9 %)
map_idle   @16 MHz: IDENTICAL (back 161, shown+pointer 158)                        fps 8.241 -> 8.838 (+7.3 %)
get_men    @8  MHz: IDENTICAL (back 88,  shown+pointer 55)                         fps 5.266 -> 5.374 (+2.0 %)
get_men    @16 MHz: IDENTICAL (back 213, shown+pointer 212)                        fps 10.797 -> 11.946 (+10.6 %)
battle_320 @8  MHz: IDENTICAL (back 90,  shown+pointer 55)                         fps 5.368 -> 5.590 (+4.1 %)
battle_320 @16 MHz: IDENTICAL (back 231, shown+pointer 230)                        fps 11.765 -> 12.753 (+8.4 %)
```
(`get_men @16`: 55 / 55 consecutive same-tick render-only frames identical; "base frames == the frame 2 flips earlier" 0 of 212: no frame of this run equals the one in the buffer it was drawn over, so a stale-content dependence would have shown.) A first run of get_men @16 at 700 VBL with `--walk`: IDENTICAL, 144 back / 143 shown+pointer.

### 4.2 With the default p3b (predict-ahead) in both runs `ab_p3b_tonly.txt`
`... --base p4_ptr_a ... pm_tooltip p3b_interp p3b_delta --base-poke b8a80:0001 --poke b8a80:0001 --tonly ...` (the recipe of hotpaths2.md section 6: TOFF forces tick passes to be drawn without offset in both runs, render-only frames may differ because the fraction depends on the pass phase, which p7 moves): **6 of 6 IDENTICAL** (back frames matched 51-80 per run, 0-69 render-only frames "allowed to differ" (get_men @16: 69, get_men @8: 4), all hard comparisons identical).

### 4.3 State equality `state.txt`
`python3 tools/pmtriple.py state SNAP MHZ 700`: both sides apply their live image at the first flip, every loop top (`$12fd8`) dumps `$0-$60000`, compared word by word per world tick (`pmtick.py` logger and masks, plus the three p7 sites and the key table `$2de6c-$2dea8`).
```
map_idle   8  MHz: 39 loop tops over 39 ticks IDENTICAL, negative control 39/39        map_idle   16 MHz: 121 over 56 IDENTICAL, neg 119/119
get_men    8  MHz: 76 over 56 IDENTICAL, neg 75/75                                      get_men    16 MHz: 169 over 56 IDENTICAL, neg 168/168 (RNG 0 diffs, 3 values; 19 men records moved)
battle_320 8  MHz: 75 over 56 IDENTICAL, neg 74/74 (RNG 5 values, 36 men moved)         battle_320 16 MHz: 167 over 56 IDENTICAL, neg 165/165
```
The key table mask is a finding, not a convenience: the first battle_320 @8 run showed differences at `$2de82` / `$2de9e` (`ff00` / `00ff` against `0000`, key flags written by the ACIA handler from host key events) in the first 8 loop tops. `state --selfcmp` (defaults against defaults, no p7) shows no difference in 2 runs, but `state --minus p6_cpy` (defaults against defaults without `p6_cpy`: only the pass length changes, p6_cpy is pixel- and state-neutral) shows the same kind of difference at `$2de6c-$2de70`, `$2de82` and more. So it is input timing, as the `$2dea4` mask of pmtick.py already said; the mask is `$2de6c-$2dea8`.

### 4.4 fps, 3000 VBL windows (`ab_fps3000.txt`, same set as 4.2, `--tonly`, 700 -> 3000 VBL so that one flip is 0.1-0.4 %)
```
map_idle   @8  MHz: flips 224 -> 229  fps 3.776 -> 3.859 (+2.2 %)      map_idle   @16 MHz: 516 -> 557   8.635 -> 9.321  (+7.9 %)
get_men    @8  MHz: flips 294 -> 302  fps 4.941 -> 5.079 (+2.8 %)      get_men    @16 MHz: 643 -> 702  10.753 -> 11.735 (+9.1 %)
battle_320 @8  MHz: flips 339 -> 352  fps 5.684 -> 5.908 (+3.9 %)      battle_320 @16 MHz: 698 -> 771  11.680 -> 12.906 (+10.5 %)
```
All six IDENTICAL again. Why the gain is what it is: it is the half-VBL average that a pass no longer pads to the next VBL boundary. Pass of 9.6 VBL (get_men 8 MHz): 0.33 VBL = 3.4 % minus the VBL handler that now runs inside the measured stage instead of during the wait (pmab's "work/pass" grows 0.3-1.4 %: +4 k..+21 k cycles, one pointer handler per pass); pass of 4.3 VBL (16 MHz): the same half VBL is 8-11 %. The p4_ptr cache makes that handler cheap (12 k cycles uncached, 8 MHz).
The idle that is NOT removed: when a pass is shorter than one VBL (the paused game: 100 flips per 100 VBL before and after) the flip waits for the VBL exactly as the loop did, so the frame rate cannot exceed the refresh.

### 4.5 No tearing: the video base against the draw target `trace.txt`
`python3 tools/pmtriple.py trace SNAP MHZ 700 [--orig | --nowait | --pause]`. Four debugger breakpoints (persistent) log, atomically, `VBL`, the cycle counter, `[$ff8201]`, `[$ff8203]`, `[$2df78]`, `[$2df7c]`: at the VBL handler entry (`$1270`: the base register at that moment = the buffer scanned from this VBL on, `[$2df78]` = the buffer the handler draws the pointer into), at the first draw of the pass (`$13096`, the window copy), at the flip entry (`$187a`) and after the flip (`$13872`). A draw interval = `$13096` -> flip entry, with D constant in it. **The check: at its start, at every VBL inside it and at its end, D must differ from the scanned buffer AND from the pointer buffer.** Hatari latches the video base at the VBL; the debugger stops are atomic, so these are exact values, not samples.
```
p7, 700 VBL            draw intervals / VBLs inside   violations   (L,D) at flip entry                 VBLs between flips (min / max / mean)   flip return -> first draw
map_idle   8  MHz            44 / 658                      0       (A,B) x15 (B,C) x15 (C,A) x14        14 / 17 / 15.6                          129 327 cycles (S-pass logic)
map_idle   16 MHz           120 / 684                      0       (A,C) x40 (B,A) x40 (C,B) x40         5 / 7 / 5.78                            28 061
get_men    8  MHz            72 / 675                      0       (A,C) x24 (B,A) x24 (C,B) x24         8 / 13 / 9.58                           46 448   (original: 99 849)
get_men    16 MHz           160 / 685                      0       (A,C) x53 (B,A) x54 (C,B) x53         3 / 5 / 4.33                            18 464
battle_320 8  MHz            73 / 679                      0       (A,C) x24 (B,A) x25 (C,B) x24         8 / 12 / 9.40                           37 801
battle_320 16 MHz           170 / 689                      0       (A,C) x57 (B,A) x57 (C,B) x56         3 / 5 / 4.06                            15 749
get_men 16 MHz, PAUSED      698 / 698                      0       (A,C) x233 (B,A) x233 (C,B) x232      1 / 1 / 1.00                            1 098   (original: 142 546; spacing also 1)
get_men 8 MHz, ORIGINAL      70 / 620                      0       (A,B) x35 (B,A) x35                   8 / 13 / 9.77
get_men 8 MHz, NEGATIVE CONTROL (test_nowait: the double buffer with the loop-head wait removed): 72 / 672, VIOLATIONS 106: "drawing into B while the scanned buffer is B" and "... while the pointer buffer is B" at every draw start
```
The minimum of 1 VBL between flips (also in the paused game) shows that no flipped frame is replaced before it was shown. The negative control proves the checker can fail.

### 4.6 World-tick rate is untouched `rate.txt`
`python3 tools/pmtriple.py rate SNAP MHZ 1500 --hz 50|60 [--orig]`: world ticks `$4bb3e` per EMULATED second between two atomic samples (VBL + cycle counter at one stop each), defaults with and without p7, same live apply and pointer driver:
```
get_men    8 MHz 50 Hz: defaults 121 ticks = 4.031/s     + p7 121 = 4.031/s       battle_320 8 MHz 50 Hz: 120 = 3.997/s    + p7 120 = 3.997/s
get_men   16 MHz 50 Hz: defaults 120 = 3.997/s           + p7 120 = 3.997/s       map_idle  16 MHz 50 Hz: 120 = 3.997/s    + p7 120 = 3.997/s
get_men   16 MHz 60 Hz: defaults 100 in 25.02 s = 3.997/s + p7 100 = 3.997/s      (cycles/VBL 267 158 / 267 136 = 16 MHz / 60: the refresh really was 60 Hz)
```

## 5. Cold boots (`pmtriple.py boot`, builds `build/triple/p7/{floppy,hd}` = defaults + p7; shots `work/shots/triple/`)
Every run: sites `$13090 4eb9000db200`, `$1386c 4eb9000db100`, `$1898 4eb9000db3004e71` in RAM, `MARKER = 'PMPO'`, then the scenario (map view, `get_men`, the query window on a house, 10 s at 16 MHz), with `(L, D)` read at every flip entry for 5 s after each step and the data block T:
```
build / machine                          boot            (L, D) at flip entry, 5 s each step (map / get_men / query)         T after   16 MHz, 10 s   verdict
floppy STE 1 MB TOS 1.62                 146 s           (A,C) x9 (B,A) x9 (C,B) x9 | same | (A,C) x6 (B,A) x7 (C,B) x6        IN=0 OURS=1  45 passes / 661 VBL   OK
floppy ST 1 MB TOS 1.04 (FLAGS 0x6)      146 s           (A,C) x7 (B,A) x6 (C,B) x6 | x8 x8 x8 | x4 x4 x3                      IN=0 OURS=1  45 / 661              OK
floppy Mega STE 4 MB TOS 2.06 (60 Hz)    146 s           (A,C) x9 (B,A) x9 (C,B) x9 | same | x6 x6 x6                           IN=0 OURS=1  45 / 793 VBL          OK
HD GEMDOS STE 1 MB (hd build)            98 s            (A,B) x9 (B,C) x9 (C,A) x10 | x9 x9 x9 | x6 x6 x6                      IN=0 OURS=1  44 / 661              OK + save/load
HD --acsi STE 1 MB (HDDRIVER, TOS swap)  98 s            (A,C) x9 (B,A) x9 (C,B) x9 | same | x6 x6 x6                           IN=0 OURS=1  45 / 661              OK + save/load
```
`$70000` holds a frame afterwards (19 449-19 528 non-zero bytes of 32 000 in every run: it is drawn into). The HD runs also did Option -> FILE -> SAVE and LOAD slot A through the game's own menus (modal loops with plain flips): `saved vs loaded: 0 differ`, `SAVEDISK.DAT` slot A == saved, then the loop is back on the three buffers (`after save + load: (L, D) ... (A,C) x7 (B,A) x6 (C,B) x7 IN=0 OURS=1`, iteration counter advancing). Screenshots after each step: `work/shots/triple/triple_*_{map,getmen,query,16mhz,after_saveload}.png` (the query window over the 3D view, the hover tooltip in the top bar, the pointer and the army icon are as in the original). "16 MHz, 10 s" = `set_cpuclock(16)` then 10 s of wall time: the game kept running (`in_game` true); the first number is the step of `$2df70` (the world-tick counter, not a frame count) in the VBLs given, which is the harness window, not a rate measurement (rates: section 4.6). Raw: `work/triple/boot_*.txt`.

**Re-verified against PMPack's core move** (committed `pmpatch.py` / `core.s`: HOOK1 `$B8140`, HOOK2 `$B8190`, APPLY `$B81F0`, TABLE `$B8250`; defaults now also `fal_ym`, `pm_credit`; nothing in p7 hard-codes a core address, its blobs are at `$DB000-$DB3FF`): `build/triple/p7` rebuilt (`build --floppy --hd --only <current defaults> p7_triple_wait p7_triple_flip p7_triple_tail`: payload `$b8000..$dc023`, 24 sites, `verify` ok) and the cold boots repeated, `work/triple/core2/boot_*.txt`: floppy STE 1 MB `(A,B) x9 (B,C) x9 (C,A) x9`, floppy ST 1 MB TOS 1.04 `(A,C) x6 (B,A) x6 (C,B) x6`, floppy Mega STE 4 MB `(A,C) x9 (B,A) x9 (C,B) x9`, HD `--acsi` STE 1 MB with save + load (`0 differ`, `(A,C) x7 (B,A) x6 (C,B) x7` afterwards): all `COLD BOOT OK`, `OURS=1` in the main loop; the pmab no-p3b matrix of 4.1 repeated (`ab_nop3b_core2.txt`): **6 of 6 IDENTICAL again** (fps +0.9 / +7.6 / +2.3 / +10.6 / +4.4 / +8.6 %); the free-RAM floppy run repeated with the new default set (`core2/fill_floppy_ste1m.txt`: 0 of 36 084 changed after map, get_men, query window and battle). The state, trace, rate and 3000-VBL fps gates ran on live images of the same patch bytes (the old core layout only moves the front / hook code); the HD and Mega STE fill runs were not repeated with the new core.

## 6. Limits and open points
* **Only the main loop is three-buffered.** Modal screens (`$cce2` requester loop, save / load menus, fades, level / end screens) keep `$187a` / `$1870` unchanged on whichever two of A, B, C D and L happen to be; the save / load menus and the query window were exercised in the cold boots, the message requester `$cce2`, the overview-map clicks and the end screens were not.
* A frame is shown one VBL after its flip, as before (no added latency: tflip waits instead of queueing a pending frame, so the buffer count is 3 only to make D independent of the scanned buffer).
* 8 MHz gains are small (+2-4 %: a pass is 8-17 VBL, so half a VBL is 3-5 %), 16 MHz +8-10 %; machines faster than 16 MHz gain more per pass until a pass drops under a VBL, where the flip wait is the pacing.
* `p4_chase` (not default, not exact) and `test_nowait` share the site `$13090` and are refused together with p7 by pmpatch's site-overlap check. `qol_hover` / `pm_tooltip` draw into D every pass and are compatible.
* The floppy save / load, and the HD save / load on a plain ST, were not run with p7 [INFERENCE: same code paths as the HD runs].
* Real hardware: not run. The scheme assumes the STE / ST latch the video base at the VBL (what Hatari does, and what the original relies on).
* **Found on the way, not caused by p7:** `p6_cpy` + `p4_spr` live-applied (`pmab.make_live` + `pmtick.at_flip`, or a `b VBL > N && pc = $1880` apply as pmab does) to the get_men or battle_320 snapshot at 8 MHz WITHOUT the `test_walk*` pointer driver give a bus error in the VBL pointer code within a second: [obs, breakpoint `pc = $147c && a4 > $f0000`] `A4 = $006f0220`, `Bus Error reading at address $6f0220, PC=$147e`; `$2df78 = $24400`, `$2df7c = $1c700` are fine, the pointer words `$2df92 = $0000`, `$2df94 = $adfd` (also `$1c492/$1c494`) are not: `a4 = L + $adfd * 160`, so a mis-assembled IKBD absolute-mouse packet, the signature of the lost-ACIA-byte bug of loading.md section 7.1. With `p4_spr` alone, with `p6_cpy` alone, with `test_walk*` (which replaces the two copies of the packet words), and on map_idle it does not happen, so pmab's pointer driver hides it. **Root-caused afterwards (PMBusErr, `work/notes/buserr.md`): `p6_cpy`'s 10-row blitter chunks kept the IKBD ACIA waiting for two chunks (Hatari), so a received byte was overwritten (overrun), the mouse packet lost a byte and `$2df94` became `$adfd`. Not a snapshot artefact: a cold boot of the same set without the `snd_*` patches crashes the same way; the shipped set (with `snd_*`) only avoided it by timing luck. Fixed with 4-row chunks (`p6_cpy`) + a position guard (`p4_clamp`).** The text below is the original, wrong, inference. The cold boots with `p6_cpy` + `p4_spr` (this note's and the earlier ones) ran fine with the real mouse, so [INFERENCE] it is a snapshot / live-apply artefact (an IKBD packet in flight at the restore meeting the blitter's HOG chunks), but it was not root-caused and I did not run the two patches live without the pointer driver on a cold-booted machine with mouse traffic at 8 MHz for long. `pmtriple.py state` therefore carries `test_walk*`.
