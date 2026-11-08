# Render audit: is the game "simply doing too much"?

Read-only analysis. Nothing in patches/, tools/ or build/ was touched. Scratch scripts and raw logs are in `/tmp/render_audit/` (see Reproduce at the end).
Every number is either measured (source named) or marked `[INFERENCE]`.

## 0. Method and caveats

| Run | Snapshot | RAM | Window | Flips | cy/frame | VBL/frame | fps |
|---|---|---|---:|---:|---:|---:|---:|
| **w** | `1mb_ingame_walking` | 1 MB | 76.2 M cy (~475 VBL) | 50 | 1.524 M | 9.5 | 5.3 |
| **f** | `1mb_ingame_foot` (standing, static view) | 1 MB | 76.1 M cy | 40 | 1.903 M | 11.9 | 4.2 |
| **b** | `ingame_foot_banked_turn` (**2 MB**) | 2 MB | 76.2 M cy | 36 | 2.116 M | 13.2 | 3.8 |

- The "~1.9 M cycles/frame" figure in the question is the **f** (standing) scene. Walking is 20% cheaper and the banked turn 11% dearer.
- Profiles: Hatari `profile on` with a symbol file generated from `m68dis.call_targets` plus the `$4eca..` jump-table stubs. `profile callers` gives per-call-site **inclusive and exclusive** cycles, so the stage buckets come from the real call graph, not from address ranges. In w, Σ of exclusive costs over all call edges = 99.92% of the profiled cycles.
- Counts come from `profile save` per-address execution counts, divided by flips per window. The first and last frame of a window are partial (±1 frame, about ±2–3%).
- All snapshots hold the **unpatched** game. §1 also gives the same budget with the shipped `p4_*` set live-applied (`mw2patch.py live`, applied atomically at a flip).
- **w drifts**: the player walks, so the first 130 VBL (pixel/overdraw captures) differ from the full 475-VBL window (objects 1/frame in the profile window, 0 in the capture frames). **f is exactly periodic**, since all 10 captured frames have identical fill counts. Use f for exact comparisons.
- Pixel measurements: `$38cd0` (span fill) entry hooked with `:trace :file` dumping registers and `$7b6b0/$7b9d0`; the span tables were decoded to per-frame pixel maps (13 / 10 / 8 complete frames for w / f / b). The cockpit mask is decoded from the `$68000` list (5,396 opaque px of 45,440).

## 1. Frame budget map (Q1)

Cycles/frame (k) and % of the frame, unpatched. Each stage is the call-graph exclusive cost of its functions. "obj" is the part reached through the object path (`$1c3fc` → `$3d404`); shared leaves (walker, fill) are split per call site.

| Stage (functions) | w k (%) | f k (%) | b k (%) | of which obj (w / f / b k) |
|---|---:|---:|---:|---|
| **Transform** (terrain cell classify + vertex slot/xform `$1d8d4`/`$1da66`/`$1da92`; object matrix/vertex xform `$3be3e`, `$3c080`, `$3c02a`, `$3bfa2`, decoders `$3c2de..$3c58c`) | 218 (14.3) | 329 (17.3) | 379 (17.9) | 124 / 243 / 271 |
| **Clip** (terrain stream outcode OR/AND `$1fa54`, edge clip `$1fdf0`, `$1fb4c`; object `$382a2` family) | 190 (12.5) | 282 (14.8) | 254 (12.0) | 59 / 178 / 131 |
| **Edge walk** (`$3c5c4` terrain, `$3c5e2` + `$3bb6e` driver objects) | 189 (12.4) | 271 (14.2) | 259 (12.2) | 15 / 140 / 54 |
| **HUD** (`$19f54`: radar `$1b6f4`, sprite blits `$28fa2`, text, gauges) | 187 (12.3) | 144 (7.5) | 311 (14.7) | 0 |
| **Span fill** (`$38c6e`, `$38cd0`, ~112 variants) | 154 (10.1) | 233 (12.3) | 268 (12.7) | 8 / 74 / 29 |
| **Terrain grid** (grid init `$1d768` 85–87 k + cell→triangle gen/backface `$1ebda` 52–69 k) | 152 (10.0) | 135 (7.1) | 154 (7.3) | 0 |
| **Logic** (player sim `$33bca` 43 k incl. 2 terrain probes `$1ba24` 28 k; `$36ad8` 30 k; `$34adc` 20 k; misc) | 131 (8.6) | 140 (7.4) | 136 (6.4) | 0 |
| **World/object selection** (hierarchical cull `$1d434` 60–66 k; marker pass `$20088` 39–41 k; object BSP traversal) | 125 (8.2) | 143 (7.5) | 155 (7.3) | 23 / 45 / 50 |
| **Cockpit** replay `$30f2c` | 63 (4.1) | 63 (3.3) | 63 (3.0) | 0 |
| **Sky** fill `$1b996` | 55 (3.6) | 54 (2.9) | 54 (2.6) | 0 |
| **Project** (`$1fa04` terrain, `$383ce` objects) | 44 (2.9) | 85 (4.5) | 59 (2.8) | 5 / 51 / 20 |
| **Sort** (object depth buckets `$3bd0c/$3bda0`; terrain has none) | 5 (0.3) | 12 (0.7) | 11 (0.5) | 5 / 12 / 11 |
| **VBL/IKBD interrupts** | 8 (0.6) | 10 (0.6) | 12 (0.6) | 0 |
| **Total** | 1524 | 1903 | 2116 | **239 / 744 / 566 = 15.7 / 39.1 / 26.8 %** |

