# Explosion circles left in the sky after the camera moves (`p4_hud_pfx_circle`)

**Status: fixed** by a new patch `patches/p4_hud_pfx_circle.s` (`default: yes`, site `$1d188`, deferred, blob `$b4fc0`, 6 bytes at the site).
Evidence below is raw output I produced (paths under `work/explosions/`, raw logs in `work/explosions/logs/`); anything not measured is marked `[INFERENCE]`.

## 1. Verdict

* **Ours, not stock.** The stock game clears every circle (deterministic gate, section 5a, stock vs the v1.4 display set: 46674 differing bytes; stock cold boots STE and TT: 0 stale pixels after the explosion).
* **Not TT-only.** The same stale pixels reproduce on an STE 1 MB cold boot, on a TT (TOS 3.06, `--mmu true`, 4 MB) cold boot and on a 2 MB STE snapshot restore (the display set, no timing patches).
* **Culprit:** the `p4_hud_pfx_*` clean-prefix set (the same family as `mask.md`). Bisect (section 3): `p4_hud_pfx_*` alone reproduces; the rest of the display set (`p4_grid`, `p4_proj_*`, `p4_walk*`, `p7_*`) alone is identical to stock. `p7_skip_render`, `p3cp_*`, `p4_cell`, `p7_ck_*` are NOT involved.

## 2. Mechanism (with evidence)

`KB[b]` (`$b4680`, `$b4682`) = number of 8-line blocks from line 58 that `p4_hud_pfx_fill` (`$1b996`) does not refill in back buffer b because they "already hold the final sky + cockpit image". `p4_hud_pfx_replay` (`$30f2c`) sets `KB[b] = (YMIN - 58) >> 3` and `YMIN` is the smallest first row of any filled polygon of the frame, recorded by `p4_hud_pfx_ymin` at `$38cd0` (`cmp.w YMIN.l,d6` where the span filler contract is "d6.w = first row", `038c84: 3c00 move.w d0, d6` in the polygon wrapper `$38c6e`).

Explosions are NPC type 0 / effect records drawn by `$1cdae`/`$1ce56` -> `$1ce90` -> `$1ceda` -> `$1cf64`, which fills a disc through the SAME span filler but NOT through the polygon wrapper:

```
01d16a:  41f90007b6b0   lea.l    $7b6b0.l, a0
01d170:  43f90007b9d0   lea.l    $7b9d0.l, a1
01d176:  3e39000181dc   move.w   $181dc.l, d7
01d17c:  203867a6       move.l   $67a6.w, d0
01d180:  34386808       move.w   $6808.w, d2
01d184:  36386806       move.w   $6806.w, d3
01d188:  4eb85020       jsr      $5020.w          ; 005020: jmp $38cd0.l
01d18c:  4e75           rts
```
(`python3 tools/m68dis.py work/dumps/ram_ingame_lobos.bin 1d16a --end 1d1f0`; `--callers 5020` = `01d188` only, `--callers 38cd0` = `038caa` only: the polygon wrapper and the disc fill are the only two entries.)

At `$1d188` d6 holds a BYTE OFFSET (`01d1e2: dc4e add.w a6,d6` advances it by a6 = 160 per row), not a row, so `cmp.w YMIN.l,d6 / bge` in `p4_hud_pfx_ymin` never lowers YMIN for a disc. Measured at the first disc of an explosion (`work/explosions/trace188.py`, raw `logs/trace188_circle_calls.log`, patched live with the 4 pfx patches):

```
0001d188 4eb8 5020                jsr $00005020.w
  D5 00003160   D6 000042E0   D7 FFFF001A          ; d6 = $42e0 = 17120 = 107*160 (a row*160 byte offset, not a row), d7+1 = 27 rows
  A0 0007B6B0
000B4684: 00 66                                    ; YMIN = $66 = 102
000B4680: 00 00 00 00                              ; KB (first hit of the frame, before the replay)
0007B6B0: 32 48 c0 00 32 e0 ff fe 33 80 ...        ; first edge entry $3248 = 80*160 + 72: the disc starts on row 80
```
So the disc is drawn on rows 80.. while YMIN says "nothing above row 102". The replay then stores `KB = (102-58)>>3 = 5` (the per-flip `$b4680` dump of the pfx-only run: `f02 KB0 KB1 YMIN = 0005 0005 0066`, `f06 0005 0006 0067`, `f08 000d 000d 00a3`): the next time that buffer is drawn into, `$1b996` starts at line 58 + 8*KB and **does not refill the disc**, and the cockpit replay skips the records above the same line. The disc stays until KB drops (horizon moves up), which gives the straight-edged cut-offs of the report: only the part of the disc on rows that the terrain fill / the shrinking prefix reaches is erased.

