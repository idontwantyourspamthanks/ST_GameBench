# Powermonger: World War I Edition — enhancement plan

Base: the Pompey Pirates #106 cracked release (`disks/pp106.st`; README.md for the disk
layout and the two boot chains). Method: `.omp/skills/st-game-speedup`, the sibling project
`../done/powermonger/` as the reference.

## User decisions (2026-11-21)

Port from the original Powermonger project:
1. **The separation of world ticks from frame rate** — the `tick_*` design: real-time world
   steps (T/S/R pass kinds), VBL-based, 50/60 Hz safe, state-equality gates.
2. **The tooltips** — the `pm_tooltip` design: hover help written into the game's own bar.
3. **The keyboard shortcuts** — the `qol_keys` design: keys write the same words the click
   path writes; phantom-click protection.
4. **The performance work if applicable** — profile first; the WW1 engine is a different
   build, so each of `p4_ptr/p4_spr/p6_tri/p6_slope/p6_cpy` must be re-found (or dropped) by
   what the profile shows.

Not ported unless asked: the DMA-sound rewrite, the HD loader, the TT/Falcon cache and
pointer fixes, triple buffering, rain interpolation (decide later, after the four above).

## Phases

- **P0 Harness (done in progress):** `tools/pmww.py` boots the folder run of `WWIEDITN.PRG`
  (A: = a de-booted copy of the game disk, needed by the game's TOS-level data loads).
  Navigation: name prompt works by keys; clicks need `poke_click` (README). Remaining: the
  options-screen item boxes, the chart, the map view; then `boot_to_game()`, snapshots
  (map view idle / get men / battle), baseline fps + world rate at 8/16 MHz.
- **P1 Reverse-engineer (read-only, parallel):** the WW1 engine in RAM (the options screen
  already has it resident): the main loop and pass kinds, the VBL/flip/screen buffers, the
  IKBD and click dispatch, the HUD draw and the icon hit-test tables (tooltip target), the
  keyboard handler (keys target), the sound player (timer-A YM? — the DMA decision later),
  the loader (TOS GEMDOS from A:) and free RAM for a payload. Compare each with the original's
  notes: the routines should be the same algorithms at different addresses.
- **P2 Patch delivery:** the carrier rides in `WWIEDITN.PRG` (its text is TOS-loaded; the
  packer reads the payload itself — the `Fseek(62082)` offset is code we can patch, so the
  text can grow and the payload move). The hook installs at the game-proper hand-over
  (the equivalent of the original's `$10a6`), payload in proven-free high RAM
  (`$b8800..$effff` candidate — re-prove with the pattern fill).
- **P3 The four ports**, in the order above, each with its gates (state equality for the tick,
  pixel gates for tooltips, key==click world state for the keys, measured cycles for the perf).
- **P4 Regression + packaging:** floppy build from `pp106.st` (the disk has 2048 bytes free —
  the payload may not fit as a plain file; options: extend `WWIEDITN.PRG`'s text and let the
  packer read more, or use spare sectors past the FAT; decide at P2). HD build: the data
  loads are already TOS-level, so the HD build is a folder + `WWIEDITN.PRG`, no TOS swap
  needed (verify at P2). Machine matrix as the original's.

## Evidence so far (README has the details)

- `work/notes/frameloop.md`: the main loop (`$13dA8`), the flip (`$e0e`, buffers
  `$2ed98/$2ed9c`), the VBL counter `$71b7c`, the pass counter `$2ed90`, the complete
  1990-patch → WW1-site map (tick_head/tick_pass/tick_men/tick_click/flip/p6_cpy), the
  profile, delivery/free RAM.
- `work/notes/input.md`: the IKBD ACIA handler, the absolute-mouse packet words, the VBL
  button dispatch + the click latch (`$2edb6`/`$2edae`), the icon panel (`$6c16`, 4x6-px
  cells), the `poke_click` synthesis.
- `work/notes/baseline.md`: 3.55 passes/s at 8 MHz vs 6.97 at 16 MHz (**1.96x** — the tick
  defect); profile (renderer 39.8%, YM sample IRQ 14.2%, window copy 7.6%); **the user's
  real-STE report (~2 fps, vs 3-4 for the 1990 game)** — a like-for-like busy-scene
  measurement is the next baseline step.
- The engine is a different build from the 1990 game: no byte match; the renderer is a
  static unrolled block-pattern combiner, not the 1990 triangle walker (`frameloop.md` 6a).
- The single-part crack: `WWIEDITN.PRG` text = the Pompey Packer; payload read from its own
  file at 62082 → `$c1d84`; the chain: Toxic intro → doc displayer → game.
- The game's data loads go through TOS GEMDOS from drive A: (the Alien's ramdisk covers only
  the save-disk check), so any HD build keeps the files next to the program.
- Input: buttons only reach the game in IKBD packets that come with movement; the harness
  synthesizes them through the game's own latch path (`poke_click`).
