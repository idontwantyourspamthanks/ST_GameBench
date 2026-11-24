# Overlander — Baseline Analysis

- **Game:** Overlander (Elite Systems, 1988 — `"Overlander-Atari ST Final V1.9 06/07/88"`, 68000 code by Darren Pegg, graphics by Gary Tonge & Peter Tattersal, ST YM sound by Jas. C. Brooke, Amiga music/SFX by Mark Cooksey).
- **Original disk:** `originals/overlander_elite.zip` → `overlander.stx` (80 single-sided 9-sector FAT12 tracks + copy-protection tracks 80–81).
  - Files: `AUTO\RUN.PRG` (3,294 B, self-modifying XOR decryptor + track-80 protection), hidden `AUTO\RUN.PRO` (78,336 B, encrypted main PRG; decrypts to 77,376 B flat code loaded at `$00aa9a..$01d8da`), `LOADSCR.IMG` (25,600 B), `G.TOS` (239,182 B, 40-entry graphics/data bank loaded at `$0278f6..$061f28`).
- **Hardware scan (`tools/hwscan.py` on decrypted `$00aa9a..$01d8da`):** **0 `crit`** findings (151 `warn`: MFP IRQ/Timer B raster splits, vector writes `$68/$70/$94/$118/$120`, 1 sync check `$ff820a`).

## Cross-Machine Behaviour (Original STX)

| Machine | TOS | Result | Notes |
|---|---|---|---|
| **8 MHz 1 MB ST** | 1.04 | Boots (needs `--fastfdc no`) | Title/menus work; ~16–19 fps driving. |
| **8 MHz 1 MB STE** | 1.62 | Boots (`--fastfdc no`), **crashes ~3s into driving** | **19.0 fps (2.63 VBLs/frame)** on open road; **15.8 fps (3.16 VBLs/frame)** with enemy/banner. Crashes with `03:Address Error: Odd access` at `PC=$01785a` (`A0=$0051ba`, `A3=$017787`) — enters built-in `DEBUG ENTERED V0.1` monitor! |
| **16 MHz 2 MB Mega STE** | 2.06 | Boots (`--fastfdc no`), runs at 8 MHz default; **35.0 fps** at 16 MHz | **1.84× gameplay speedup** at 16 MHz because `$aaa0` frame cap is 1 VBL (50 Hz). |
| **32 MHz 4 MB TT** | 3.06 | **Fails to boot** (drops to GEM Desktop) | `AUTO\RUN.PRG` self-modifying XOR decryptor + STX protection fails under 68030 I-cache; in-game Timer B handler (`$b822/$b834`) also uses self-modifying `bra.b`; VGA mode needs ST Low switch. |
| **16 MHz 4 MB Falcon** | 4.04 | **Fails to boot** (drops to GEM Desktop) | Same 68030 I-cache + STX loader failure + `$b822/$b834` self-modifying Timer B code. |

## 8 MHz STE CPU Profile (Clean 50-VBL Driving Capture, 19.0 fps)

Total: `3,349,716` cycles (~67k CPU cyc/VBL, ~176k CPU cyc/frame; `2.63 VBLs/frame`).

| Subsystem | Address Range | Cycles | Share | STE Optimization Opportunity |
|---|---|---:|---:|---|
| **Road scanline span drawer** | `$017826–$017a4c` | 1,051,776 | **31.4%** | STE Blitter horizontal solid/kerb span fills (`HOP=0/1`, `ENDMASK1/2/3`) → ~4–5× faster |
| **Masked sprite blitters** (cars, obstacles, shots) | `$00de82`, `$00e41c`, `$00e616` | 513,204 | **15.3%** | Currently computes `~(p0\|p1\|p2\|p3)` mask on the fly! Precomputed mask + STE Blitter `SKEW`/`NFSR`/`ENDMASK` → ~4–5× faster |
| **Road 3D perspective & segment builder** | `$017470–$017744`, `$013c60–$014046` | 641,468 | **19.2%** | Keep on CPU (or micro-optimize); fast enough once blitting is offloaded |
| **Parallax mountain / horizon strip blitter** | `$00e122–$00e31a` | 253,700 | **7.6%** | STE Blitter `SKEW` + `FXSR` 16-line strip copy → ~4× faster |
| **Sky solid fill** (`movem.l`) | `$00e7da–$00e84c` | 249,960 | **7.5%** | Single-shot STE Blitter fill (`HOP=1`, `OP=3`) → ~5× faster |
| **HUD / text character plotter** | `$01332e–$0135a4` | 246,820 | **7.4%** | Byte-by-byte 4-plane font plotter |
| **Game logic, Timer B raster splits, YM sound, misc** | `$01248c`, `$00b024`, `$00ce00–$00d300`, etc. | 392,988 | **11.6%** | Timer B sky gradient (`2.2%`), Jas. C. Brooke YM driver (`~1.5%`) |

## Key Bugs & Enhancement Opportunities

1. **Hardcoded low-RAM BSS (`$000800–$007340`, 24 unique refs)** — Overlander places its stack (`$008436`) and work tables (`$000800`, `$003b44`, `$004fda`, `$00561a–$007340`) directly in TOS low RAM, causing `03:Address Error` crashes on TOS 1.62+ (STE/Mega STE/TT/Falcon). Relocating these 24 addresses to clean allocated BSS fixes stability across all TOS versions.
2. **Self-modifying code & STX protection** — Replacing `AUTO\RUN.PRG` with a clean unpacked/decrypted `OVERLAND.PRG` (from `RUN.PRO`) and replacing the self-modifying `bra.b $b834` in the Timer B handler (`$b822/$b834/$b840`) unlocks 68030 compatibility (TT & Falcon) and instant HD/floppy loading.
3. **STE Blitter acceleration (61.8% of frame is pure pixel blitting!)** — Offloading road spans, sky fill, parallax mountains, and masked sprites to the STE Blitter cuts frame time from ~2.6–3.2 VBLs (16–19 fps) to ~1.3–1.6 VBLs, enabling a **locked 25.0 fps (2.00 VBLs/frame)** on 8 MHz STE (and paced 25.0 fps on Mega STE/TT/Falcon so faster machines don't run 2×–3× too fast).
4. **Amiga 4-channel stereo STE DMA Audio** — The Amiga ADFs in `alt/amiga/` contain an uncompressed, PC-relative 4-channel Paula player (`$229b6–$24000`) plus ~56 KB of raw 8-bit signed PCM music samples (`$24000–$32000`) and ~32 KB of SFX samples (`$60000–$68000`). With ~0.4–0.7 VBLs of Blitter-freed headroom on 8 MHz STE, we can port the full Amiga soundtrack + sampled SFX to our atomic cursor-tracked STE DMA ring buffer (just like Flood!).
5. **STE 12-bit extended palettes** — Smooth 4096-color sky sunset gradients and Amiga palette refinement on STE/Mega STE/Falcon.
