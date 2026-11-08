# P7 items 1+2: cockpit coverage table, polygon cull, fill-row trim (`patches/p7_ck_*`)

All patches are `default: no`. Evidence tooling: `work/p7_ck/ck.py` (ident / cyc), `work/p7_ck/boot.py`, `work/p7_ck/boot_fps.py`, `work/p7_ck/poison.py`.
Gates compare **p4 set live-applied (A)** with **p4 set + p7_ck (B)** (the p4 defaults the code interacts with: `p4_walk*`, `p4_proj*`, `p4_grid`,
`p4_hud_pfx_*`, `p4_hud_reset`; no tick/p3b/p5), both applied at the same flip, so every run sees the same game frames. Unobserved statements are marked `[INFERENCE]`.

## 0. Result

| cy/frame (20 frames, same frames in every run) | 1mb_ingame_foot | 1mb_ingame_walking | ingame_foot_banked_turn |
|---|---:|---:|---:|
| p4 set (baseline) | 1,693,768 | 1,251,419 | 2,017,721 |
| item 1 terrain polygons (`p7_ck_poly`) | 1,656,524 (-2.20 %) | 1,212,608 (-3.10 %) | 1,995,280 (-1.11 %) |
| item 1 objects only (`p7_ck_obj`) | 1,682,992 (-0.64 %) | 1,251,647 (+0.02 %) | - |
| item 1 = poly + obj | 1,645,391 (-2.85 %) | 1,212,608 (-3.10 %) | 1,992,168 (-1.27 %) |
| item 2 fill trim alone (`p7_ck_fill`) | 1,677,353 (-0.97 %) | 1,247,141 (-0.34 %) | 2,011,963 (-0.29 %) |
| item 2 on top of poly | 1,646,465 vs 1,656,524 (-0.61 %) | 1,214,827 vs 1,212,608 (**+0.18 %**) | - |
| everything (poly+obj+fill) | 1,638,861 (**-3.24 %**) | 1,214,827 (-2.93 %) | 1,990,379 (-1.35 %) |

Raw lines: `python3 work/p7_ck/ck.py cyc <snap> <set> 5 25` (`1mb_ingame_foot /tmp/ck/p4 cycles 33875352 over 20 frames = 1693768 cy/frame`, ...).
Cold boot, 1 MB STE, standing (static view, `boot_fps.py`, flips per 1000 VBL, cull sites alternately live / reverted to the original bytes in the same session):
live 97, reverted 92, live 96, reverted 93 (**+4.5 %**). Walking there is not comparable (the position changes between windows).

Recommendation: ship items 1 (poly + obj). Item 2 (`p7_ck_fill`) pays only when many wide rows sit under the dashboard (foot standing -0.6 %), is +0.18 % worse
in the walking benchmark; keep it off unless that scene type matters (section 5).

## 1. The coverage table: runtime, per vehicle type (not a build-time constant)

- The overlay list (`$68000`, `$71bc` points to it) is written by the encoder `$30e30`, called only from `$28cee` inside `$28cc0` (3D-view entry; `m68dis --callers 30e30`).
  `$28cc0` indexes the table `$732c` with `$6220` (type) and stores word 0 in `$7824`; `$304a2` draws that picture file (`jsr $2783e`) and `$30e30` encodes it
  (colour 15 = transparent, `$30ea6-$30eb0`).
- `$732c` (dump) maps the 22 types to 18 distinct picture files: `4c 47 52 4f 51 4a 55 53 48 4b 4e 4a 45 46 4d 44 49 4a 56 54 50 4a` (type 13 = on foot = `$46`);
  FFB (`grafix00`) directory entries for those file numbers have different lengths (`$44` 2072, `$45` 3015, `$46` 1424, `$47` 1360, `$48` 2935, ...). So the list is
  **not the same for every cockpit** (the Lobos on-foot list has the same md5 in all three snapshots, which only proves it is constant per type).