Pre-render logic, render, HUD and flip are strictly sequential. Per-frame totals match `frameloop.md` (render ≈ 79–84%).

Where the render sits (inclusive, from `profile callers`):
- `$1dbbe` = 79.3 / 84.4 / 79.1% of the frame.
- `$1fa54` terrain pass (includes objects) = 45.9 / 59.6 / 54.2%.
- Objects `$1c3fc` alone = 15.9 / 39.0 / 27.0%.
- HUD `$19f54` = 12.3 / 7.5 / 14.4%.

What the shipped `p4_*` patches already take (same snapshots, patches live):

| | w | f | b |
|---|---:|---:|---:|
| cy/frame unpatched → p4 | 1.524 → 1.230 M (−19%, scene drift) | 1.903 → 1.732 M (**−9.0%**) | 2.116 → 2.007 M (−5.2%) |
| grid init `$1d768` | 87 → 31 k | 85 → 32 k | 87 → 32 k |
| sky `$1b996` | 56 → 13 k | 55 → 19 k | 55 → 47 k |
| cockpit `$30f2c` | 64 → 25 k | 64 → 29 k | 64 → 60 k |

Remaining budget after p4 in f (1.732 M): transform 17.3%, clip 16.6%, fill 14.0%, edge walk 13.7%, HUD 8.6%, logic 8.0%, selection 8.0%, project 5.0%, grid 4.9%, cockpit 1.6%, sky 1.1%.

The profile is flat: no single stage above 18% after the shipped patches. Objects are the largest identifiable block in f and b.

## 2. Work efficiency, per frame (Q2)

Counts from `profile save` execution counts (w / f / b), plus pixel captures.

### Terrain funnel

| Step | w | f | b | Source |
|---|---:|---:|---:|---|
| Grid records re-initialised | 1024 | 1024 | 1024 | `$1d782` loop, 32×32 |
| Hierarchy: 27×27 = 729 leaf cells (9×9×9 loops) | | | | `$1d4c2..$1d58a` |
| level-1 blocks tested / passed | 9.2 / 5.4 | 9 / 5 | 9.2 / 5.5 | |
| level-2 blocks tested / passed (4×4 vertex window copied) | 48.8 / 11.9 | 45 / 11 | 49 / 12.8 | |
| level-3 cells tested | 107 | 99 | 116 | `$1d572` |
| cells within draw distance (accepted) | 68.8 | 63 | 80 | `$1d578`; 36% of tested cells are dropped by distance |
| cells with ≥1 triangle surviving the screen outcode AND test | 30.2 | 19 | 25.5 | `$1ecba` calls minus `$1ea9e/$1eaf0` calls |
| triangles generated | 60.5 | 38 | 51 | emit sites `$1ed4c/6c/8e/ae` |
| triangles removed by the backface test | **0** | **0** | **0** | tests = emits at `$1ea9e`, `$1eac4`, `$1eaf0`, `$1eb16` |
| triangles in the stream | 60.4 | 38 | 51 | `$1fa68` |
| – wholly inside window (no clip) / straddling (clipped) / rejected | 35.5 / 22.9 / 2.0 | 17 / 20 / 1 | 26.2 / 22.3 / 2.5 | `$1faac`, `$1fad4`, remainder |
| polygons filled (terrain) | 58.4 | 37 | 48.5 | `$38c6e` calls from `$1face/$1fb44` |

