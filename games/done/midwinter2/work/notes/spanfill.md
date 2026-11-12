# Span fill: terrain polygon rasterisation ($3c5c4/$3c5e2 edge walker + $38c6e/$38cd0 fill)

All disassembly from `python3 tools/m68dis.py work/dumps/ram_ingame_lobos.bin <addr> --profile work/prof/walking.txt`.
All dynamic evidence from Hatari snapshot `ingame_foot_walking` via `tools/mw2harness.py` (raw output in §7).

## 1. Scope and cycle share

| Region | Addresses | % of profiled cycles (walking.txt, total 35,321,256 cy ≈ 22 frames) |
|---|---|---:|
| Biased walker entry | `$3c5c4–$3c5e2` | 1.84% |
| Walker head (setup) | `$3c5e2–$3c68a` | 4.39% |
| Unrolled walk bodies (201 copies) + horizontal-edge handler | `$3c68a–$3d3a6` | 0.51% + 4.23% + 0.05% = 4.79% |
| Fill dispatch `$38c6e`+`$38cd0` | `$38c6e–$38d22` | 2.40% |
| Fill variants (span writers) | `$38d22–$3bb00` | 11.60% |
| Terrain driver `$1fa54` | `$1fa54–$1fbc6` | 2.57% |
| Object display-list decoders `$3c2de,$3c4ac,$3c4fa,$3c542,$3c54a,$3c56a,$3c58c` | | 4.73% |

**Total described here: ≈ 32.3% of profiled cycles.** The two hot buckets of the baseline
(`$3c5e2` 10.5%, `$38cd0` 12.5%) are both parts of this one pipeline.

## 2. Role — the full terrain rasterisation pipeline

Per rendered frame the terrain pass `$1fa54` runs once (0.98 calls/flip, §7 Run C),
reading a polygon stream (`a5 = [$66d0]`) against a vertex table at `$7c718` (a4).
Per polygon:

1. `move.w (a6)+,$6808` (`$1fa7c`) — colour/shade class word for the polygon.
2. Per edge (`$1fabc`/`$1fb0c` loops): `movem.w (a4,d4.w),d2-d3` fetches two signed
   vertex coords, then `jsr $501a` → **`$3c5c4`, the edge walker** (≈185 calls/frame, §7).
   Clipped edges go through `$1fdf0` first (`bsr $1fdf0` + `bne` skip, `$1fae4`) —
   confirmed by Projection agent (bp-verified): `$1fdf0` = Cohen-Sutherland clip in
   homogeneous (X,Y,W); the `$1fa04` divide pass emits signed centre-origin coords
   (half-extents 159 x / 71 y), matching the walker's ±160/±129 bias convention.
3. After the last edge: `jsr $4fea` → **`$38c6e` → `$38cd0`, the span filler**
   (≈33–62 calls/frame, §7). ≈3–4.7 edges per polygon.

### 2a. Edge walker `$3c5c4`/`$3c5e2` — NOT a pixel writer

`$3c5c4`: `neg.w d1/d3/d0/d2; addi.w #$a0,d0/d2; addi.w #$81,d1/d3; bra $3c5e6` —
converts signed centre-origin coords (centre x=160, y=129) to draw coords, then shares
the body of `$3c5e2` (direct entry keeps caller coords; both save `movem.l d0-d7/a0-a6`).
Contract in: d0,d1 = x0,y0; d2,d3 = x1,y1 (draw coords, rows must end up in [0,200)).

The walker writes **one 4-byte entry per scanline**: `{ word0 = byte offset y*160 +
(x div 16)*8 ; word1 = mask[x mod 16] }` into `$7b6b0` (200×4B) when `y1 ≥ y0`
(`$3c5e6 lea $7b6b0,a0`), else into `$7b9d0` with endpoints exchanged and x+1
(`$3c5f4–$3c600`). Verified live in §7 (E5: d5=$4A78 = 119*160+24 stored at
`$7b9d0+4*119`; E9: row 132 = {$52A8,$FC00} = offset 132*160+40, mask[6], x=86).

