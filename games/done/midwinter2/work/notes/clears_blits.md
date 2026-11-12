# Clears, grid init and the masked HUD blit — $1b966/$1b996, $1d768/$1d8d4 family, $30e30/$30f2c

## 1. Scope and share of profiled cycles

`work/prof/walking.txt` (total 35,321,256 cycles, 256 VBL ≈ 26 frames), summed per address range:

| Range | Role | Share |
|---|---|---:|
| $1b966–$1b994 | 2-D rotate helper (jsr $4f7e = $359ac), ~63 calls/frame | 1.13% |
| $1b996–$1ba02 | sky-colour fill of screen lines 58–199 (movem.l bulk stores) | 2.90% |
| $1d768–$1d7a4 | per-frame init of 32×32 grid of 16-byte records at $6c000 | 4.46% |
| $1d8d4–$1da64 | cell visibility classify + vertex-cache walk | 1.34% |
| $1da66–$1da90 | vertex slot alloc/lookup | 2.78% |
| $1da92–$1dace | vertex height → view-space transform (3× muls) | 1.54% |
| $1d434–$1d49e | view-vector precompute (writes $18556/$1855c) | 0.03% |
| $30e30–$30f2a | RLE encode of HUD overlay (event-driven; **0 hits walking**) | 0.00% |
| $30f2c–$30f70 | per-frame masked and/or replay of that overlay onto back buffer | 3.35% |

Total **17.53%** of profiled cycles. Frame = 11.4 VBL × 160 kcycles = 1.82 Mcycles, so per frame:
fill 46.5 k (2.55%), grid init 71.5 k (3.92%), classify+alloc+xform 90.9 k (4.98%), replay 53.8 k (2.95%), rotate 18.2 k (1.0%).

## 2. Roles, inputs, outputs

**$1b996 (fill).** `01b99a: movea.l $67a6.w, a6` (back-buffer base), `01b9a4: adda.l #$2440, a6` (= line 58), d7 = $46 → 71 iterations of 8 `movem.l` stores ($1b9c8–$1b9f0) writing 320 B = 2 lines per iteration, `01b9f6: lea.l $140(a6), a6`, `dbra`. Registers are constants: d0=d1=$7fff7fff, d2–d5/a0–a5=$ffffffff. Output per line: bytes 0–7 = `7fff7fff 7fff7fff` (pixel 0 = colour 0, pixels 1–15 = colour 15), bytes 8–159 = $ffff (colour 15). Writes **22,720 B/frame = lines 58–199 × 160** of the back buffer ($67a6; captured = $70000). Colour 15 is the sky blue (screenshot: uniform blue above horizon; no sky spans exist — post-raster line 100 still holds the pure fill pattern). Output is byte-identical every frame (only the buffer base alternates). Called 1×/frame: from $1dca4 (3-D path, after $1ebda, before rasterizer $1fa54) or $1dbe8 (pitch-extreme path after $4ffc/$266a4; 0 hits walking).

**$1b966 (rotate).** Reads angle $6294, jsr $4f7e (→$359ac sin/cos), rotates (d2,d3)/(d0,d1) fixed-point, asr #$6, neg d1. No memory writes. 63 calls/frame from $1b752/$1b7c6/$1b944 (per-object loops).

**$1d768 (grid init).** `lea $6c000,a0`; d1 = word $18790 + word $18792 (grid-centre cell coords, captured $002f/$0032); 32×32 loop: `clr.l $6(a0)`, byte `$b(a0)` = (d1+d7+d6)&1 (checkerboard parity), a0 += 16. Writes 1024×5 B inside the 16,384 B grid $6c000–$6ffff (work buffer, not screen). 1×/frame from $1dc66.

**$1d8d4/$1da66/$1da92 (classify + vertex cache).** Walks cell-pointer list a6=($18758) ($7b6b0); per visible cell reads 4 corner heights ((a0),$10(a0),$200(a0),$210(a0)), classifies (byte $a(a0) = $ff/$01/$00 at $1d974/$1d9a2/$1d9d0), and for each corner calls $1da66: slot lookup in $7c718 via record word $8(a0); stale/new → $1da92: stamp slot word 0 with cursor d7, transform height by 3× `muls.w $18568/$1856a/$1856c(pc)` + per-cell base adds (d4=$188d8, d5=$18a18 tables), `movem.w d0-d2,$6(a1,d7.w)`, append index to a4 list ($18760→$1877e). Writes: scratch slots $7c718+ (cursor 8 → $91c captured = 2,324 B/frame), index list 83×2 B, record bytes $a/$8. Nothing touches the screens. 1×/frame; $1da66 252×/frame, $1da92 83×/frame.

