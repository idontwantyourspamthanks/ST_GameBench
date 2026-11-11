# Projection & 3D transforms: $1fa54/$1fdf0/$200b4 (line engine + markers), $3bfa2/$3c02a/$3c080/$3bb6e (polygon engine)

Scope: $1fa04–$1fb4c, $1fdf0–$20086, $200b4–$20222, $3bb6e–$3bbc8, $3bfa2–$3c2de,
plus context ($3be3e pipeline, $3838c/$383ce/$38442, $1dc12 driver).
Cycle shares from `work/prof/walking.txt` (35,321,256 cycles ≈ 22 frames at 11.4 VBL/frame):

| Region | Cycles | % of profiled | per frame |
|---|---:|---:|---:|
| `$1fa54`–`$1fb4b` (edge walk/cull) | 891,440 | 2.52% | 40.5k |
| `$1fdf0`–`$20086` (line clipper) | 1,665,396 | 4.71% | 75.7k |
| `$200b4` (marker divs) | 479,276 | 1.36% | 21.8k |
| `$20136`+`$201ac` (marker variants) | 62,528 | 0.18% | 2.9k |
| `$3bfa2` (partial rotation) | 497,948 | 1.41% | 22.6k |
| `$3bfd4`+`$3c000` (vec×matrix) | 323,172 | 0.92% | 14.7k |
| `$3c02a` (scalar×vec pairs) | 748,384 | 2.12% | 34.0k |
| `$3c080`–`$3c2de` (vertex assembly) | 705,704 | 2.00% | 32.1k |
| `$3bb6e` (span driver, excl. $3c5e2) | 20,748 | 0.06% | 0.9k |
| **Total in scope** | **5.39M** | **15.3%** | **245k** |

(Context, owned by others: `$1fa04` divide pass 1.18%; `$383ce` polygon divide 0.22%;
`$3c2de`–`$3c58c` table builders ~2.6%; `$3c5e2` span fill ~10.5%.)

## 1. Three separate "projection" consumers

There is **no single projection routine**. Two render engines + one marker pass:

**A. Terrain/line engine** (`$1dc12` driver, via `jmp $5002` vector at `$1dc0c`):
`$1d768`/`$1d8d4` build cached view-space vertices in a 16-byte-record table at **$7c718**
(filled by `$1da66`/`$1dad0`: `movem.w d0-d2,$6(a1,d7.w)` at `$1dac2` = X,Y,W).
`$1fa04` does outcodes + **perspective divide**; `$1fa54` walks the polygon command
stream (`$66d0`) and culls/draws edges; `$1fdf0` clips straddling edges.

**B. Object/polygon engine** (`$3d466` per object → `$3bc5e` → `$3be3e`):
rotation by factored partial products (`$3bfa2`, `$3c02a`), bytecode vertex assembly
(`$3c080`) into 8-byte view-space records at **$783e8**, outcodes (`$3838c`),
polygon cull (`$38442`), **perspective divide** (`$383ce`), quad clipping (`$385b4`×4),
depth sort (`$3bd0c`/`$3bda0`), then `$38b8c`→`$3bb6e`→`$3c5e2` span fill.

**C. Marker pass** (`$20088` from `$1dc6a`): `$200b4`/`$20136`/`$201ac` divide
pre-scaled longs by `$66e0`, window-test, and insert into a hash grid (`$20222`).

## 2. Matrix layout and fixed-point formats

- **Rotation matrix: `$17fc6`, 9 words, row-major, 2.14 fixed point ($4000 = 1.0).**
  Built by `$389c0`-region code composing rotations via `jsr $4fc0` (sin/cos vector,
  16384-scale: `$7654`=16384, `$7652`=0 in dump) and `$3d7a6/$3d7d4/$3d85c/$3d8e2`
  (matrix mults, a1 = `$17fc6` at `$38a44`/`$38aa4`). Per-object matrices are copied
  from object record +6 by `$3dafc` (`move.l (a0)+,(a1)+` ×4 + `move.w`, 18 bytes) at `$3d4ae`.
  Runtime capture (bp `$3bfa2`): `$17fc6 = 4000 0000 0000 / 0000 c000 0000 / 0000 0000 c000`
  = diag(1,−1,−1) — axis-aligned at that moment.
