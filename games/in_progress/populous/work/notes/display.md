# Populous display: the pointer and the background copy

PopDisplay, 2026-11-11. 1 MB STE, TOS 1.62, Hatari 2.6.1, 8 MHz, PP's HAGA build, snapshots `busy_castles`, `busy_quake_volcano`, `genesis_start`. Addresses are RAM addresses of `work/dumps/busy.bin` (text base `$AD96`); listings are `tools/m68dis.py`. Patches `patches/pop_ptr.s`, `patches/pop_bgcopy.s` (both `; default: no`, blobs `$C2000-$C26CB`, data `$C2400` + 448); gate `tools/popabtest.py`; raw outputs `work/gates/display_*.txt`. Everything not backed by a listing line or a pasted tool output is marked [INFERENCE].

## Result

Gate (`popabtest.py gate`, 289 flips per run, both buffers + world RAM per flip, two mid-frame samples per flip): **IDENTICAL** for `pop_ptr`, `pop_bgcopy`, both, and both + `pop_land_score` + `pop_land_mul`, on all three snapshots; every broken patch FAILS (section 4). `popabtest.py cpytest`: 96/96 identical registers, CCR and memory against the original `$14a28`.

Turns per second at 8 MHz (150 world turns timed from the same turn in every run, VBLs counted between two breakpoints; the percentage is against the same snapshot without / with the land patches). Pointer = cycles per VBL in `$16dea`-`$16f12` + the blob; copy = cycles per frame in `$14a28`-`$14a4e` + the blob (1000-VBL profile, `Hatari.profile`). `LAND` = `pop_land_score` + `pop_land_mul`.

busy_castles (77 buildings, castles in view)

| set | VBL per turn | turns/s | gain | pointer, still | copy |
|---|---:|---:|---:|---:|---:|
| none | 15.527 | 3.220 | | 11,470 | 247,619 |
| ptr | 14.833 | 3.371 | +4.7 % | 5,171 | 248,007 |
| cpy | 14.727 | 3.395 | +5.4 % | 11,469 | 138,712 |
| ptr + cpy | 14.080 | 3.551 | **+10.3 %** | 5,232 | 138,719 |
| LAND | 10.533 | 4.747 | | 11,457 | 246,838 |
| LAND + ptr | 10.113 | 4.944 | +4.1 % | 5,743 | 243,209 |
| LAND + cpy | 9.733 | 5.137 | +8.2 % | 11,500 | 134,887 |
| LAND + ptr + cpy | 9.360 | 5.342 | **+12.5 %** | 5,891 | 136,029 |

busy_quake_volcano (hills, 90 buildings)

| set | VBL per turn | turns/s | gain | pointer, still | copy |
|---|---:|---:|---:|---:|---:|
| none | 17.480 | 2.860 | | 11,486 | 256,433 |
| ptr | 16.693 | 2.995 | +4.7 % | 5,071 | 257,620 |
| cpy | 16.687 | 2.996 | +4.8 % | 11,479 | 142,670 |
| ptr + cpy | 15.940 | 3.137 | **+9.7 %** | 5,114 | 143,404 |
| LAND | 11.633 | 4.298 | | 11,487 | 260,629 |
| LAND + ptr | 11.133 | 4.491 | +4.5 % | 5,702 | 260,874 |
| LAND + cpy | 10.807 | 4.627 | +7.7 % | 11,486 | 147,351 |
| LAND + ptr + cpy | 10.347 | 4.832 | **+12.4 %** | 5,853 | 147,223 |

genesis_start (9 walkers, 2 buildings; the copy is 22 % of the frame here)

| set | VBL per turn | turns/s | gain | pointer, still | copy |
|---|---:|---:|---:|---:|---:|
| none | 6.687 | 7.478 | | 11,470 | 238,895 |
| ptr | 6.473 | 7.724 | +3.3 % | 6,739 | 238,091 |
| cpy | 5.893 | 8.484 | +13.5 % | 11,470 | 132,366 |
| ptr + cpy | 5.720 | 8.741 | **+16.9 %** | 7,055 | 131,781 |
| LAND | 6.067 | 8.242 | | 11,464 | 241,701 |
| LAND + ptr | 5.880 | 8.503 | +3.2 % | 7,059 | 240,467 |
| LAND + cpy | 5.273 | 9.482 | +15.0 % | 11,469 | 134,682 |
| LAND + ptr + cpy | 5.127 | 9.753 | **+18.3 %** | 7,541 | 135,525 |