Key instructions:
- `$3c622 mulu.w #$140,d5` — **320 = screen width**; d5 = y0*320+x0 = pixel index p;
  `$3c66e lsr.w #1,d5` → y*160+x/2, per-step `and.w d7,d5` (d7=$FFF8) clears 3 fraction
  bits → y*160+(x div 16)*8 = **byte offset of the 16-px interleaved group**.
- `$17a66` — **reciprocal table T[i]=round(65536/i), i≤200**, boot-built by `$3d3a8`
  (`divu.w d0,d1` loop to `cmp #$c9`; dump §7 E1). `$3c636 move.w (a2,d3.w),d1` reads
  T[dy], `$3c640 mulu d2,d1` (d2=dx), `$3c642 addi.l #$1400000,d1` (+320<<16):
  increment I = 320 + dx/dy in 16.16 fixed point.
- `$40000` — **16 left-fill masks** {0,$8000,…,$FFFE} (top i bits set), boot-built by
  `$3d3e0` (dump §7 E1). Walker keeps d4 = $0004_0000 + 2*(x mod 16) (`move.l #$40000,d4`
  `$3c666`; upper word survives the word-sized add/and ops) → `movea.l d4,a3;
  move.w (a3),(a0)+` fetches mask[x mod 16].
- `$3c602–$3c618`: `$180ee`/`$180ec` = polygon min/max row (init $1000/$F000 at
  `$1fa68`) = the fill's row range.
- `$3c656 lea $3d30a,a1; suba.w d3,a1` (d3 = 16*dy) → `jmp (a1)` enters an **unrolled
  block of 201 copies** of the 8-instruction body, `$3c68a–$3d314` (3216 B = 201×16;
  dy=200 enters exactly at `$3c68a`). No loop: falls through dy+1 bodies to
  `movem.l (a7)+; rts` at `$3d314`.
- dy=0: `$3c5ee beq $3d31a` — horizontal handler writes one entry to each table for
  rows y0/y1 (`$3d34a–$3d3a0`, same encoding).
- Setup ≈430 cy/call (2×movem 120, 2×mulu ≈140) vs ≈10.6 rows × 44 cy body — **setup is
  ~half the walker cost** (185 × 430 ≈ 80k cy/frame = the 4.39% head share).

### 2b. Span filler `$38c6e` → `$38cd0` → variants — the pixel writer

`$38c6e`: d6 = ymin (`$180ee`), d7 = ymax−ymin (skips unless 0 ≤ d7 < 200, `$38c90`);
a0/a1 = `$7b6b0/$7b9d0 + 4*ymin`; d0 = `[$67a6]` = **draw-buffer base long** (observed
`$000600C0`/`$00070000`, §7 E6/E7); d2 = `[$6808]` colour class, d3 = `[$6806]`;
`bsr $38cd0`.

`$38cd0` dispatcher: class byte d2 indexes a 256-entry table at `$3ba5a` (d3==0) or
`$3baea` (`$38cdc`), then word table `$3b85a`, then a 28-byte record in `$3ac1a` giving
two variant entry offsets (d2/d3 = `$38cd0+off`), two dither words (d4/d5) and four
per-plane pattern longs (a3–a6); **variant chosen by ymin parity** (`andi #1,d6` `$38d14`,
`jmp (a2)` `$38d1c/$38d20`) = the 2-row dither phase. Observed: d4=$7777, d5=$DDDD,
a3–a6 = $FFFFFFFF,$FFFF7777,$FFFFFFFF,$FFFFDDDD (parity 0) / $FFFF7777,$77777777,
$FFFFDDDD,$DDDDDDDD (parity 1) (§7 E7/E8/E9).

**Screen-address trick:** the dispatcher leaves the base's *upper word* ($0006/$0007) in
d0; every variant loop does `move.w (a0)+,d0` (low half only) then `movea.l d0,a2` →
a2 = $0006xxxx = **full frame-buffer address** (both buffer bases have low word 0).
Verified: D0 = `$000652A8` = $60000 + 132*160+40 at the write loop (§7 E9). Double
buffering rides entirely on this stale upper word.

Per scanline (variant `$3a1be`/`$3a220`; all variants share the shape):
`move.w (a0)+,d0` (left group offset) · `move.w (a0)+,d2` (left mask) ·
`movea.l d0,a2` (screen addr) · `sub.w (a1)+,d0` (d0 = signed byte span width).