**$1d434.** View vectors: $187b0/$187ae × $18568-6c → `movem.w d0-d2,$18556/$1855c`. 12 B/frame, 0.03%.

**$30e30 (encode, event-driven).** a1 = ($71c0) = source buffer ($770e long; = a screen buffer the HUD was drawn into), a0 = ($71bc) = list buffer ($68000). Rect from $67ae/$67b0 (x 1..319 → 20 16-px spans) and $67b2/$67b4 (y 58..199). Per span reads 4 plane words, writes $ffff back (erase), and emits into the list: nothing if all-white; `[~off][cnt][longs…]` run-copy if fully opaque; else `[off.w][mask.w×2][or.l×2]` (14 B, 8 dst bytes). Called from $28cee ($28cc0: sets $71bc=$68000, $71c0=$770e); callers $31632/$32ebc/$33016. **0 hits in 256 VBL walking** → list static during play.

**$30f2c (replay).** a0 = ($71c0) = $67a6 (set at $1dc06), a1 = ($71bc) = $68000. d7 = record count; per record: `adda.w d0,a0; d1=(a1)+; d0=(a0)&d1|(a1)+; (a0)+=d0; d1&=(a0); d1|=(a1)+; (a0)+=d1` (masked), or negative offset → run-copy longs. Writes **4,496 B/frame** (354 masked recs = 2,832 B + 28 run-copy recs = 1,664 B; list = 6,734 B, 382 records). Region = lines 58–199 but sparse: left/right visor bars (px ~16–31 and ~272–303, lines ~64–184) + bottom dashboard (lines ~184–199) — matches screenshot exactly. Bytes written are identical every frame while the list is unchanged (verified: post-replay $72440 = `7ffe7ffc 7ffc7ffc ffff7fff 37ff07ff` = static simulation of the dump list). 1×/frame via $1dc0c `jsr $5002` → `jmp $30f2c`.

## 3. Call graph

- $1b996 ← $1dbe8, $1dca4 (both in $1dbbe per-frame dispatch: $1dbbe ← jmp table $5056).
- $1b966 ← $1b752, $1b7c6, $1b944 (bsr).
- $1d768 ← $1dc66; $1d434 ← $1dc78; $1d8d4 ← $1dc7c (all in $1dc12 ← jmp table $505c, called from $1dbbe).
- $1da66/$1da92 ← $1d8d4 body ($1d97a/$1d986/$1d990/$1d99a; $1da92 also ← $1db6c/$1db8c).
- $30e30 ← $28cee (in $28cc0 ← $31632/$32ebc/$33016).
- $30f2c ← $1dc0c via `jsr $5002` (`005002: jmp $30f2c.l`).
- Callees: $1b966→$4f7e($359ac); $1d8d4→$1da66/$1dad0/$1db5e/$1db54; $30e30 none.

## 4. Hot loops

**Fill loop $1b9c8–$1b9fa, 71 iters/frame** (1 call/frame). Per iter: movem.l 12 regs (48 B) 56c + 10 regs 48c + 10 regs 48c + 8 regs 40c, ×2 groups = 384c nominal, + lea 4 + dbra 10; measured 649 c/iter (46,485 c/frame; profile lines $1b9c8 0.40%, $1b9cc .35, $1b9d2 .35, $1b9d8 .29, $1b9de .41, $1b9e4 .35, $1b9ea .35, $1b9f0 .29, $1b9f6 .03, $1b9fa .05 = 2.87%). 2.03 c/byte (16-bit bus).

**Grid loop $1d782–$1d798, 1024 iters/frame**: clr.l $6(a0) 16c, move.w 4, add.w 4, add.w 4, andi.w #1 8, move.b $b(a0) 12, adda.w #16 8, dbra 10/14 ≈ 70c; measured 69.9 c/iter (71,580 c/frame; $1d782 1.32%, $1d78c .44, $1d790 .66, $1d794 .66, $1d798 .67, $1d786/.788/.78a ≈ .66).

