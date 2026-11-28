# Entombed — Technical Research Notes

**Game:** *Entombed* by Nick Concannon (ST Format Issue 30 coverdisk, `SIDE_2\ENTOMBED\ENTOMBED.PRG`)  
**Architecture:** Pure hand-written 68000 assembly (single TEXT section + BSS, no copy protection, TOS/XBIOS-clean).

---

## 1. Binary & Memory Footprint

`ENTOMBED.PRG` on disk is 51,568 bytes — a self-extracting packed TOS executable (`TEXT=0x1b2` depacker stub, `DATA=0xc79e` packed PRG payload, `BSS=0x11194`). Once unpacked and relocated in RAM (example load at basepage `$012476` on TOS 1.62):

| Segment | Address (TOS 1.62) | Size | Contents |
|---|---:|---:|---|
| `TEXT` | `$012576 .. $02f9bc` | 119,878 B (`$1d446`) | All 68000 code (`$012576..$018127`, ~23.5 KB), tables/vars (`$018128..$0193ff`), all 5 levels (`$019400..$01f9b3`, ~26 KB), graphics & sound (`$01f9b4..$02f9bc`, ~65.5 KB, marked by `##GRAP##`) |
| `DATA` | — | 0 B | Everything assembled in one section |
| `BSS` | `$02f9bc .. $063e12` | 214,102 B (`$34456`) | Double-buffered screens (`$02fa00` / `$037a00`), pre-shifted tile buffers, primary tilemap (`$05a1bc`, 3,840 B), alternate tilemap (`$05b0bc`, 3,840 B), per-tile object pointer map (`$05bfbc`, 15,360 B), change schedule (`$05fbbc`), active entity pool (`$061bbc`), tile properties (`$063bbc`, 256 B), switch state array (`$063cbc`, 256 B) |
| **Total** | `$012476 .. $063e12` | **333,980 B (~326 KB)** | Fits comfortably in a **512 KB STfm** (~150 KB free) and leaves **~650 KB free on a 1 MB STe** |

**Hardware / OS interface:**
- Pure XBIOS/GEMDOS: `Setscreen` (XBIOS 5), `Setpalette` (XBIOS 6), `Vsync` (XBIOS 37), `Dosound` (XBIOS 32), `Kbdvbase` (XBIOS 34) + `Ikbdws` (XBIOS 25) for joystick reporting.
- Uses **zero** STe hardware today: no Blitter, no STe hardware scroll, no DMA audio.
- Runs identically on **512 KB STfm (TOS 1.04)** and **1 MB STe (TOS 1.62)**.

---

## 2. Where Is the Frame Budget Going?

Measured in Hatari (50 Hz PAL, 8 MHz 68000, cycle-exact) in **Tomb 1**:
- **512 KB STfm (TOS 1.04):** `16.67 FPS` (**3.0 VBLs/frame**, 66–67 flips per 200 VBLs)
- **1 MB STe (TOS 1.62):** `16.67 FPS` (**3.0 VBLs/frame**, 66–67 flips per 200 VBLs)

### Per-Frame Cycle Breakdown (Tomb 1, steady-state gameplay)

One 50 Hz PAL VBL = **160,256 cycles**. Three VBLs = **480,768 cycles**.