Accepted cells that end up with **no polygon at all**: 56% in w, 70% in f, 68% in b. The hierarchy test is frustum-coarse and conservative. Those cells still pay the per-cell classify, slot lookups and polygen prefix, about **1.7 k cy per cell** (classify 384 + slot lookup/xform 822 + `$1ec28` prefix 510, measured per address).

### Vertices

| | w | f | b |
|---|---:|---:|---:|
| slot lookups (`$1da66`) | 275 | 252 | 320 |
| transformed (`$1da92`) | 89.8 | 83 | 101.5 |
| unique corner vertices of the cell list | 89.8 | 83 | 101.5 |
| perspective-divided (`$1fa44`, outcode 0) | 30 | 20 | 23.5 |
| used by a drawn polygon (one frame, stream decoded) | 52 of 98 | 32 of 83 | 26 of 104 |

**No vertex is transformed twice per frame.** The cell list's unique corner set equals the `$1da92` count in all 13 / 10 / 8 captured frames. The per-frame slot cache (grid record `+8` → `$7c718` slot, cursor `$67c4`) gives 3.0–3.2 lookups per transform. The vertex count is not the waste.

What is wasted is transform + outcode of vertices that no drawn polygon uses (47%, 61%, 75%), about 330 cy each [INFERENCE from `$1da92` 298 c + outcode ~60 c].

### Edges and spans

| | w | f | b |
|---|---:|---:|---:|
| edge-walker calls (`$3c5c4`) | 172.8 | 104 | 142 |
| `$1fdf0` clip calls: rejected / trivially accepted / full clip math | 12.3 / 10.6 / 45.7 | | |
| walker rows (unrolled bodies) | 1059 | 1732 | 2376 |
| fill rows (span-loop heads) | 510 | 847 | 1162 |

172.8 walker calls ≈ 58.4 polygons × 3. Interior mesh edges are shared by two triangles and are walked twice [INFERENCE: geometry].

### Objects

| | w | f | b |
|---|---:|---:|---:|
| marker records considered (all world objects, 2 divs each) | 57 | 56 | 57.6 |
| pass the ±8-cell window test (hash inserts `$20222`) | 1.0 | 4.0 | 3.1 |
| drawn (`$1c4fc`) | 1.0 | 2.0 | 2.1 |
| BSP leaves transformed/clipped/sorted (`$3bc5e`) | 5 | 10 | 10.7 |
| polygons into the depth bucket (`$3bd30`) / rasterised (`$3bb6e`) | – / 3.2 | 29 / 34 | 8.9 / 10.8 |
| object pixels written (capture) | 0 (capture frames) | 630 | 156 |
| **cost per drawn object** (inclusive `$1c3fc`) | 242 k | **370 k** | 272 k |

- 98% of the marker records are rejected after two `divs`. This is `$20088` (39–41 k/frame, 2.1–2.6%); `p4_proj_div` already shortcuts the divides.
- In f, two objects cost 741 k cycles (39%) for **630 pixels**, 312 of them under the cockpit. Every object polygon is tiny (average 20 px).
- Object model selection is by record type only: `$1c456..$1c488` indexes `$514a[type&$1f]`. There is **no distance LOD** for objects.

## 3. Overdraw (Q3)

Window = 320×142 = 45,440 px (rows 58–199). Means over complete captured frames.

| px per frame | w | f | b |
|---|---:|---:|---:|
| sky fill writes (`$1b996`, 22,720 B = 2840 groups) | 45,440 | 45,440 | 45,440 |
| span-fill pixel writes (terrain+objects) | 7,001 (15.4%) | 9,717 (21.4%) | 20,104 (44.2%) |
| – unique pixels covered by spans | 6,382 | 8,684 | 18,758 |
| – **painter's overdraw** (writes − unique) | 619 (8.8% of span px) | 1,033 (10.6%) | 1,346 (6.7%) |
| span fills: rows / spans / 16-px groups written | 442 / 430 / 857 | 829 / 787 / 1,377 | 1,434 / 1,433 / 2,629 |
| – interior (opaque) / edge (RMW) groups | 140 / 716 | 143 / 1,234 | 363 / 2,266 |
| cockpit opaque pixels (replay, 4,496 B = 562 groups) | 5,396 | 5,396 | 5,396 |
| sky overwritten by terrain/objects | 6,382 (14%) | 8,684 (19%) | 18,758 (41%) |
| sky overwritten by cockpit only | 1,599 | 1,484 | 2,060 |
| terrain **under opaque cockpit** (unique px) | 3,797 (**59%** of terrain) | 3,912 (45%) | 3,336 (18%) |
| **final composition**: sky / visible terrain+objects / cockpit | 82.4 / 5.7 / 11.9 % | 77.6 / 10.5 / 11.9 % | 54.2 / 33.9 / 11.9 % |
| spans wholly under the cockpit | 185 (43%) | 345 (44%) | 151 (11%) |
| **polygons wholly under the cockpit** (exact mask / simple rectangle test) | 12.2 / 6.5 | 11 / 5 | 4.2 / 2.8 |