**Replay loop $30f3a–$30f50, 382 recs/frame**: masked rec ≈ move.w(a1)+ 8 + adda 8 + move.l(a1)+ 16 + move.l(a0) 16 + and.l 8 + or.l(a1)+ 16 + move.l(a0)+ 16 + and.l(a0) 16 + or.l(a1)+ 16 + move.l(a0)+ 16 + dbra 10 ≈ 146c; measured 141 c/rec (53,816 c/frame; $30f4c .31%, $30f4a .27, $30f46 .27, $30f48 .27, $30f42 .23, $30f40 .23, $30f3a .16, $30f3c .17, $30f3e .15, $30f50 .23).

**Vertex xform $1da92, 83 iters/frame**: 3× muls.w (~40c each) + 6 add.w (a3)+ + movem.w + list append ≈ 298 c measured ($1da9a .21%, $1da9e .24, $1daa2 .22 of profile). **Slot lookup $1da66, 252 iters/frame** ≈ 176 c measured.

## 5. Data structures

| Addr | Size | Meaning |
|---|---|---|
| $67a6 | l | back-buffer base ($60000/$70000); fill + replay dst |
| $6c000–$6ffff | 16384 | 32×32 grid of 16-B cell records (512-unit cells centred on player): +0.w height, +4.w vertex-slot offset in $7c718, +6.l per-frame scratch (cleared by $1d768; **no other writer**, watch 0 hits/155 VBL), +a.b visibility class ($ff/$01/$00), +b.b checker parity (read by `tst.b $b(a6)` at $1ed2a/$1ee62/$1ef8a/$1f132/$1f2da = dither select), +c.w/+e.w not determined |
| $18790/$18792 | w | grid-centre cell coords (parity base); from $18784/$18788 >> 9 + 50 ($1dc46–$1dc5c) |
| $7c718+ | ≤ ~8 KB | vertex slot cache: word0 stamp, +4.w, +6..+a.w view coords, +c.l; cursor $67c4 (8 → $91c captured) |
| $18758/$1875c/$18760/$1877e | l | cell-pointer in-list / visible-cell out-list / vertex-index list head+end (83 words/frame) |
| $18568/$1856a/$1856c | w | view-matrix constants (muls factors) |
| $67ae/$67b0/$67b2/$67b4 | w | HUD overlay rect: x 1..319, y 58..199 |
| $71bc / $71c0 / $770e | l | RLE list base ($68000) / replay dst (= $67a6) / encode source buffer |
| $68000–$69a4e | 6734 | RLE list: count.w then 382 records (14 B masked / 4+8k B run-copy). Overlaps live word $6888 (HUD distance) — list is only re-read by replay, and $6888 sits inside a masked record's offset field; consistent at dump time (faithful simulation reproduces $70000 exactly) |

## 6. Optimisation opportunities (8 MHz STE frame = 1.82 Mcycles)