- **bmi (normal span, `$3a1ec`)**: left group: `or.w ~maskL` into plane words 0–2,
  plane 3 = `(mem & maskL) | (~maskL & dither)` (`and.w d4/d5,d3; and.w d2,(a2);
  or.w d3,(a2)+`); interior groups: `move.l a3,(a2)+; move.l a4,(a2)+` per 8-B group
  (loop `$3a200`, d0 counts +8 to 0) — **opaque 4-plane stores of the 2-row dither
  pattern**; right group symmetric with maskR (`$3a208–$3a218`).
- **beq (both edges in one group, `$3a22c`)**: combined mask `~maskL & maskR`, planes
  0–2 OR'd, plane 3 dithered. **bpl≠0 (crossed)**: row skipped (`$3a246`).

**Screen write format:** 320×200×4bpp interleaved; 16 px = one 8-byte group
(p0w,p1w,p2w,p3w); spans quantised to group boundaries, exact edges via $40000 masks;
colours are **row-parity dither patterns** — the observed class fills planes 0–2 with 1
and plane 3 with $7777/$DDDD per row parity = dither between colours 7/15 (bit-exact
walkthrough in §7 E9). Interior = plain `move.l` stores; edges = RMW `or.w`/`and.w`.

### 2c. Object pipeline decoders `$3c2de`, `$3c4ac`, `$3c4fa`, `$3c542/$3c54a/$3c56a`, `$3c58c`

Called in sequence per object by `$3be60` (after vertex transform `$3bfa2` — muls matrix
rotation — and projection `$3c02a/$3c080`), a5 = object display-list stream, a6 = arena
cursor (base `$67f0`; records = 16-bit offsets from it); section starts at
`$3be04/$3be08/$3be0c/$3be10`.
- `$3c2de` (1.21%): per-vertex opcode dispatch (`jmp $3c362(pc,d4.w)`/`jmp $3c3fe(pc,d5.w)`),
  operands via byte indices from tables `[$3bdea]/[$3bdee]/[$3bdf2]`, summed as d0±d1±d2
  (8 sign combos), then `asr.w #8,d4; addq.w #8,d4`, clamped [0,15] (`$3c490–$3c49e`),
  stored stride 8 → **[INFERENCE] per-vertex 4-bit shade**.
- `$3c4fa` (1.09%): RLE-decodes arena offsets relative to `[$3be08]-$67f0` into stride-4
  words (runs `d6+=4`, negative skips, 16-bit literals) — drawing index lists.
- `$3c58c` (0.70%): from `[$3be0c]-$67f0`, expands byte-counted runs into stride-8
  records (a6) plus a stride-4 side list (a3).
- Draw-queue consumer `$38b8c`: pops records off queue `$6de4` (pushed `$3bdc8`),
  shade + `$18766` → `$6808` colour class, then `jsr $3bb6e`/`$3bbca` — per-edge
  `bsr $3c5e2` ($3bbb4/$3bc48) + `jsr $4fea` fill. **0 hits in my windows** (§7): no
  queued objects on foot; walking.txt still shows `$38b8c` at 0.23%.

## 3. Call graph

```
$1fa54 terrain pass (1×/frame)
 ├─ $1fdf0 edge clip/project (per edge, Projection agent)
 ├─ jsr $501a → $3c5c4 ─┐  (185×/frame)
 │   falls into $3c5e6 ─┴→ walker: $17a66 recip table, $40000 mask table,
 │                          unrolled bodies $3c68a–$3d314, horiz $3d31a
 │                          writes $7b6b0/$7b9d0, updates $180ee/$180ec
 └─ jsr $4fea → $38c6e → $38cd0 dispatcher → jmp variant ($39c8a/$3a220/…)
                                reads $7b6b0/$7b9d0 + [$67a6] base + [$6808]/[$6806]
                                writes pixels to $60000/$70000 buffer
$38b8c object queue pop → $3bb6e/$3bbca → bsr $3c5e2 (direct) → jsr $4fea fill (idle on foot)
$3be60 object decode → $3bfa2/$3c02a/$3c080 transform → $3c2de,$3c4ac,$3c4fa,$3c542,$3c56a,$3c54a,$3c58c,$3bf6a
Boot init: jsr $4ff0 → $3d3a8 (builds $17a66); jsr $4ff6 → $3d3e0 (builds $40000)
Other user of $7b6b0/$7b9d0 (NOT this pipeline): $1cf64 window/HUD renderer stores full
  longs there ($1d1b6/$1d214; stale `{$0006,$d090}` in §7 E4) and fills via jsr $5020.
```