- **Transform scale: `muls` then `asl.l #$2` + `swap` = (a·b) >> 14** — the standard
  vertex transform everywhere (`$3bfb6`–`$3bfc6`, `$3c048`–`$3c05c`, `$1da9a`–`$1dab0`).
- `$180e6` (3 words) = object/view vector, copied from object record (a6)+0,2,4 at `$3d48a`.
  `$3bfd4`: `$3be14[3i+j] = ($180e6[i] · M[3i+j]) >> 14` (9 words). `$3c000`:
  `$3be26[3i+j] = ($3be38[i] · M[3i+j]) >> 16` (swap only, no asl). `$3be38` = forward
  vector built by `$38bda` (`muls #$1bb6` of `$764a` table entry; static: $fff,$1000,$16a0).
- **Focal length: `$682a` = 164** (from `$17fc4` via `$3bc62`), used by polygon divide
  `$38402: muls.w d3,d0 / $38406: divs.w d2,d0` → `x' = x·164/z + $764e(160)`,
  `y' = y·164/z + $7650(128)`; screen bounds `$67ae..$67b4` = x∈[1,319], y∈[58,199].
- **Line engine projection (`$1fa04`): `x = X·159/W`, `y = (Y + Y asr 2)·71/W`**
  (`$1fa40: muls.w d5,d0 / $1fa44: divs.w d2,d0`, d5=`$1fbd6`=159, d6=`$1fbd8`=71,
  runtime-confirmed). Signed center-origin coords, window 319×143; Y pre-scaled ×2.25
  (`$1fa24`–`$1fa2a`). W==0 → (160,100) fallback (`$1fa32`–`$1fa3e`). Consumer `$3c5c4`
  negates and biases +(160,129) (confirmed by SpanFill agent).

## 3. Vertex/record formats

**Line-engine vertex, `$7c718` + offset, 16 bytes** (`$1da66`/`$1fa04`/`$1fdf0`):
| off | size | meaning |
|---|---|---|
| +0 | long | screen (x,y), signed center-origin (written `$1fa48`–`$1fa4a`) |
| +4 | word | outcode, bits 0–3 **duplicated at 8–11**, bit4 dup bit12 (`$1f9b6`: $808=X>W right, $202=Y>W bottom, $404=X<−W left, $101=Y<−W top, $1010=W≤0 behind). 0 = visible; ≠0 ⇒ **divide skipped** (`$1f9f8 beq $1fa2e`) |
| +6,+$8,+$a | word×3 | view X, Y, W |

**Polygon-engine vertex, `$783e8` + offset, 8 bytes** (`$3c080` out; `$3838c`, `$383ce`):
+0 view x, +2 view y, +4 view z, +6 outcode. `$3838c` bits: 0=x>z, 1=x<−z, 2=y>z,
3=y<−z, 4=z≤0 (`$383a2`–`$383c2`). `$383ce` overwrites in place with screen x,y and
screen outcode bits 0–3 (also `moveq #$10,d2` reject for z≤0 at `$383f8`).

**Polygon-engine scene record (a4 in `$3be3e`)**: +0/+2/+4 = counts of the 3 coordinate
sections (unique X, Y, Z value lists, 1 word each); +6/+8/+a = counts of 3 scalar
sections; +$c = count; +$e → `$53d4` (vertex record count for `$3838c`, =11 in dump);
+$10,+$16 counts for `$3bf6a`; +$18: data. Output pointers land in table `$3bdde`..`$3be10`
(runtime: `$78000,$78018,$78030,$78042,$7804e,$7805a`). Scratch buffer `$78000`+; final
record buffer `$67f0..$67ec` (runtime `$783e8..$78548`, `$67c4`=352 bytes used).

**Marker record, `$4bfa8` + 16·i** (written `$1c04e`–`$1c082`, count `$6f78`=55 at hit):
+$12 long Xpre, +$16 long Ypre, +$1a word obj-delta, +$1c/+$1d bytes, +$1e shape·4,
+$20 negative key. `$200b4`: `divs.w d7,d0/d1` with d7=`$66e0`; quotients → `$53ec/$53ee`
(no code reads found — [INFERENCE] consumed via indexed base or HUD), then
`x−= $670a(50); y = −(y−$670c(50))`, window ±8, cell = `y·512 + x·16 + $1ad0` → hash
insert `$20222` (buckets `$6c000`, links `$7c0d8`, key counter `$7682`, count `$6f7a`).

## 4. Call graph

