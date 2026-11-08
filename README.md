# gamebench

**Speeding up and modernising classic Atari ST games by patching them, without their source code.**

This repository holds the tools, the patches and the full working notes. It does **not** contain any game, any TOS ROM, or anything extracted from them. You need your own copies (see [Getting the game files](#getting-the-game-files)).

The first finished project is **Midwinter 2: Flames of Freedom**. Midwinter (1) is in progress. [`games-to-build.md`](games-to-build.md) is the wish list.

## What the Midwinter 2 patches do

Measured on an emulated 1 MB 8 MHz Atari STE, same scene, against the unpatched game:

| | Original | Patched |
|---|---|---|
| Walking (3D view) | 56 frames | 69 frames (+23%), identical picture |
| Standing still | about 4 fps | about 25 fps, identical picture |
| Game speed on a 16 MHz machine | 2.3× too fast | correct (fixed real-time logic rate) |
| On-foot motion on faster machines | 5 steps/s, jerky | smooth (25 Hz player steps) |
| Steering | "yoke" (inputs set a turn rate that persists) | direct (turn while held / while the mouse moves) |
| Loading screens | repeated grey flashes | none; screen changes load about 2× faster |
| 4 MB+ machines | (patched builds hung; fixed) | work on 1-14 MB |

The plain-English write-up of how each change works, what the original code did and why it was changed is in [`games/midwinter2/REPORT.md`](games/midwinter2/REPORT.md).

## How it was done (openly)

The work was done by a human directing an AI coding agent, Claude, in the [omp](https://github.com/can1357/oh-my-pi) harness, with several sub-agents working in parallel on research, patching and testing. The method is designed so that **nothing is taken on trust**:

- Every claim in the notes cites either a disassembly line or raw emulator output. Unverified statements are marked `[INFERENCE]`.
- Every patch has to pass these gates before it is switched on:
  - **Its original bytes are verified:** the patcher applies all patches or none, and leaves a marker in RAM.
  - **It draws a byte-identical picture:** both or all three screen buffers are compared against the unpatched game at the same frame, from the same saved machine state.
  - **It speeds things up measurably:** CPU cycles per frame and frames per second.
  - **It cold-boots** from the desktop into the 3D view on several machines (ST, STE, Mega STE, TT/Falcon via EmuTOS) and RAM sizes (1, 2 and 4 MB and more).
- Agents' findings were re-checked live before anything was built on them. Some were wrong, and the notes record where.

The agent "skills" in [`.omp/skills/`](.omp/skills/) capture the method, the emulator harness and the hard-won traps. They are written for the AI to read, but they work as a human guide too.

## Layout

| Path | What |
|---|---|
| `tools/stharness.py` | Headless [Hatari](https://www.hatari-emu.org/) harness. Each instance gets a private Xvfb display, so input injection never touches your desktop. It handles snapshots, scripted mouse and keyboard input, fps, CPU profiles, world-speed measurement and deterministic A/B frame capture. |
| `tools/m68dis.py` | 68000 disassembler for RAM dumps, with call-target labels, xrefs, callers and per-address profile cycles (uses [capstone](https://www.capstone-engine.org/)). |
| `tools/pp_depack.py` | Unpacks the self-extracting `RUNME.TOS` of PP's HAGA hard-disk conversions. |
| `.omp/skills/` | Method, harness, PP-conversion internals and delegation rules. |
| `games/midwinter2/` | **Midwinter 2: done.** `REPORT.md` (overview), `PLAN.md`, `patches/` (about 50 patch sources, 68000 assembly), `tools/` (patch builder, harness, launchers, packaging), `work/notes/` (reverse-engineering notes with evidence), `work/*/` (test scripts and raw logs). |
| `games/midwinter/` | **Midwinter: in progress.** Same layout. |
| `tos/` | Empty: put your TOS images here (see `tos/README.md`). |

## Getting the game files

The patches are for **PP's HAGA hard-disk versions** (2014) of the Midwinter games, which you need to obtain yourself. Each game's `README.md` lists the expected files and their MD5 sums. Put them in the game folder (`games/midwinter2/RUNME.TOS`, `HAGA`, `FILES/`, …). The patch tools verify every original byte they replace and refuse to build against anything else.

Building a patched copy, for example Midwinter 2:

```sh
cd games/midwinter2
python3 tools/mw2patch.py verify           # checks your files against the expected original bytes
python3 tools/mw2patch.py build            # patched HD copy in build/game/ (originals untouched)
python3 tools/mw2patch.py build --floppy   # patched floppy images in build/floppy/
tools/play.sh                              # run it in Hatari (needs TOS images in ../../tos)
```

Requirements:
- Linux, Python 3.10+, `hatari` (2.6+), `vasmm68k_mot` (vasm, Motorola syntax) for assembling patches;
- for the test harness: `Xvfb`, `xdotool` and Python `capstone` + `Pillow`.

## Credits and legal

- *Midwinter* and *Midwinter II: Flames of Freedom* are © Maelstrom Games / Rainbird / MicroProse.
- The hard-disk conversions (`RUNME.TOS`, `HAGA`, the converted disk images) are by **PP**.
- TOS is © Atari Corp. EmuTOS is GPL and available from its project.
- None of these are included here. This repository contains only original tools, patch source code, and analysis notes. Notes and patches necessarily quote short byte sequences and disassembly of the games for interoperability and documentation.
- The code and documentation in this repository are released under the MIT licence (see `LICENSE`).