Per-flip pixel counts (palette index 10 = orange, 11 = white, rows 58-179, both buffers) - after the explosion has ended the stock frames have 0, the patched ones keep the remnants for ever, camera turning the whole time:

```
STE cold, v1.4 default WITHOUT the fix (logs/analysis_ste_nofix.txt):   flip 19..139: orange 3050 / white 1070 (buf 60000), 2653 / 962 (buf 70000), constant
TT  cold, v1.4 default WITHOUT the fix (logs/analysis_tt_nofix.txt):    flip 57..137: orange 2526 / white 1098 (buf 60000), 3909 / 1885 (buf 70000), constant
STE cold, stock (logs/analysis_ste_stock.txt), TT cold, stock (logs/analysis_tt_stock.txt): flip 17/19..139: 0 / 0, 0 / 0
STE cold, WITH the fix (logs/analysis_ste_fix.txt) and TT WITH the fix (logs/tt_fix_run1_analysis.txt): 0 / 0 after the explosion
```
Sheets: `cold_ste_nofix_sheet.png` (the user's screenshot: orange and white blobs in the sky band with flat lower edges), `cold_tt_nofix_sheet.png`, `cold_ste_fix_sheet.png`, `cold_tt_fix_sheet.png`, `cold_ste_stock_sheet.png`; screenshots `ste_nofix_end.png`, `ste_fix_end.png`, `tt_nofix_end.png`, `tt_fix_end.png`.

## 3. Bisect (deterministic, STE snapshot, per-frame simulation)

Method: `work/explosions/expseq.py SNAP SET OUTDIR --dist 700 --n 36 --turn-at 4 --turn 4278714368` restores `work/explosions/jeep_fired.sav` (Jeep on Dhafra, one missile in flight: `$3532 + 3*$42` type 27 state 12), applies the set live at the first flip after absolute VBL 154200, pokes the missile slot (position 700 units ahead, life word `$36` = 1 so it detonates on the next tick) and the mouse yoke `$6fb6 = $ff510000` (turn), and saves both screen buffers (visible 32000 B), `$67a6`, the KB block `$b4680`, the heading, the palette, for each of 36 consecutive flips. `cmpdirs.py A B 36` counts differing bytes per flip and buffer. Sets: `stock` (nothing live), `display` (the 26 display patches of the abtest gate), `nofix` (display minus the new patch), or a comma list. (A first batch of bisect runs shared one live image name and was discarded; the numbers below are from runs with a per-set hash name.)

```
stock  vs  display set without the fix (26)   TOTAL 46674   (logs/gate_main_stock_vs_nofix.txt)
stock  vs  pfx 4 patches only                 TOTAL 46674   (same count)
stock  vs  display minus pfx 4 patches        TOTAL 0
stock  vs  display + p4_hud_pfx_circle (27)   TOTAL 0       (logs/gate_main_stock_vs_fixed.txt)
```

## 4. The fix

`patches/p4_hud_pfx_circle.s` (new file: the format allows one site per patch, and the site is the disc fill's `jsr $5020.w ; rts` at `$1d188`, not the `$38cd0` entry that `p4_hud_pfx_ymin` hooks):

```
        org     $1d188
        jmp     $b4fc0.l
        org     $b4fc0
        move.l  d4,-(a7)
        move.w  $181e2.l,d4             ; cy
        sub.w   $181de.l,d4             ; cy - r = first possible row
        cmp.w   YMIN.l,d4
        bge.s   .n
        move.w  d4,YMIN.l
.n:     move.l  (a7)+,d4
        jmp     $38cd0.l                ; was jsr $5020.w / rts
```
* YMIN = min(YMIN, cy - r). `$181e2` (cy) and `$181de` (r) are the disc parameters `$1ce90` stores before the fill (`01cec4: move.w d1,$181e2.l`, `01ceca: move.w d3,$181de.l`; `--xref` shows no other writer; `$1ceda` derives its clip rows from the same values: `01cf0c: sub.w d2,d5` / `01cf0e: add.w d2,d6`). The disc lies inside rows cy-r .. cy+r, so a smaller YMIN is always safe: it only makes the prefix smaller. A negative value is clamped to KB 0 by `p4_hud_pfx_replay` (`subi.w #58,d0 / bpl`).
* The displaced `jsr ; rts` is a tail call `jmp $38cd0.l` (the filler's `rts` returns to the caller of `$1cf64`, as before). d4 is saved; the filler reads d0/d2/d3/d7/a0/a1/a6, untouched. Cost about 70 cycles per disc (a frame has some dozens during an explosion).
* `mw2patch.py verify`: ALL OK (`logs/verify.txt`). Blob `$b4fc0-$b4fdb` is free (`p8_tt_ptr` ends at `$b4f81`, `$b4fa0..` unused).

## 5. Gates (raw)

### 5a. Explosion sequence, frame-matched against stock (STE snapshot, 36 flips, both buffers)
`work/explosions/logs/gate_*.txt` (`cmpdirs.py`: differing visible bytes per flip, `[buf60000, buf70000]`):
```
main (700 units, turn left from flip 4)    stock vs fixed   TOTAL 0       stock vs nofix  TOTAL 46674
d300L (300 units, turn left from flip 3)   stock vs fixed   TOTAL 0       stock vs nofix  TOTAL 35096
d1500R (1500 units, turn right from flip 6) stock vs fixed  TOTAL 0       stock vs nofix  TOTAL 3911
d0 (missile detonated where it is)         stock vs fixed   TOTAL 0
```
Negative control = the "nofix" column (the same gate fails without the new patch, and the failures are the stale discs: `before_after_60000.png`, `before_after_70000.png`: columns stock | without the fix | with the fix; the middle column keeps orange/white blobs with flat lower edges at flips 9, 14, 25, 34 where the other two have a clean sky).
First lines of `logs/gate_main_stock_vs_nofix.txt`: `f03 [0, 273]`, `f04 [513, 273]` ... `f14 [0, 793]`, `f15..f36 [0, 473]` (473 bytes of buffer 70000 stuck for 22 flips).

### 5b. MW2 abtest display set (27 patches: the 26 of the earlier gates + `p4_hud_pfx_circle`), `tools/abtest.py --flips 10` and `--flips 40`, both default snapshots
Raw: `logs/abtest_display.txt` (final run) and `logs/abtest_display_run1_foot10_flake.txt` (see below).
A first run printed `1mb_ingame_foot: pixels DIFFER (36 bytes)` at `--flips 10` (base fps 6.9, an unusually fast, loaded host; the same snapshot/flip count) and IDENTICAL for the other three. Re-running the foot snapshot at `--flips 10` with the 26-patch set (without the new patch) and with the 27-patch set, back to back, gave IDENTICAL both times (`work/explosions/logs/abtest_foot10_with_without.txt`), and the final full run (pasted below) is IDENTICAL everywhere, so the 36 bytes are the known load-dependent difference, not the new patch `[INFERENCE: cause not isolated]`.

```
### abtest --flips 10
1mb_ingame_walking: pixels IDENTICAL; fps base 3.1 (63 flips) -> patched 3.4 (67 flips)
1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (85 flips) -> patched 27.4 (549 flips)
exit 0
### abtest --flips 40
1mb_ingame_walking: pixels IDENTICAL; fps base 2.8 (56 flips) -> patched 3.4 (68 flips)
1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (84 flips) -> patched 27.4 (548 flips)
exit 0
```

### 5c. Cold boots (HD build `build/MW2Boom` = the v1.4 defaults + `p4_hud_pfx_circle`)
`work/explosions/cold_exp.py MACHINE BUILD TAG`: cold boot -> Raids map -> Dhafra Jeep (`{'island': 3, 'vehicle': 1, 'view': 2}`, marker `MWPO`), fire (Space) until a missile is in slot 3, put its detonation 700 units ahead (debugger write at a flip), turn the camera with the real mouse (30 px steps, right then left) while dumping both buffers at 140 consecutive flips. Builds: `build/MW2Boom` (fixed), `build/MW2BoomNoFix` (defaults minus the new patch = v1.4 as shipped), `build/MW2BoomStock` (no patches).

| run | machine | result |
|---|---|---|
| fixed | STE 1 MB TOS 1.62 | explosion drawn (orange 5782 px at flip 6) and gone from flip 16 on; 0/0 for the other 124 flips; `MWPO`, no bus error (`logs/cold_ste_fix.log`) |
| fixed | TT 4 MB TOS 3.06 `--mmu true` | explosion drawn (orange 9012/10020 px at flip 13), 0/0 from flip 45 on (`logs/tt_fix_run1_analysis.txt`); `MWPO`, no bus error. (A second TT run, `logs/cold_tt_fix.log`, only used for the flip check below, missed the detonation: no missile in the slot at the poke.) |
| v1.4 without the fix | STE 1 MB | 3050 / 1070 and 2653 / 962 stale px for ever (`logs/analysis_ste_nofix.txt`) |
| v1.4 without the fix | TT | 2526 / 1098 and 3909 / 1885 stale px for ever (`logs/analysis_tt_nofix.txt`) |
| stock | STE 1 MB | explosion drawn, 0 / 0 after it (`logs/analysis_ste_stock.txt`) |
| stock | TT 4 MB | explosion drawn (orange 11627 px at flip 7), 0 / 0 from flip 19 on (`logs/analysis_tt_stock.txt`, `cold_tt_stock_sheet.png`). The first three stock-TT tries failed in the navigation helper (`{'island': 65535}`; cause not isolated `[INFERENCE: the pointer-less stock TT map, map_pointer.md]`); the fourth restored a map state saved after the cold boot with a 20 s settle (`cold_exp.py ... --reuse --pre 20`, map screenshot `tt_stock_map.png`) |

### 5d. TT: does the 3D view redraw while driving? (Main's question about the TT floppy 0-flips measurement)
HD build, TT 4 MB TOS 3.06 `--mmu true`, Jeep driving (mouse Y forward twice), 500 VBL each, from `logs/cold_tt_nofix.log` and `logs/cold_tt_fix.log`:
```
FLIPCHECK flips per 500 VBL: {'$ff8201': 172, '$ff8203': 1, '$67a6': 213} fps $ff8201 = 17.20 | player pos moved True
FLIPCHECK flips per 500 VBL: {'$ff8201': 171, '$ff8203': 1, '$67a6': 214} fps $ff8201 = 17.10 | player pos moved True
```
So on the HD TT build `($ff8201).b` toggles at 17.2 flips/s while the view is live; `$ff8203` changed once in 500 VBL, and in the 140-flip dumps 103/139 and 116/139 consecutive flip pairs have different pixels in at least one buffer (`logs/analysis_tt_*.txt`). The `$ff8201` register is therefore the right flip register on this HD build; I did not run the floppy TT build, so the floppy 0-flips result is not explained here `[INFERENCE: it is not the flip register]`.

## 6. Other draws above the clean prefix (not fixed, checked statically)
The only other references to the draw target `$67a6` are the sky fill (`$1b99a`), the cockpit replay set-up (`$1dc06`), the flip (`$26eb8`), `$1b6c6` (map-window clear, `$1b6be`), `$2e196` (3D entry clear) and the polygon wrapper (`$38c9e`) (`m68dis --xref 67a6`). Polygons and discs are the only per-frame primitives that reach the filler (`--callers`). HUD gauges/text use their own pointers. `[INFERENCE]`: nothing else draws into rows 58-199 above YMIN between the sky fill and the replay; the deterministic runs of 3 distances and 2 turn directions agree with that.

## 7. Files
`patches/p4_hud_pfx_circle.s`; `work/explosions/`: `expseq.py` (deterministic sequence capture), `cmpdirs.py`, `cmpsheet.py`, `bufimg.py`, `idxcount.py`, `trace188.py`, `mkpre.py` (made `jeep_fired.sav`), `cold_exp.py`, `analyze_cold.py`, `scen.sh`, sheets/screenshots, `logs/`.
Line for `patches/README.md` (HUD overlay section, lead's file, not edited): "`p4_hud_pfx_circle` (`$1d188`, deferred, blob `$b4fc0`, part of the clean-prefix set): the disc/explosion fill enters the span filler with a byte offset in d6, not its first row, so YMIN never covered it and explosion circles above the horizon stayed on screen; it lowers YMIN to cy - r before the fill (`work/notes/explosions.md`)."
