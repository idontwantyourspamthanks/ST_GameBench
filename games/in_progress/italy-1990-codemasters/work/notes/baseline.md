# Italy 1990 (Codemasters) — Baseline Analysis & Reverse-Engineering Notes

## 1. Original Disk & Binary Layout
- **Source:** `originals/Italy '90 (1990)(Codemasters)[cr Hotline].st` (737,280 B, non-exec clean bootsector; `ITALY.TOS` is byte-identical to Birdy's crack, md5 `3ab489a4c996ca80cb5b661007b2ab6e`).
- **Structure of `ITALY.TOS` (337,333 B):**
  - Entry stub unpacks menu/loader to `$68000` -> copies to `$400..$12000` (`$11c00` B).
  - Copies two packed sub-game payloads into RAM:
    - `$12000..$2ff04` (`$1df04` B): **1: 11-A-SIDE SOCCER** (unpacks to `$400` via `$2c04`, jumps to `$400`).
    - `$2ff04..$581d8` (`$282d4` B): **2: SOCCER SKILLS** (unpacks to `$400` via `$2c04`, jumps to `$400`).
  - `hwscan.py` on unpacked 11-A-SIDE SOCCER (`$400..$20000`): **0 `crit`**, 100% plain 68000 ST code (zero STE Blitter, zero STE HSCROLL, zero STE DMA sound).

## 2. Baseline Performance (8 MHz STE, TOS 1.62)
Measured from `work/snapshots/match_baseline.sav` during active 11-a-side play:
- **Frame rate:** **22.40 fps** (`112` frames in `250` VBLs = **2.23 VBLs/frame**, oscillating between 25 fps and 16.7 fps).
- **CPU Profile (150 VBLs, 19,281,208 cycles):**
  - `$6000–$61ff` (**23.38%**): Pitch tilemap software copy (`$5fc2`, `movem.l` loop redrawing 8×6 32×32 tiles = 256×168 px every frame).
  - `$4900–$4aff` (**23.01%**): Software 16px masked sprite blitter (`$4930`, `ror.l/rol.l` + `and.w/or.w` per scanline for every player, shadow, number, and ball).
  - `$230a–$231a` (**18.18%**): VBL spin wait (`cmp.w $1213a, d0`).
  - `$a000–$a6ff` (**~8%**): Player AI + update loop.
  - `$cd00–$cdff` (**4.16%**): Bottom HUD bar redraw.
  - `$7700–$77ff` (**2.65%**), `$c000–$c0ff` (**2.41%**): Partial pitch tile clip & sprite Y-sort.

## 3. 11-A-SIDE SOCCER Engine Map (Unpacked RAM)
- **Screen buffers:** `$11cf6` (`$70000`) and `$11cfa` (`$78000`), swapped at `$d2f0`.
- **Interrupts:**
  - VBL: `$226c` (`$70.w`)
  - Timer B (HBL split at line 168 for bottom HUD): `$3980` (`$120.w`)
  - IKBD: `$2444` (`$118.w`), latest scancode stored at `$11d00.l` (`X` key = `$2d`).
- **Free RAM (inside 512 KB):** `$3a000–$3cfff` (12 KB empty); on 1 MB+ STE/Mega STE/TT/Falcon, `$80000–$fffff` (512 KB completely free).
- **Main Match Loop (`$d272–$d334`):**
  - `$d272`: `jsr $230a` — Wait 1 VBL (`$1213a`).
  - `$d278`: `jsr $d488` — Camera Y tracking (`$fd68` camera vs `$fb98` ball).
  - `$d27e`: `jsr $b2a8` — Camera Y velocity -> position clamp (`0..$410`).
  - `$d296–$d2a4`: Copy `camX` (`$fd68+2`) -> `$ee50`, `camY` (`$fd68+4`) -> `$ee4c`.
  - `$d2ac`: `bsr $5fc2` — **3-column horizontal flip (`camX = 0 / $c0 / $180`) + pitch tilemap copy**.
  - `$d2b0`: `bsr $aad8` — Ball boundary / goal / throw-in / corner / goal-kick check (`X` playable `$16..$25a`).
  - `$d2b4`: `bsr $b4d4` — Active player auto-switch (`$ee10..$ee16`).
  - `$d2b8`: `bsr $a09e` — **All 22 players update loop** (`$f0b8`, stride `$3a` = 58 bytes).
  - `$d2bc`: `bsr $9f82` — Goalkeepers (`P00` at `$f0b8`, `P11` at `$f336`).
  - `$d2c0`: `bsr $9456` — Set pieces / GK kick / throw-in states.
  - `$d2c4`: `bsr $bc34` — Frame/animation counters (`$edf2`, `$edf4`, `$edee`).
  - `$d2c8`: `bsr $bccc` — Visible sprite culling & queuing (uses `$ee50` = `camX`, `$ee4c` = `camY`).
  - `$d2cc`: `bsr $c020` — Y-sort & sprite draw (calls `$4930`).
  - `$d2d0–$d2d8`: `$9000`, `$cd52`, `$ce78` — HUD / clock / score bar.
  - `$d2f0`: Screen flip (`$11cf6` <-> `$11cfa`, writes `$ff8203`/`$ff8201`).

## 4. Pitch Tilemap & 3-Column Flip (`$5fc2`)
- **Tilemap:** `$122e6`, **20 tiles wide × 38 tiles tall** (`640 × 1216` px total stadium).
- **Tileset:** `$2d770`, **32×32 px** tiles (`$200` = 512 bytes each, 4 bitplanes).
- **Current 3-column flip (`$5fdc–$6028`):**
  - `ball.x <= $ce` (206): `camX = 0`, tile col offset `0`
  - `$ce < ball.x <= $19c` (412): `camX = $c0` (192), tile col offset `6`
  - `ball.x > $19c` (412): `camX = $180` (384), tile col offset `12`
- **Viewport:** Currently 8 tiles wide = **256 × 168 px** centered (`+$10` bytes = +32 px left margin).

## 5. Player & Ball Structs & Why Original AI Is Terrible
- **Ball struct (`$fb98`):** `+$02` = `x`, `+$04` = `y`, `+$08` = `vx`, `+$0a` = `vy`, `+$0c` = `z` (height).
- **22 Player structs (`$f0b8`, stride `$3a` = 58 bytes):**
  - `P00` (`$f0b8`) = Team 1 GK, `P01..P10` = Team 1 outfield.
  - `P11` (`$f336`) = Team 2 GK, `P12..P21` = Team 2 outfield.
  - Key fields: `+$00` ID (`0..21`), `+$02` `x`, `+$04` `y`, `+$08` `vx`, `+$0a` `vy`, `+$1c` anim/dir, `+$20` chase target dir, `+$24` controller (`0`=AI, `1..4`=Human, `6`=auto-chase), `+$26` facing (`0..7`), `+$32` special action state.
- **Original AI (`$a5fc`):**
  - Updates only 5 players per frame (`$ee54 & 3`).
  - Quantizes ball `(x, y)` into a coarse 128×128 px grid cell and reads a static `(target_x, target_y)` table at `$11362`.
  - Walks slowly toward that static coordinate and turns to face the ball (`$b466`). No pressing, no marking, no support runs, no dynamic formation scaling.
- **CPU Ball-Carrier (`$b8c4`, called from `$ca8a`):**
  - Returns a virtual joystick byte (U/D/L/R + Fire) for the CPU player currently with the ball.