```
$1dc12 (view driver, via jmp $5002)
 ├ $1d768/$1d8d4 terrain vertex build (→ $1da66/$1dad0 fill $7c718 records)
 ├ $20088 markers ─┬ $200b4 (divs $200d2/$200d4) → $20222 hash insert
 │                 ├ $20136, $201ac (same shape, other record tables)
 ├ $1dcd2 (W >>= $67be), $1fa04 (outcode $1f9b6 + divide $1fa44/$1fa46)
 ├ $1ebda, $1b996, then:
 └ $1fa54 edge walker (stream $66d0, verts $7c718)
    ├ $1fdf0 homog. Cohen–Sutherland clip (mulu/divu at $1ff02/$1ff04, $1ff6c/$1ff6e,
    │        $1ffd4/$1ffd8, $2003e/$20042; result → $1fde8/$1fdec, flags $1fbe8/$1fbea)
    ├ $501a (jmp vector → $3c5c4 edge walker, SpanFill note)
    └ $1fb4c (corner fill-ins using consts $1fbd6..$1fbe0 = 159,71,−159,−71)
$3d466 (per object/scene) → $3bc5e → $3be3e
 ├ $3bf22 (header), $3bfd4, $3c000 (vec×matrix, 9 muls each)
 ├ $3bfa2 ×3 (partial products: coord·matrix-column >>14, interleaved triples)
 ├ $3c02a ×3 (per scalar s: two words s·Σcol($3be26), s·Σcol($3be14), >>14)
 ├ $3c080 (bytecode vertex assembly: base ± Xpart ± Ypart ± Zpart + delta runs)
 ├ $3c2de/$3c4ac/$3c4fa/$3c542/$3c56a/$3c54a/$3c58c (index/edge/shade tables)
 ├ $3bf6a (per-polygon visibility OR), $382a2 → $3838c/$38442/$383ce(divide)/$385b4
 ├ $3bd0c/$3bda0 (depth sort, recursive $3bd62)
 └ $38b8c → $3bb6e (per polygon: chained index walk (a0..a3 all = $67f0; verified)
            → d0-d3 = coord pairs → bsr $3c5e2 span fill; sets $180ec/$180ee ymin/ymax)
```

## 5. Hot loops (per-iteration cycles; execs = profile cycles ÷ per-exec cost; ÷22 frames)

| Loop | Iter cost | Execs/frame | Notes |
|---|---:|---:|---|
| `$3bfb0`–`$3bfce` (`$3bfa2`) | ~243 cy | **93 coords** (2052 total; `move.w (a2)+,d3` 16416cy/8) | 3 muls (~38 ea, `muls d0,d3` 0.23%=81k/38≈2056 ✓), 3 asl.l, 3 swap, 3 stores; ~280 muls/frame |
| `$3c042`–`$3c078` (`$3c02a`) | ~438 cy | **78 scalars** (1710 total) | **6 muls each** (~468/frame) — all three multiplicands loop-invariant |
| `$3c080` bytecode | ~270 cy/vertex | **119 verts out** (`clr d1` $3c1fa 2622 execs), 8.6 groups ($3c0b2) | no muls; double `jmp (pc,dN.w)` dispatch ($3c20c, $3c236) |
| `$1fdf0` per call | ~1039 cy avg | **73 calls** ($1fe02 1603 execs) | ~50 divu/frame total ($20042: 0.21%=74k cy ⇒ ~650 execs; $1ff04 ~10/f; $1ff6e ~9/f); overflow guard `asr.l #$5` loop $20036 |
| `$1fa54` OR/AND cull | ~30 cy/vertex ref | — | $1fa8e/$1fa96 ~0.26% combined; fully-in → $501a direct, fully-out → skip |
| `$200c6`–`$2012c` (`$200b4`) | ~455 cy | **48 records** (1064 execs) | 2 divs (~0.88% of frame in divides alone; $200d2+$200d4 = 0.44%+0.44%) |
| `$1fa04` divide | ~340 cy/visible vert | **~34** (muls $1fa40 744 execs) | 2 divs + 2 muls; off-screen verts pay only ~60cy outcode ($1f9b6 1766 execs = ~80/frame) |
| `$383ce` divide (context) | ~320 cy/vert | **~5** (muls $38402 ~93 execs) | polygon engine divides only vertices of surviving polygons ($38442 cull first) |