Worst case for `pop_ptr`, the pointer moving every VBL (the VBL stub adds 5 to x each VBL, no flip hook; `fps --moving`): pointer 10,855 -> 11,563 cycles per VBL (+708, +6.5 % of the pointer, about 0.5 % of a busy frame), turns/s 3.219 -> 3.202 (busy_castles), 2.862 -> 2.846 (quake), 7.448 -> 7.411 (genesis). Raw lines: `work/gates/display_fps.txt`. The profile counts instruction cycles only and attributes the copy as 247,619 per frame against the study's 257,000 measured with the frame; the patched copy is 138,712 (the code's own cycle count from the 68000 timings is about 146,000 [INFERENCE: manual timings, not re-derived against Hatari's table]).

Cold boots of the HD build (`poppatch.py build --hd --only pop_noprot pop_credit pp_bigram_cache pop_ptr pop_bgcopy --out build/PopDisplay/hd`), STE TOS 1.62 1 MB and ST TOS 1.04 1 MB (section 7).

## 1. The original code

The pointer is drawn by the game's VBL routine, which sits in the TOS VBL queue (`016c44 move.l #$16d70,(a0)`):

```
016d70  movem.l d0-d7/a0-a6,-(a7)
016d74  bsr.w $16c96                 ; button state machine ($3d566 / $3c514 latches)
016d78  tst.w $16d26.l / 016d7e bne.b $16d88      ; hide count
016d80  bsr.w $16dea                 ; RESTORE: the saved 16 rows back to the buffer of the last draw ($16f12)
016d84  bsr.w $16e20                 ; DRAW: pointer into the displayed buffer $3c50c, background saved to $2478c
016d88  tst.w $2195e.l ...           ; sound flag; then the IKBD poll `move.b #$d,$2(a6)`, flag $16d28, counter $16d2a
```

`$16dea` reads `$16f12` (0 = nothing to restore), `$2498c` (rows - 1) and `$2498e` (stride `$90` = two 8-byte groups per row, `$98` = one); `$16e20` computes the address `$3c50c + y * 160 + (x & ~15) / 2`, stores it to `$16f12`, reads the 5 words per row of the shape (`$3d572 + $22b06[$2169a] * 160`), saves 8 or 16 bytes per row to `$2478c` and merges the shape in (`ror.l d5` of mask and 4 planes). Nothing else touches `$16f12`, `$2498c`, `$2498e` or `$2478c` (`m68dis --xref`: `$16f12` at `016dea`, `016e7e`, `016d52 clr.l`; `$2498c` at `016e02`, `016e3a`; `$2498e` at `016dfc`, `016e50`; `$2478c` at `016df6`, `016ea4`). The hide routine `$16d2e` restores and clears `$16f12`; `$16d5e` shows. 8 callers hide (`$11c9e`, `$1245c`, `$14a4e`, `$16b94`/`$16b9a`, `$180fc`, `$18464`, `$1d0d8`). PP's stub at `$6890` puts an `rts` over `$16d70` during disk access (`m68dis --xref 16d70`: `006890 move.w #$4e75,$16d70.l`, `0068a2 move.w #$48e7,$16d70.l`); the patch does not touch that.

Measured (profile, 1000 VBL, busy_castles): 11,470 cycles per VBL in `$16dea` + `$16e20`, one pair per VBL whether or not anything moved (`hotpaths.md`: 7.4 % of the busy frame).

The copy (callers `00b5f4`, `00b6f4`, `01d58a`):

```
014a28  link.w a5,#0 / movem.l a0-a1,-(a7) / movea.l $3c510.l,a0 / movea.l $3b016.l,a1 / move.w #$1f3f,d0
014a40  move.l (a1)+,(a0)+ / dbra d0,$14a40 / movem.l (a7)+,a0-a1 / unlk a5 / rts
```

Source `$3b016` = `$78000` (`bgptr 00078000` read from the emulator), destination `$3c510` = the back buffer, 8000 x 30 cycles.

## 2. pop_ptr (site `$16d80`)

Site: the two `bsr.w` (8 bytes, `610000686100009a`) become `jsr $c2000.l` + `nop`; the blob returns to `$16d88`.

The skip test needs all of: `$16f12` == the address recorded after the last draw; `$3c50c`, `$24786`, `$24788`, `$2169a`, `$3d572`, `$2498c`, `$2498e` equal to what that draw saw; the ROWS x (16 | 8) screen bytes under the pointer == the image that draw left (`cmpm.l`); the 160 shape bytes at `$3d572 + $22b06[$2169a] * 160` == the copy taken at that draw. Then restore writes the saved pixels S over the rectangle and the draw saves S again and merges the shape back: same screen bytes, same `$2478c`, same `$2498c`, `$2498e`, `$16f12`. If any test fails the blob runs `jsr $16dea` / `jsr $16e20` (the original routines, unchanged) and records. Why each part is there:

- `$16f12` and `$3c50c`: a flip swaps `$3c50c` (`016f1a`-`016f32`), so the first VBL after a flip is always the full path, and it restores into the old buffer exactly as the original does; a hide clears `$16f12`.
- position, shape, sheet: the inputs of the draw. `$2498c/e` follow from the position; compared because the restore reads them.
- the rectangle: the game draws into the displayed buffer in places (`--xref 3c50c` finds 104 references; 8 routines hide the pointer around their drawing (the `$16d2e` callers above)). Not trusted: compared. A mismatch means someone drew under the pointer, and the original would then restore S over it and redraw.
- the shape rows: the sprite sheet is rewritten at world (re)load (`$14ee0` -> `$15092`, destination `$3d572`). Compared, not trusted: 1.1 k cycles of the 4.0 k per skipped VBL.
- images are recorded lazily: the first full draw only records the inputs (`pKEYV`); the next full draw that finds the same inputs also records the 16 x 16 rectangle and the 160 shape bytes. A pointer that moves every VBL therefore pays about 0.7 k cycles over the original (measured above), a pointer that stands still one extra full draw per frame.
- the draw's inputs are re-read after the draw; if an IKBD packet changed them during it, nothing is recorded. Rows outside 0..15 or a stride other than `$90`/`$98` are never recorded.

Cost of a skipped VBL, about 4.0 k cycles [INFERENCE from the count: 16 rows x (4 x (cmpm.l 20 + bne.s 8) + adda 8 + dbra 10) = 2.1 k, shape 10 x (4 x 28 + 10) = 1.2 k, 15 key compares about 0.7 k]. Measured average per VBL: 5,171 (busy_castles, still pointer, 14.8 VBL per frame: one or two full draws of about 14.5 k and 13 skips) against 11,470.

Not covered by the pixel gate: the pointer on a real IKBD path (checked by hand in the cold boots, section 7) and TT / Falcon (the blob has no hardware access; relocation is done by `poppatch`, `verify` lists 27 relocated longs).

## 3. The gate: `tools/popabtest.py`

**Input.** The game polls the IKBD in absolute mode (`$0d` at `016dd0`) and the packet handler copies the reply into `$24786/$24788/$2478a` (`020048`, `020052`, `02003e`), so a poke is overwritten within a VBL and a host mouse arrives at a wall-clock moment. The gate (1) turns those three stores (`$2003e`-`$2005b`) into nops, (2) replaces the main loop's flip call (`00b940 jsr $16f16`) with a stub that waits for the VBL flag as `$16f16` does (`jsr $16f48`), masks interrupts, writes position / buttons / held key (`$37eec`, read at `00b94c`) from a table with one row per flip, runs the game's own click state machine `jsr $16c96` on them, swaps the buffers with the instructions of `016f1a`-`016f3a`, captures, and unmasks, and (3) hooks the VBL routine after the pointer code (`016d88 tst.w $2195e.l` -> `jsr`, the instruction is replayed last so its flags reach the `beq`). All of it is in both runs; the patch under test is the only difference.

**Capture.** Three breakpoints on stub addresses run `savebin` into a FIFO that the harness drains (opened read-write so it never sees EOF between writes; no emulated time passes): after every flip both buffers (`$4f500`, `$57200`, 32,000 B each) + the world RAM `$21100-$3d7ff` (116,480 B) + a header; in the 4th and 6th VBL after a flip the displayed buffer.

**Compared**, byte for byte: both buffers and the world RAM at every flip (except `$24990-$249a3`, the sample player's state, advanced by a timer interrupt in real time: `landscore.md` gate b), the displayed buffer at each mid-frame sample. The world is frame-coupled, one turn per pass, so flip i of one run is turn T0 + i of the other whatever the cycle counts. The world RAM includes the pointer's variables (`$24786`, `$2498c`, the save buffer `$2478c`, `$2169a`).

**Scenario** (`build_script`, 289 flips; reference-run coverage read from the captured world RAM):

```
busy_castles: scenario (reference run) {"flips": 289, "pointer_still_flips": 154, "pointer_moved_flips": 134, "shapes": [0, 1, 2], "shape_changes": 4, "modes": [1, 2, 6], "mode_changes": 4, "paused_flips": 6, "button_flips": 24, "junk_flips": 9, "shape_flips": 7, "xpos_flips": 5, "hidden_at_flip": 0, "flips_with_terrain_change": 39, "distinct_views": 16}
```

pointer standing still (154 flips) and moving (134) over the map, book, minimap, left and right panels and all four corners; the edge cases x > 304 (one column) and y > 184 (clipped rows); sub-16-pixel moves (x + 1 per flip inside one word column); icon clicks that change the mode (`$21d8e`: 2 -> 1 query -> 2 raise/lower -> 6 magnet -> 2), clicks on the map (raise, lower, place the magnet: terrain changes in 39 flips), keypad scrolling (16 distinct views), the pause icon (6 paused flips: `$16b64` draws the icon in the displayed buffer under the pointer, between `$16d2e`/`$16d5e`), and three injections under a still pointer in the 3rd VBL after a flip, which the original VBL erases in the 4th: JUNK (the stub XORs the pointer's rectangle in the displayed buffer: the game drawing under it; 9 flips), SHAPE (the 160 shape bytes are XORed; 7 flips), XPOS (x ^ 1: same word column, other shift; 5 flips). The hide path itself is reached through the icon clicks [INFERENCE: no counter was kept; `hidden_at_flip` is 0 because the hide is not open at a flip].

**Two races of the original game, removed from both runs.** The first version of the gate showed a few differing bytes between two runs that differ only in timing (the land patches change the turn time by 30 %, not a pixel). Both are in the original code:

1. A VBL that falls between the position write and the buffer swap draws the new pointer into the OLD buffer. Cured by masking interrupts from the position write to the capture (a window of about 500 cycles, 0.3 % of the flips: it showed twice in 237 flips).
2. The first VBL after a flip restores the pointer's saved background into the OLD buffer (`$16f12` still points there), which the game is by then re-drawing from the clean background. Where that write lands relative to the copy and the tile draws depends on the CPU speed, and a stale rectangle (the old frame's pixels under the old pointer) can stay in the new frame. The stub clears `$16f12` after the swap, in both runs; the restore then does nothing and the draw goes into the new buffer as before. Evidence that this write is the whole cause: with it kept (`--keep-stale`) a timing-only change differs in a few flips, with the clear it is IDENTICAL on all three snapshots:

```
--keep-stale, land patches only (timing change, no pixel change): busy_castles bad flips 2 (samples 2), quake 1 (0), genesis 2 (2)
```

(raw: `work/gates/display_mutants.txt`, last block.) The same set with the clear (`python3 tools/popabtest.py gate --set pop_land_score pop_land_mul`, `work/gates/display_gate_land.txt`):

```
busy_castles         pop_land_score+pop_land_mul        IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 578 bad 0 (only in one run: ref 0, new 0)
busy_quake_volcano   pop_land_score+pop_land_mul        IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 576 bad 0 (only in one run: ref 2, new 0)
genesis_start        pop_land_score+pop_land_mul        IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 565 bad 0 (only in one run: ref 9, new 0)
GATE IDENTICAL (exit 0)
```

The patches do not change this behaviour: `pop_ptr` runs the original routines in that VBL, and `pop_bgcopy` only moves the instant the copy ends. Since a shorter copy lets the stale write land after it more often [INFERENCE from the geometry: the write happens at a random instant of the 160 k-cycle VBL period, the copy is 257 k -> 146 k cycles], the stock artifact can show a little more often with `pop_bgcopy`; it is the original's artifact (in the first runs, before the clear existed, the differing flips of timing-only runs showed 2 to about 150 bytes, near the old and the new pointer rectangles and, with the pointer over the minimap, small groups at rows 35-46; raw analysis scripts were not kept). Removing it in the game would need the restore into the old buffer to be skipped when the next frame re-copies everything, which is not true for dialogs (which do not re-copy): not done.

**Result** (`python3 tools/popabtest.py gate --set none --set pop_ptr --set pop_bgcopy --set pop_ptr pop_bgcopy --set pop_land_score pop_land_mul pop_ptr pop_bgcopy`; `none` = a second unpatched run, the harness's own determinism control; "only in one run" = a sample that one run did not reach because its frame had fewer than 6 VBLs, counted, not compared):

```
busy_castles         none                               IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 578 bad 0 (only in one run: ref 0, new 0)
busy_castles         pop_ptr                            IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 578 bad 0 (only in one run: ref 0, new 0)
busy_castles         pop_bgcopy                         IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 578 bad 0 (only in one run: ref 0, new 0)
busy_castles         pop_ptr+pop_bgcopy                 IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 578 bad 0 (only in one run: ref 0, new 0)
busy_castles         pop_land_score+pop_land_mul+pop_ptr+pop_bgcopy IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 577 bad 0 (only in one run: ref 1, new 0)
busy_quake_volcano   none                               IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 578 bad 0 (only in one run: ref 0, new 0)
busy_quake_volcano   pop_ptr                            IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 578 bad 0 (only in one run: ref 0, new 0)
busy_quake_volcano   pop_bgcopy                         IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 578 bad 0 (only in one run: ref 0, new 0)
busy_quake_volcano   pop_ptr+pop_bgcopy                 IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 578 bad 0 (only in one run: ref 0, new 0)
busy_quake_volcano   pop_land_score+pop_land_mul+pop_ptr+pop_bgcopy IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 576 bad 0 (only in one run: ref 2, new 0)
genesis_start        none                               IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 574 bad 0 (only in one run: ref 0, new 0)
genesis_start        pop_ptr                            IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 572 bad 0 (only in one run: ref 2, new 1)
genesis_start        pop_bgcopy                         IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 542 bad 0 (only in one run: ref 32, new 0)
genesis_start        pop_ptr+pop_bgcopy                 IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 521 bad 0 (only in one run: ref 53, new 0)
genesis_start        pop_land_score+pop_land_mul+pop_ptr+pop_bgcopy IDENTICAL: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 369 bad 0 (only in one run: ref 205, new 0)
GATE IDENTICAL (exit 0)
```

## 4. Negative controls

Each is a deliberately broken copy of the patch source (`MUTANTS` in `popabtest.py`, assembled into a scratch copy of `patches/`), run through the same gate on busy_castles; every one must FAIL:

```
##### mutant ptr_norect
busy_castles         pop_ptr@ptr_norect                 DIFFERENT: flips compared 289 (both buffers + world each), bad flips 9 (world only 0), mid-frame samples 578 bad 23 (only in one run: ref 0, new 0)
##### mutant ptr_noshape
busy_castles         pop_ptr@ptr_noshape                DIFFERENT: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 578 bad 5 (only in one run: ref 0, new 0)
##### mutant ptr_nopos
busy_castles         pop_ptr@ptr_nopos                  DIFFERENT: flips compared 289 (both buffers + world each), bad flips 0 (world only 0), mid-frame samples 578 bad 3 (only in one run: ref 0, new 0)
##### mutant ptr_nobuf (needs --keep-stale: the scaffold's stale-restore removal forces the full path after every flip)
busy_castles         pop_ptr@ptr_nobuf                  DIFFERENT: flips compared 289 (both buffers + world each), bad flips 22 (world only 8), mid-frame samples 578 bad 22 (only in one run: ref 0, new 0)
##### mutant cpy_short
busy_castles         pop_bgcopy@cpy_short               DIFFERENT: flips compared 289 (both buffers + world each), bad flips 470 (world only 43), mid-frame samples 578 bad 466 (only in one run: ref 0, new 0)
##### mutant cpy_tail
busy_castles         pop_bgcopy@cpy_tail                DIFFERENT: flips compared 289 (both buffers + world each), bad flips 425 (world only 10), mid-frame samples 578 bad 418 (only in one run: ref 0, new 0)
##### mutant cpy_off
busy_castles         pop_bgcopy@cpy_off                 DIFFERENT: flips compared 289 (both buffers + world each), bad flips 575 (world only 109), mid-frame samples 578 bad 574 (only in one run: ref 0, new 0)
##### stale race kept (--keep-stale): timing-only change (land patches), pop_ptr, pop_bgcopy
busy_castles         pop_land_score+pop_land_mul        DIFFERENT: flips compared 289 (both buffers + world each), bad flips 2 (world only 0), mid-frame samples 578 bad 2 (only in one run: ref 0, new 0)
busy_castles         pop_ptr                            DIFFERENT: flips compared 289 (both buffers + world each), bad flips 4 (world only 1), mid-frame samples 578 bad 4 (only in one run: ref 0, new 0)
busy_castles         pop_bgcopy                         DIFFERENT: flips compared 289 (both buffers + world each), bad flips 2 (world only 1), mid-frame samples 578 bad 2 (only in one run: ref 0, new 0)
busy_quake_volcano   pop_land_score+pop_land_mul        DIFFERENT: flips compared 289 (both buffers + world each), bad flips 1 (world only 1), mid-frame samples 576 bad 0 (only in one run: ref 2, new 0)
busy_quake_volcano   pop_ptr                            DIFFERENT: flips compared 289 (both buffers + world each), bad flips 3 (world only 1), mid-frame samples 578 bad 2 (only in one run: ref 0, new 0)
busy_quake_volcano   pop_bgcopy                         DIFFERENT: flips compared 289 (both buffers + world each), bad flips 2 (world only 0), mid-frame samples 578 bad 2 (only in one run: ref 0, new 0)
genesis_start        pop_land_score+pop_land_mul        DIFFERENT: flips compared 289 (both buffers + world each), bad flips 2 (world only 0), mid-frame samples 566 bad 2 (only in one run: ref 7, new 3)
genesis_start        pop_ptr                            DIFFERENT: flips compared 289 (both buffers + world each), bad flips 2 (world only 0), mid-frame samples 571 bad 2 (only in one run: ref 2, new 3)
genesis_start        pop_bgcopy                         DIFFERENT: flips compared 289 (both buffers + world each), bad flips 1 (world only 1), mid-frame samples 543 bad 0 (only in one run: ref 30, new 0)
```

`ptr_norect` skips the rectangle compare (caught by JUNK), `ptr_noshape` skips the shape-row compare (caught by SHAPE), `ptr_nopos` ignores `$24786` (caught by XPOS), `ptr_nobuf` ignores `$3c50c` (caught only with `--keep-stale`, because the stub's clear of `$16f12` forces the full path after every flip and so hides that check; with the stale write kept 22 flips and 22 samples differ against 2 to 4 for the unmutated patch in the same mode [INFERENCE: the pointer missing from the displayed buffer]), `cpy_short` copies 780 bytes too few, `cpy_tail` omits the last longword, `cpy_off` writes one block at a wrong offset.

## 5. pop_bgcopy (site `$14a28`)

Site: the first 8 bytes (`link` + `movem`) become `jmp $c2600.l` + `nop`; the blob replaces the whole routine and ends in `rts`.

The copy is 32,000 bytes: 615 blocks of 52 bytes through `d0-d7/a2-a6` (`movem.l (a1)+,regs` + `movem.l regs,d16(a0)`, 15 blocks per round, 41 rounds, loop end by `cmpa.l (sp),a0` against an end pointer on the stack because all 13 registers hold data) plus the last 20 bytes as five `move.l (a1)+,(a0)+`; the last one sets the flags exactly as the original's last long does (N, Z from the data, V = C = 0, X untouched; nothing after it touches the flags). Registers: all 15 are pushed and popped; the saved `d0` gets its low word set to `$ffff` first (the original leaves `dbra`'s -1 there; the high word is kept). Interrupts stay open; the longest uninterruptible instruction is a 13-register movem (12 + 8 x 13 = 116 cycles [INFERENCE: 68000 manual]; the original's is 20), far below the 10 k cycles of an IKBD byte time that limit a chunked copy (`powermonger/work/notes/buserr.md`). Measured: 247,619 -> 138,712 cycles per frame (busy_castles; profile bucket); +13.5 % turns/s on the idle start scene.

Equivalence test (`popabtest.py cpytest`): a verbatim copy of the original `$14a28` (read from the disk image by `poppatch.expected_ram`) and the blob run on the same inputs inside the running game: random `d0-d7/a0-a6`, every CCR input (0..31, three times each), the last longword of the background 0 / negative / positive; registers, SR (X N Z V C) and the 32,128 bytes around the back buffer (64 sentinel bytes before and after, the buffer pre-filled with a pattern) compared:

```
cpytest: 96 trials (random d0-d7/a0-a6, CCR 0..31 each three times, last longword 0 / negative / positive), registers + CCR + the 32,128-byte window incl. sentinels compared: 96 identical, 0 different
## mutant cpy_tail
trial 3: regs equal True ccr orig 00100 new 00000 window differs 1; first differing reg []
trial 4: regs equal True ccr orig 01000 new 00000 window differs 1; first differing reg []
cpytest: 96 trials (random d0-d7/a0-a6, CCR 0..31 each three times, last longword 0 / negative / positive), registers + CCR + the 32,128-byte window incl. sentinels compared: 0 identical, 96 different
## mutant cpy_short
trial 3: regs equal True ccr orig 00100 new 00000 window differs 1; first differing reg []
trial 4: regs equal True ccr orig 01000 new 00000 window differs 1; first differing reg []
cpytest: 96 trials (random d0-d7/a0-a6, CCR 0..31 each three times, last longword 0 / negative / positive), registers + CCR + the 32,128-byte window incl. sentinels compared: 0 identical, 96 different
## mutant cpy_off
trial 3: regs equal True ccr orig 00100 new 00100 window differs 1; first differing reg []
trial 4: regs equal True ccr orig 01000 new 01000 window differs 1; first differing reg []
cpytest: 96 trials (random d0-d7/a0-a6, CCR 0..31 each three times, last longword 0 / negative / positive), registers + CCR + the 32,128-byte window incl. sentinels compared: 0 identical, 96 different
```

**Is the copy needed every frame? Yes; it cannot be skipped or shortened exactly.** At every call of `$14a28` from the main loop (`pc = $b6f4`) the back buffer was compared with the background (`popabtest.py copy`, 40 copies per snapshot):

```
{'snap': 'busy_castles', 'copies': 40, 'bg_changed_between_copies': 6, 'dst_bytes_differing_from_bg_(8-byte granularity)': [11400, 11596, 11864], 'dst_rows_differing_(of_200)': [185, 191, 198], 'union_over_frames_bytes': 12192, 'union_bounding_box_(rows, byte columns)': (0, 199, 0, 159)}
{'snap': 'busy_quake_volcano', 'copies': 40, 'bg_changed_between_copies': 6, 'dst_bytes_differing_from_bg_(8-byte granularity)': [10904, 11198, 11376], 'dst_rows_differing_(of_200)': [176, 183, 192], 'union_over_frames_bytes': 11944, 'union_bounding_box_(rows, byte columns)': (0, 199, 0, 159)}
{'snap': 'genesis_start', 'copies': 40, 'bg_changed_between_copies': 4, 'dst_bytes_differing_from_bg_(8-byte granularity)': [10024, 10191, 10312], 'dst_rows_differing_(of_200)': [167, 170, 175], 'union_over_frames_bytes': 10352, 'union_bounding_box_(rows, byte columns)': (0, 199, 8, 159)}
```

The destination differs from the source in 10-12 k bytes (31-38 %) spread over 167-198 of the 200 rows and over the whole width (bounding box = the screen): it holds the previous frame's terrain, sprites, text and pointer, so the copy is what erases them. The source is not constant either: it changed between copies in 4-6 of 40 (the game draws into it: icons, minimap). An exact partial copy needs the list of every writer into the back buffer (`--xref 3c510` finds 51 references) or a dirty-rectangle design for the terrain (`PLAN.md` item 8); not done. The blitter is no faster than the movem loop here (`algorithms.md` section 3B) and has the IKBD byte-time limit.

## 6. Notes for the next pass

- A skipped VBL still costs about 4.0 k cycles (rectangle 2.1 k, shape rows 1.2 k, key compares 0.7 k). The shape compare could go if every writer of the sprite sheet were hooked (the unpacker `$15092`, 7 call sites) and a generation counter compared instead: not done (a missed writer would be a silent, rare divergence).
- PopBuildGate found a bus error at `PC=$16eca` with `pp_nofade` on HD. `$16eca` is `and.w d0,(a4)` in the draw `$16e20` (listing above), the screen write of the pointer; [INFERENCE] a garbage position after a lost IKBD byte (Powermonger's `buserr.md`). `pop_ptr` leaves that code as it is on every full draw; plan item 9 (position clamp) is the cure.

## 7. Cold boots (`work/scratch/popdisplay/boot_cell.py`, HD build above, real IKBD path)

```
{'cell': 'ste1mb', 'in_play': True, 'marker': 'POPO', 'flags': '00000003', 'ee16': '6052', 'site_16d80': '4eb9000c20004e71', 'site_14a28': '4ef9000c26004e71', 'blob_c2000': '203900016f126700', 'blob_c2600': '48e7fffe3f7cffff'}
{'turn_before': 147, 'turn_after': 213, 'pos': '00d20096', 'valid': '00010001', 'a4': '00055328', 'f12': '00055328'}
{'cell': 'st1mb', 'in_play': True, 'marker': 'POPO', 'flags': '00000003', 'ee16': '6052', 'site_16d80': '4eb9000c20004e71', 'site_14a28': '4ef9000c26004e71', 'blob_c2000': '203900016f126700', 'blob_c2600': '48e7fffe3f7cffff'}
{'turn_before': 147, 'turn_after': 213, 'pos': '00d20096', 'valid': '00010001', 'a4': '00055328', 'f12': '00055328'}
```

Both cells: START GAME reached play, marker `POPO`, both sites applied, the blobs in RAM (`2039 00016f12 6700` = `move.l $16f12.l,d0 / beq.w`), the turn counter moving, and after moving the host mouse twice the pointer cache holds a recorded draw (`pKEYV`/`pVALID` = 1/1, `$16f12` = the recorded address `$55328`). Shots (git-ignored): `work/shots/display_boot_{ste1mb,st1mb}_ptr1.png` and `_ptr2.png` show the pointer at two places. The mouse moves went through Hatari's IKBD, not the injection.

Not done: TT and Falcon (the build relocates the patches; the machines slice owns the boots), 2 and 4 MB cells, floppy, 16 MHz measurements, a hand test of in-game LOAD with the patches on.

## 8. Files

`patches/pop_ptr.s`, `patches/pop_bgcopy.s`, `tools/popabtest.py` (`gate`, `fps`, `copy`, `cpytest`, `mutants`), `work/gates/display_*.txt` (raw outputs quoted above), `work/scratch/popdisplay/boot_cell.py` (cold-boot cell).