## 4. Hot loops

**Walker body** — 201 unrolled copies at `$3c68a + 16*i` … `$3d30a` (one per scanline),
8 instructions, 68000 cycles: `and.w d6,d4` (d6=$1E: keep 2*(x mod 16)) 4 ·
`and.w d7,d5` (d7=$FFF8: group-align offset) 4 · `movea.l d4,a3` (→$40000 mask ptr) 4 ·
`move.w d5,(a0)+` (store offset) 8 · `move.w (a3),(a0)+` (store mask) 12 ·
`add.w d0,d3` (16.16 error accum, d0=frac(I)) 4 · `addx.b d1,d4` (x += 2I+carry) 4 ·
`addx.w d2,d5` (offset += I/2+carry) 4 = **44 cy per scanline**.

Iterations/frame: unrolled region 4.74% × 1.605M cy/frame ≈ 76k cy → **≈1730 edge-
scanline steps/frame**; ÷185 edges → mean |dy| ≈ 9–11 rows/edge (matches d7 = 8–14 in
E6–E9). Walker head 4.39% ≈ 70k cy/frame ÷ 185 calls ≈ **430 cy setup/call**.

**Fill span loop** (`$3a1ec` shape, per scanline): head 5 instrs ≈ 32 cy; left edge group
4 RMW ≈ 40 cy; interior `move.l a3,(a2)+ / move.l a4,(a2)+ / addq / bne` = 24+12 cy per
8-byte group; right edge ≈ 40 cy; `dbra` loop-back 10 cy. ≈ 130 cy + 36 cy per interior
group. Fill variants total 11.6% ≈ 186k cy/frame over ≈ 62 polys × ≈10 rows ≈ 600 spans →
≈ 310 cy/span average (≈3–4 interior groups/span, average span ≈ 40–60 B ≈ 80–120 px).

## 5. Data structures / variables

| Address | Size | Meaning |
|---|---|---|
| `$7b6b0` | 800 B | left/down-edge table: 200 rows × {u16 group byte-offset, u16 left mask} |
| `$7b9d0` | 800 B | right/up-edge table, same layout (x+1 stored) |
| `$17a66` | 402 B | reciprocal table T[i]=round(65536/i), i≤200 (boot-built `$3d3a8`) |
| `$40000` | 32 B | masks[16]: {0,$8000,$C000,$E000,$F000,$F800,$FC00,$FE00,$FF00,$FF80,$FFC0,$FFE0,$FFF0,$FFF8,$FFFE} (boot-built `$3d3e0`) |
| `$67a6` | long | draw-buffer base ($000600C0/$00070000 observed); written only by flip routine `$26e98`/`$26eb8` mirroring slots `$770e/$7712` (Func38cd0, static xref); upper word doubles as address high half in fill loops |
| `$180ee`/`$180ec` | word | polygon ymin/ymax (draw rows), init $1000/$F000 |
| `$6808`/`$6806` | word | polygon colour/shade class → variant+pattern select |
| `$7c718`(a4)/`$66d0` | —/long | terrain vertex coord table (signed pairs) / polygon stream pointer (a5) |
| `$6de4/$6de8` | — | object polygon draw queue (stack) |
| `$3ba5a/$3baea`,`$3b85a`,`$3ac1a` | — | fill-variant lookup chain: class→variant offsets, d4/d5 dither words, a3–a6 plane-pattern longs |

## 6. Optimisation opportunities (STE)

Frame budget ≈1.82M cy (11.4 VBL @ 8 MHz); this pipeline ≈25–27%. Blitter ≈1 cy/byte of
bus time; HOG halts the CPU (nothing else to overlap inside the fill anyway).