Vertices per frame (walking scene): ~93 unique rotated coords → ~119 assembled view-space
polygon vertices across ~11 object transforms (`$3be3e` runs ≈11×/frame, from `$3bfd4`
171872cy/~700 per call); ~80 line-engine vertices outcoded, ~34 divided; 48 markers divided.

## 6. Optimisation opportunities (frame ≈ 1.6M cycles)

1. **`$3c02a` invariant hoist — biggest cheap win, bit-exact.** d3,d4,d5 (and d0,d1,d2)
   are loaded once before the loop; the body computes `s·d3 + s·d4 + s·d5`, which equals
   `s·(d3+d4+d5)` mod 2^32. Precompute the two column sums per call (a0/a1 advance by 2
   between calls, sums change per call, not per iteration): 6 muls → 2 muls + 2 add.l.
   Saves ~140 cy × 78 ≈ **11k cy/frame ≈ 0.7%**. Risk: low — needs |Σcol| ≤ 32767 guard
   (observed products are ~±1792-scale; add a fallback if a sum overflows the word).
2. **`$200b4` divs pair → signed shift.** `$66e0` = 512 at runtime and unchanged over
   40 VBL (watch breakpoint, zero hits). `divs #512` truncates toward zero; exact
   replacement: `if (d0<0) d0+=511; asr.l #9` (or swap-based) — **bit-identical**.
   Saves ~250 cy × 48 ≈ **12k cy/frame ≈ 0.75%**. Must keep a divs fallback if
   `$66e0` ever ≠ power of two ([INFERENCE] zoom modes may change it — not observed walking).
   Extra: the ±8 window test could run *before* the divide via long compares against
   `42·$66e0 .. 59·$66e0`, skipping both divs for most markers — blocked only by the
   unconditional `$53ec/$53ee` stores; no reader of those words was found by xref
   (3 writes only), so [INFERENCE] elidable after confirming via watchpoint.
3. **`$3bfa2` axis-aligned matrix fast path.** Captured matrix = diag($4000,$c000,$c000):
   output = (±c,0,0), no muls needed. Per call (3/object), test the 9 matrix words for
   0/±$4000 and use a copy/neg/clr loop when axis-aligned: ~243 → ~60 cy/coord.
   Up to **~13k cy/frame ≈ 0.8%** if most objects are axis-aligned (1 of 1 sampled was —
   frequency [INFERENCE]). Bit-exact. Risk: low.
4. **`$3c080` pre-decoded streams.** Replace the byte-stream + double indirect jump table
   with a loader-time-decoded flat op array (sign octet + 3 byte-offsets per vertex):
   est. 30–50% of 2.0% = **0.6–1.0% of frame**. Bit-exact adds; risk: medium (must patch
   every scene-load path; extra RAM ≤ stream size).
5. **Reciprocal table for clip/divide passes — small, precision-sensitive.**
   `$1fdf0` (~50 divu/frame ≈ 0.35%) and `$1fa04` (~68 divs/frame ≈ 0.5%): a
   4096-entry word reciprocal indexed by W>>4 (8 KB) turns each divide into mulu+shift,
   saving ~0.5–0.6% total, but introduces ±1 px error → clipped edge endpoints and
   terrain vertices jitter by a pixel. Visual-tradeoff candidate; needs before/after shots.
   The divu divisors in `$1fdf0` are normalised < $10000 by the `asr.l #$5` loop, so a
   256-entry table on the high byte would cover them with ≤0.4% relative error.
6. **Object-level frustum cull before `$3be3e`.** ~11 objects/frame × ~9.4k cy transform
   cluster each; a bounding-sphere test in view space before `$3bc5e` could skip objects
   behind/beside the camera. Saving scales with scene density (0.2–0.4% walking, more in
   busy scenes). [INFERENCE — not yet measured how many transformed objects end fully
   outside x∈[1,319],y∈[58,199]; `$38442` already culls per polygon after transform.]
7. **STE blitter: none of these functions benefit.** They are scalar muls/divs and
   short stores; blitter wins live downstream in `$3c5e2` span fill and the `$1b996`/
   `$1d768` clears (other notes). The one synergy: cheaper transforms → fewer VBLs per
   frame → blitter/CPU overlap budget grows.

## 7. Verification (raw Hatari output, snapshot `ingame_foot_walking`)