Reading:
- Painter's overdraw is small: **6.7–10.6% of span pixels**, about 0.6–1.0% of the frame at the measured fill rate (variant cycles per span pixel: w 108 k / 7,001 = 15, f 181 k / 9,717 = 19, b 223 k / 20,104 = 11; so 9 / 19 / 15 k) [INFERENCE: pixel-proportional].
- Sky over-fill is by design (the sky is a bulk fill and terrain is drawn over it). In unpatched code this is 45,440 px/frame written (2.6–3.6% of the frame); the shipped `p4_hud_pfx_*` already stops it re-writing rows the terrain never touched.
- The terrain pixel count is tiny. Walking: terrain covers 7,001 px (15%) of the window, and its first row is at y≈173 (the screenshots confirm a sky-dominated view).
- The large over-draw is geometric, not painter's: 59% / 45% / 18% of terrain pixels are hidden under the opaque cockpit. Polygons that are **entirely** hidden are drawn and walked at full price.
- Across the three stages the frame writes 58–71 k px (w: 45,440 sky + 7,001 spans + 5,396 cockpit = 57.8 k) to show 45.4 k.

Consecutive frames differ by little (capture buffers `$60000` vs `$70000`, two adjacent frames):

| | window bytes differing | 16-px groups differing | HUD rows 0–57 |
|---|---:|---:|---:|
| f (standing) | **0 of 22,720** | 0 of 2,840 | 0 of 9,280 |
| w (walking) | 208 (0.9%) | 87 (3.1%) | 28 B |
| b (banked) | 1,199 (5.3%) | 338 (11.9%) | 126 B |

## 4. Algorithmic choices (Q4)

**a) Painter's sort `$3bd0c`.**
- Objects only. Cost is 4.9 / 12.4 / 10.7 k per frame (**0.3 / 0.7 / 0.5%**).
- The terrain has no sort at all. The visible cell list is emitted in a precomputed back-to-front block order; in a captured frame the `+4` distance word falls 2624 → … → 0 along the list. The per-frame table build `$1e750` costs 7.6 k (0.5%), `$1e838` 1.5 k.
- Painter's order makes the output correct (overdraw ≤ 10.6% of span px). Dropping the sort is not an opportunity; a front-to-back skyline would only save the 0.6–1.0% overdraw.

**b) Per-frame grid rebuild.**
- `$1d768` rewrites 1024 records × (`clr.l +6` + parity byte) every frame: 85–87 k unpatched (4.1–5.7%).
- Fields `+6` are always zero (no other writer, `clears_blits.md`). The parity byte changes only when the grid centre parity flips.
- `p4_grid` (shipped) is down to 31–32 k (1.8–2.6% after p4). A skip-when-parity-unchanged exit removes most of the rest.
- The 4×4 height block copies from `$40040` are 11–13 blocks per frame; cost is inside `$1d434` (60–66 k, 3.2–4.2%).

**c) Homogeneous clipping on every edge?** No, the pipeline already has polygon-level trivial reject/accept.
- Per frame in w: 60.4 stream polygons → 35.5 trivially inside (no clip), 22.9 clipped, 2 rejected.
- Only the 22.9 straddling polygons call `$1fdf0`: 68.6 calls/frame, avg 1241 cy (85 k = 5.6% in w, 3.9% in f, 3.9% in b).
- Inside `$1fdf0`: 12.3 calls reject at once, 10.6 accept at once, and **45.7 do the full cross-product math** (the six `muls` at `$1fe5c..$1fe76` cost ≈ 14.4 k/frame in w; the `divu` at `$1ff04` ≈ 1.6 k). The rest is the `movem` save/restore and result writes (8.8 k for the `movem.l` pair alone).
- Polygon-level trivial accept covers 61% of the polygons; edge-level work on the straddlers is what is left.