| Subsystem | Address | % of CPU | Cycles / Frame | VBLs | What It's Doing |
|---|---|---:|---:|---:|---|
| **Tilemap draw** | `$0136e2..$01451e` | **66.3%** | ~317,800 | **1.98** | Redraws the entire 320×192 playfield (10×12 tiles of 32×16 px) from scratch every frame using `movem.l` + `or.l` + **4× `movep.l`** per scanline |
| **Dynamic shadow pass** | `$01353e..$0135a4` + `$0136ae..$0136e0` | **7.8%** | ~37,500 | **0.23** | Scans all 11×13 visible tiles *twice* per frame: mutates tiles into shadowed IDs before drawing, then restores them back after drawing |
| **HUD text/status bar** | `$01794c`, `$017976` | **5.3%** | ~25,300 | **0.16** | Redraws the entire bottom 8 px status strip every frame with `movep.l` |
| **Game logic, sprites & flicker** | `$015f62`, `$016682`, `$012e7e`, `$014c36`, `$01451e`, `$015010` | **6.1%** | ~29,400 | **0.18** | Player physics, camera, enemies/traps/projectiles, sprite blitting, tomb-change flicker swap |
| **Total Active Work** | | **85.5%** | **~410,000** | **2.56** | Exceeds 2 VBLs (320,512 cyc) by ~90k cycles → drops to 3 VBLs |
| **Vsync idle wait** | `$e00000` (TOS ROM) | **13.8%** | ~66,400 | **0.41** | Busy-waiting in XBIOS `Vsync()` for VBL #3 |

### Key Takeaways
1. **74.1% of the entire frame (2.22 VBLs)** is spent in a single function: **`$013504` (the full-screen tilemap renderer)**.
2. **All actual gameplay + sprites + HUD combined is only ~54,700 cycles/frame (~34% of a single 50 Hz VBL)!** Without the HUD redraw (only needed when lives/score/inventory/delay changes), game logic + sprites is just **~29,400 cycles/frame (18.4% of 1 VBL)**.
3. **Why is the tilemap renderer so slow?**
   - It uses `movep.l` (24 cycles per instruction × 4 per 32px scanline = **96 cycles** just for screen writes, plus `movem.l` + `or.l` = **~156 cycles per 32×1 strip**, × 10 tiles × 192 lines ≈ **300,000+ cycles**).
   - It re-renders all 120 tiles every frame even when the camera hasn't moved at all!
   - It recomputes and reverts drop-shadow tile IDs on the live map every single frame instead of baking them on level load / tile-swap.

---

## 3. Why Movement Feels Slow (and How to Speed It Up)

All gameplay physics, animations, enemy patrols, projectiles, and tomb-change timers are **100% frame-coupled** (1 tick per rendered frame, no VBL delta-time):

- **Horizontal walk / jump / fall (`$0147ce`, `$01480e`, `$01494a`, `$014a46`, `$014bc6`):** `±2 px/frame`
  - At **16.67 FPS**: `2 × 16.67 = 33.3 px/sec` (~9.6 seconds to cross one 320px screen!).
  - Why 2 px/frame? The original tile renderer pre-shifts tiles into 4 horizontal phases (0, 2, 4, 6 px), so camera X (`$18142`) must stay a multiple of 2.
- **Vertical jump (`$014798`, `$01495e`):** `-4 px/frame` for 7 frames (`$19230 = 7`, total height 28 px), then falls at `+4 px/frame`.
- **Ladder climb (`$014b7c`, `$014b96`):** `±4 px/frame`.
- **Camera deadzone (`$014ee0..$014fe4`):** Tracks player directly (`cam_x += dx`, `cam_y += dy`) whenever Ya Salam crosses `[cam_x + $80 .. cam_x + $a0]` horizontally or `[cam_y + $48 .. cam_y + $60]` vertically.

### Speed-Up Options
1. **25 FPS (2 VBLs/frame) with 1:1 physics:** Instant **1.5× speed & 1.5× smoothness** (`50 px/sec` walk, zero jump-arc changes, preserves every single puzzle timing ratio).
2. **50 FPS (1 VBL/frame) with selectable / tuned pacing:**
   - **Option A (1.5×–2× feel at true 50 Hz visual smoothness):** Run physics at 25 Hz (every 2nd VBL) with 1-px interpolated camera/sprite motion on STe, OR run physics at 33–50 Hz with slightly tuned walk speed (`±2 px/frame` at 25 Hz = `50 px/sec`, or `±1 px/frame` at 50 Hz = `50 px/sec` on STe hardware scroll, or `±2 px/frame` at 33 Hz = `66.7 px/sec`).
   - **Option B (Selectable "Classic / Fast" speed toggle):** Keep all jump heights/distances identical by adjusting tick rate (e.g. 25 Hz = 1.5× speed, 33 Hz = 2.0× speed) while rendering at 50 FPS!
   - **Note on tomb-change timer (`$1815e`):** Increments by `+1` per game frame (`$0128ce`). If we raise the frame rate, we should either keep logic/timer ticking at the chosen gameplay Hz or scale the delay/timer countdown so hourglass seconds still match real-world seconds.