- Types 5, `$15`, `$11` skip the replay (`$1dbee-$1dc04`): the cull is off for them.
- Therefore the table is built at run time from the list that is actually in RAM: `p7_ck_tab` hooks the encoder exit (`$30f26`, the `movem.l (a7)+ ; rts`), i.e. it is rebuilt
  every time the list is, for every type; `p7_ck_enter` builds it lazily (`BUILT = 0`) so live-applied snapshots work.
  Build cost is a few 100 k cycles once per 3D entry [INFERENCE: not profiled].
- Decoding is pixel exact: record formats from the replay loop (`$30f3a-$30f68`): masked = `delta.w, mask.l, or1.l, or2.l`, opaque pixel = mask bit 0 in all four planes
  (`~(mH|mL)`; the encoder writes the same word twice), run-copy = `~delta.w, n-1.w, 8n bytes` = 16 opaque px per group.
- Rows kept: `KR0 = 176` .. 199 (24 rows; the dashboard starts at 182 on foot, polygons above 176 are never culled: they would have to fit in a 6-7 px wide pillar strip,
  none of the 31 captured frames has one). At most two runs per row in order of appearance (a third is dropped: conservative). Verified in the cold-booted game (1 MB and 4 MB):
  the table in RAM equals the table recomputed in Python from the live `$68000` list (`boot.py`: "F table rows mismatching the decoded list: 0").
- Three views of the same data: `XTAB` runs as x words, `KEYS` absolute edge-table keys, and the F table (section 2) that replaces XTAB in place.
  Key of pixel x in row y = `((y*160 + (x>>4)*8) << 16) | mask[x&15]` = the `{offset.w, mask.w}` long the edge walker stores (`work/notes/spanfill.md`, masks at `$40000`).
  Within a row it is strictly increasing in x, so "span [L, R) inside run [a, b]" is `Ka <= L && R <= key(b+1)` with two long compares and respects the 16-px group masks exactly.

Lobos on-foot table (decoded): rows 176-181 `(38,43) (276,281)` (pillars), 182 `(38,120) (199,281)` ... 191 `(35,130) (189,284)` (wings), 192-199 one run `(34,285)` .. `(30,289)`.

## 2. Item 1: reject polygons wholly under the cockpit before walk and fill

### Where the wholly-hidden polygons are
Offline from the captures of `render_audit.md` (`work/p7_ck` analysis, 13/10/8 frames): wholly-under polygons per frame w/f/b = 12.2/11/4.2 (7 terrain + 4 objects in f).
Decoding the polygon stream + vertex slots at `$1dcaa` (`/tmp/render_audit/v_*`): of the polygons wholly under the cockpit **2/0/0 are fully inside the window** (outcode OR = 0) and
**8/7/5 are clipped at the window bottom** (all outside vertices below the bottom edge: OR = `$0101`). A cull in the in-window branch (`$1faac`) would catch almost nothing.
The stream data show why: stored `(x, y)` of an outside vertex is stale (only outcode-0 vertices are projected, `$1f9b6-$1fa4c`), so a pre-clip test has to project them itself.

