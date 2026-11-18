# Powermonger (Bullfrog 1990): enhancement plan

Base: the original floppy, `disks/protected.st` (`AUTO\WAR.PRG`, unmodified). Method: `.omp/skills/st-game-speedup`.
Study: `work/notes/{boot,baseline,frameloop,hotpaths,entities}.md`.

## User decisions (2026-11-09)
- Ship both a floppy and an HD version. The original is floppy-only, so the HD version needs file-based loading.
- **Essential:** game-world timing fixed to real time, as in Midwinter. The world is currently coupled to the frame rate (2.1–2.9× faster at 16 MHz).
- **Agreed work** (pixel-identical unless stated):
  1. a fixed-rate logic tick (VBL-based, logic steps before one render; logic is about 2% of a pass);
  2. STE DMA sound replacing the timer-A YM sample player (10–26% CPU while a sample plays). YM stays on plain ST. Higher-quality samples may come later from a user-supplied source;
  3. mouse pointer redraw only when it moves or the buffers swap (5–7%);
  4. sprite blits: pre-shifted sprites and/or the STE blitter, which can shift and mask in hardware (3–6%). Plain ST keeps the CPU path;
  5. the 3D window copy: copy only the window (about 2%), and find out whether the copy can be avoided altogether by drawing into a flipped buffer. Blitter vs CPU for whatever copy remains;
  6. maths tables: exact replacements only (constant multiplies by 55/160/480/316, `divu #20`; the triangle-setup `divu` only if proven exact);
  7. static-frame skip when nothing in view changes (exact);
  8. terrain overdraw culling: NOT exact as proposed, so it needs before/after screenshots and the user's approval, or an exact variant.
- Mega STE, TT and Falcon testing is held until these changes land.

## Phases
- **P1 Patch delivery and HD loader** (`PMLoader`): verify-then-apply trampoline, payload in free RAM, the floppy build, and an HD build that loads from files.
- **P2 Timing** (`PMTiming`): fixed tick. Prototyped live on snapshots in parallel with P1.
- **P3 Performance and sound:** items 2–7 above.
- **P4 Overdraw culling (approval needed), regression, packaging** (HD and floppy zips, launcher, report).
- **P5 Men interpolation** (2026-11-09, user decision: predict-ahead / extrapolation, world still 4 ticks/s): `p3b_interp` + `p3b_delta`, `; default: no`; `work/notes/interp.md`.
- **Release credit** (2026-11-10, user requirement; `pm_credit`, `; default: yes`, version **1.0**): a small `v<VERSION> enhanced by dad_prg` line, in one dim palette colour, at the very bottom (rows 194-199) of the main menu screen; the version is the `TXT:` line of `patches/pm_credit.s` (zip names and READMEs take it from there); `work/notes/credit.md`.
- **Combined default set** (2026-11-10, PMIntegrate; `work/notes/combined.md`): `p7_triple_*`, `qol_keys`, `qol_keys2`, `qol_hover`, `qol_hover2` and `tick_rain` (replaces `tick_wx`) are `; default: yes`, with `tt_ptr` (TT + Falcon pointer), `pm_intro_*` and `p4_clamp`. `tt_ptr` moved from `$1898` (p7_triple_tail's site) to `$188c`. Gates, cold boots on ST / STE / Mega STE / TT / Falcon / HD and the fps table are in combined.md.