**d) Dither dispatch per span.**
- The pattern variant is chosen **per polygon**, not per span (the row-parity variants `$38d1c/$38d20`).
- Dispatch `$38cd0..$38d21` costs **262 cy/call** (3 dependent table loads + 4 `movea.l`), and the `$38c6e` prologue 450 cy/call. 712 cy × 58–68 polygons = 43 / 49 / 42 k (**2.8 / 2.6 / 2.0% of the frame**).
- The 40 cy/call estimate in `f38cd0.md` is low. The span-loop variants themselves cost 108 / 181 / 223 k per frame (w: 108 k / 510 span heads = 212 cy per span).

**e) Anything cached across frames when the view is static (f)?** Nothing.
- `$1dc12` starts with `move.w #$8,$67c4` (vertex-slot cursor reset), then redoes grid init, hierarchy cull, classify/transform, polygen, sky, terrain and objects, HUD and cockpit replay every frame.
- f's frames are **bit-identical** (0 differing bytes in window or HUD between adjacent frames). All per-frame counters in f are identical frame to frame (83 vertices, 63 cells, 829 rows in all 10 captures).
- Renderer + HUD = **91.9% of the frame (1.75 M cy)** recomputes pixels that do not change in a standing frame. Logic + IRQ are the remaining 8%.
- The only cross-frame caching present is the HUD gauge dirty counters (`$1812a..$18138`, see `p3b_render.s`); the radar, sprites and clock are redrawn every frame (HUD 143 k standing).

## 5. Draw distance and LOD (Q5)

- Grid: 32×32 = 1024 records allocated. The hierarchy walks 27×27 = 729 cells (9×9×9). Per frame only 99–116 are inside the frustum blocks, 63–80 inside the draw distance, **19–30 draw anything** (2.6–4.1% of 729).
- Draw distance is set every frame at `$2029e..$202ba`: `$18772 = $a90` (cut), `$18774 = $900`, `$18776 = $790`, `$18778 = $640`. Cells compare `+4` (a grid-distance metric) against these. The three inner thresholds also select the fog dither band (`$18766` = band 0..3; band 3 = `$900..$a90`).

Polygons by fog band (captured frames):

| band | w polys / px / avg px | f | b |
|---|---|---|---|
| 0 (near) | 20.2 / 3,131 / 155 | 4.0 / 159 / 40 | 25.0 / 14,868 / 595 |
| 1 | 14.8 / 2,007 / 135 | 12.0 / 3,767 / 314 | 12.8 / 2,616 / 205 |
| 2 | 7.1 / 655 / 93 | 6.0 / 1,620 / 270 | 5.5 / 810 / 147 |
| 3 (far) | 15.1 / 1,207 / 80 | 14.0 / 3,541 / 253 | 12.5 / 1,653 / 132 |

Polygon size (w): 22% of polygons are under 64 px, holding 5% of the pixels; 56% are under 128 px, holding 32%.

**Measured effect of a shorter draw distance** (poked immediate at `$202a0`, same snapshots, 505 VBL profile, f exact, w/b drift with the speed of play):

| | f | w | b |
|---|---:|---:|---:|
| baseline cy/frame | 1.903 M | 1.524 M | 2.116 M |
| cut `$a90 → $900` (band 3 removed) | 1.732 M (**−9.0%**); renderer −9.5%; cells 63→55, polygons 38→23.9 | 1.338 M (−12.2%) | 2.006 M (−5.2%) |
| cut `$a90 → $790` (bands 2+3 removed) | 1.657 M (**−12.9%**); renderer −15.5%; cells 49, polygons 16.3 | 1.230 M (−19.3%) | 1.905 M (−9.9%) |

- This is a visual tradeoff: the far dithered band disappears and the terrain ends earlier. The numbers are reported as cost only.
- A model of the cost (`[INFERENCE]`): fixed per-polygon cost ≈ 5.4 k cy (walker setup 3 × ~760, dispatch + prologue 712, stream 750, clip share) + ≈ 310 cy per polygon row. The f result (−171 k for 14 fewer polygons and 8 fewer cells) agrees with ≈ 12 k per polygon incl. cell overhead.
- Far cells are expensive for what they show: a band-3 polygon averages 80 px / 7 rows (w) yet pays the same ~5 k of fixed cost as a 600-px one.
- A far-cell merge (2×2 cells → 2 triangles in bands 2–3) would keep the distance and cut polygons and cells by up to ¾ in those bands: **~5–8%** [INFERENCE, from the −12.9% number minus a pixel-proportional share]. Not measured; needs a new mesh path.