### `p7_ck_poly` (site `$1fa9a`, `tst.w d1 ; beq.w $1faac`)
- Candidates: `d1 = $0101` exactly and `d2 = 0` and EN. `$0101` = every outside vertex satisfies `-W <= X <= W`, `W > 0`, `Y' < -W` (Y' = 2Y + (Y>>2), `$1fa1a-$1fa2c`); no vertex above, left, right or behind.
  Others are never wholly under: a left/right/top clip leaves pixels at x = 1/319 or above row 176, which no opaque run covers. Non-candidates cost 4-6 instructions.
- bbox: in-window vertices use the stored `(sx, sy)`; outside vertices use `sx = X*159/W` with the game's own `muls`/`divs` (`$1fa40-$1fa46`; constants read from `$1fbd6`); no overflow possible since `|X| <= W`.
  `sy` of an outside vertex is irrelevant (below the bottom: bbox bottom = row 199). Draw coordinates `x = 160 - sx`, `y = 129 - sy` (walker `$3c5c4`: neg + `$a0`/`$81`).
  Rejects early when an in-window vertex has `sy > SYT` (above the first dashboard row, SYT = -53 for the on-foot list) or `Y0 < KR0`.
- Test: `[X0-2, X1+2]` inside one run of the **F table** row Y0, where `F(r) = U(r) & F(r+1)` is the set of columns opaque in every row `r..199` (computed once in `p7_ck_tab`).
  A polygon clipped at the bottom spans Y0..199, so "bbox inside F(Y0)" is exactly "bbox inside every row's runs", with one lookup instead of a row loop (a row loop cost ~850 cycles per candidate).
  It is done twice: with the in-window vertices only (no divide to reject) and then with the outside vertices added.
- Rounding margin: the clip (`$1fdf0`) puts the new vertices exactly on the boundary row (y = 129 + 71 = 200) with x from `mulu d0,.. divu`, error < ~1.5 px; so PADX = 2, PADY = 0.
  The rows are the in-window vertices' exact integers. **Validated** with a debug build (not shipped: it ran the polygon normally and compared the real edge tables `$7b6b0/$7b9d0` with the
  predicted bbox keys at padding 2/1/0 px): 2,237 would-cull polygons over `1mb_ingame_foot` (385), `1mb_ingame_walking` (1,010), `ingame_foot_banked_turn` (314), `ingame_lobos_foot` (390),
  `ingame_foot_turning` (50), `ingame_foot_walking` (88): **0 violations even at 0 px padding**.
- Hit rate (offline emulation of the exact test on the three frame dumps, pad 0 on Y): 6/8, 6/7, 4/5 of the truly hidden clipped polygons; the misses are polygons whose bbox is wider than their
  top rows (wing edge narrower at the top). In the emulator (DBG counters, foot): 18.6 candidates, 6.2 culled per frame; walking 13 / 6.9.
- Cost per culled polygon [measured]: foot -37 k cy/frame for 6.2 culls (net, including the hook), walking -39 k for 6.9.

### `p7_ck_obj` (site `$3bb6e`, 12 bytes: `movem.l ; move.w #$f000,$180ec.l`)
Object polygon rasteriser (only caller: the draw-queue pop `$38b8c`). The polygon is a ring of half-edges: first edge `2(a0,$17a60)`, next `2(a1,e)`, vertex `(a3,(a2,(a1,e)))` = x.w, y.w in
draw coordinates, already clipped. The hook leaves at the first vertex above row 176 (~60 cycles), else bbox `[xmin-1, xmax+1] x [ymin..]` and the same F lookup at `ymin`. A culled
polygon replays the state the original leaves for the next polygon (`$180ec = $f000`, `$180ee = $1000`, `$17a5e = 0`) and returns with the registers restored.
Validated with the same debug method: 256 would-cull object polygons (`1mb_ingame_foot`, `ingame_lobos_foot`, 60 flips each), 0 violations at padding 0.
Gain: foot -0.64 % on its own (4 hidden object polygons/frame), walking 0 (no object polygons), nothing lost there.

### EN: when the cull is allowed (`p7_ck_enter` `$1fa54`, `p7_ck_exit` `$1dcae`)
EN = 1 only inside a terrain pass that is followed by the cockpit replay: called from the main renderer (`4(a7) = $1dbe2`, the return address of `jsr $505c` at `$1dbde`; the alternate scene
render `$328e2 -> $505c` never replays the cockpit, the same test `p4_hud_pfx_fill` uses) and `$6220` not in {5, `$15`, `$11`}. EN is cleared right after the pass, so the object and fill hooks
cannot fire for object/fill callers outside it [INFERENCE: `$3d404` is reached through the jump slot `$4fcc`, whose callers were not traced, so other screens may draw objects]. The terrain stream walker has exactly one caller (`$1dcaa`).

