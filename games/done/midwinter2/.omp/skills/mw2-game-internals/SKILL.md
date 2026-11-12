---
name: mw2-game-internals
description: Reverse-engineered map of Midwinter 2 (Atari ST, HAGA HD build by PP): files and disk-image format, boot and loading pipeline, memory map, frame loop, renderer hot spots and costs, timing model, input and controls pipeline, and key RAM variables. Use when reading disassembly, choosing a patch site, or reasoning about game behaviour. Each fact points to the work/notes file holding its evidence.
---

# Midwinter 2: internals

No source. Facts come from disassembly of `work/dumps/ram_ingame_lobos.bin` (address = file offset) and from Hatari runs. Disassemble with `python3 tools/m68dis.py <dump> <hex> [--profile work/prof/walking.txt] [--xref hex] [--callers hex]`. A function runs to the next call target.

## Files and loading (`work/notes/loading.md`)
- **`RUNME.TOS`** is PP's loader.
  - It is LZ self-packed: the depacker is in the first 230 bytes, and an unpacked copy is `work/dumps/RUNME_unpacked.tos`.
  - It loads HAGA (hardware detection, clock/cache menus), the intro picture, then the boot stub.
- **`FILES/FFA..FFC`** are raw 720 KB images.
  - Tracks are interleaved: offset = track·9216 + side·4608 + (sector−1)·512.
  - Each image starts with a 1536-byte directory: magic `grafix00`/`mission0`, then 191 × 8-byte entries `[xor-cksum][offset-in-track][start track-side][u24 len]`.
  - **Files are uncompressed** and checksummed.
  - FFD is the campaign disk; it is blank until War Room → Start New Campaign. FFE is personnel.
- **Boot:**
  - FFA file 8 loads to `$806-$3104`, and file 9 to `$3104-$3DB10` (all the resident code).
  - Then PP's patcher runs at `$4BC-$59C`, which ends `jmp $3104`.
  - `$18d96...` (the sky fill etc.) arrives later from FFB file 1.
- **Runtime reads:** PP's service Freads 200 KB chunks into `$81000`, and the game copies them on.
  - The service code is the **HAGA** file, copied verbatim to phystop−$8000 (`$F8000` on 1 MB, `$1F8000` on 2 MB).
  - In the original, it faded the palette to grey and back once per chunk read. `pp_nofade` removes that (`work/notes/load_fade.md`).
  - The per-file completion point is `sub_278A6` rts `$2794A`.
  - Our hook is at `$2789A`, the exit of `sub_2783E`.
- **Free RAM:** `$B2852-$E83E5` on 1 MB in game. PP's 1 MB service sits at `$F7554`. 512 KB is impossible.

## Video and frame loop (`frameloop.md`)
- Low res 320×200, 4 interleaved planes, 160 bytes/line.
- Double-buffered at `$60000/$70000`.
  - The flip is `sub_26E98` (`jsr $4f36` at `$315c6`), and it writes only `$ff8201`.
  - `$67a6` is the draw target; `$67aa` is the buffer displayed.
- **The in-game loop runs `$31486-$315de`:**
  - Logic block: `$31486-$315a4`.
  - Render gate: `tst $6298` (non-zero = skip render).
  - `clr.w $7020` at `$3159c`.
  - Render: `jsr $5056` → `$1dbbe`, about 83% of the frame.
  - Post-render calls, then the flip.
  - There is no VBL wait; it is fully CPU-bound. Baseline: about 4.2 fps (12 VBL/frame) at 8 MHz on 1 MB.
- **VBL handler `$26298`:**
  - `$262c8` joystick poll `$26b58`.
  - `$26c1e` keyboard ramp.
  - `$262d0` increments `$7020` (cleared every frame) and `$770c` (wraps at 6).
  - The hook pointer is `$5138`.

## Renderer costs (walking, `work/prof/walking.txt`; notes in `spanfill.md`, `f38cd0.md`, `projection.md`, `clears_blits.md`)
| Area | Share | Notes |
|---|---|---|
| `$38cd0` span filler | 12.5% | About 112 unrolled 4-plane variants. Dither-pattern fills; KEEP the dithering. |
| `$3c5e2`/`$3c5c4` edge walker | 10.5% | Writes {offset, mask} per scanline to `$7b6b0`/`$7b9d0`. Setup optimised by `p4_walk`. |
| `$1fdf0`, `$1fa54`, `$3c02a`, `$3c080`, `$3bfa2`, `$200b4` | about 15% | Transform, clip, project. 2.14 matrix at `$17fc6`; focal `$682a` = 164. |
| `$1d768` terrain-grid init | 4.5% | 32×32×16 B at `$6c000`. Fields +6/+8 are per-frame scratch. Optimised by `p4_grid`. |
| `$1b996` sky fill | 4.4% | `movem` fill of lines 58–199. The blitter does not help. |
| `$30f2c` HUD overlay replay | about 3% | Static masked cockpit, redrawn every frame. Under study (`work/notes/cockpit.md`). |

The profile is flat, so gains come from many 1–3% wins.

## Simulation timing (`simtiming.md`, `tick_inventory.md`)
- The original game uses a fixed step per FRAME with no dt, so game speed scales with fps. It is 2.3× faster at 16 MHz.
- **Player integration:** `$31570 jsr $33bca` → `sub_033bde` → `$344ac`.
  - Position: `$66e6/$66ea` (long). Heading: `$6742`, 10-bit even, mirrored to `$6294`/`$764a`.
  - Bank `$6746`, pitch `$674a`, throttle `$6750`, speed `$6772`.
  - Route/altitude accumulator: `$764c`, which drives the HUD distance `$66e2` → `$6888`.
- **Game clock:** `$eb8c`, in minutes. Countdown `$6290` reloads to 32, so there are 33 ticks per game minute.
- **`$6220`** is the player type: 13 = on foot, 1 = parachute, 5/21 = others. 22 types, each with a control-parameter block at `$54dc0 + type·$3e`.
- **Shipped:**
  - Option A: fixed 5 Hz logic, 10 VBL per tick.
  - Partial B on top: the on-foot player moves in 1/5 sub-steps at 25 Hz, and the world block runs every 5th sub-tick.

## Controls (`controls.md` + corrections in `controls_joystick_check.md`, `p5_controls.md`)
- **IKBD handler `$26882`:**
  - Mouse packets `$f8-$fb` are accumulated into 16.16 `$6fb6` (Σdx) and `$6fba` (−Σdy). They were never cleared: that is the "yoke".
  - Joystick `$ff` → `$26b58`.
  - Keys go to table `$7686`.
- **Per-mode feeds:** the mouse is gated by `$eb7a`, the joystick (`$26b58`, J mode only) and the keyboard ramp (`$26c1e`, K mode only) all feed `$6fb6`.
  - controls.md's "joystick steering is dead code" is WRONG.
- **Consumers:** X at `$34152` (`bsr $347f2`), Y (throttle) at `$341dc` (`bsr $3481e`). Then deadzone/clamp from the type block, then `$6766`/`$6768`, then the heading or bank apply.
- **Direct-control patches** (`p5_ctl_*`) replace the X path. Tunables: `MOUSE_GAIN`, `YAW_PCT`.

## Other variables
| Address | Meaning |
|---|---|
| `$700a` | UI context (2 in game) |
| `$6298` | Render gate |
| `$676e` | Probe/collision result |
| `$66ee/$66f2/$66fe` | Pre-move position copies (the collision revert baseline) |
| `$f984` | Fatigue heading drift |

Treat any older note claim as suspect until re-verified: two were wrong (joystick dead code; the sky patch site at `$1b9c0`).
