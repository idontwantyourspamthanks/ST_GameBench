# Overlander — Track & Campaign Editor Notes (`ovltrack.py` / `OVLTRACK.TRK`)

Reference notes for a future session building a Moonshine Racers–style track & campaign editor (`ovltrack.py`, modeled on `games/done/moonshine-racers/tools/msrtrack.py`) on top of **Overlander Enhanced v1.0**.

All offsets below are relative to `OVERLAND_orig.PRG` TEXT base (`+0x00000` = original load address `$00aa9a`).

---

## 1. Verified Level & Track Data Structures

### A. Level Descriptor Table (`+0x06d74`, `$01180e`)
Loaded by `$00bb60..$00bb86` (`+0x010c6..+0x010ec`):
- **5 stock levels** (`0..4`), each **`$58` (88 bytes)** (`mulu #$58, d0`):
  - Level 0: `+0x06d74` (`$01180e`)
  - Level 1: `+0x06dcc` (`$011866`)
  - Level 2: `+0x06e24` (`$0118be`)
  - Level 3: `+0x06e7c` (`$011916`)
  - Level 4: `+0x06ed4` (`$01196e`)
- Active level descriptor pointer is stored in `$3c(game_base)` (`$aad6`).
- Known fields within each 88-byte descriptor:
  - `+$00..+$0f`: Fuel price, cargo payouts, level parameters (exact word-by-word map TBD — inspect readers of `$3c(game_base)`).
  - `+$10..+$2f` (32 bytes): Level 16-color 9-bit ST palette (copied into live palette at `bss_lowram + $6a40`, original `$007240`).
  - `+$50.w`: Signed relative offset from descriptor start to the level's **sky raster band table** (`move.l a0, $586(game_base)`).
    - Sky band table format: word 0 = horizon palette byte offset (`0..30`), followed by `(dy_delta.w, pal_offset.w)` pairs.
    - Note: Our v1.0 STE 12-bit sky gradient builder (`do_ste_sky_build` in `patches/overlander_patch.s`) reads `$586(game_base)` + the live palette at `$007240` dynamically every frame, so custom palettes & sky tables automatically get 12-bit STE gradients on STE/Mega STE/Falcon!

### B. Road Segment & Event Stream Feeder (`+0x0974a`, `$0141e4..$014256`)
Every `$c8` (200) road steps (`$c99c(game_base)` countdown), `$0141e4` consumes **4 bytes** from the active track stream pointer `$c99e(game_base)` (`$17438(pc)`):

| Byte | Purpose | Jump Table | Target State |
|---:|---|---|---|
| **0** | **Curve pattern** index (even byte offset) | `$014258` (`+0x097be`) | Writes curve generator ptr to `$243ea+$54` (horizontal road table), sets `$243ea+$50 = 1` |
| **1** | **Hill / elevation pattern** index (even byte offset) | `$014266` (`+0x097cc`) | Writes hill generator ptr to `$24392+$54` (vertical road table), sets `$24392+$50 = 1` |
| **2** | **Event / enemy / scenery spawner #1** (`0` = none) | `$014302` (`+0x09868`) | `jsr` to spawner (enemy cars, roadside trees/boulders, road signs, level-complete trigger, etc.) |
| **3** | **Event / enemy / scenery spawner #2** (`0` = none) | `$014302` (`+0x09868`) | Second simultaneous spawner (allows combining e.g. roadside scenery + enemy wave on the same 200-step chunk) |

---

## 2. Gaps to Reverse-Engineer Before Building `ovltrack.py`

A future LLM implementing the track editor only needs to inspect these 5 small areas in `OVERLAND_orig.PRG`:

1. **Complete 88-byte Level Descriptor Map (`+0x06d74`, `$3c(game_base)`):**
   - Scan all references to `$3c(game_base)` (`+0x003c`) to label every word in `+$00..+$57` (specifically: where the level's track stream pointer, level name string, fuel price, stage length, mountain graphic index, and cargo options are stored).
2. **Curve Pattern Table (`$014258`) & Hill Pattern Table (`$014266`):**
   - Disassemble/dump the relative-offset tables at `$014258` and `$014266` and the small curve/hill descriptor structs they point to (curvature rate, duration, crest height, dip depth).
   - Check valid index ranges so `ovltrack.py validate` rejects out-of-bounds byte values.
3. **Event / Spawner Jump Table (`$014302`):**
   - Map every valid entry in `$014302` (enemy types, roadside objects, signs like `"Devils Straights"`, fuel/bridge/end-of-level triggers).
   - Identify the exact **end-of-level / city-arrival trigger** byte so custom tracks cleanly finish and advance to the next city.
4. **Stock Track Stream Locations & Lengths:**
   - Locate where `$c99e(game_base)` is initialized for each of the 5 stock levels (and whether any level shares or loops streams), so `ovltrack.py decode --all` can dump all 5 stock tracks losslessly to JSON.
5. **External Campaign File Hook (`OVLTRACK.TRK`):**
   - Add a `load_bin_file("OVLTRACK.TRK", ...)` call in `do_patch_init` (just like `AM_MUS.BIN` and `AM_SFX.BIN` in `patches/overlander_patch.s`), loading custom level descriptors + track streams into a small BSS buffer (~8–16 KB; plenty of RAM headroom in 1 MB since v1.0 uses only 558 KB!).
   - When `OVLTRACK.TRK` is absent, stock levels play untouched.

---

## 3. Recommended `ovltrack.py` Subcommands (Matching `msrtrack.py`)

- `decode [0..4|--all] -o OUT.json` — lossless decode of stock levels (descriptors, palettes, sky bands, 4-byte road/event streams).
- `encode TRACK.json -o OUT.bin` — compile JSON back to native binary.
- `validate FILE...` — bounds-check curve/hill/spawner indices, end-of-level trigger presence, palette validity, and stream length.
- `render SRC -o OUT.png` — render top-down 2D road path (integrating curve patterns), elevation profile (integrating hill patterns), and enemy/scenery event strip.
- `campaign new|add|list|extract` — pack custom levels into `OVLTRACK.TRK`.
- `disk CAMP.trk -o OUT.st` — build a 720 KB FAT12 floppy containing `OVLTRACK.TRK` (or a standalone bootable custom campaign floppy based on `v1.0`).