**(a) `$3bfa2` exact math + buffers.** `b pc=$3bfa2 :trace :once :file f1` /
`b pc=$3bfd2 ... :file f2`:
```
> r                      (at $3bfa2 entry)
  D7 00000004  A2 0005706E  A3 00078000  A5 00017FC6
> m a5 20
00017FC6: 40 00 00 00 00 00 00 00 c0 00 00 00 00 00 00 00   ; M = diag(16384,-16384,-16384)
> m a2 12
0005706E: 00 00 00 0a 00 19 00 05 00 00 00 c8                ; coords 0,10,25,5,0
> r                      (at $3bfd2 rts)
  A2 00057076  A3 00078018                                    ; 5 words in, 30 bytes out
> m $78000 48
00078000: 00 00 00 00 00 00 00 0a 00 00 00 00 00 19 00 00
00078010: 00 00 00 05 00 00 00 00 ...                        ; (10·$4000)>>14 = 10 ✓
```
**(b) `$1fa04` divide.** `b pc=$1fa48 :trace :once :file f3` (after both divs):
```
  D0 FD10FF7D  D1 FB1EFFDB  D2 000009B0  D5 0000009F  D6 00000047  A1 0007C784
> m a1 16
0007C784: ff 7e ff db 00 00 f8 00 fd ba 09 b0 00 88 fd 84
```
Record: X=$f800(−2048), Y=$fdba(−582), W=$09b0(2480), outcode 0.
X·159 = −325632; /2480 = **−131 = $FF7D** (D0 quotient; rem $FD10=−752 ✓).
(2·(−582) + (−582 asr 2 = −146))·71 = −1310·71 = −93010; /2480 = **−37 = $FFDB** ✓
(rem $FB1E=−1250 ✓). Old screen coords $ff7e/$ffdb at +0/+2 = previous frame ✓.

**(c) `$1fdf0` reject + successful clip.** `b pc=$1fdf0 :once :file f7`; `b pc=$20082 && d6=0 :once :file f8`:
```
reject hit:  D4 000004E8 D5 000601BC ... (exit) D4 00000404 D6 00000404  ; AND=$404 (both left) → bne skip
accept hit:  D6 00000000 D4 00000000 D5 00000000
> m $1fde8 24
0001FDE8: ff 61 ff cd ff 77 ff d9   ; A'=(-159,-51) — x exactly at left bound −159
> m $1fbe8 12
0001FBE8: 00 04 00 00               ; flag: A clipped at bound #4 (bit2=left)
```
Mid-clip at `$20044` (after `divu` at `$20042`): `D0 1EF00099` (quotient 153),
`$1fbd6 = 00 9f 00 47` = (159,71) at runtime ✓.

**(d) `$200b4` divs pair.** `b pc=$200d6 :once :file f5` (after both divs):
```
  D0 01000018  D1 0100005D  D6 00000037  D7 00000200   A0 0004BFA8
> m a0 32
0004BFA8: 00 17 00 00 00 00 00 00 03 4c 00 00 06 98 00 00
0004BFB8: 09 e4 00 00 31 00 00 00 bb 00 00 00 00 ff 00 00
```
long at +$12 = $00003100 = 12544; d7 = `$66e0` = **512**; 12544/512 = **24 rem 256** ✓
(D0). Long at +$16 = $0000BB00 = 47872/512 = **93 rem 256** ✓ (D1). D6 = 55 = `$6f78`
record count. `b ($66e0).w ! ($66e0).w :trace` over 40 VBL: **no hits** (constant 512).

**(e) `$3bb6e` entry + final buffers.** `b pc=$3bb6e :once :file f6`:
```
  A0 A1 A2 A3 all = 000783E8   D0 00000240 (= $17a60)
> m $17a60 4  → 02 40 00 02     > m $6808 2 → 01 0c (shade/palette word set by $38bc0)
```
`b pc=$3bf6a :once :file f10` (after transform+assembly complete):
```
> m $3bdde 24
0003BDDE: 00 07 80 00 00 07 80 18 00 07 80 30 00 07 80 42 00 07 80 4e 00 07 80 5a
> m $783e8 40
000783E8: 07 00 01 34 06 de 00 00 07 00 01 34 06 66 00 00   ; view verts (x=$0700,y=$0134,z=$06de)
> m $67ec 8
000067EC: 00 07 85 48 00 07 83 e8   ; buffer $783e8..$78548
> m $67c4 4 → 01 60 (352 bytes used)
```