## 6. Verdict (Q6)

### Ranked remaining opportunities

Percentages are of the unpatched frame (w / f / b); the arithmetic is in each row. Rows 1–11 are pixel-identical by construction. Rows 12–16 are not.

| # | Opportunity | Est. % of frame | Pixel-identical | Effort | Risk |
|---|---|---|---|---|---|
| 1 | Skip the whole render (and HUD redraw) when camera, heading, zoom, objects and HUD state are unchanged since the last frame **in both buffers** | **~92% on standing frames, 0% while moving** (f: renderer 84.4% + HUD 7.5%) | yes, if the state test is exact | medium | medium-high (hidden animation/HUD state; double-buffer rule: draw twice, then skip) |
| 2 | Skip polygons wholly under the opaque cockpit (exact mask, or a rectangle test `x 34–285, y ≥ 192`) in `$1fa54` before walk+fill | rect: 1.9 / 1.2 / 0.6%; exact mask: 3.6 / 2.6 / 0.9% (≈ 4.5 k per polygon [INFERENCE: walker 3 × 762 + dispatch/prologue 712 + stream 750 + rows; no clip] × 6.5 / 5 / 2.8 rect and 12.2 / 11 / 4.2 exact polygons) | yes | low (rect) – medium (mask) | low |
| 3 | Per-cell early-out in the polygen path (cells that fail the screen outcode AND test skip classify + `$1ec28` prefix) | 1.5–2.5% (38.6 / 44 / 54.5 culled cells × ~0.7 k saved cycles) [INFERENCE] | yes (pure early-out) | high | medium |
| 4 | Fill entry: replace the 3-load dispatch and trim the 15-register `movem` save set | 1.2–1.7% (pool 43 / 49 / 42 k; assumes ≥ 60% of 712 cy saved × 58–68 polygons) [INFERENCE] | yes | low-medium | low |
| 5 | Grid init: skip when the centre parity is unchanged (after `p4_grid`) | 1.8–2.5% (31–32 k) | yes | low | low (check other modes that write `+b`, `clears_blits.md` #1) |
| 6 | HUD: hoist the sin/cos (`$4f7e` → `$359ac`, 98 cy per call, 5.5 k) out of the 56-iteration radar loop and keep the rotation coefficients in registers (`$1b966`: 56 × 479 cy incl. = 27 k) | 0.5–0.8% [INFERENCE] | yes | low | low |
| 7 | HUD: dirty-gate the sprite blit `$28fa2` (26 k/frame standing) and the other redraw-every-frame elements, with the existing 2-buffer dirty counters | 1.4–3% when unchanged | yes | medium | medium |
| 8 | Vertex slot lookup rewrite (275 × 207 cy = 57 k in w) | 1.2–1.5% | yes | medium | low-medium |
| 9 | Edge walker per-edge overhead after `p4_walk` (~544 cy/edge × 173 + restore) | 1.5–2% (trim); 6–8% (fused walker/fill, `spanfill.md` #2) | yes | medium / **high** | medium / high |
| 10 | Clip `$1fdf0`: skip the 6-`muls` setup for outcode patterns that need no intersection | 1–1.5% | yes | medium | medium |
| 11 | Object pipeline micro-opts (pre-decoded vertex streams, `$3c080` etc.; `projection.md` #3, #4) | 1–3% of a 16–39% block | yes | medium | medium |
| 12 | **Object LOD / impostor for far or tiny objects**: 1–2 objects cost 120–370 k each (5 BSP leaves × ~70 k) for ≤ 630 px | pool 15.7 / 39.1 / 26.8%; savings depend on the LOD | **no** | high | high |
| 13 | Draw distance −1 band (`$a90 → $900`) | **−5.2% to −12.2%** (f −9.0%, measured) | no | trivial | visual only |
| 14 | Draw distance −2 bands (`$a90 → $790`) | **−9.9% to −19.3%** (f −12.9%, measured) | no | trivial | visual only |
| 15 | Cockpit crop (`p4_hud_crop_*`, measured in `cockpit.md`) | +7.5% fps | no | done, off by default | visual |
| 16 | Far-cell merge LOD | ~5–8% [INFERENCE] | no | high | medium |

Sum of rows 2–11 on **moving** frames (row 7 = 0, since an unchanged-state skip does not fire): **≈ 10.6% (low ends) to 19% (high ends)** of the unpatched frame. With row 7 at its 3% maximum the high end is 22%. Each row is small and they overlap slightly. Rows 1 and 12–14 are where the large numbers sit.

### Is the game simply doing too much?

**Mostly no, with three exceptions.** The suspicion is half right: the scene is small, but the cost per primitive is high.

1. **The geometry is tiny.**
   - Per frame: 19–30 cells with polygons, 37–60 triangles, 83–104 vertices (20–30 divided), 0–2 objects.
   - Terrain/object spans cover 14–41% of the window before the cockpit is drawn; the final image is 54–82% bare sky, 6–34% visible terrain/objects and 12% cockpit (the sky is a constant fill).
   - Adjacent frames differ in only 0.9% of the window bytes while walking (w, one adjacent pair) and in 0 bytes standing (f, one pair, and all 10 captured f frames have identical span tables).
   - The work is not excessive in content. The renderer already has hierarchical frustum culling, a per-frame vertex cache (no vertex transformed twice), polygon-level trivial accept, backface test, back-to-front order without sorting, and fog bands. It is not a naive loop.
2. **The cost is the per-primitive overhead.** The terrain engine spends ≈ 14.5 k cycles per drawn polygon (w: render 1,209 k − objects 242 k − sky 56 k − cockpit 64 k = 847 k for 58.4 polygons) for ~110 px each: 847 k / 6,382 unique pixels ≈ 133 cy per terrain pixel. Fixed costs (walker setup 3 × ~760, dispatch + prologue 712, clip 1.2 k per straddling edge, stream, per-cell 1.7 k) dominate over rows and pixels (≈ 70/30 in the §5 model). A per-pixel cost of 15 cy in the fill loop is already modest; there is no pixel-bound hot loop left to tune.
3. **Real redundancy exists but is narrow:**
   - Recomputing a bit-identical frame while standing (92% of the frame cycles, row 1).
   - HUD 7.5–14.7% of the frame redrawn every frame (the radar loops all 57 world objects, `$1b966` rotation per object).
   - Objects: 1–2 BSP models with 5 leaves each cost 242–370 k each (15.7–39.1%) and show 0–630 px; no distance LOD.
   - 56–70% of the in-range terrain cells never produce a polygon, 21% of polygons are wholly under the cockpit, and 47–75% of transformed vertices are not used by a drawn polygon.

**On "little is left to gain":** after the shipped `p4_*` patches the remaining pixel-identical items are ~10–19% in total, spread over about 10 changes of 0.5–4% each (rows 2–11), with no single hot spot above ~4%. That is the "flat profile" result, and for moving frames it is a small gain (≈ +0.5–0.9 fps at 5 fps).

Larger numbers need either:
- a visual tradeoff (draw distance −9..−19%, object LOD, cockpit crop +7.5%), or
- a structural change: static-frame skip (row 1) or an incremental/retained renderer (consecutive frames differ in 3–12% of 16-px groups, so the headroom is large but this is a new engine), or the fused edge-walker + span-fill (6–8%).

## Reproduce

All in `/tmp/render_audit/` (one Hatari at a time, snapshots only):
- `prof2.py <snap> <out> <mem_kb> <vbls>`: symbols + profile + `profile callers` + `profile save` (`w`/`f`/`b` runs, `505` VBL).
- `prof3.py <snap> <out> --mem --live <prefix> --poke 'w $202a0 $09 $00'`: shipped-patch (`live_p4`) and draw-distance runs.
- `an.py`, `tree.py`, `stages.py`: parse the saved profiles, inclusive call tree, stage buckets (explicit function → stage map, terrain/object split by call site).
- `cap.py` + `capan.py` + `overdraw.py`: `$38cd0` hook with table dumps → per-frame pixel maps, overdraw, cockpit overlap, band stats.
- `vcap.py`: vertex slot, cell list and polygon stream decode at `$1dcaa` (vertices used vs transformed).
- `ident.py`: adjacent-frame buffer comparison (`capture_frames`).
- `syms.txt`: symbol file (`call_targets` + stubs).
