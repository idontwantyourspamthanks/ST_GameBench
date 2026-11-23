# Powermonger WW1: the frame loop, the tick-port map, delivery and free RAM

Evidence tags: **[obs]** = raw emulator/debugger output quoted (reproducible with the stated
command), **[disasm]** = read from a live RAM dump (`work/dumps/mapview_live.bin`, 1 MB STE,
TOS 1.62, taken at the 3D map view from `work/snapshots/mapview.sav`), **[INFERENCE]** = not
verified.

The 1990 sibling (`../../done/powermonger/`) is the reference for every "the 1990 game" line.

## 1. The main loop (3D map view) [disasm, obs]

At the map view the pass body is `$13dA8..$144xx`. The strip below is from the live dump; the
call targets were identified by their heads (section 2):

```
13da0  tst.w   $5a856        ; a pause/skip gate
13da8  addq.l  #1,$2ed90     ; <-- THE WORLD/PASS COUNTER (the 1990 game's $2df70)
13dae  addq.l  #1,$50fd8     ; a second timestamp counter
13db4  jsr     $1359a        ; logic 1: selection scan (min/max walk of a $13706 table)
13dba  jsr     $576a         ; logic 2: message/order queue ($5574e records, $154 B each)
13dc0  jsr     $d712         ; logic 3: selection/UI state refresh ($5a81c)
13dc6  jsr     $3276         ; logic 4: territory/HUD status ($5574e + n)
13dcc  clr.w   $13ccc        ; <-- render flag (cleared, set when the speed countdown hits 0)
13dd2  movea.l $2ed9c,a1     ; draw buffer
13dd8  lea     $20(a1),a0
13ddc  move.l  a0,$e7c2
13de8  subi.w  #1,$5a854     ; <-- THE SPEED COUNTDOWN (the 1990 game's $57ff0)
13dee  bne     $13e24        ;     NZ = skip the render
13df2  move.w  $5a852,$5a854 ;     reload the period
13dfc  move.w  #1,$13ccc
13e04  jsr     $e04          ; <-- WAIT FOR THE VBL (poll $2edac)
13e0a  jsr     $13a94        ; THE 32,000-BYTE WINDOW COPY (see 2; the 1990 game's p6_cpy)
13e10  tst.w   $5a856 / 13e18 jsr $18570 / 13e1e jsr $fc78   ; HUD/scroll updates
13e24  jsr     $1b90a        ; weather/season animation (phase at $1b900, step $1b8fe)
13e2a  jsr     $1853a        ; scrolling text row ($1040a)
13e30  jsr     $17462        ; territory status draw
13e36  jsr     $158b2        ; <-- THE MEN/ENTITY WALK (the 1990 game's $14b62)
13e3c  jsr     $6396         ; UI message queue ($5a882, dispatch table $63dc)
13e42  jsr     $74e0         ; render tail, ends in the FLIP
13e48  ...                   ; scroll offsets, $d62a, the icon hit test $6c16, the click
                             ;   latch tests $13e82+ (the input/UI section)
```

**Pass counter** `$2ed90`: [obs] two reads 5 s apart at the map view: $24 -> $3b (27 passes)
over 316 VBL -> **4.27 passes/s at 8 MHz**; the VBL counter `$71b7c` 5343 -> 5659. The speed
period `$5a852 = 1` at the map view, so a pass = a rendered frame here (the countdown
`$5a854` reloads to 1).

## 2. The flip, the buffers, the VBL and the clock [disasm, obs]

- **Flip** `$e0e`: `d0 = [$2ed9c]; d1 = [$2ed98]; [$2ed9c] = d1; [$2ed98] = d0;`
  `d0 >>= 8; move.l d0,$ff8200.w` (the video base); `clr.w $2edac`; `rts`. The 1990 game's
  flip was `$187a`; the buffers there `$2df7c/$2df78`, here **`$2ed98/$2ed9c`** (live at the
  map view: $25200 / $1d500).
- **VBL wait** `$e04`: `tst.w $2edac; beq.s $e04; rts` (test-only). `$df2`: `clr.w $2edac`
  then the wait (the "wait for the NEXT frame" form).
