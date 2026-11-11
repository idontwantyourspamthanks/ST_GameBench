# Populous: the land score (`$18244`), the step test (`$181d6`) and the multiply helper (`$20796`)

2026-11-11. 1 MB STE, TOS 1.62, Hatari 2.6.1, 8 MHz. Addresses are RAM addresses of PP's HAGA build (`work/dumps/busy.bin`); listings are `tools/m68dis.py`. Patches: `patches/pop_land_score.s`, `patches/pop_land_mul.s`, both `; default: no`. Test scaffolding: `work/scratch/landscore/`. Raw gate outputs: `work/gates/`. Anything not backed by a listing line or by a tool output pasted here is marked [INFERENCE].

## Result

| | busy_castles | busy_quake_volcano |
|---|---|---|
| turns per second, unpatched | 3.174 | 2.989 |
| with `pop_land_score` | 4.585 | 4.286 |
| with `pop_land_mul` | 3.244 | 3.035 |
| with both | **4.727 (+49%)** | **4.402 (+47%)** |
| land score, cycles per call (with its step tests) | 10,407 -> 1,626 | about 10,470 -> 1,689 |
| multiply helper, cycles per call | 390 -> 208 | 390 -> 208 |

Same world, turn by turn: 521 of 521 turn hashes identical on both snapshots, with and without earthquakes, volcanoes and a flood (gate b). Same outputs on every call: 24,586 land-score calls and 62,026 multiplies, 0 differences (gate a); 114,286 inputs on real and random maps, 0 differences (exhaustive test).

## 1. The original routines

### `$181d6(cell.w, offset.w)`: may a walker step from this cell by this offset

Called with `move.w offset,-(a7)` / `move.w cell,-(a7)` / `jsr` (13 call sites: `m68dis --callers 181d6`).

```
0181d6  link.w a5,#0 / movem.l d1-d4/a0,-(a7)
0181de  clr.l d0
0181e0  move.w $8(a5),d2            ; cell
0181e4  move.w $a(a5),d3            ; offset
0181e8  beq.b $1823a                ; offset 0: return 0
0181ea  move.w d2,d4 / add.w d3,d4  ; cell + offset
0181ee  blt.b $1822a / cmp.w #$1000,d4 / bge.b $1822a      ; outside 0..4095: return 1
0181f6  andi.w #$3f,d3 / cmp.w #$3,d3 / ble.b $18204 / ori.w #$ffc0,d3   ; dx: 0..3 stay, 4..63 become -60..-1
018204  andi.w #$3f,d2 / add.w d2,d3                        ; x + dx
01820a  blt.b $1822a / cmp.w #$3f,d3 / bgt.b $1822a         ; outside 0..63: return 1
018212  lea.l $36eb6.l,a0 / ext.l d4 / adda.l d4,a0
01821c  cmpi.b #$0,(a0) / beq.b $18236                      ; water: return 3
018222  cmpi.b #$2f,(a0) / beq.b $18230                     ; rock: return 2
01823a  movem.l (a7)+,d1-d4/a0 / unlk a5 / tst.w d0 / rts
```

- In: two words on the stack (not changed). Out: `d0.l` = 0 (ok, or offset 0), 1 (off the map), 2 (rock), 3 (water); CCR from `tst.w d0`, X from the last `add.w` executed (unchanged when the offset is 0).
- Preserved: `d1-d4`, `a0`, `a5`; nothing else is touched.
- RAM read: one byte `map_blk[cell + offset]` (`$36eb6` + 0..4095), only after both range tests pass.
- RAM written: none, except 32 bytes of dead stack below the caller's SP (frame pointer, five registers; the caller's 8 bytes of arguments and return address are above them).

### `$18244(owner.w, cell.w)`: the land score

Called with `move.w cell,-(a7)` / `move.w owner,-(a7)` / `jsr` from five places; every caller passes `owner = byte & $ff` and uses only `d0.w` afterwards:

```
00d6f2  move.w $8(a5),-(a7) / move.b $1(a5),d0 / and.w #$ff,d0 / move.w d0,-(a7) / jsr $18244 / addq.l #4,a7 / move.w d0,-$6(a6)
00e282  move.w $8(a0),-(a7) ... jsr $18244 / addq.l #4,a7 / move.w d0,-$c(a6) / tst.w d0 / ble.b $e2b6     ; every building, every turn
00f3fe  move.w -$a(a6),-(a7) ... jsr $18244 / addq.l #4,a7 / move.w d0,-$8(a6) / beq.b $f42a              ; settle search
010306  move.w $8(a5),-(a7) ... jsr $18244 / addq.l #4,a7 / move.w d0,d7 / cmpi.w #$bea,d7                ; building type ($103a4)
010bfa  move.w $8(a0),-(a7) ... jsr $18244 / addq.l #4,a7 / tst.w d0 / ble.b $10c50
```

The routine (complete: `m68dis busy.bin 18244 --end 18344`):

