# Player Manager (Atari ST) — Performance & Match Engine Reference

Measured on **Hatari 8 MHz 68000 STE, 1 MB RAM, TOS 1.62, RGB 50 Hz** (unless noted otherwise).

---

## 1. New Game Setup Performance (Task 0 & Task 1)

| Build | Teams / Players | Virtual Time (8 MHz STE) | Speedup |
|---|---:|---:|---:|
| Unpatched `originals/PLAYERME` | 44 teams / ~920 players | ~460 s (7m 40s) | 1.0× |
| Patched `micro_opt.s` (bit-exact + Option A) | 44 teams / ~920 players | ~109 s (1m 49s) | 4.2× |
| Patched `micro_opt.s` + `league92.s` | 92 teams / 1,918 players | ~253 s (4m 13s) | 1.8× faster than original despite 2.1× more clubs/players |

---

## 2. Match Engine Performance (Task 2 — Kick Off 2 Overlay)

### Root Cause of "Laggy" Feel (Fixed)
In `patches/ko2_bridge.s`, `-$34c4(a4)` was mistakenly set to `1` (assuming it was an Aftertouch toggle). In Kick Off 2, `-$34c4(a4)` is actually **Game Speed / extra VBL delay** (`$0134b4` computes `-$4ed6(a4) = (1 << speed) >> 1`, and the main loop at `$01b4bc` waits `-$4ed6(a4)` *additional* VBLs after every rendered frame).
- `-$34c4 = 0` (`-$4ed6 = 0`): **50.00 FPS** (standalone Kick Off 2 default; Aftertouch is always active in KO2's physics).
- `-$34c4 = 1` (`-$4ed6 = 1`): **25.00 FPS cap** (waits 2 VBLs per frame -> halves framerate and doubles input latency).

### Measured Match Engine Metrics (1 MB 8 MHz STE, 50 Hz PAL)

| Configuration | Speed Delay (`-$4ed6`) | Measured Active FPS | VBLs / Frame | VBL Idle Headroom (`$1b4b2..$1b4b6`) | Timer B Stripes (`$120.w`) |
|---|---:|---:|---:|---:|---|
| Standalone Kick Off 2 (`originals/KICKOFF2`) | `0` | 50.00 FPS (cap) | 1.00 | — | `$018e36` (`$0060`/`$0050`, 48 lines) |
| Patched PM + KO2 (before fix, `-$34c4 = 1`) | `1` | **24.90 FPS** (122 frames / 245 VBLs) | 2.01 | — | `$018e36` (`$0060`/`$0050`, 48 lines) |
| Patched PM + KO2 (after fix, `-$34c4 = 0`) | `0` | **50.00 FPS** (1,803 frames / 1,803 VBLs) | 1.00 | **~42.5% idle** (active play, ~57.5% CPU used) | `$018e36` (`$0060`/`$0050`, 48 lines) |

> **Headroom note for future Amiga tiled pitch port:** At 50 FPS on an 8 MHz 68000 STE, Kick Off 2 currently uses ~57.5% of a 20 ms VBL (~42.5% idle headroom, ~92,000 cycles/frame free during light play; ~18% idle when many players are simultaneously on screen). On STE, the hardware Blitter + horizontal fine-scroll registers can offload a tiled pitch background with minimal CPU cost if we keep sprite overdraw disciplined.

---

## 3. Horizontal Grass Stripes Verification (Timer B HBL Raster)

Both unpatched Player Manager (`$01b5c2..$01b63c`) and Kick Off 2 (`$018d06..$018e66`) use the exact same Atari ST Timer B raster technique:
- VBL queue (`$456.w`) calls `$018d06`, which reads vertical camera position `camY` (`$2739c.l`), computes `(camY + 200) % 96`, sets top stripe colour `$27186.l` to `$0060` (bright green) or `$0050` (medium green), and loads Timer B data register `$fffa21` with `tb_init = 48 - (phase % 48)` scanlines.
- Timer B ISR (`$120.w = $018e36`) toggles `$ff8240` via `eori.w #$30, $27186.l` (`$0060 <-> $0050`) every 48 scanlines.

Verified on 1 MB STE (`build/game`):
- `VBL queue`: `['0xdfb16', '0x18d06', ...]`
- `Timer B ($120.w)`: `0x018e36`
- Active vertical scroll check:
  - Frame 1 (`t2_scroll_1.png`): `camY = 596`, `tb_init = 20`
  - Frame 2 (`t2_scroll_2.png`): `camY = 580`, `tb_init = 36` (exact 16-scanline shift matching the 16 px vertical camera movement)
  - Top goal (`t2_stripe_A.png`): `camY = -17`, `tb_init = 9`