- **VBL flag** `$2edac`: set by the VBL handler's light path (`$766: move.w #1,$2edac; rte`),
  cleared by the flip (`$e2c`) and by the wait's first form.
- **VBL counter** `$71b7c` [obs]: ticks ~50/s; incremented in the full VBL path
  (`$774: addq.l #1,$71b7c`). The 1990 game's `$6f304`; the low word is `$71b7e`.
- **VBL handler** `$75e` (vector `$70`): `tst.w $75c` -> light path (`$2edac=1; rte`); else
  counter++, `tst.w $2ec86` -> `jsr $1c4de`, then the `$79a` dispatch indexed by the IKBD
  buttons byte `$1d2af` (0 = the idle path, which re-programs the IKBD mouse position every
  frame; 4 = the left-latch code `$81e`; 8/10 = the release paths).
- The 32K window copy at **`$13a94`**: `movem.l (a0)+,d2-d7/a2-a3` / `movem.l ...,(a1)` /
  `adda.w #$20,a1`, dbra `$1f3` (500 rows x 2 movem) — the same "copy the clean window
  picture to the back buffer" job as the 1990 game's `p6_cpy` (its 50-chunk STE-blitter
  patch is the performance-port analogue; the IKBD overrun trap applies to any long blits).
- The **sound**: timer C (vector `$134` -> `$1bc92`) is the YM sample player:
  `move.l $5ef96.l,a0; d0 = (a0)+; beq -> silence ($1bccc: $fa19=0, sf $2d7b3, bclr #5
  $fa0f)`; else `$1bc9a = a0` (a self-modified pointer in the code!), tables at `$1bce6`/
  `$1bcea`, `movep.l d1,-$720f(a0)` = the YM registers `$ff8800/02/04/06` (the 1990 game's
  `movep.l` at `$b5ee..$b624`/`$1af58`, and the `fal_ym` Falcon bus-error trap applies).
  Timer A (vector `$120` -> `$1d090`) is a trivial border-flicker stub at the map view.

## 3. The tick-port map (the 1990 patch -> the WW1 site)

| 1990 patch / anchor | 1990 site | WW1 equivalent | WW1 site [disasm/obs] |
|---|---|---|---|
| `tick_head` pass head | `$13020` | the pass head before the counter bump | `$13dA0..$13dA8` |
| world counter | `$2df70` | pass counter | **`$2ed90`** (bumped `$13dA8`) |
| VBL counter | `$6f304` | VBL counter | **`$71b7c`** |
| 50/60 Hz sync | `$ff820a` bit 1 | same register (verify live) | `$ff820a` [INFERENCE] |
| `tick_pass` speed branch | `$13074` (`$57ff0`) | countdown branch | **`$13de8`** (`$5a854`, period `$5a852`) |
| render flag | — | `$13ccc` (1 = render) | `$13ccc` |
| `tick_men` men update | `$14b62` called `$130c2` | men/entity walk | **`$158b2` called `$13e36`** |
| `tick_wx`/`tick_rain` weather | `$1abaa` called `$130b0` | season/weather animation | **`$1b90a` called `$13e24`** (phase `$1b900`, step `$1b8fe`) |
| `tick_click` latch lifetime | `$2df70` operands `$12f8/$1354/$1373e` | the `$2ed90` operands | **`$836` (latch copies `$2ed90->$2ed94`), `$144b2`/`$144c0` (expiry)** |
| flip | `$187a` | flip | **`$e0e`** (buffers `$2ed98/$2ed9c`) |
| VBL wait | — | wait | **`$e04`** |
| `p6_cpy` 32K window copy | the window copy | copy | **`$13a94`** |
| `p4_spr` sprite blits | masked blits | block copy | `$7588` (`movem.l d3-d7/a2-a4,(a1)`) — the fast blit primitive [obs: hit at a render sample] |

The pass-kind design is the 1990 one: hook the head, accumulate real time from the VBL
counter (1/300 s units, `$ff820a` sync bit), and on a render-only pass jump straight to
`$13dcc` (the render setup, skipping the four logic calls); on a "behind" pass force the
`$13de8` countdown to skip the render; redirect the three `$2ed90` click-lifetime operands to
a per-pass counter because `$2ed90` becomes per-tick once the head hook skips it.

