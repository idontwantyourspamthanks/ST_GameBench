# gamebench

**Speeding up and modernising classic Atari ST games by patching them, without their source code.**

This repository holds the tools, the patches and the full working notes. It does **not** contain any game, any TOS ROM, or anything extracted from them. You need your own copies (see [Getting the game files](#getting-the-game-files)).

Done: **Midwinter** and **Hunter**. In final testing: **Midwinter 2: Flames of Freedom** and **Powermonger**. Upcoming games are listed in [`games/queue/README.md`](games/queue/README.md).

## What the patches do

Both games get the same treatment: faster drawing with a byte-identical picture, game speed that no longer depends on the clock speed, and direct steering. The full evidence, disassembly and measurements are in each game's report.

### Midwinter 2: Flames of Freedom — [`REPORT.md`](games/in_progress/midwinter2/REPORT.md)

Measured on an emulated 1 MB 8 MHz Atari STE, same scene, against the unpatched game:

- **Faster, same picture:** walking 56 → 69 frames (+23%); standing still about 4 → 25 fps (redraw of an unchanged view skipped).
- **Correct speed on a 16 MHz machine**, where it used to run 2.3× too fast; on-foot motion is a smooth 25 Hz instead of 5 jerky steps/s.
- **Direct steering** instead of the original "yoke" (where inputs set a turn rate that persists).
- **Loading:** no repeated grey flashes, and screen changes load about 2× faster.
- **4 MB+ machines:** patched builds no longer hang; they work on 1-14 MB.

### Midwinter — [`REPORT.md`](games/in_progress/midwinter/REPORT.md)

Same method and tooling, applied to the older game: 11-15% fewer cycles per frame with all three screen buffers identical, and 63% fewer when standing still with the redraw skip on.

- **Exact replay:** the world runs 5 steps per second of real time at 8 or 16 MHz, and every step matches the original's state, including the random-number stream.
- **Faster at 8 MHz:** about 10% when moving, up to about 2× standing still. At 16 MHz you keep the extra frames (standing 7.8 → 19.0 fps) and the world no longer runs at double speed.
- **Direct controls** replacing the shared "yoke" routine — verified on skis; the buggy and hang-glider patches are in place but were never driven in testing.

## How it was done (openly)

The work was done by a human directing an AI coding agent, Claude, in the [omp](https://github.com/can1357/oh-my-pi) harness, with several sub-agents working in parallel on research, patching and testing. The method is designed so that **nothing is taken on trust**:

- Every claim in the notes cites either a disassembly line or raw emulator output. Unverified statements are marked `[INFERENCE]`.
- Every patch has to pass these gates before it is switched on:
  - **Its original bytes are verified:** the patcher applies all patches or none, and leaves a marker in RAM.
  - **It draws a byte-identical picture:** both or all three screen buffers are compared against the unpatched game at the same frame, from the same saved machine state.
  - **It speeds things up measurably:** CPU cycles per frame and frames per second.
  - **It cold-boots** from the desktop into the 3D view on several machines (ST, STE, Mega STE, TT with TOS 3.06, Falcon with TOS 4.04) and RAM sizes (1, 2 and 4 MB and more).
- Agents' findings were re-checked live before anything was built on them. Some were wrong, and the notes record where.

The agent "skills" in [`.omp/skills/`](.omp/skills/) capture the method, the emulator harness and the hard-won traps. They are written for the AI to read, but they work as a human guide too.

## Layout

| Path | What |
|---|---|
| `tools/stharness.py` | Headless [Hatari](https://www.hatari-emu.org/) harness. Each instance gets a private Xvfb display, so input injection never touches your desktop. It handles snapshots, scripted mouse and keyboard input, fps, CPU profiles, world-speed measurement and deterministic A/B frame capture. |
| `tools/m68dis.py` | 68000 disassembler for RAM dumps, with call-target labels, xrefs, callers and per-address profile cycles (uses [capstone](https://www.capstone-engine.org/)). |
| `tools/hwscan.py` | Machine checklist up front: scans a 68000 RAM dump (with a code range) or a TOS program for ST-machine-specific hardware access (YM mirrors, blitter, DMA sound, joypad ports, Mega STE cache, TT/Falcon registers, `$ff820a` sync, MFP, ACIA, vector writes), following `lea`/`movea`/`d(An)` bases, with a risk level and a one-line note per access. |
| `tools/pp_depack.py` | Unpacks the self-extracting `RUNME.TOS` of PP's HAGA hard-disk conversions. |
| `.omp/skills/` | Method, harness, PP-conversion internals and delegation rules. |
| `games/in_progress/midwinter2/` | **Midwinter 2.** `REPORT.md` (overview), `PLAN.md`, `patches/` (patch sources, 68000 assembly), `tools/` (patch builder, harness, launchers, packaging), `work/notes/` (reverse-engineering notes with evidence), `work/*/` (test scripts and raw logs). |
| `games/done/powermonger/` | **Powermonger (v1.0): done.** Same layout; [`REPORT.md`](games/done/powermonger/REPORT.md). |
| `games/in_progress/populous/`, `games/in_progress/populous-2/` | **Populous and Populous 2.** Same layout; `PLAN.md` and `work/notes/` (the shared Bullfrog-family study is `populous/work/notes/bullfrog_family.md`). |
| `games/done/hunter/` | **Hunter (v1.1, Jaguar pad): done.** Same layout; [`REPORT.md`](games/done/hunter/REPORT.md). |
| `games/in_progress/midwinter/` | **Midwinter (v1.1 released; back in progress for Jaguar pad support).** Same layout; [`REPORT.md`](games/in_progress/midwinter/REPORT.md). |
| `games/done/` | Games declared finished. A game moves here (`git mv`) when it's declared ready, and back to `in_progress/` if new work is needed. |
| `games/queue/` | **Upcoming games:** one folder per game with a README (source, file list, loader type) and early notes; the game files in `originals/` are git-ignored. The list is [`games/queue/README.md`](games/queue/README.md). |
| `tos/` | Empty: put your TOS images here (see `tos/README.md`). |
| `hd/` | Git-ignored except its README: a hard-disk driver you supply, for games whose loader needs a real ACSI disk (Hunter). |
| `games/*/alt/` | Git-ignored: other versions of a game you own (e.g. the Amiga release), used as reference or as a source of assets at build time. |

## Getting the game files

The patches are for **PP's HAGA hard-disk versions** (2014) of the Midwinter games, which you need to obtain yourself. Each game's `README.md` lists the expected files and their MD5 sums. Put them in the game folder (`games/in_progress/midwinter2/RUNME.TOS`, `HAGA`, `FILES/`, …). The patch tools verify every original byte they replace and refuse to build against anything else.

The commands are identical in each game folder; `games/in_progress/midwinter` uses `mw1patch.py` where `games/in_progress/midwinter2` uses `mw2patch.py`. For Midwinter 2:

```sh
cd games/in_progress/midwinter2
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
