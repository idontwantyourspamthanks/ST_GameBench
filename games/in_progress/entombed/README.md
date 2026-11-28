# Entombed

- Slug: `entombed`
- Status: **in progress** (initial technical research & level-format reverse-engineering complete)
- Source: ST Format Issue 30 coverdisk (`originals/stf30a.msa`, `SIDE_2\ENTOMBED\ENTOMBED.PRG`)
- Original: *Entombed* by Nick Concannon (free coverdisk game, no copy protection, pure 68000 assembly)
- Local copies: `originals/` and `work/extracted/` (git-ignored, never committed)
- Research notes: [`work/notes/RESEARCH.md`](work/notes/RESEARCH.md)

## Files

| path | bytes | md5 |
|---|---:|---|
| `originals/stf30a.msa` | 791617 | f0111a23bda0776a8d076c1b828e341e |
| `originals/stf30a.msa` : `SIDE_2/ENTOMBED/ENTOMBED.PRG` | 51568 | c1435c2b2d1d1d4c4231c33a66b005a8 |
| `originals/stf30a.msa` : `SIDE_2/ENTOMBED/ENTOMBED.DOC` | 4270 | f75dce7fdb6209c0604f44b19f414172 |

## Summary of Findings

- **Baseline performance:** Locked **16.67 FPS (3 VBLs/frame)** identically on 512 KB STfm (TOS 1.04) and 1 MB STe (TOS 1.62).
- **Primary bottleneck:** **74.1% of CPU (~355k cycles/frame = 2.22 VBLs)** is spent in the full-screen tilemap renderer (`$013504`), which redraws all 120 tiles every frame using `movep.l` and recomputes/reverts dynamic drop-shadows twice per frame. All gameplay logic + sprites combined is only **~29.4k cycles/frame (18.4% of a single 50 Hz VBL)**.
- **50 FPS potential:** Achievable on **1 MB STe** with hardware 8-way scrolling + Blitter (~50–60k cyc/frame = 35% of 1 VBL, leaving ~100k cyc/frame free and ~500 KB RAM for DMA audio), and **25 FPS** (or 50 FPS with a ring-buffer) on a **512 KB STfm** by baking shadows, dirty-flagging the HUD, and replacing `movep.l` with `movem.l`.
- **Level format:** 100% reverse-engineered across all 5 tombs — 8×4 sparse rooms of 10×12 dual-layer ASCII grids (primary + alternate swap layer), typed anchor object descriptors for pickups/enemies/traps/switches/checkpoints/doors, and a timed flicker/layout-change script. Ready for a full visual level editor.