---

## 4. Optimization Paths: 512 KB STfm vs. 1 MB STe

Because non-tilemap work is only **~30–55k cycles/frame** out of a **160,256-cycle** 50 Hz VBL budget, **50 FPS is achievable on BOTH machines**!

### A. Bog-Standard 512 KB STfm (No Blitter, No HW Scroll)
Can a plain 512 KB STfm hit **25 FPS** or even **50 FPS**? **YES!**

1. **Easy 25 FPS (zero architecture change):**
   - **Bake drop-shadows** on level load + tile-change instead of scanning/restoring 11×13 tiles every frame → saves **~37.5k cyc/frame**.
   - **Dirty-flag the HUD** (only redraw when lives/score/items/delay change) → saves **~25k cyc/frame**.
   - **Replace `movep.l` with interleaved word/long `movem.l` stores** (or fast word-aligned blitting when `cam_x & 15 == 0`, or 16-bit word-packed pre-shifted tiles): writing 16 bytes (32px × 4 planes) via `movem.l d0-d3,(a2)` takes **40 cycles** instead of `4× movep.l` (**96 cycles**) — cutting the tile renderer from ~318k down to **~170–190k cycles**!
   - Total frame time: **~210–230k cycles** → locked **25 FPS (2 VBLs)** on 512 KB STfm with plenty of headroom!