```
018244  link.w a5,#0 / movem.l d1-d6/a0-a2,-(a7)
01824c  move.w $8(a5),d6 / addi.w #$1f,d6       ; own field tile: $1f + owner
018254  move.w $a(a5),d2                        ; cell
018258  clr.w d4                                ; score
01825a  clr.w $3b040.l
018260  lea $22b8c,a2 / lea $36eb6,a0 / lea $3c560,a1
018272  clr.w d5                                ; k = 0..16
018274  clr.w $37ef4.l
01827a  move.w (a2)+,d3                         ; offset k
01827c  move.w d3,-(a7) / move.w d2,-(a7) / jsr $181d6 / adda.l #$4,a7
01828c  tst.w d0 / beq.b $1829e
018290  cmp.w #$2,d0 / bne.w $18318             ; 1 (off the map) or 3 (water): next
018298  addi.w #$fff1,d4 / bra.b $18318         ; 2 (rock): score - 15, next
01829e  add.w d2,d3                             ; cell index
0182a0  cmp.b (a0,d3.w),d6 / beq.w $182ba       ; own field: good
0182a8  cmpi.b #$f,(a0,d3.w) / bne.w $182c8     ; flat: good, and
0182b2  move.w #$1,$37ef4.l                     ;   "a flat cell was counted"
0182ba  tst.w d4 / bne.b $182c2 / move.w #$32,d4
0182c2  addi.w #$f,d4 / bra.b $182d6            ; score = (score or 50) + 15
0182c8  tst.w d5 / bne.b $182d6                 ; other land: the cell itself (k = 0) ends the scan,
0182cc  movem.l (a7)+,d1-d6/a0-a2 / unlk a5 / clr.w d0 / rts          ;   return 0
0182d6  move.b (a1,d3.w),d1                     ; what stands on the cell
0182da  cmp.w #$9,d5 / bge.b $182fe
0182e0  cmpi.b #$2a,(a1,d2.w) / bne.b $182fe    ; the centre holds $2a and k < 9:
0182e8  cmp.b #$29,d1 / blt.b $182fe / cmp.b #$2c,d1 / bgt.b $182fe
0182f4  addi.w #$1,$3b040.l / bra.b $18318      ;   pieces $29..$2c are counted, not tested
0182fe  tst.w d5 / beq.b $18318
018302  cmp.b #$20,d1 / ble.b $18318 / cmp.b #$2c,d1 / bgt.b $18318
01830e  movem.l (a7)+,d1-d6/a0-a2 / unlk a5 / clr.w d0 / rts          ; a building $21..$2c nearby: return 0
018318  addi.w #$1,d5 / cmp.w #$11,d5 / bne.w $1827a
018324  cmp.w #$23,d4 / bge.w $1832e / clr.w d4                       ; below 35: 0
01832e  cmp.w #$131,d4 / bne.w $1833a / move.w #$bea,d4               ; 305 (all 17 good): $bea
01833a  move.w d4,d0 / movem.l (a7)+,d1-d6/a0-a2 / unlk a5 / rts
```

Offsets (`$22b8c`, 17 words, raw `xxd -s 0x22b8c -l 34`): `0000 ffc0 0001 0040 ffff ffc1 0041 003f ffbf ff80 0002 0080 fffe ff82 0082 007e ff7e` = 0, -64, 1, 64, -1, -63, 65, 63, -65, -128, 2, 128, -2, -126, 130, 126, -130: the cell, its 8 neighbours, then 8 cells at distance 2. Nothing writes the table: its 18 references are all `lea $22b8c` followed by reads (`m68dis --xref 22b8c`: `$f3a2`..`$1d09e`, e.g. `00f3a8 move.w (a0,d0.l),-(a7)`).

- In: two words on the stack (not changed).
- Out:
  - `d0.l` = 0, or 65 + 15 x (good cells after the first) - 15 x (rock cells) when that is 35 or more, or `$bea` for 305. The high word is 0 (`clr.l d0` in the last `$181d6`).
  - `$3b040.w`: when `map_bk2[cell]` = `$2a`, the number of cells among the first 9 that carry `$29..$2c` (the centre counts itself); otherwise 0. Read at `00e98e cmpi.w #$9,$3b040.l` only.
  - `$37ef4.w`: 1 when a flat (`$f`) cell was counted before the routine ended, else 0. Read at `00e554` and `00e97a` (`move.w $37ef4.l,d0`) only.
  - Both words are left as they stand on the two early returns (partial counts).
  - CCR: N, Z of `d0.w`, V = C = 0. X: 0 after the full scan (`addi.w #1,d5`) and after the `$182cc` return (`add.w d2,d3` with d3 = 0); after the `$1830e` return it is the carry of the last add executed: `addi.w #$f,d4` on a good cell, `add.w d2,d3` (= 1 exactly when the offset is negative) on other land.
- Preserved: `d1-d6`, `a0-a2`, `a5`. Not touched: `d7`, `a3`, `a4`, `a6`.
- RAM read: the two arguments, the 17 table words, `map_blk[cell + off]` (twice per cell, once more in `$181d6`), `map_bk2[cell + off]`, `map_bk2[cell]`.
- RAM written: `$3b040`, `$37ef4`, and 72 bytes of dead stack below the caller's SP.
- Note on the first cell: the offset is 0, so `$181d6` returns 0 without looking; a cell that is itself water or rock falls to `$182c8` and returns 0.

### `$20796`: 32 x 32 multiply of the C compiler (368 call sites)

```
020796  link.w a6,#0 / movem.l d0-d3/d7,-(a7) / clr.w d7
0207a0  move.l $8(a6),d1 / bge.b $207aa / moveq #1,d7 / neg.l d1
0207aa  move.l $c(a6),d2 / bge.b $207b6 / eori.w #1,d7 / neg.l d2
0207b6  move.l d1,d3 / andi.l #$ffff0000,d3 / beq.b $207c4 / swap d3 / mulu.w d2,d3
0207c4  move.l d2,d0 / swap d0 / tst.w d0 / beq.b $207d0 / mulu.w d1,d0 / add.w d0,d3
0207d0  swap d3 / clr.w d3 / mulu.w d1,d2 / add.l d2,d3
0207d8  tst.w d7 / beq.b $207de / neg.l d3
0207de  move.l d3,$c(a6) / movem.l (a7)+,d0-d3/d7 / unlk a6
0207e8  move.l (a7)+,(a7) / tst.l $4(a7) / rts
```