### Interaction with `p4_hud_pfx_*`
The clean-prefix set assumes rows above `YMIN` (first row of any filled polygon) are untouched and already final. A culled polygon never reaches `$38cd0`, so `YMIN` only gets larger; rows at or below
`58 + 8*min(oldKB, newKB)` are refilled with sky and replayed, and the replay overwrites every opaque pixel, so the culled pixels (all under opaque cockpit pixels) end up the same. Verified by
abtest-style identity with the pfx set live in both runs (section 6).

### Row 200 (not a pixel-identity issue, but the gate must know)
The clip window's bottom is row 200 (`129 + 71`), one below the screen: the walker/fill write that row into the 768 bytes after each buffer (`$67d00-$67fff`, `$77d00-$77fff`; edge entries
`{$7d28, $fffc}` / `{$7d40, $fffc}` are at table row 200 = `$7b9d0`/`$7bcf0`, `m $7b9d0` in `/tmp/ck_r200.log`). A culled polygon no longer writes there, so those bytes differ
from the original (79-129 bytes on walking, 108-119 banked turn, 0-4 foot). `tools/abtest.py` and `Hatari.capture_frames` save `$8000` per buffer, so **plain abtest reports DIFFER; the 32000 visible bytes per
buffer are identical** (`ck.py ident` reports both). Nothing reads that memory: `poison.py` fills both tails with random bytes in one run and compares with an unpoisoned run after 40 flips:
visible screens, game RAM `$400-$5FFFF` and `$78000-$B1FFF` identical on `1mb_ingame_walking` and `ingame_foot_banked_turn`.

## 3. Item 2: fill rows under opaque runs (`p7_ck_fill`, site `$38c6e`)
Hook: the 6-byte jmp covers `movem.l` + the first half of `lea $7b6b0.l,a0`, so the blob replays that lea and rejoins at `$38c78` (a first version rejoined at `$38c72`, which was the second half of the jmp: bus error).
After the walker, with the left/right tables and `$180ee/$180ec` known, rows are dropped from the bottom while `L >= Ka && R <= Kb` of one run (KEYS: absolute keys, two long compares per row,
`-(An)` addressing), row 200 is dropped unconditionally, and the fill is skipped when no row remains. Whole rows only, a span is never split or narrowed, so the 16-px edge masks are untouched
and the dither phase (`$38d14`: parity of `$180ee`) is unchanged because ymin is not moved.
Why only that: (a) span-end trimming (new `L = key(b+1)` or `R = key(a)` for a span that starts/ends inside a run but is not contained) removes at most 48/38/50 interior groups per frame
(1.7 / 1.4 / 1.8 k cycles at 36 cy/group, offline over 31 captured frames) and every test costs more; (b) head and middle rows: measured -> the 15 head rows/frame did not pay for the setup.
A first version with head trimming cost +10.5 k cycles on foot net (fill rows -91.5 k, hook 102 k): per-row test ~156 cycles vs ~210 saved. The shipped tail-only loop (~104 cycles/row)
nets -16 k on foot alone, but after `p7_ck_poly`/`obj` removed the wholly-hidden polygons only the partially hidden ones are left and walking gets slightly worse (+2.2 k).
Counters (foot, 21 frames, first version): 87 fills/frame, 73 with ymax >= 176, 434 tail rows trimmed/frame, 14.7 head rows, 13.5 fills skipped.

## 4. Space and sites
`p7_ck_tab` `$b5280` (532 B), `p7_ck_enter` `$b5494` (72), `p7_ck_exit` `$b54dc` (18), `p7_ck_poly` `$b54ee` (306), `p7_ck_obj` `$b5620` (178), `p7_ck_fill` `$b56d2` (248); data `$b5000` (24 B vars),
XTAB/F `$b5020` (192), KEYS `$b50e0` (384). Range `$B5000-$B57FF`. Six sites: `$30f26`, `$1fa54`, `$1dcae`, `$1fa9a`, `$3bb6e` (12 B), `$38c6e` (10 B).
Apply all six `p7_ck_*` of a group together: `tab + enter + exit` are the base; `poly`, `obj`, `fill` each need EN/the table.