2. **True 50 FPS on 512 KB STfm (Incremental / Ring-Buffer Scroll + Dirty Tiles):**
   - Instead of redrawing all 120 tiles every frame, maintain a **clean background ring-buffer** (slightly larger than 320×192, e.g., 352×208 = ~36 KB — fits easily in 512 KB's ~150 KB free RAM!).
   - Only draw the **newly scrolled edge strip** (at most 1 column = 12 tiles or 1 row = 10 tiles) + any **animated/flickering tiles** (~10–20 tiles/frame max = **~25–40k cycles**!), then copy/blit or restore sprites over it!
   - Wait: without STe HW scroll, shifting a 320×192 playfield by 2px still needs a screen copy (~120k cyc via `movem.l`) unless you scroll in 16px steps or use **4 pre-shifted full-screen buffers / sync-scrolling**. With pure CPU `movem.l` tile blit + dirty-only when stationary:
     - **Stationary camera:** 50 FPS easily (~45k cyc/frame).
     - **Scrolling camera:** Locked **25 FPS** on STfm (very smooth, 1.5× original), or **50 FPS** if scrolling with a 4-phase pre-shifted word-copy buffer (~110k cyc copy + 30k logic = ~140k < 160k!).

### B. 1 MB STe (Hardware Scroll + Blitter + DMA Audio)
On a **1 MB STe**, the hardware is practically *tailor-made* for Entombed:

1. **STe Hardware 8-Way Scrolling (`$ff820d` low-byte base, `$ff820f` line-width modulo, `$ff8265` fine H-scroll 0..15):**
   - Gives **1-pixel smooth 8-way scrolling** with **ZERO full-screen redraws** and **ZERO pre-shifted tile copies**!
   - We allocate a wide virtual playfield buffer (or a **352×224 rolling/ring buffer** in the ~650 KB free RAM, or even a **screen-wrapping 512-wide buffer** — wait: an entire 80×48 level is `2560×768` = 983 KB, too big for 1 MB, so a **rolling ~384×256 buffer (~49 KB × 2 for double-buffering = ~98 KB)** is ideal!).
   - Each frame, we only draw:
     - Newly revealed edge tiles when scrolling (0 to ~13 tiles/frame)
     - Any flickering / animated (`+`) tiles currently on-screen
     - Restore old sprite backgrounds + draw active sprites!
   - **Cycle cost:** **< 15,000–25,000 cycles/frame** for the entire tilemap!
   - Combined with ~30,000 cycles of game logic + sprites = **~50,000–60,000 cycles/frame = 35% of ONE 50 Hz VBL → ROCK-SOLID 50 FPS** with **100,000+ cycles/frame to spare!**
2. **STe Blitter (`$ff8a00..$ff8a3d`):**
   - **Tile blitting** into the rolling buffer (16-pixel-aligned 32×16 tiles, 4 planes): ~1,600 cycles per tile (vs ~2,650 CPU cycles), zero pre-shift RAM needed!
   - **Sprite save/restore & masked blitting** (Ya Salam, mummies, skeletons, arrows, platforms): hardware barrel-shifter (`$ff8a3d` skew) + endmasks (`$ff8a28..$ff8a2c`) eliminates all software bit-shifting for 1-pixel sprite placement!
   - **HUD bar** (split-screen via Timer B HBL at scanline 192 so the HUD stays rock-steady at the bottom while the top 192 lines use STe hardware scroll!).
3. **STe DMA Audio (`$ff8900..$ff8924`):**
   - Original game uses **XBIOS `Dosound`** (YM2149 PSG beeps/swooshes, ~16 short sound effects in `$01851c`) and has **no in-game music**.
   - With ~100,000 free CPU cycles/frame and ~500+ KB free RAM on 1 MB STe, we can add **zero-CPU-cost 8-bit DMA sound effects** (footsteps, bow twang, arrow thud, trap clicks, boiling water/fire ambience, chime on pickup) and/or **ambient Egyptian DMA music / YM chiptune**!

---

## 5. Complete Level Data Structure (100% Byte-Accurate across All 5 Tombs)

Verified with a Python parser against all 5 levels in `ENTOMBED.PRG` (**0 unparsed bytes** on Tomb 5; trailing `.` buffer padding on Tombs 1–4).

### 5.1 Level Pointer Table (`$0191e8`)

5 big-endian 32-bit pointers (Tombs 1–5):

| Tomb | RAM Addr | Offset from `TEXT` (`$012576`) | Size | Active Rooms | Timed Events | Start `(x, y)` | `cam_max (x, y)` | Timer Param |
|---|---:|---:|---:|---:|---:|---|---|---:|
| Tomb 1 | `$019400` | `$6e8a` | 2,782 B | 7 / 32 | 20 | `(416, 152)` | `(1312, 208)` | 5 |
| Tomb 2 | `$019ede` | `$7968` | 3,738 B | 9 / 32 | 74 | `(34, 472)` | `(1632, 576)` | 16 |
| Tomb 3 | `$01ad78` | `$8802` | 4,444 B | 12 / 32 | 53 | `(1088, 688)` | `(2240, 576)` | 21 |
| Tomb 4 | `$01bed4` | `$995e` | 5,220 B | 14 / 32 | 41 | `(480, 264)` | `(1632, 576)` | 32 |
| Tomb 5 | `$01d338` | `$adc2` | 9,852 B | 32 / 32 | 41 | `(992, 680)` | `(2240, 576)` | 80 |

*(Immediately followed by `##GRAP##` at `$01f9b4`.)*

### 5.2 Level Header (42 bytes)

```
+0x00  uint16  start_x       ; Ya Salam starting X in world pixels
+0x02  uint16  start_y       ; Ya Salam starting Y in world pixels
+0x04  uint16  cam_max_x     ; Max horizontal camera scroll (pixels)
+0x06  uint16  cam_max_y     ; Max vertical camera scroll (pixels)
+0x08  uint16  timer_param   ; Shifted << 12 into $192da
+0x0A  char[32] room_grid    ; 8×4 grid of ASCII '0' (absent) / '1' (present), row-major
```

- World dimensions: **8 rooms wide × 4 rooms tall** = 32 rooms.
- Each room: **10 tiles wide × 12 tiles tall** (`320×192` pixels = 1 screen).
- Full runtime tilemap: **80 × 48 = 3,840 (`$f00`) tiles**.
- Absent (`'0'`) rooms are auto-filled with solid wall (`$19`/`$1a` alternating by row) in the primary map (`$5a1bc`) and empty (`$18`) in the alternate map (`$5b0bc`).

### 5.3 Room Records (1 per `'1'` in `room_grid`, row-major)

Each present room consists of:
1. **240-byte ASCII tile grid** (12 rows × 20 chars):
   - Columns `0..9` → **Primary tilemap** (`$5a1bc`)
   - Columns `10..19` → **Alternate tilemap** (`$5b0bc`, used for tomb-change swaps/flickers)
2. **`N` Object/Entity/Trap/Trigger descriptors**, where `N` = count of uppercase anchor letters `'A'..'Z'` (excluding `'B'` and `'K'`) appearing anywhere in that room's 240-byte grid!

**Static Tile Characters (`$0182b8`, 37 entries) & Tile Property Flags (`$063bbc`):**

Property bits: `bit 7` = casts shadow, `bit 6` = collectible/interactive, `bit 5` = solid floor, `bit 3` = deadly hazard, `bit 2` = blocks arrows, `bit 1` = solid wall, `bit 0` = ladder/ceiling.

| Char | Tile ID | Props (`$63bbc`) | Meaning |
|---|---:|---:|---|
| `.` | `$18` | `$00` | Empty background |
| `0`, `1` | `$19`, `$1a` | `$ab` | Solid tomb brick (auto-tiled bevels/corners on load!) |
| `~`, `#` | `$1d`, `$1e` | `$ab` | Alternate solid wall / stonework |
| `2`..`6` | `$3b`,`$3a`,`$3c`,`$3d`,`$3e` | `$ab` | Decorative solid walls |
| `-` | `$1c` | `$20` | One-way platform (standable, pass-through from below) |
| `\|` | `$20` | `$01` | Ladder (auto-connects top/middle via `$41`/`$42`) |
| `]` | `$21` | `$00` | Ladder / background decoration |
| `=` | `$1f` | `$00` | Background / beam |
| `^`, `<`, `>`, `\` | `$24`–`$27` | `$0c` | Spikes (up, left, right, down — deadly + blocks arrows) |
| `f`, `g` | `$01`, `$00` | `$09`, `$08` | Fire hazard (deadly) |
| `w`, `x` | `$03`, `$02` | `$09`, `$08` | Boiling water / Perrier (deadly) |
| `_` | `$05` | `$08` | Floor hazard (deadly) |
| `*` | `$04` | `$00` | Decoration / animation tile |
| `{`, `}` | `$22`, `$23` | `$04` | Wall launcher (left/right) |
| `)`, `(` | `$14`, `$15` | `$04` | Aimed/special launcher (Tomb 5) |
| `B`, `K`, `A`, `H`, `P`, `T`, `0x9c` | `$28`,`$1b`,`$29`,`$2e`,`$36`,`$2f`,`$3f` | `$40` | Pickups & triggers (Bow, Key, Arrows, Hourglass, Treasure, Switch, Exit!) |

**Anchor Object Descriptors (immediately after the 240-byte room grid):**

Every descriptor starts with `[anchor_letter: 'A'..'Z'] [type_char] [params...]`:

| Type | Param Size | Tile Placed | Handler | Description |
|---|---:|---:|---:|---|
| `A` | 1 B | `$29` | — | **Arrows pickup** (`count`) |
| `B` | 0 B | `$28` | — | **Bow pickup** |
| `K` | 0 B | `$1b` | — | **Key pickup** |
| `H` | 1 B | `$2e` | — | **Hourglass pickup** (`delay_seconds`) |
| `P` | 1 B | `$36` | — | **Treasure / Points / Extra life** (`type`) |
| `D` | 1 B | `param[0]` | — | **Direct raw tile ID override** |
| `T` | 2 B or 15 B | `$2f` | — | **Switch** (`switch_id, value` → writes `$63cbc[id]`), OR if `param[0] == $ff`: **Checkpoint** (15 B: `$ff`, tile, tile_above, `px(u16)`, `py(u16)`, bows, arrows, keys, delay, `timer(u16)`, change_idx, pad) |
| `C` | var (`$fe`-term) | `$2c` | — | **Container / Breakable / Sub-script block** |
| `U` | 1 B + `$fe`-term | `$2a` + `$2b` above | `$0170de` | **2-tile Locked Door / Triggered Spawner** (spawns embedded `$fe`-terminated descriptors via `$0157ce` when opened!) |
| `-` | 4 B | `$30` | `$01686e` | **Moving Platform** (`dx_min, dx_max, speed, phase`) |
| `+` | 9 B | `param[0]` | `$017036` | **Cycling / Disappearing / Switch-controlled Tile** (`tileA, tileB, t1, t2, t3, t4, switch_id, init_state, flag`) |
| `{` / `}` | 6 B | `$22` / `$23` | `$016732` | **Wall Arrow Launcher (L/R)** (`delay, period, speed, switch_id, init_sw, flag`) |
| `)` / `(` | 12 B | `$14` / `$15` | `$0167d0` | **Special / Aimed Launcher** (Tomb 5: 3×u8 + 2×u16 + 5×u8) |
| `M` | 5 B | `$30` | `$0168ea` | **Mummy enemy** (`dx_min, dx_max, speed, dir, param`) |
| `S` | 6 B | `$30` | `$016e1e` | **Skeleton / Shooter enemy** (`dx_min, dx_max, speed, dir, fire_rate, param`) |
| `Q` | 5 B | `$30` | `$016c50` | **Flying / Bouncing enemy** (Tomb 5) |
| `X` | 5 B | `$30` | `$016aa4` | **Tomb 5 Guardian / Hazard / Portal** |

### 5.4 Timed Layout Change / Flicker Schedule (`$015ee0..$015fd6`)

Immediately after the last room's descriptors is the tomb-change script, terminated by `$ff`:

- Each event begins with a **16-bit big-endian frame timestamp** `T` (stored as `T + $8000` in `$5fbbc`, compared against the frame counter `$1815e` which starts at `$8000`).
  - Before `T` arrives, when within the warning window, the main loop (`$01274e` / `$0128bc`) swaps the tiles between `$5a1bc` and `$5b0bc` *before* drawing and swaps them right back *after* drawing → **visual flicker while preserving original collision**!
  - When `T` is reached, the swap becomes permanent and sound `$0f` plays.
- Inside each event:
  - **Room selector byte** (bit 7 set): `0x80 | (room_x << 4) | room_y` (`room_x ∈ 0..7`, `room_y ∈ 0..3`)
  - One or more **horizontal tile runs**: `(length_minus_1: u8, (local_x << 4) | local_y)`
  - Terminated by `$ff` (end of event) or another byte with bit 7 set (next room in the same event).

---

## 6. Ideas to Discuss Next

1. **Performance target:** Dual-path (STe HW scroll + Blitter = locked 50 FPS; STfm 512 KB = fast `movem.l` + baked shadows + dirty HUD = locked 25 FPS or 50 FPS ring-buffer)?
2. **Game speed / feel:** 25 Hz logic (1.5× speed, classic physics) vs. selectable Normal / Turbo speed, and 1-pixel smooth scrolling on STe!
3. **STe Audio:** Add DMA SFX and/or ambient Egyptian music alongside the YM2149?
4. **Level Editor:** Because the format is clean ASCII grids + compact typed descriptors + timed swap runs, we can build a slick standalone Python/web visual level editor that reads/writes all 5 tombs (and custom tombs!) directly and injects them into an unpacked/patched `ENTOMBED.PRG`!
