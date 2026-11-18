# Powermonger main loop and the coupling of world speed to frame rate

All addresses are RAM addresses of the 1 MB STE TOS 1.62 run of `protected.st` (the game code is loaded low: `$1270-$1c300`, data above). Evidence: disassembly with `tools/m68dis.py` on `work/dumps/*.bin`, profiles in `work/prof/`.

## Interrupts
* **VBL handler `$1270`** (installed by the game): `addq.l #1,$6f304` (VBL tick, `$1286`), IKBD/mouse decode (jump table `$12ac`), and from `$13c4` a **software mouse pointer**: restore the 16 saved lines (`$1c49e`), draw the 2-word-wide masked sprite into the *back* screen buffer `$2df78` (`$1458-$14c0`). About 10k cycles per VBL (6-8 % of an idle frame). The handler does NOT set the flag the loop waits on in the normal case; `$2df8c` is set at `$1278` only when `$126e != 0`.
* **MFP timer A handler `$1af32`**: sample playback through the YM2149 volume registers (`movep.l d1,-$720f(a0)` with a0=`$fa0f`, `$1af58`), reading bytes from `$5c357`. About 3.7 kHz, ~270 cycles each: **12 % of an idle frame while a sample plays** (3333 IRQs in 45 VBL).
* No use of `$4ba`, `$462`, `$466` (the `$462`/`$466` hits found by byte search are data/operands, no code reads them), no MFP timer reads in the loop.

## The loop (`$12fd8` ... `bra.w $12fd8` at `$13888`)
One pass per presented frame. In `work/prof/*_stages.json` the call sites are timed with `e CycleCounter`.
```
12fd8  view limits from $57ffc (zoom), $4bb3a/$4bb3c (scroll x,y)
1302e  addq.l #1,$2df70      iteration counter (only when $57ff2 == 0)
13034  addq.l #1,$4bb3e      second copy
13040  jsr $127e6   \   logic
13046  jsr $6522    |   (small)
1304c  jsr $d322    |   proximity scan of the 160 captain-group records ($4e514, stride $20)
13052  jsr $3e06    /   captain/army upkeep, 6 captains of $13c bytes at $51538
13074  subi.w #1,$57ff0 ; bne -> skip   $57ff0 counts down from $57fee (game-speed divider, 1 = every pass)
13090  jsr $1870    wait for $2df8c != 0 (VBL flag) - the only wait in the loop
13096  jsr $12ce0   copy of the 3D window background (movem.l loop, ~170 k cycles)
130a4  jsr $178ae
130aa  jsr $f898    LANDSCAPE + OBJECTS (terrain triangles, objects interleaved per cell via $115e0)
130b0  jsr $1abaa   season/weather dissolve + `addq.w #1,$57fec` (see below)
130b6  jsr $17878 / 130bc jsr $165b2 / 130c2 jsr $14b62   HUD, overview map, status bars
130c8  jsr $6a3a / 130ce $7a56 / 130f6 $d23a / 130fc $7202   UI and windows (tiny)
1310x.. click/keyboard dispatch (compass, icons, overview) ...
1373c  keyboard table $2de6c: scroll ($4bb3a/c), rotate ($ff9a +-16), tilt ($ff96/$ff98), $ff9c, zoom ($57ffc +-1 -> $fe04)
1386c  jsr $187a    flip: swaps $2df7c/$2df78, `move.l d0,$8200.w` (video base), clears $2df8c
13872  jsr $1a276
```
Screens: two buffers (`$2df7c`, `$2df78` = `$1c700`, `$24400` in the snapshots), `$ff8201` toggles 1/2.

## Verdict: world speed is COUPLED to the frame rate (fixed step per loop pass)
Nothing in the simulation looks at a clock. The loop does `$2df70 += 1` and every simulation step is one increment per pass:
* A walking man's position words (person record offsets 8 and 10, see entities.md) change by **32 units per axis per pass** (`dx = 32*k` for k passes; 160 per 5 passes, 224 per 7, 480 per 15).
* `$57fec` (season/animation tick, `$1abcc addi.w #1,$57fec`) and `$4bb3e` rise by exactly 1 per pass.
* The only things per VBL are the mouse pointer, the sample IRQ, the VBL counter `$6f304`, and the loop wait `$1870` (so at most 50 passes/s; with `$57fee` > 1 the loop runs several passes per VBL wait).
* The manual agrees: "If you have a computer with an advanced processor, you might want to slow the game down" (game-speed track = `$57fee`).

Measured (emulated seconds = VBL/50; restores of the same snapshot; sampled with `ram_at_vbls` at +10/+110/+210/+310 VBL):

| snapshot | CPU | passes/s | flips/s (fps) | walking man L1 distance per pass | per emulated second |
|---|---|---|---|---|---|
| map_idle | 8 MHz | 2.0-2.5 | 2.33 | 12-28 | 24-60 |
| map_idle | 16 MHz | 6.0-6.5 | 6.17 | 23-41 | 150-249 |
| get_men | 8 MHz | 3.5-4.2 | 3.83 | 31-34 | 118-135 |
| get_men | 16 MHz | 8.0-8.5 | 8.17 | 25-32 | 210-277 |
| explore (dev snapshot, per-axis step 32 = same law) | 8 MHz | 3.5 | | 32/axis | 224/axis per 7 passes |
| explore | 16 MHz | 7.0-7.5 | | 32/axis | 2x per second |

Per pass the world advances identically; per emulated second it advances 2.1-2.9 times faster at 16 MHz. **Coupled**: men, clock tick `$57fec`, season/weather phase, camera scroll/rotate steps and animation all move per pass. Only the cursor, sample IRQ and VBL count are per VBL.
The full per-sample numbers are in baseline.md.

## What a fixed-rate tick would look like
The loop already contains the hook: `$57ff0/$57fee`. Passes are the unit of simulation, so a Midwinter-style decoupling is: let the logic stage (`$13040-$13052`, `$1abaa`, camera/key handling at `$1373c`) run once per fixed real-time tick derived from `$6f304` (VBL counter) and let the render stage (`$12ce0`, `$f898`, HUD, flip) run when the CPU allows, skipping the render when behind. Logic is ~2 % of a pass (stages table in baseline.md), so catching up several logic steps per render is cheap. [INFERENCE] untested: the render stage reads state the logic stage writes (people table, `$4bb3a/c`), and the order logic -> render inside a pass must be kept.