1. **Blitter interior span fill (per scanline): B_HOP=3 (literal source), B_OP=3
   (replace), SRC-wrap pattern blit, 1D.** In interleaved layout a span's interior
   (opaque 4-plane pattern bytes) is ONE contiguous byte range. Pre-build per colour
   class a 16 B × 2 row source tile (= the a3/a4 and a5/a6 pattern longs); per scanline
   B_SRC_XWR wraps the source every 16 B, row parity picks the tile row via source start
   (+16), B_LIN_LEN=1, width = interior bytes. Setup ≈ 8 word-writes ≈ 60–70 cy +
   ≈1 cy/byte vs CPU ≈2.7 cy/byte. **Break-even ≈ 45–60 B; typical span interior
   30–50 B → marginal; wide bands (sky/sea/horizon, W>100 B) win ~50%.** Saving:
   interior ≈60% of 11.6% fill ≈ 7% of frame at best, realistically **2–4%** walking,
   more in vehicle/sea scenes. Risk: medium — keep B_OP/B_HOP/modulos resident, write
   only length+addresses per line. Halftone HOP=1 can NOT express per-plane patterns in
   one blit (one halftone bit applies to all planes); per-plane splitting costs 4× setup
   → loses.
2. **Merge walker+fill (remove table round-trip).** Tables exist only because edges are
   walked before ymin/ymax is known. A fused incremental span filler (x_L/x_R per row
   computed inside the fill loop) deletes 2 stores + 2 loads + the 430-cy/call setup per
   edge: walker 11.0% → ≈3%, fill +≈1%. **Net ≈ 6–8% of frame.** Risk: high —
   restructures the `$1fa54`+`$38cd0` contract, must keep dither/masks bit-identical;
   `$7b6b0/$7b9d0` are shared with the `$1cf64` HUD renderer (keep tables for it).
3. **CPU-only walker tune (low risk, ≈2–3%):** replace `mulu #$140` (70+ cy) with a
   y*320 table beside `$17a66`; merge the `$3c5c4/$3c5e2` entries to avoid double
   `movem`; fold the `and.w d6,d4`/`and.w d7,d5` masks away via pre-masked increments
   and 3-bit-fraction adds → body 44→36 cy ≈ 1.0% of frame.
4. **Blitter edge-group RMW:** 4 `or.w`/`and.w` per edge group ≈ 80 cy CPU vs 2 mini-
   blits ≈ 120 cy incl. setup — **not worth it**; keep edges on CPU.
5. **Visual-tradeoff candidates** (need sign-off): (a) single fixed dither pattern
   instead of row-parity pairs → halves variant count, constant per-row setup;
   (b) spans quantised to 16-px groups without edge masks (±15 px silhouette error —
   likely rejected); (c) solid (undithered) fill for polygons < N rows.
6. **Per-frame sizing:** ≈185 edges, ≈1730 walker rows, ≈62 fills, ≈600 spans,
   ≈2400 interior groups/frame.
7. Per Func38cd0 (work/notes/f38cd0.md): walking-profile fill cost is dominated by the
   `$39c8a` 50%-dither family (6.13%; solid `$38d22` only 1.79%), pattern sets are
   per-colour-class (112 variant records) → blitter design needs one 16B×2-row source
   tile per class/parity (≈112×32 B ≈ 3.5 KB), payoff tracks the dither-family share.

## 7. Verification (raw Hatari output)

All from `Hatari(snapshot='work/snapshots/ingame_foot_walking.sav')`, breakpoints armed as
`h.debug('b pc = $X :trace :once :file /tmp/spanfill/eN.txt')`.

**E1 — walker entry regs + boot tables** (`b pc = $3c5e2 :trace :once :file e1.txt`; e1 = `r / m $7b6b0 64 / m $40000 32 / m $17a66 24`):
```
D0 00000139  D1 0000009A  D2 0000013A  D3 0000009A   ; edge (313,154)->(314,154): dy=0 horiz
00040000: 00 00 80 00 c0 00 e0 00 f0 00 f8 00 fc 00 fe 00
00040010: ff 00 ff 80 ff c0 ff e0 ff f0 ff f8 ff fc ff fe   ; masks[16] as claimed
00017A66: 00 00 ff ff 80 00 55 55 40 00 33 33 2a ab 24 92
00017A76: 20 00 1c 72 19 9a 17 46                            ; T[i]=round(65536/i)
```