## 5. Decisions for the lead
- Flip `p7_ck_tab p7_ck_enter p7_ck_exit p7_ck_poly p7_ck_obj`. `p7_ck_fill` only if standing/object-heavy scenes matter more than the walking benchmark.
- The identity gate must compare the 32000 visible bytes (row 200 above); `ck.py ident` prints both.
- Ideas not done: in-window polygons (0-2 per frame hidden), polygons with `W <= 0` outside vertices, hits lost to bbox looseness (20 %), pillars (no polygon in 31 frames).

## 6. Gates (raw)

Visible-area identity (`work/p7_ck/ck.py ident <snap> A B <flips>`; both buffers `$60000/$70000`, rows 0-199; triple = (flip, visible bytes differing, dead bytes `$7d00-$7fff` differing)).
Items 1+2, A = p4, B = p4 + p7_ck_{tab,enter,exit,poly,obj,fill}:
```
1mb_ingame_walking flips [10, 40] VISIBLE IDENTICAL [(10, 0, 79), (40, 0, 129)]
1mb_ingame_foot flips [10, 40] VISIBLE IDENTICAL [(10, 0, 0), (40, 0, 0)]
ingame_foot_banked_turn flips [10, 40] VISIBLE IDENTICAL [(10, 0, 108), (40, 0, 119)]
```
Item 1 only (B = p4 + tab/enter/exit/poly/obj) and item 2 only (B = p4 + tab/enter/exit/fill), flips 10 and 40:
```
polyobj 1mb_ingame_walking VISIBLE IDENTICAL [(10, 0, 32), (40, 0, 34)]
polyobj 1mb_ingame_foot    VISIBLE IDENTICAL [(10, 0, 4), (40, 0, 4)]
fill    1mb_ingame_walking VISIBLE IDENTICAL [(10, 0, 79), (40, 0, 129)]
fill    1mb_ingame_foot    VISIBLE IDENTICAL [(10, 0, 0), (40, 0, 0)]
```
Combined with CellCull's `p7_cell_pre` + `p7_cell_cull` (A = p4 + cell, B = A + p7_ck, same three snapshots, flips 10/40):
```
1mb_ingame_walking flips [10, 40] VISIBLE IDENTICAL [(10, 0, 79), (40, 0, 129)]
1mb_ingame_foot flips [10, 40] VISIBLE IDENTICAL [(10, 0, 0), (40, 0, 0)]
ingame_foot_banked_turn flips [10, 40] VISIBLE IDENTICAL [(10, 0, 108), (40, 0, 119)]
1mb_ingame_foot     p4c     1645940 cy/frame -> p4c_all 1591148 (-3.33 %)
1mb_ingame_walking  p4c     1219498 cy/frame -> p4c_all 1182629 (-3.02 %)
```
Cold boot of the FULL default set + p7_cell_pre/cull + p7_ck (all six) built with `mw2patch.py build ... --out build/p7ck`, `boot.py`:
```
cell ste1mb ste 162 1024 build/p7ck          cell mste4mb megaste 206 4096 build/p7ck
3D view: $6220=d $700a=2                     3D view: $6220=d $700a=2
MWPO: 000B2FF8: 4d 57 50 4f  MWPO           MWPO: 000B2FF8: 4d 57 50 4f  MWPO
EN(between passes) 0 BUILT 1 SYT -53         EN(between passes) 0 BUILT 1 SYT -53
F table rows mismatching the decoded list: 0 F table rows mismatching the decoded list: 0
walk 0x6400 -> 0x5db4 moved                  walk 0x6400 -> 0x5c75 moved
```
(`boot.py` also tried a cull-live vs reverted screen comparison in the same session; it reports DIFFER only because the cold-booted view is not static: the two buffers of the *patched* run already differ by 160 bytes, so
it proves nothing and the identity evidence is the snapshot gates above. The 1000-VBL fps pairs it printed (47 vs 56 flips) were walking into different terrain; the standing pairs from `boot_fps.py` are in section 0.)
