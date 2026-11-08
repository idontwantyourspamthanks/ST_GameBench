# Edge walker setup rewrite (patches p4_walk, p4_walk_c4, p4_walk_tab, p4_walk_ret)

Apply together: `--only p4_walk p4_walk_c4 p4_walk_tab p4_walk_ret`. Blob $B3C00-$B3D75 (374 B of the $400 range; no tables).

## What changed
- `$3c5e2` and `$3c5c4` (6 B each) and the `$501a` jump slot jump into the blob. The old setup `$3c5c4-$3c689` is now dead. The 201 unrolled bodies `$3c68a-$3d313` are untouched. The blob enters them via `jmp (a1)` with the same register state: a0 = table+4y, a1 = `$3d30a-16*dy`, d0 = frac(I), d1 = 2*int(I)|$E1, d2 = int(I)/2|7, d3 = $8000, d4 = $4_0000|p, d5 = p>>1, d6 = $001E, d7 = $xxxxFFF8.
- `mulu #$140` becomes `y + 4y` then `asl.w #6` (exact for every 16-bit y, mod 2^16 like mulu). The blob needs no table.
- Registers saved/restored: d2-d3/d5-d7/a0-a1/a3 (8 regs, `movem` mask $0BEC at `$3d316`). Not saved: d0, d1, d4 (dead after the call in every caller) and a2 (the blob never touches it).
- `lea $17a66` is now a3, used as the base for T[], ymin `$180ee`=$688(a3) and ymax `$180ec`=$686(a3). `cmp`/`move` use d16(an) instead of abs.l (12 vs 16 and 16 vs 20 cy).
- The fwd/bwd paths are separate macro expansions (no `exg`, `addq` cancels in dx). The positive-dx and negative-dx tails are also duplicated, so no `bra` is taken.
- `addi.l #$1400000` becomes `swap` + `add.w #320`. Only the high word changes, and d0 was already copied.
- Constants: moveq #4/swap, moveq #$1e, moveq #-8, or.w #7 (3-4 cy each).
- dy=0: `beq` to a local restore. The old `$3d31a` handler is `bra.w $3d3a2` (dead code after it), so no entries are written, as before. min/max are not updated, as before.

## Caller register proof (d0, d1, d4, a2 preserved or dead)
Callers: `jsr $501a` at `$1fac6,$1fb0c,$1fb86,$1fba8,$1fbba` (the same code is duplicated at `$9f00c...`), and `bsr.w $3c5e2` at `$3bbb4,$3bc48`.
- `$1fac6`: after return `move.w (a6)+,d4` (d4 dead), loop `$1fabc` reloads d0,d1 from d2,d3 (d2,d3 preserved) and `movem.w (a4,d4.w),d2-d3`.
- `$1fb0c`: d0-d3 loaded by `movem.w $1fde8.l,d0-d3`. After return: `move.w d5,d4`, `move.w (a6)+,d5`, so d5 is live (saved), d0,d1,d4 dead.
- `$1fb86/$1fba8`: after return `move.w d2,d0; move.w d3,d1`. d2,d3 are saved. d6,d7 are live in `$1fb4c` (saved). d0 is reloaded before use at `$1fb94/$1fb9a`.
- `$1fbba`: followed by `rts`. Its caller reloads (`$1fafe`: `movem.w ... d0-d3`).
- `$3bbb4/$3bc48`: after return `move.w 2(a1,d6.w),d6; cmp.w d6,d7`, and the loop reloads d5,d4,d2,d3,d0,d1 (`$3bb94-$3bbb0`, `$3bbf0-$3bc48`). a0-a3, d5-d7 are live (a0,a1,a3,d5,d6,d7 saved; a2 untouched).
- No other references to `$3c5c4`/`$3c5e2` or `$501a` as a call target exist in the 2 MB dump (byte search; the odd-address `501a` hits are data).

## Cycle accounting per call (typical walking edge: `$3c5c4` entry, fwd, dx>=0, ymin/ymax not updated, popcount(dx)=4 -> mulu 46)
Old, including restore: save 128 + conv 48 + bra 10 + lea 12 + cmp 4 + beq.w 12 + bpl 10 + min cmp 16+10 + max cmp 16+10 + sub/move 8 + mulu#imm 46 + add/add/add/adda 4+8+8 ... + T lookup (lea 12, add 4, move 14, asl 12) + sub 4 + bmi 8 + mulu 46 + addi.l 16 + bra 10 + lea 12 + suba 8 + tail 76 + restore 132 = **728 cy**.
New: save 72 + conv 48 + cmp 4 + beq.s 8 + bpl.w 10 + lea 12 + min 12+10 + max 12+10 + sub/move/add/add/add 20 + asl#6 18 + add 4 + lea 12 + adda 8 + add 4 + move 14 + asl 12 + lea 12 + suba 8 + sub 4 + bmi 8 + mulu 46 + tail 100 + restore 76 = **544 cy**.
Saving about 184 cy/call, about 34k cy/frame at 185 calls (2.1% of 1.6M cy/frame). Bodies are unchanged at 44 cy/row.