1. **Grid init $1d768 → skip-when-unchanged (save ≈3.9% of frame, risk low-med).** Parity byte only changes when ($18790+$18792)&1 flips (watchpoint: 0 changes/155 VBL); the `clr.l 6(a0)` clears an already-zero long (watchpoint on ($6c006).l/($6c016).l: 0 hits/155 VBL ⇒ no other writer). Patch: compare parity base with last frame's; if equal, `rts` (keep one forced run at mode entry). Verify on vehicle/indoor snapshots before shipping (other modes use $1d7a6-family writers of +$b).
2. **Fill $1b996 → STE blitter fill (save ≈1.9%, risk med).** 22,720 B constant pattern: blitter fill ~1 word/cycle ⇒ ~11.4 k cycles of CPU stall (non-HOG) vs 46.5 k CPU. Must poll BUSY before $1fa54. Plain ST keeps CPU path.
3. **Fill → clip to sky (save 0.9–2.5% scene-dependent, risk med, overlaps #2).** Terrain spans + replay overwrite everything below the horizon (walking: horizon ≈ line 152 ⇒ 47 of 142 lines dead; banked turn: nearly all). Clip end line = horizon from the projection state; gaps in span coverage would show stale pixels, so gate on span-coverage proof or accept as approved tradeoff.
4. **Replay $30f2c → keep CPU RMW, micro-optimise (save ≈0.5–0.8%, risk low).** 0 records have and-mask 0, so no flatten-to-copy win; but 16-B-granular re-encode (merge adjacent partial spans) halves per-record overhead (~170 recs saved × ~40 c), and the 28 run-copy records (1,664 B contiguous per line-run) can go through one blitter M2M copy each. STE blitter cannot do per-word varying masks (halftone RAM is 16 B), so full blittering is not available.
5. **Replay → draw-once + clip (save 2.95% + fill/terrain under HUD, risk high, VISUAL TRADEOFF).** Only valid if the dither holes in bars/dashboard showing live terrain are replaced by clip windows; screenshot-approval required (holes currently show sky above horizon, terrain below).
6. **Vertex xform $1da92 → height×const tables (save ≈0.4–0.5%, risk med).** 3× muls.w by frame-constant $18568-6c on a word height: 3× 512-entry word tables (3 KB) replace ~120 c with ~24 c per vertex (83/frame). Slot-walk $1da66 (252 calls × 176 c): cache hits already 169/252; persistent cursor + generation stamp instead of $67c4 reset could cut alloc path (~0.5–1%, risk med, needs slot-layout care).
7. **$1b966 rotate (1.0%)**: 63 calls/frame × 289 c, dominated by jsr $4f7e; table-able but belongs to the projection agent's scope. $1d434: ignore (0.03%).

Realistic total in-scope: **≈6–7% of frame** (items 1+2+4+6), up to ≈10% with approved tradeoffs (3+5).

## 7. Verification (raw outputs, Hatari 2.6.1, snapshot ingame_foot_walking)

Counts, 256-VBL window (`b pc=$X :trace` + `b ($ff8201).b ! ($ff8201).b :trace`, delta of "matched N times"):
`$1d768 26, $1b996 26, $30f2c 25, $30e30 0, $1da92 2158, $1dc12 26, $1d8d4 26, $1da66 6552, flips 26` → 1×/frame each (83 xform, 252 lookup/frame); encode never runs. 155-VBL window: `watch rec0+6 0, watch rec0+b 0, watch rec1+6 0, $1b966 952` (≈63/frame).

Fill writes the pattern (bp $1b996 entry vs $1b9fe exit, `:file` with `m $67a6 4 / m $72440 16`):
entry: `000067A6: 00 07 00 00`; `00072440: 7f fe 7f fc 7f fc 7f fc ff ff 7f ff 37 ff 07 ff` (previous frame's HUD bytes)
exit:  `00072440: 7f ff 7f ff 7f ff 7f ff ff ff ff ff ff ff ff ff` (fill pattern; $62440 untouched) ⇒ 22,720 B of back buffer rewritten identically each frame.

Grid init (bp $1d768 entry / $1d7a4 exit): entry `00018790: 00 2f 00 32`, rec0 `... ff 01 ...`, rec1 `... 10 00 ...`; exit rec0 `... ff 00 ...`, rec1 `... 10 01 ...`, rec31($6c1f0) `... 3b 01 ...`→ parity byte flipped with centre parity; +6..+9 = 00 both sides.

Replay (bp $30f2c entry): `000071BC: 00 06 80 00 00 07 00 00` (list $68000, dst $70000), `000067AE: 00 01 01 3f 00 3a 00 c7` (rect x1..319, y58..199), list head `01 7d 24 40 ff fc ff fc 00 02 00 00 …`; exit ($30f54): `00072440: 7f fe 7f fc 7f fc 7f fc ff ff 7f ff 37 ff 07 ff` — byte-identical to the previous frame's value and to a faithful Python simulation of the dump list (4,496 B, 0 bytes differ).

Classify/xform (bp $1d8d4 entry/exit): `000067C4: 00 08` → `09 1c` (2,324 B slots), `0001877E: 00 07 9f e6` (83 index words = $1da92 count). $1da66 entry regs: `A0 0006D090 A1 0007C718 A4 00079F40 A5 0007BA98 D4 000188D8 D5 00018A18 D7 00000008` ⇒ record ptr, slot base, index list, cell list, base tables, cursor — all scratch, no screen addresses.

Post-raster (bp $1dcae, after $1fa54): line 100 of new buffer `00073E80: 7f ff 7f ff 7f ff 7f ff ff ff ff ff ff ff ff ff` = untouched fill ⇒ fill colour IS the sky (no sky spans); line 170 `00076A40: … 5d dd 5d dd …` = terrain over fill; line 190 `000776C0: … 44 44 …` = terrain under dashboard zone (replay lands later).
