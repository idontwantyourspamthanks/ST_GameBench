# Hunter (PP Gamex HD build): enhancement plan

Follows the Midwinter method (`.omp/skills/st-game-speedup`). User preferences carry over: target a 1 MB 8 MHz STE; nothing may break up to TT/Falcon or at 4 MB; pixel-identical by default; game speed must not depend on CPU speed.

## Decisions
- **Ship both HD and floppy versions (user rule for all games; HD matters on Mega STE/TT).** PP's Gamex build is HD-only, so the floppy set is built from a floppy release in `alt/floppy/` (Paper Bag or Replicants crack, user-supplied, git-ignored).
- **Controls:** keep as they are (the user considers them sensible).
- **STE sample sound (user decision):** replace the YM effects with the Amiga version's samples through STE DMA, on STE-class machines only. Plain ST keeps the YM.
  - **2-voice software mixer at 6258 Hz, mono.** Chosen after listening to `tools/ste_preview.py` renders. Estimated cost 7–9% of the CPU (`work/notes/sound.md` §3).
  - **Voice allocation:** the game's 3 effect channels map onto 2 voices by priority, reusing the original driver's request/priority logic. Which channel loses out is still to be designed; an engine loop plus the newest one-shot is the likely rule.
  - **Engine pitch follows speed**, as on the Amiga; the ST never did this. The voice's phase increment is driven from the vehicle speed.
  - **Samples:** extracted at build time from the user's own Amiga ADF (`tools/amiga_extract.py`, `games/hunter/alt/`). Never stored in git.
  - **Open:** how to deliver the payload through the Gamex loader; STE detection by hardware probe (the cookies are unreliable under Gamex); 4 MB free-RAM check.

- **68030 data cache off while the floppy loader runs (user decision, keep for now):** the 68030 does not snoop FDC DMA and the Paper Bag loader never flushes; Hatari doesn't show the problem, so this is real-hardware caution (fps cost unmeasured).

## Phases
- **P0 Harness and benchmarks** (`HunterBench`): `tools/hunter.py`, snapshots, baseline, frame-rate coupling, hot paths.
- **P1 Sound feasibility:** done (`work/notes/sound.md`).
- **P2 Patch delivery** for Gamex.
- **P3 Timing**, if the world speed is coupled to the frame rate.
- **P4 Display speed-ups**, pixel-identical.
- **P5 STE DMA sound.**
- **P6 Regression, packaging.**
