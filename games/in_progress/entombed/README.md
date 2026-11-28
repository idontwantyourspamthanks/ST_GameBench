# Entombed

- Slug: `entombed`
- Status: **in progress** (STe Enhanced prototype built & verified at locked **50.00 FPS** & **60.00 FPS** with unlinked timestep + 1-px interpolation)
- Source: ST Format Issue 30 coverdisk (`originals/stf30a.msa`, `SIDE_2\ENTOMBED\ENTOMBED.PRG`)
- Original: *Entombed* by Nick Concannon (free coverdisk game, no copy protection, pure 68000 assembly)
- Local copies: `originals/` and `work/extracted/` (git-ignored, never committed)
- Research notes: [`work/notes/RESEARCH.md`](work/notes/RESEARCH.md)
- Build & test tools:
  - `python3 tools/build_entombed.py` — unpacks `originals/stf30a.msa`, assembles `patches/entombed_patch.s` (`vasmm68k_mot`), and outputs `work/disk_overlay/ENTOMBED.PRG`
  - `python3 tools/bench.py --tag test --title --move` — headless Hatari STe 50/60 Hz FPS, world-tick, and screenshot verification

## Files

| path | bytes | md5 |
|---|---:|---|
| `originals/stf30a.msa` | 791617 | f0111a23bda0776a8d076c1b828e341e |
| `originals/stf30a.msa` : `SIDE_2/ENTOMBED/ENTOMBED.PRG` | 51568 | c1435c2b2d1d1d4c4231c33a66b005a8 |
| `originals/stf30a.msa` : `SIDE_2/ENTOMBED/ENTOMBED.DOC` | 4270 | f75dce7fdb6209c0604f44b19f414172 |

## Verified STe Performance & Architecture (1 MB STe, 8 MHz, TOS 1.62)

| Mode | Original | STe Enhanced | World Tick Rate |
|---|---:|---:|---:|
| **50 Hz PAL** | 16.67 FPS (3.0 VBLs/f) | **50.00 FPS (1.0 VBL/f)** | **16.67 Hz (locked)** |
| **60 Hz NTSC (`H` key)** | — | **60.00 FPS (1.0 VBL/f)** | **16.67 Hz (locked)** |

### Implemented Enhancements (`patches/entombed_patch.s`, 3,210 B)
- **Unpacked relocatable build pipeline** (`tools/unpack_entombed.py`, `tools/build_entombed.py`) with instant startup (skips the original 138 KB tile pre-shifter).
- **STe Hardware 8-Way Scrolling (`$ff820d`, `$ff820f`, `$ff8265`)** using double-buffered `352×208` playfield buffers with in-place Blitter scrolling and dirty-tile incremental Blitter updates (~700 cycles per 32×16 4-plane tile).
- **STe Blitter Masked Sprites** with hardware 1-pixel skew (`$ff8a3d`), on-the-fly plane normalization & mask generation, and automatic dirty-tile restore.
- **Timer B Split-Screen HUD at scanline 192** rendering to a static, dirty-checked 8-line buffer (0 CPU cycles on unchanged frames, zero scroll jitter).
- **Unlinked Fixed-Timestep Engine + 1-Pixel Render Interpolation**: game logic ticks at a constant `16.67 Hz` regardless of 50 Hz / 60 Hz / CPU speed, while camera and all entity-tagged sprites linearly interpolate to exact 1-pixel positions every single VBL.
- **Live `'H'` 50/60 Hz Toggle** in-game + discreet `enhanced by dad_prg v1.0` credit on the title screen.