## 4. Delivery and free RAM [obs, disasm, INFERENCE]

- **The carrier**: `WWIEDITN.PRG` = header 28 B + text 62050 B + one zero reloc long (4 B) +
  the packed payload from file offset **62082** (the packer does `Fseek(62082)` and
  `Fread 221820 B -> $c1d84`; both constants are code in the TOS-loaded text). Extending the
  text (and patching 62082) moves the payload safely; a front stub in the added bytes can
  copy the patch records to high RAM before the original first instruction runs. The 1990
  design (front stub -> payload records -> hook at the stage hand-over; the hook compares
  every site's original bytes, then writes all or nothing) transposes directly: hook the
  packer's final jump into the depacked GAME stage. The stage entries/hand-over are still to
  be found (`PLAN.md` P2; the packer's per-stage depack targets need the offline depacker
  transcription for `verify`).
- **Free RAM at the map view** [obs] (1 MB STE dump `mapview_live.bin`, 256-byte blocks):
  non-zero: `$08200-$0dbff`, `$0dd00-$0faff`, `$0fc00-$2cfff`, `$2d500-$448ff`,
  `$44d00-$4ceff`, ..., `$5a700-$71bff`, **`$c1d00-$ffcff` (the packer's payload
  `$c1d84..$f7f3c` stays resident — the Alien's ramdisk)**. The clean span
  **`$72000-$c1cff` (~324 KB)** is all zero at the map view — the payload candidate (the
  1990 game's `$b8800..$effff` is partly occupied here by the packer payload). The
  pattern-fill proof (the 1990 method) is still required across boot -> chart -> map view ->
  battle.
- The game's screen buffers move per screen ($1d500/$25200 at the map view); a payload must
  stay above the engine's tables ($71bxx) — `$72000+` does.

## 6. Baseline measurements (map view, snapshot `mapview.sav`)

[obs] Passes/s == fps here (speed period `$5a852 = 1`, every pass renders and flips):

| | 8 MHz | 16 MHz | ratio |
|---|---:|---:|---:|
| passes/s (= fps, map view) | 3.55 (earlier run 4.27) | 6.97 | **1.96x** |

The world is CPU-speed-coupled (the defect the tick port fixes; the 1990 game showed
2.1-2.9x). The map view is a low-detail scene; a battle will be slower (the 1990 baseline
was 2.4-4.0 fps there).

**Profile** (1200 VBL, raw `work/notes/profile16.txt` for 16 MHz; percentages of total cycles):

| page | 8 MHz | 16 MHz | what |
|---|---:|---:|---|
| `$08300` | **39.8%** | **40.5%** | the block-pattern combine loop `$8344..$83f0` (see 6a) |
| `$1bc00`/`$11c00` | **14.2%** | 11.6% | the timer-C YM sample player (`$1bc92+`, `movep` to `$ff8800`) |
| `$13a00` | **7.6%** | 7.7% | the 32K window copy (`$13a94`) |
| `$00900` | 6.3% | 3.1% | screen/UI code |
| `$0e800` | 3.2% | 3.2% | entity/HUD code |
| `$00e00` | 2.5% | 4.5% | flip/ACIA/waits |
| `$07500` | 1.9% | — | the blit primitive (`$7588`) |
| `$17400` | 1.9% | — | pathfinding (`divu` math) |

### 6a. The 40% renderer: a block-pattern combiner, not a triangle walker [disasm, obs]

**Correction to an earlier draft of this note:** the hot code at `$82C8-$83F0` is NOT
runtime-generated. It is static, hand-written, fully unrolled code, and the zeros at
`$8200-$82C1` are simply unused space before it.

The render tail `$74e0` (called once per pass from the main loop `$13e42`, and by the chart
screens from `$14b08`/`$14baa`/`$cb80`/`$d2f8`):
- sets the span limit `[$82c4] = draw_buffer + $7d00` (the 32000-byte window end),
- picks a pattern table `a6 = $8406`,
- walks up to 4 block descriptors in a table at `$74be` (each: a data offset into `$74c0`,
  a packed row/col position: row = 160-byte lines, column = 8 bytes per 4 px),
- per block: reads (height, width) then calls `$82c8` once per 4-pixel word across/rows down.

`$82c8` (the 40%): for each call it reads four plane-phase bytes, builds four pointers
`a6 + 12*row` with per-plane 2-bit phases (the shift table at `a6-8..a6-5`), then a
word-at-a-time loop:
```
move.w (a0)+,d4 ; rol.w d0,d4 ; andi.w #$f000,d4
move.w (a1)+,d5 ; rol.w d1,d5 ; andi.w #$f00,d5 ; or.w d5,d4
move.w (a2)+,d5 ; rol.w d2,d5 ; andi.w #$f0,d5  ; or.w d5,d4
move.w (a3)+,d5 ; rol.w d3,d5 ; andi.w #$f,d5   ; or.w d5,d4
move.w d4,(a5)+
```
(×4 unrolled, then `cmpa.l [$82c4],a5` / `bge`). About 20 instructions per 4 output pixels.
The four nibbles `$f000/$f00/$f0/$f` are the four columns of one 16-px word. `$82c8` through
its `rts` at `$83f0` is **byte-identical** to the 1990 font composer at `$8838` (296 bytes).
`a6` is not an anonymous pattern table: `$8406` matches the 1990 font at `$8976` (1536 bytes,
12 bytes differ, all in glyphs 124..127). Index `ch` selects block `48 * (ch >> 2)`, column
`ch & 3`. Colour 1 is the cell background. ASCII 32..126 decode as the letterforms, which is
why the panel text and the map patterns share this one blit. The "12*row" above is
`(ch & ~3) * 12`, the byte offset of that block.

So the WW1's map-view terrain is drawn as **positioned blocks of a dithered pattern**, at
4-pixel granularity through a per-plane rotate/mask/or combine — not as clipped triangles
walked per scanline. Consequence for the perf port: the 1990 `p6_tri`/`p6_slope` wins (exact
`divu` tables + chunked DDA) do not transpose — there is no per-triangle `divu` and no edge
walk in this hot loop. The candidates here are: a pre-shifted pattern cache or wider
unrolling (the 1990 game's own "pre-shifted pattern ring" idea), a table-driven combine, or
the STE blitter if its shift/mask can express the nibble interleave (to be studied; the
IKBD ACIA overrun rules apply to any long blitter burst).

**Performance verdict ("if applicable"): yes, the 1990 wins map onto three of these:**
1. **The YM sample player, 11-14% of all cycles** — the 1990 game's STE DMA-sound port
   (`snd_*`: 26.4% -> 4.9% there; the biggest single measurable win) applies directly: the
   same sequencer, the same `movep` register writes, the same `fal_ym` Falcon trap. Plain
   ST keeps the YM path.
2. **The 32K window copy, 7.6%** — the 1990 `p6_cpy` STE-blitter port (50 chunks of 4 rows;
   the IKBD ACIA overrun trap from `buserr.md` applies to every long blit).
3. **The terrain renderer, 40%** — the single biggest cost, but the WW1 mechanism differs
   (6a): the 1990 game clipped triangles and walked them per scanline (`p6_tri`/`p6_slope`
   with exact `divu` tables); the WW1 draws positioned **pattern blocks** through a
   per-plane rotate/mask/or combine at 4-pixel granularity. No `divu` and no edge walk in
   the hot loop; the 1990 patches do not transpose. This needs its own study (a pre-shifted
   pattern cache / wider unroll / table-driven combine / STE blitter feasibility).
4. The sprite blit `$7588` (1.9%) is the `p4_spr` analogue (smaller here than in 1990).
5. The pointer/VBL work (`$e00`, 2.5%) is the `p4_ptr` analogue (the 1990 win was 4-6%).

## 7. Limits / open questions

- The 50/60 Hz sync read (`$ff820a` bit 1) is [INFERENCE]: verify before relying on it.
- The four "logic" calls at `$13db4..$13dc6` are partly UI/HUD-ish (`$d712`, `$3276`); the
  tick head must decide whether they belong to the tick or the render (the 1990 game kept
  the HUD on the render path). Test by state equality, as the 1990 game did.
- The stage hand-over, the depacker transcription and the battle-scene snapshot are still
  open (P2/P4).