**E5 — mid-walk store** (`b pc = $3d210 :trace :once`, body instr `move.w d5,(a0)+`):
```
D0 000086B0  D1 86B002E5  D4 0004001E  D5 00004A78  D6 0000001E  D7 0000FFF8
A0 0007BBAC  A2 00017A66  A3 0004001E
0003d210 30c5  move.w d5,(a0)+ == $0007bbac [4a70]
```
A0 = $7b9d0+4*119 → row 119; d5 = $4A78 = 119*160+24 (group offset); d4 = $0004_001E →
mask fetch $4001E = masks[15]; d6/d7 = the $1E/$FFF8 alignment masks.

**E6/E7 — fill entry + variant dispatch** (`b pc = $38c9e / $38d1c :trace :once`):
```
E6: D6 00000096 D7 0000000E A0 0007B908 A1 0007BC28     ; ymin=150, 14 rows, table+4*ymin
    00038c9e 2038 67a6  move.l $000067a6.w [00070000],d0
E7: D0 000600C0 D2 00039C8A D3 00039CF8 D4 00007777 D5 0000DDDD D7 00000009
    A3 FFFF7777 A4 77777777 A5 FFFFDDDD A6 DDDDDDDD
    00038d1c 4ed2  jmp (a2) == $00039c8a                  ; parity-1 variant
E8: (at $38d20) D0 000600C0 A3 FFFFFFFF A4 FFFF7777 A5 FFFFFFFF A6 FFFFDDDD → jmp $0003a220
```

**E9 — write address proof** (`b pc = $3a224 :trace :once`, instr `movea.l d0,a2`; file also `m a0 16 / m a1 16`):
```
D0 000652A8  D2 0003FC00  D4 00007777  D5 0000DDDD  D7 00000008
A0 0007B8C4  A1 0007BBE0  A3 FFFFFFFF A4 FFFF7777 A5 FFFFFFFF A6 FFFFDDDD
0007B8C4: 53 48 ff e0 ...   ; next $7b6b0 row 133: {$5348=133*160+40, $ffe0=mask[11]}
0007BBE0: 52 a8 fe 00 ...   ; $7b9d0 row 132: {$52A8=132*160+40, $fe00=mask[7]}
000067A6: 00 07 00 00       ; base flipped to $00070000 between frames
```
D0 = $000652A8 = stale upper word $0006 (from `move.l $67a6,d0`) | table low word $52A8
= row 132, group 5 of buffer $60000. Consumed `$7b6b0` row 132 = {$52A8, $FC00=mask[6]
→ xL=86}; right row 132 = {$52A8, $FE00=mask[7] → xR=87}; `sub.w (a1)+,d0` = 0 →
single-group path: d3 = ~$FC00 & $FE00 = $0200 (pixel 86); planes 0–2 `or.w $0200`;
plane 3 `and.w d5($DDDD),$0200` = 0 → colour 7 this row, 15 on $7777-phase rows:
2-row dither, bit-exact as described in §2b.

**Run C — call counts, one window** (7 trace breakpoints armed together; 12 s host window;
counts = occurrences of `pc = $X :trace` / `$ff8201 = ` in the log diff; breakpoint load
makes the emulated fps unrepresentative, ratios are the measurement):
```
VBLs=641 flips=52
$3c5c4: 9614  per flip=184.9   (edge walker calls)
$3c5e2: 0     per flip=0.0     (object direct entry idle on foot)
$38cd0: 3214  per flip=61.8    (fill dispatches)
$3bb6e: 0 ; $3bbca: 0          (object edge-walk idle on foot)
$1fa54: 51    per flip=0.98    (terrain pass = 1/frame)
edges per fill = 2.99
```
Earlier windows (fewer bps, 170/213 flips): walker entries (`$3c5e6`) 156/frame, fills
33/frame (4.7 edges/poly). Spread = scene evolution + bp overhead; order of magnitude:
**~150–190 edges, ~30–60 polygon fills per frame.** Consistency vs profile: unrolled
bodies 4.74% ⇒ 76k cy/frame ÷ 44 ≈ 1730 edge-rows/frame ⇒ mean |dy| ≈ 9–11 rows/edge,
matching d7 = 8/9/14 captured in E6–E9.