- In: two longs on the stack. Out: their product modulo 2^32 in place of the second; the first is removed (`move.l (a7)+,(a7)` moves the return address over it). CCR = `tst.l` of the product; X from the last of `add.l d2,d3` / `neg.l d3`.
- Preserved: every register. RAM written: the result slot and 24 bytes of dead stack.
- For two operands in 0..65535 the path is: both `bge` taken, both high-word tests zero, `d3` = 0, `mulu.w d1,d2`, `add.l d2,d3` (no carry: X = 0), no `neg`.

## 2. The study's claim, checked on the real routine

The claim (`algorithms.md`, D): "same result in 1,073 of 1,078 building-turns", from a Python model that had never been compared with the routine.

**The model is right.** `work/scratch/landscore/lslib.py` holds a model written from the listing above; `exhaust.py` runs the real `$18244` inside Hatari for every cell and both owners on the RAM of each snapshot and compares the model on the same RAM (`model_vs_orig` in the table of section 5: 0 differences in 114,286 inputs, including random maps and garbage arguments).

**The claim holds.** `gates.py trace` redirects `$18244` to a stub that calls the original and logs every call (return address, turn, cell, `d0`, owner, `$3b040`, `$37ef4`). For the per-building call (`$e294`, return address `$e29a`), the three outputs were compared with the same building's outputs one turn earlier:

```
{'snap': 'busy_castles', 'first_turn': 777, 'records': 6520, 'dropped': 0, 'whole_turns': 83, 'calls_by_return_address': {'$e29a': 6442, '$f416': 71, '$1031a': 6, '$10c12': 1}, 'building_turns_with_previous': 6210, 'same_3_outputs_as_previous_turn': 6187, 'same_d0_as_previous_turn': 6201, 'no_previous_turn': 81, 'duplicate_keys': 0, 'calls_per_turn': 77.6}
{'snap': 'busy_quake_volcano', 'first_turn': 2043, 'records': 7296, 'dropped': 109, 'whole_turns': 82, 'calls_by_return_address': {'$e29a': 7177, '$f416': 102, '$1031a': 14, '$10c12': 3}, 'building_turns_with_previous': 6933, 'same_3_outputs_as_previous_turn': 6926, 'same_d0_as_previous_turn': 6928, 'no_previous_turn': 93, 'duplicate_keys': 0, 'calls_per_turn': 87.9}
```

6,187 of 6,210 (99.63%) and 6,926 of 6,933 (99.90%) building-turns repeat the previous turn's result; the study said 99.54%. (`dropped`: the 102 KB log filled during the last turn of the second run; only whole turns are counted.) 98.8% of all calls come from the per-building site `$e294`.

## 3. Designs considered

| Design | Cost per call after | Gain (share of the unpatched busy frame) | What must be right |
|---|---|---|---|
| A. Inline rewrite: `$181d6` folded into `$18244`, unrolled over the 17 offsets | 1,626 cycles measured (from 10,407) | 27%: 8,781 cycles x 77 calls of a 2.52M-cycle turn (its share goes from 31.8% to 7.3% of a shorter turn) | the routine itself, provable from two listings and testable over its whole input domain (8,192 arguments x map contents) |
| B. A + cache per (owner, cell), invalidated by every writer of `map_blk` / `map_bk2` within the pattern | about 170 on a hit [INFERENCE: instruction count] | about 4 points more: 77 calls x about 1,450 cycles = 0.11M cycles, 6.5% of the 1.7M-cycle patched turn | A, plus hooks on 41 store sites in 14 routines and on the load (section 6), each replacing a `lea` + store pair in compiled code, and the proof that no writer was missed |
| C. Incremental update on terrain change (keep each building's score, adjust on writes) | as B | as B | as B, plus the early-exit rules (first building in table order, partial `$3b040` / `$37ef4`) reproduced by deltas: not practical |
| D. Exact tables (per-cell class, per-cell score) | no better than A: the inner test is already two byte compares | none over A | |

**Chosen: A.** It takes 27 of the 33 points with no state of its own, so there is nothing to invalidate and no writer list to trust. B is the only way to most of what is left (7.3% of the patched turn); its hook list is ready in section 6 if the fixed 5 turns/s tick turns out to need it. A missed writer in B would be a silent, rare divergence; a mistake in A shows up at once in the exhaustive test.

`$181d6` itself is left as it is. After `pop_land_score` it is called about 0.75 times per building-turn by other code (5,285 calls against 7,008 score calls in one profile) and costs 1.1 to 1.3% of the patched frame. A version without `link` / `movem` was written on paper at 262 cycles against 346: a gain of 0.3% of the frame, not worth a 110-byte site.

## 4. The new code

### `pop_land_score` (site `$18244`, 8 bytes -> `jmp $c0000` + `nop`; blob `$c0000`-`$c0fd1`)

The path is chosen from the two arguments and `map_bk2[cell]`:

| Input | Path | Share of calls (gate a) |
|---|---|---|
| owner > 1, or cell outside 0..4095 | the original routine: the displaced `link` / `movem`, then `jmp $1824c` | 0 |
| cell at 2 or more from every edge | 17 cells unrolled (`CELL` macro, `d16(a0)` addressing, `a0` = `&map_blk[cell]`, `map_bk2` at `+$56aa`) | 88% |
| the same with `map_bk2[cell]` = `$2a` | offsets 1..8 by the `CCELL` macro (counts `$29..$2c`), then the common offsets 9..16 | (in the 88%) |
| cell within 2 of an edge | the same unrolled code, each offset guarded by one bit of a mask (`ECELL` macro) | 12% |
| cell within 2 of an edge with `map_bk2[cell]` = `$2a` | the original loop with `$181d6` inlined | 0 in play (17 good cells cannot exist there) |

Why each path returns what the original returns:

1. **No edge test can fail for an interior cell.** The offsets are dx, dy in -2..2 (table above; `$181d6` derives dx from `offset & $3f`, values 62, 63, 0, 1, 2 -> -2, -1, 0, 1, 2). For x and y in 2..61 both range tests of `$181d6` pass, so its result depends on the tile only: 3 for 0, 2 for `$2f`, else 0. The entry test `(cell - $80) <u $f00` is y in 2..61, and `((cell & $3f) - 2) <=u 59` is x in 2..61.
2. **Order of the tile tests.** The original tests water and rock first (inside `$181d6`), then own field, then flat. The new code tests field and flat first. The four values 0, `$2f`, `$f` and `$1f + owner` are distinct when owner is 0 or 1, which the entry guarantees (`cmpi.w #1,4(sp)` / `bhi orig`), so the order cannot change the outcome.
3. **The `tst.w d4` / `move.w #$32,d4` step is dead after the first cell.** The first cell either returns 0 or sets the score to 50 + 15 = 65. From there the score changes by +15 or -15, so it is 65 + 15j, which is never 0. The unrolled code therefore starts at 65 and adds or subtracts 15.
4. **Objects.** `tst.b` first: a zero byte fails both original tests (`ble $20`). Non-zero bytes go through the original's two signed compares. With the centre not `$2a` the castle branch `$182e0` is never taken; with the centre `$2a` it is taken for k < 9 only, which is the `CCELL` chain.
5. **Outputs on every exit.** `$3b040` is cleared on entry and incremented in memory as in the original; the flat flag lives in `d1` and is written to `$37ef4` on all four exits (three "return 0" exits and the tail), so the partial values of the early returns are kept.
6. **CCR.** Tail: `moveq #0,d0` / `add.w d3,d0` gives `d0.l`, N, Z, and V = C = X = 0. Return 0 on a good cell: `moveq #0,d0`, X left from `add.w d2,d3` (same operands as the original's `addi.w #$f,d4`). Return 0 on other land: `move.w #$14,ccr` (X = Z = 1) for a negative offset, `sub.l d0,d0` (Z, X = 0) for a positive one, as the original's `add.w d2,d3` leaves it. Return 0 on the cell itself: X = 0.
7. **The edge mask.** `$181d6` accepts `cell + offset` when 0 <= x + dx <= 63 and, given that, 0 <= cell + offset <= 4095 is 0 <= y + dy <= 63. So "offset k stays on the map" is `mx[x] & my[y]`, two 64-word constant tables at the end of the blob (bit 15 = offset 1). A skipped offset is what the original does with result 1 (`bne $18318`). The tables were compared with the model of `$181d6` for all 4,096 cells x 16 offsets (0 differences), and one wrong bit is caught by the exhaustive test (mutant below).
8. **Registers.** `d1-d5/a0` are saved and restored (`movem`, no flags); `d6`, `a1`, `a2`, `a5` are not touched on the unrolled paths.
9. **Stack.** The new code writes 24 bytes below the caller's SP instead of 72. Nothing but dead stack differs (gate b lists `$3f2..`-`$3f4b5`, below SP = `$3f4f0`).

The X flag is reproduced although nothing reads it: a scan of `$af40`-`$21100` finds `addx` / `subx` / `negx` / `roxl` / `roxr` / `abcd` / `sbcd` byte patterns only at `$152e8`-`$166bc`, `$17b1a`-`$180c4` and `$1fd8a` (tables and hand-written routines), none in the compiled callers at `$d6f2`-`$10c50`.

### `pop_land_mul` (site `$20796`, 8 bytes -> `jmp $c1000` + `nop`; blob `$c1000`-`$c1033`)

```
tst.w 4(sp) / bne slow / tst.w 8(sp) / bne slow     ; both operands 0..65535?
move.l d0,-(sp) / moveq #0,d0 / add.w 10(sp),d0     ; first operand; X = 0
mulu.w 14(sp),d0 / move.l d0,12(sp)                 ; product over the second operand
move.l (sp)+,d0 / move.l (sp)+,(sp) / tst.l 4(sp) / rts
slow: link.w a6,#0 / movem.l d0-d3/d7,-(sp) / jmp $2079e
```

For two operands below 65536 the original computes exactly `mulu` of the low words with no sign fix-up and X = 0 (path listed in section 1); the exit sequence is the original's. Every other operand pair runs the original code. In the busy scenes every call takes the fast path (62,026 of 62,026).

## 5. Gates

All runs: snapshot restored, patch applied when the main loop reaches `$b800` on a fixed turn, no input afterwards. Two unpatched runs of the same snapshot are identical in the whole 1 MB (control below), so runs can be compared byte for byte.

### Exhaustive: original vs new vs model (`exhaust.py`, raw `work/gates/exhaust.txt`)

A stub calls the original and the new routine (blob loaded, site not hooked) for every input and compares `d0.l`, CCR (5 bits), `$3b040`, `$37ef4` and all of `d1-d7/a0-a6` inside the emulator. `fuzz` = `map_blk` / `map_bk2` overwritten with random tiles and objects (mode 0 hostile, 1 mostly good land with castle clusters, 2 very few defects, 3 rock and water). Lines 3 and 4 use garbage arguments (owners 2, `$10`, `$e1`, `$f0`, `$ff`; cells -140..-1 and 4096..4240).

```
{'snap': 'busy_castles', 'turn': 777, 'fuzz': None, 'ccr_in': 0, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 191, 'castle': 11}
{'snap': 'busy_quake_volcano', 'turn': 2043, 'fuzz': None, 'ccr_in': 31, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 173, 'castle': 10}
{'snap': 'busy_castles', 'turn': 777, 'fuzz': None, 'ccr_in': 31, 'inputs': 3895, 'expected': 3895, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 500, 'castle': 0}
{'snap': 'busy_quake_volcano', 'turn': 2043, 'fuzz': (7, 0), 'ccr_in': 0, 'inputs': 3895, 'expected': 3895, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 89, 'castle': 0}
{'snap': 'busy_castles', 'turn': 777, 'fuzz': (1, 0), 'ccr_in': 31, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 56, 'castle': 0}
{'snap': 'busy_castles', 'turn': 777, 'fuzz': (2, 1), 'ccr_in': 0, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 104, 'castle': 0}
{'snap': 'busy_quake_volcano', 'turn': 2043, 'fuzz': (3, 1), 'ccr_in': 16, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 203, 'castle': 0}
{'snap': 'busy_quake_volcano', 'turn': 2043, 'fuzz': (4, 0), 'ccr_in': 15, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 100, 'castle': 0}
{'snap': 'genesis_start', 'turn': 173, 'fuzz': None, 'ccr_in': 0, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 132, 'castle': 0}
{'snap': 'busy_castles', 'turn': 777, 'fuzz': (5, 2), 'ccr_in': 31, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 1542, 'castle': 1}
{'snap': 'busy_quake_volcano', 'turn': 2043, 'fuzz': (6, 2), 'ccr_in': 0, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 1451, 'castle': 5}
{'snap': 'busy_castles', 'turn': 777, 'fuzz': (8, 2), 'ccr_in': 21, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 1563, 'castle': 1}
{'snap': 'busy_quake_volcano', 'turn': 2043, 'fuzz': (9, 1), 'ccr_in': 10, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 165, 'castle': 1}
{'snap': 'busy_castles', 'turn': 777, 'fuzz': (10, 3), 'ccr_in': 0, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 434, 'castle': 0}
{'snap': 'busy_quake_volcano', 'turn': 2043, 'fuzz': (11, 3), 'ccr_in': 31, 'inputs': 8192, 'expected': 8192, 'emu_mismatch': 0, 'reg_faults': 0, 'py_orig_vs_new': 0, 'model_vs_orig': 0, 'nonzero': 401, 'castle': 0}
paths covered 112 of 112; missing []
RESULT PASS
```

"paths" = every exit of the unrolled chains: (interior | interior castle | edge) x (cell itself not good; building at each offset 1..16 on a good cell and on other land; full scan giving 0, a score, `$bea`), plus the exits of the edge-castle loop (`lslib.all_paths`).

### (a) Every call of N busy frames (`gates.py a`, raw `work/gates/gate_a.txt`)

`$18244` and `$20796` are redirected to a stub that runs the new code and the original with the same arguments, registers and CCR, compares outputs (as above; for the multiply: product, CCR, all 15 registers), and lets the game continue with the original's result. 150 turns per snapshot.

```
{'snap': 'busy_castles', 'turns': '777..926', 'score_calls': 11426, 'score_mismatch': 0, 'score_reg_faults': 0, 'score_unrolled': 10108, 'score_edge': 1318, 'mul_calls': 29624, 'mul_mismatch': 0, 'mul_reg_faults': 0, 'mul_fast_path': 29624, 'logged': 0, 'first_records': []}
{'snap': 'busy_quake_volcano', 'turns': '2043..2192', 'score_calls': 13160, 'score_mismatch': 0, 'score_reg_faults': 0, 'score_unrolled': 11510, 'score_edge': 1650, 'mul_calls': 32402, 'mul_mismatch': 0, 'mul_reg_faults': 0, 'mul_fast_path': 32402, 'logged': 0, 'first_records': []}
```

### (b) Whole-world RAM, turn by turn (`gates.py b`, `bfx`, `bctl`; raw `work/gates/gate_b*.txt`)

Both runs carry the blobs and a stub on the main loop's `jsr $db8a` that hashes, before every turn, all game data and bss `$21100`-`$3d7ff` and the loaded data `$3f600`-`$4f4ff` (two 32-bit values: sum of longs, and rotate-xor of longs) and logs {turn, RNG seed `$3d56c`, sum, rox}. Only the patched run has the two sites changed. At three turns the complete 1 MB is saved from both runs and compared.

Excluded from the hash, and why:

- `$24990`-`$249a3`, the sample player's state. It is advanced and cleared by the timer-A interrupt in real time (`017188 move.l $2499c.l,d3` ... `0171ba move.l d3,$2499c.l`; end of sample `01716a clr.b $24991.l`, `017162 move.w #$0,$249a0.l`), and the patched run reaches the same turn sooner. Measured first with nothing excluded: 515 of 521 hashes equal, the six others in two groups of three turns (831-833, 1151-1153), and the dumps at those turns differ only in `$2499e`-`$2499f` inside the hashed ranges (`831 [('$2499f-$2499f', '4a', '97')]`, `832 [('$2499e-$2499f', '1124', '0f6a')]`, `833 [('$2499e-$2499f', '1f21', '1b54')]`, `830 []`, `834 []`). A dump taken while a sample played in one run only shows the other bytes of the block (`$24991`, `$249a1`).
- The stack (`$3d800`-`$3f5ff`), the screens and everything outside the two ranges are not hashed; they are compared at the checkpoints.

Excluded from the checkpoint comparison: nothing. Every differing range is listed and explained; the patch's own ranges are the two sites (the blobs `$c0000`-`$c0fd1` and `$c1000`-`$c1033` are loaded in both runs and are equal).

```
{'snap': 'busy_castles', 'pair': 'U vs P', 'turns': '783..1303', 'turn_records': 521, 'identical_records': 521, 'first_different_turn': None, 'hash_ranges': ['$21100-$2498f', '$249a4-$3d7ff', '$3f600-$4f4ff'], 'rng_seed_first_last': ('$4142', '$00ec'), 'vbl_at_end': (40309, 37655), 'sp_at_checkpoints': ['$3f4f0']}
  checkpoint turn 784: 209 differing bytes, 0 unexplained ranges
  checkpoint turn 1043: 328 differing bytes, 0 unexplained ranges
  checkpoint turn 1303: 284 differing bytes, 0 unexplained ranges
{'snap': 'busy_quake_volcano', 'pair': 'U vs P', 'turns': '2049..2569', 'turn_records': 521, 'identical_records': 521, 'first_different_turn': None, 'hash_ranges': ['$21100-$2498f', '$249a4-$3d7ff', '$3f600-$4f4ff'], 'rng_seed_first_last': ('$0120', '$2b54'), 'vbl_at_end': (59919, 56641), 'sp_at_checkpoints': ['$3f4f0']}
  checkpoint turn 2050: 140 differing bytes, 0 unexplained ranges
  checkpoint turn 2309: 364 differing bytes, 0 unexplained ranges
  checkpoint turn 2569: 384 differing bytes, 0 unexplained ranges
```

One checkpoint in full (the others list the same ranges; `work/gates/gate_b.txt`):

```
  checkpoint turn 1043: 328 differing bytes, 0 unexplained ranges
    $464-$469 (4): TOS _vbclock/_frclock
    $4bc-$4bd (2): TOS _hz_200
    $2b89-$2b89 (1): TOS RAM below _membot $a84e
    $378b-$378b (1): TOS RAM below _membot $a84e
    $5fad-$5faf (3): TOS RAM below _membot $a84e
    $16d2c-$16d2d (2): game VBL counter (addq.l #1 at $16dde)
    $18245-$1824b (6): site pop_land_score
    $20797-$2079d (6): site pop_land_mul
    $3f2d4-$3f4b5 (303): dead stack below SP=$3f4f0
```

Other ranges seen at some checkpoints: `$2005e` (the ACIA handler's packet byte counter: `020036 subq.b #$1,$2005e.l`), `$90d`-`$938` (the BIOS register save area: `_savptr` `$4a2` = `$0000093a`), `$24991`-`$249a1` (sample player state, above). The TOS bytes at `$ea4`, `$2b88`, `$378b`, `$5fad` are below `_membot` and were not identified [INFERENCE: timers of the TOS VBL and 200 Hz handlers; they differ by the elapsed real time, as `_hz_200` does].

With effects: the game's own commands written for player 0 at fixed turns in both runs (manna, then earthquake at +40 and +200, volcano at +110 and +260, flood at +400). `peep_slots_at_checkpoints` = (turn, used peep slots, rock cells, water cells) in each run: the flood leaves 6 and 9 peeps. Raw `work/gates/gate_b_effects.txt`:

```
{'snap': 'busy_castles', 'pair': 'U vs P', 'effects_at': [823, 893, 983, 1043, 1183], 'peep_slots_at_checkpoints': [[(784, 96, 35, 2755), (1043, 109, 45, 2698), (1303, 6, 18, 3863)], [(784, 96, 35, 2755), (1043, 109, 45, 2698), (1303, 6, 18, 3863)]], 'turns': '783..1303', 'turn_records': 521, 'identical_records': 521, 'first_different_turn': None, 'hash_ranges': ['$21100-$2498f', '$249a4-$3d7ff', '$3f600-$4f4ff'], 'rng_seed_first_last': ('$4142', '$6138'), 'vbl_at_end': (39459, 37226), 'sp_at_checkpoints': ['$3f4f0']}
  checkpoint turn 784: 209 differing bytes, 0 unexplained ranges
  checkpoint turn 1043: 343 differing bytes, 0 unexplained ranges
  checkpoint turn 1303: 316 differing bytes, 0 unexplained ranges
{'snap': 'busy_quake_volcano', 'pair': 'U vs P', 'effects_at': [2089, 2159, 2249, 2309, 2449], 'peep_slots_at_checkpoints': [[(2050, 126, 37, 2387), (2309, 123, 48, 2269), (2569, 9, 30, 3840)], [(2050, 126, 37, 2387), (2309, 123, 48, 2269), (2569, 9, 30, 3840)]], 'turns': '2049..2569', 'turn_records': 521, 'identical_records': 521, 'first_different_turn': None, 'hash_ranges': ['$21100-$2498f', '$249a4-$3d7ff', '$3f600-$4f4ff'], 'rng_seed_first_last': ('$0120', '$5ebb'), 'vbl_at_end': (58668, 56263), 'sp_at_checkpoints': ['$3f4f0']}
  checkpoint turn 2050: 140 differing bytes, 0 unexplained ranges
  checkpoint turn 2309: 300 differing bytes, 0 unexplained ranges
  checkpoint turn 2569: 289 differing bytes, 0 unexplained ranges
```

Control, two unpatched runs (`work/gates/gate_b_control.txt`): 521 of 521 records identical and 0 differing bytes in the whole 1 MB at all three checkpoints, on both snapshots.

### Negative controls (`work/gates/mutants.txt`)

A gate that cannot fail proves nothing, so each was run on a deliberately broken blob:

```
exhaust.py, one bit of mx[0] wrong:            'emu_mismatch': 17, 'py_orig_vs_new': 17
gates.py a, first score 64, mulu on the wrong word: 'score_calls': 2343, 'score_mismatch': 2095, 'mul_calls': 5653, 'mul_mismatch': 3083
gates.py b, first score 64, 120 turns:         'turn_records': 121, 'identical_records': 1, 'first_different_turn': 784
```

### (c) Turns per second at 8 MHz (`gates.py c`, raw `work/gates/gate_c.txt`; `percall.py`, raw `work/gates/percall.txt`)

`world_rate($3c506)` over 2,000 VBLs, then a 1,000-VBL profile; patches applied at the same turn in every run.

```
{'snap': 'busy_castles', 'set': 'unpatched', 'site_18244': '4e55000048e77ee0', 'vbls': 2000, 'flips': 127, 'fps': 3.175, 'turns_per_sec': 3.174, 'pct_181d6': 18.78, 'pct_18244': 13.83, 'pct_blob_c0000': 0.0, 'pct_20796': 3.16, 'pct_blob_c1000': 0.0}
{'snap': 'busy_castles', 'set': 'pop_land_score', 'site_18244': '4ef9000c00004e71', 'vbls': 2000, 'flips': 184, 'fps': 4.6, 'turns_per_sec': 4.585, 'pct_181d6': 1.53, 'pct_18244': 0.05, 'pct_blob_c0000': 7.05, 'pct_20796': 4.35, 'pct_blob_c1000': 0.0}
{'snap': 'busy_castles', 'set': 'pop_land_mul', 'site_18244': '4e55000048e77ee0', 'vbls': 2000, 'flips': 130, 'fps': 3.25, 'turns_per_sec': 3.244, 'pct_181d6': 19.28, 'pct_18244': 14.14, 'pct_blob_c0000': 0.0, 'pct_20796': 0.1, 'pct_blob_c1000': 1.61}
{'snap': 'busy_castles', 'set': 'both', 'site_18244': '4ef9000c00004e71', 'vbls': 2000, 'flips': 188, 'fps': 4.7, 'turns_per_sec': 4.727, 'pct_181d6': 1.68, 'pct_18244': 0.05, 'pct_blob_c0000': 7.17, 'pct_20796': 0.14, 'pct_blob_c1000': 2.22}
{'snap': 'busy_quake_volcano', 'set': 'unpatched', 'site_18244': '4e55000048e77ee0', 'vbls': 2000, 'flips': 119, 'fps': 2.975, 'turns_per_sec': 2.989, 'pct_181d6': 19.1, 'pct_18244': 14.13, 'pct_blob_c0000': 0.0, 'pct_20796': 3.03, 'pct_blob_c1000': 0.0}
{'snap': 'busy_quake_volcano', 'set': 'pop_land_score', 'site_18244': '4ef9000c00004e71', 'vbls': 2000, 'flips': 172, 'fps': 4.3, 'turns_per_sec': 4.286, 'pct_181d6': 1.36, 'pct_18244': 0.06, 'pct_blob_c0000': 8.09, 'pct_20796': 4.69, 'pct_blob_c1000': 0.0}
{'snap': 'busy_quake_volcano', 'set': 'pop_land_mul', 'site_18244': '4e55000048e77ee0', 'vbls': 2000, 'flips': 122, 'fps': 3.05, 'turns_per_sec': 3.035, 'pct_181d6': 19.35, 'pct_18244': 14.33, 'pct_blob_c0000': 0.0, 'pct_20796': 0.09, 'pct_blob_c1000': 1.53}
{'snap': 'busy_quake_volcano', 'set': 'both', 'site_18244': '4ef9000c00004e71', 'vbls': 2000, 'flips': 175, 'fps': 4.375, 'turns_per_sec': 4.402, 'pct_181d6': 1.33, 'pct_18244': 0.06, 'pct_blob_c0000': 8.33, 'pct_20796': 0.15, 'pct_blob_c1000': 2.42}
```

```
busy_castles unpatched: profile 155493780 cycles; $18244 calls 4747, 21412380 cycles own code = 13.77% ; $181d6 calls 84335, 29250756 cycles = 18.81% (346 per call) ; $20796 calls 12825, 390 cycles/call = 3.22%
busy_castles patched:   profile 155494732 cycles; $18244 calls 7008 (interior 6105, edge 873), 1626 cycles/call = 7.33% ; other $181d6 calls 5285 = 1.11% ; $20796 calls 18537, 208 cycles/call = 2.49%
busy_quake_volcano unpatched: profile 155557924 cycles; $18244 calls 5147, 23544472 cycles own code = 15.14% ; $181d6 calls 90527, 31408764 cycles = 20.19% (346 per call) ; $20796 calls 12490, 390 cycles/call = 3.14%
busy_quake_volcano patched:   profile 155547480 cycles; $18244 calls 7678 (interior 6718, edge 953), 1689 cycles/call = 8.34% ; other $181d6 calls 6068 = 1.27% ; $20796 calls 18588, 208 cycles/call = 2.50%
```

Reading: unpatched busy_castles, the score's own code is 4,511 cycles per call, and of the 84,335 step tests 80,699 (17 x 4,747) are its own, so one score costs 4,511 + 17 x 346.8 = 10,407 cycles; patched, 1,626. The multiply's share of the frame looks larger in the "score only" rows because the frame got shorter, not because it got slower. Turns per second are whole VBLs per frame (15.7 -> 10.6 VBLs per turn), so small gains can vanish in the rounding of one frame; the cycle shares are the stable figure.

## 6. Writers of the score's inputs (for design B; not used by the patches)

The inputs are `map_blk` (`$36eb6`), `map_bk2` (`$3c560`), the constant table `$22b8c` and the two arguments. Method (`work/scratch/landscore/writers.py`, raw output `work/gates/writers.txt`): every 32-bit constant in `$af40`-`$21100` that points into either map is listed; only the two base addresses are real operands (`$36eb6` 69 times, `$3c560` 40 times). The seven other matches are instruction pairs that happen to spell such a number (`0181fa cmp.w #$3,d3` + `6f04`, `010070` / `0111d6` + `6f14`, `01e9ae cmpi.w #$3,d7` + `6fda`, `00d826 and.w #$3,d1` and `00dc5a muls.w #$3,d1` + `d041`, `00fa52 muls.w #$3,d0` + `d06e`), so no code holds a pointer to the inside of a map. The bases appear as `lea base,aN` (100), `pea base` (6), `movea.l #base,aN` (2, the renderer `$143b2` / `$143be`, which has no store through `a1` / `a2` up to `$1457e`) and `subi.l #$36eb6,d6` (1, `$14450`). Each `lea` is followed to the first use of the register: 40 are stores, listed below; 47 are reads; 2 are the land score's own; 11 load a pointer and read through it at once (`move.b (a0),d0`), except `$dfea`, which keeps the pointer in a local and stores through it later (`$ea12`, found by reading every use of `-$8(a6)` in `$db8a`: `$e148`, `$e174`, `$e9d8` read, `$ea0e` stores).

| Routine | What it is | `map_blk` stores | `map_bk2` stores |
|---|---|---|---|
| `$bc12` | clear the world | `00be80 clr.b (a0,d7.w)` | `00be94 clr.b (a0,d7.w)` |
| `$c12c` | heights -> tiles, per rectangle | `00c1fe`, `00c26a move.b d0,(a0,d1.w)` | `00c282 clr.b (a0,d0.w)` |
| (`$c2b8`..) `$c3ec` | [INFERENCE: tile fix-up after an edit] | `00c3ec move.b d0,(a0,d5.w)` | |
| `$db8a` | peep loop: a swamp tile used up | `00ea12 move.b #$f,(a0)` through the pointer saved at `00dff4 move.l d0,-$8(a6)` | |
| `$103a4` | building type and its fields | `010430`, `01049c`, `0105b2 move.b #$f,(a0,d6.w)`; `010536`, `010624 move.b d0,(a0,d6.w)` | `010402`, `01046e`, `010584`, `0105f4 clr.b (a0,d6.w)`; `0104b6 clr.b (a0,d0.w)`; `010506 move.b d0,(a0,d6.w)`; `01066c move.b d0,(a0,d1.w)` |
| `$108f6` | [INFERENCE: fight / fire] | `010ac2`, `010b5a move.b #$42,(a0,d0.w)` | `010a8a`, `010bb2 addi.b #$15,(a0,d0.w)` |
| `$112ae` | [INFERENCE: place an object] | | `01137c move.b d0,(a0,d1.w)`; `0113ca move.b d0,(a0,d7.w)` |
| `$1140c` | [INFERENCE: remove] | `011448 clr.b (a0,d7.w)` | `01143e clr.b (a0,d7.w)` |
| `$1267a` | volcano | `0128ee move.b #$2f,(a0)` | `01290a clr.b (a0)` |
| `$12a52` | swamp | `012bc8 move.b #$35,(a0)` | |
| `$12e44` | first objects of a world | `012f6e move.b d0,(a0)` | `012fa0 move.b d0,(a0)` |
| `$12fc2` | once per turn, before the peep loop | `013290 move.b #$35,(a0,d0.w)`; `0132da move.b d0,(a0,d1.w)` | `01320e move.b d0,(a0,d1.w)` |
| `$1363a` | computer player | `01373e addq.b #$1,(a0,d0.w)` | |
| `$1e750` | command execution | `01edd2 move.b d0,(a0)`; `01ee22 move.b #$f,(a0,d0.w)` | `01ed36 move.b d0,(a0)`; `01ee52 clr.b (a0,d0.w)`; `01eec8 clr.b (a0)` |
| `$1e184` | load a saved game | `01e28c pea $36eb6` -> `jsr $206d6` with `move.w #$3f,-(a7)` (Fread, 4,096 bytes) | `01e2ac pea $3c560`, the same |

Not writers: the save routine `$1dbd6` (`01dc98` / `01dcb0 pea` -> `$1e14e`, a word-sum loop `01e166 move.w (a0,d0.l),d0`; `01dd76` / `01dda0 pea` -> `$206d6` with `#$40`, Fwrite).

Total: 21 stores into `map_blk` in 13 routines, 20 into `map_bk2` in 10, plus the load. The study's "about 60 code sites write `map_blk`" counted references, not stores. Limits of the method: it is static; a store through a pointer that travels through a variable would be missed unless found by hand as `$ea12` was [INFERENCE that there is no other]. A cache built on this list would need its own running check (recompute on every hit and compare, through play with every effect, a load and a new world) before it could be trusted.

## 7. What was not done

- `$181d6` for its other callers (section 3): 0.3% of the frame.
- Design B (section 3).
- Cold boots and other machines: the patches are plain 68000 code with no hardware access and no self-modification; they were applied live to 1 MB STE snapshots only. `tools/poppatch.py verify` passes with them and `poppatch.py live --only pop_land_score pop_land_mul` produces the same site and blob bytes the gates used (compared in this session: both blobs and both sites identical). A cold boot of a build that contains them is the delivery slice's gate.
- The dead-stack difference (24 bytes written instead of 72, and 4 instead of 24 for the multiply) could matter only to code that reads an uninitialised local. Gate b found no effect over 2 x 521 turns plus 2 x 521 with effects [INFERENCE that none exists elsewhere].

## 8. Files

- `patches/pop_land_score.s`, `patches/pop_land_mul.s`.
- `work/scratch/landscore/lslib.py` (patch parser, models, `Run.at_turn`), `exhaust.s` / `exhaust.py`, `trace.s`, `shadow.s`, `cksum.s`, `gates.py`, `percall.py`.
- `work/gates/*.txt`: raw outputs quoted above.
- Trap met on the way: a debugger write to the operand of the instruction at PC is too late (68000 prefetch); `jsr $db8a` at `$b806` must be redirected from a breakpoint on an earlier instruction (`$b800`).
