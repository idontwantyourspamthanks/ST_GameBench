---
name: st-hatari-harness
description: Run, drive and measure Atari ST games in headless Hatari with gamebench/tools/stharness.py. Covers private Xvfb displays, snapshots, cold boots, mouse/key/joystick input, fps/profile/world-rate measurement, deterministic A/B frame capture, and the Hatari debugger traps that silently break automation. Use for any emulator test, measurement or UI navigation of a game under gamebench/games/.
---

# Atari ST games: Hatari harness

`tools/stharness.py` (class `Hatari`) is the only way to drive Hatari here.
- Each instance gets its own scratch dir (`/tmp/strun-*`) and its own Xvfb display, so it never touches the user's desktop and runs in parallel safely.
- The game folder is copied to scratch as drive C:, so the originals are never written.
- Game-specific navigation (`boot_to_game` etc.) goes in `games/<game>/tools/<game>.py` as a `Hatari` subclass. Worked example: `games/done/midwinter2/tools/mw2harness.py`.

```python
import sys; sys.path.insert(0, 'tools')            # run from the gamebench root
from stharness import Hatari, TOS
h = Hatari(game_dir='games/done/midwinter', snapshot='games/done/midwinter/work/snapshots/x.sav')
h = Hatari(game_dir='games/done/midwinter', snapshot=None, memsize_kb=1024)   # cold boot, autoruns C:\RUNME.TOS
try: ...
finally: h.close()        # ALWAYS: frees Xvfb, display claim, scratch game copy
```

## Constructor options
- `machine`: `'st'|'megast'|'ste'|'megaste'|'tt'|'falcon'`.
- `tos=TOS['1.04'|'1.62'|'2.06'|'3.06'|'4.04'|'emutos'|...]`. The images live in `gamebench/tos/`.
  - Omit `tos` and the harness picks the machine's real TOS (`MACHINE_TOS`): ST/Mega ST 1.04, STE 1.62, Mega STE 2.06, TT 3.06, Falcon 4.04.
  - TOS 1.06/1.62 are STE-only.
  - Test TT and Falcon on the real TOS 3.06/4.04, as users run them. EmuTOS only on purpose: it loads programs at other addresses and behaves differently.
  - TT: add `extra=['--mmu', 'true']`, as `dist/run_tt.sh` does.
  - Binary (`hatari_bin(machine)`, also used by mw2harness and `dist/run_*.sh` via `dist/_hatari.sh`): `$HATARI` for every machine; for TT/Falcon `$HATARI_TTF`, else `HATARI_TTF=` in the git-ignored `dist/hatari.local`; else the system `hatari`. Stock 2.6.1 shows ONE palette per TT/Falcon frame (raster palette changes invisible: MW2 panel, Hunter sky); the user's patched build (per-scanline TT/Videl palette) is set in their `dist/hatari.local`. Newer builds take `--avirecord <bool>`.
- `memsize_kb`: 1024 is the usual target.
- `extra=['--joy1','keys']`: cursor keys act as joystick 1.
- `files=[...]`: what to copy as C:. The default is the whole game dir minus scaffolding.
- `overlay=`: a dir copied over C: afterwards. The default is `<game>/work/disk_overlay`, e.g. a created save/campaign disk.
- `flip_reg`: the register whose change marks a presented frame. The default is `($ff8201).b`. Check the game's flip code first: a game whose buffers differ only in `$ff8203` needs that register instead.
- `sound=True|<rate>` (opt-in, default off = `--sound off`): emulated sound ON at 50066 Hz. **Run gates for DMA-sound machines (STE, Mega STE; TT/Falcon where a patch drives the DMA/Crossbar) with emulated sound ON** (`--sound 50066`; the harness already sets `SDL_AUDIODRIVER=dummy`, so it costs nothing audible). A `--sound off` run is not the configuration the sound tick, DMA frame-end and YM paths run in on a real machine [INFERENCE: sound-off gates hid nothing by themselves in the MW2 bug, the direction fault is invisible in stock Hatari either way; the rule keeps every sound path executing].
- `trace_psg=True` (opt-in; or a list of extra `psgcheck.py` args): `--trace psg_write,fdc` is STREAMED through a FIFO into `tools/psgcheck.py` and never stored: a game with a sample player writes the PSG 100 000x/s, so a plain `--trace-file` grew to 2 GB in 4 minutes on `/tmp` (RAM) (Hunter title music, [verified]). After `h.close()`, `h.psg_check()` returns the result (`.ok`, `.violations`, `.warnings`, `.summary`); the relevant lines are in `<workdir>/psg_kept.trace`. Do not also pass `--trace` in `extra` (only the last one counts).
- `strict=True` (opt-in; or `HATARI_STRICT_PSG=1`): the strict Hatari with the YM port-direction model (below).

## Hatari leniencies (things the real chips do and stock Hatari 2.6.1 does not)
Evidence tags: [source] read in `hattari/src`; [verified] observed in a run; [INFERENCE] reasoning only.
- **PSG port direction is not modelled** [source psg.c `PSG_Set_DataRegister`: reg 14 is stored and `FDC_SetDriveSide()` called whatever reg 7 says] [verified Midwinter 2 v1.6 FFA, STE, sound on, `--disk-a`: stock Hatari reaches the "Insert Graphics Disk" prompt and the FFB swap, 230 PSGCHECK violations; the strict build never reaches the prompt, every `fdc type` line says `drive=-1`]. Real YM2149: reg 7 bit 6 = 0 (port A input) leaves the drive-select/side lines floating high, so no drive is selected and the floppy is dead; bit 7 = port B (printer data). Any patch that skips, replaces or silences a YM tick or init can lose bits 6/7 and every emulator gate still passes.
- **A game folder mounted as GEMDOS drive C: bypasses the FDC, the DMA and PSG port A completely.** Floppy behaviour is only tested with `--disk-a` / `--disk-b` images (`extra=['--disk-a', copy.st]`; never name a copy `A.st`/`B.st`).
- **PSG reads and writes are only approximately timed** [source psg.c: `M68000_WaitState(1)  /* [NP] FIXME not 100% accurate */`]; reg 14 reads return the latch, a real chip returns the pin levels (strict build: pins when port A is an input).
- **FDC leniencies** [source fdc.c]: "write track" is not supported for ST/MSA images; several wait states are `TODO check on real HW`; disk changes are only the WPT transition the TOS looks at (DSKCHG is not wired on a real ST either); `--fastfdc` (default off) skips FDC timing and "can break some programs": keep it `no` for any floppy timing/protocol gate.
- **The Falcon is stricter than an ST in one place:** a `movep.l` to the YM mirrors `$ff8804/06` bus-errors when `$ff8007` bit 5 is set [verified in `pop2_fal_ym`/`fal_ym` notes] while an ST decodes them as `$ff8800/02`.
- **FDC commands with `drive=-1` are not always a fault:** Falcon TOS 4.04 issues restore/seek with no drive selected during boot (pc `e045d2`, also in stock Hatari) [verified]. Judge a floppy fault by reg 7 (psgcheck) or by a game that hangs at its disk check, not by `drive=-1` alone.
- **`--cpuclock 16` on the command line is ignored on a Mega STE**; send `hatari-option --cpuclock 16` after start [verified, midwinter2 `bootgate.py`].
- **Everything real-hardware-only and untestable here goes in the release notes** (st-game-speedup, release checklist): blitter/bus contention, 68000 prefetch edge cases, real drive mechanics and motor/index timing, YM/DMA analogue behaviour.

## PSG gate: `tools/psgcheck.py` and the strict Hatari
- `psgcheck.py TRACE` (exit 1 on violations; `psgcheck.check(path)` returns `.ok/.violations/.warnings`) replays `--trace psg_write,fdc`: every FDC command or reg-14 write issued while reg 7 bit 6 = 0 (port A input), reg-15 writes and FDC commands with bit 7 = 0 (warning; `--strict-b` makes them violations), frames that start with bits 6/7 not both set, and non-atomic select/write pairs (an interrupt-side select of the data write's register landing between a main-code select and its data write; `movep` and uninterrupted `move.b` pairs are clean). It does NOT see reads or lost updates of the same register.
- The strict build (`tools/hatari-strict/`, build notes in its README) makes the same fault visible: port A input = drive deselected, `drive=-1` in `fdc type` lines, the game hangs at its disk check. Stock TOS 1.62 boots and `Fsfirst/Fopen/Fread` on a floppy work in it; MW2 v1.6 FAILS, v1.6.1 and the noAmiga set PASS.
- Gate recipe: floppy as `--disk-a`, `sound=True, trace_psg=True, strict=True`, boot + one disk access/swap, `h.close()`, `h.psg_check().ok`, and keep the failing build as a negative control. Wait for the game's own disk check, not a fixed time. Never run a raw `--trace psg_write` to a file on a game that plays samples.

## Snapshots
- Restore is deterministic: identical flip counts every run.
- **Snapshots hold whatever code was in RAM when saved**, i.e. unpatched code. To test a patch on a snapshot, apply it live, either with `capture_frames(..., live=prefix)` or with the debugger commands `loadbin`/`w`. Anything applied at boot or load time needs a cold boot.
- Snapshots are tied to the machine type and RAM size they were made on. Make 1 MB ones for benchmarks.
- `h.savemem(path)` writes one. Never pass a project snapshot path straight to Hatari's `--memstate`: Hatari saves back to that path and blocks on an "overwrite?" dialog.

## Measuring
- `h.fps(vbls)` counts flips. At 250 VBL one flip is about 0.2 fps, so use ≥1000 VBL for small effects. Host load skews it; compare runs made under the same load, or use profiles.
- `h.profile(vbls)` returns `[(addr, cycles)]`; bucket them by call target with `tools/m68dis.py`. Any fifo `hatari-debug` command resets the profiler, so the end breakpoint is armed first.
- `h.world_rate(addr, vbls, long=False)` gives world units per emulated second of a position variable. It's the check that game speed doesn't depend on CPU speed. Compare at `set_cpuclock(8)` and `set_cpuclock(16)`.
- `h.capture_frames(out, flip_addr, at_vbl, nth_flip, live=prefix, buffers=...)` is the deterministic A/B capture:
  - At the first call of the game's flip routine after an ABSOLUTE VBL, it optionally applies a patch set, then saves the screen buffers N flips later.
  - It is only meaningful while the simulation is per-frame (before any timing patches).
  - Compare only the visible 32000 bytes of each buffer.
- Also available: `h.peekw/peekl(addr)`, `h.debug('m $addr n')`, `h.dump(path)`, `h.vbl()`, `h.set_cpuclock(16)`.

## Equality gates (patched vs unpatched)
- **Match frames by world turn, not by flip number**, once a patch changes pass length: the faster run reaches the same turn sooner.
- **Self-test the gate:** the stock game at 8 MHz vs 16 MHz must come out IDENTICAL, or the gate compares timing noise. Populous 2's stock game shows a hover-changed pointer shape one VBL later on 8 of 128 turns depending on speed; the gate must skip exactly those.
- **Negative controls:** every gate must FAIL on a deliberately broken patch (a wrong blitter pass, a nopped compare). Paste both results.
- **Hash the world RAM every turn**, and compare all RAM at a few checkpoints. Exclude only ranges you can explain (TOS timers, the VBL counter, the patch sites, dead stack, a sample player that advances in real time).
- **Drive input as a pure function of the turn** (a test patch that walks the pointer and scrolls), so both runs see the same input.

## Input
- **Mouse:** `h.rel(dx, dy)` moves about 1 host px per screenshot px (2× ST px). The pointer is NOT grabbed: past the window edge (about ±400 x, ±290 y from centre) motion is lost. `h.center()` warps it back, but the game sees that as motion.
- **Clicks need a hold:** `h.click()` does down, 0.25 s, up.
- **Moving to a point:** `h.goto(x, y)` homes the pointer top-left, then moves. Measure where home lands for each game (`home_xy`).
- **Keys:** `h.key('KP_4')` via xdotool, or `h.keypress(scancode)` via Hatari (space 57, Return 28, Esc 1).
  - Some screens ignore keys while fading in. Retry until the screen changes.
- **Waiting on a screen:** `h.screen_matches(ref_png, box)` and `h.wait_for(ref, box, nudge=57)`.
  - Store reference crops in `<game>/work/ref/`.
  - Boxes are in 832×588 ST-screenshot coordinates, with the picture at (96,58). TT and Falcon screenshots are 640 wide with no border and are shifted automatically.
- **Prefer game-state checks over screenshots** to confirm arrival: a RAM word that identifies the screen or mode.

## Hatari debugger traps (each one cost hours)
- **Every breakpoint needs `:trace`.** Without it the debugger waits on stdin and the run hangs forever.
- **Clear with `b all`.** `bc all` is not a command; stale breakpoints doubled flip counts.
- **Capturing state at a hit:** `b pc = $X :trace :once :file cmds.txt`, where the file holds `r` / `m $addr n` lines.
  - Never re-arm a `:once :file` breakpoint inside its own file.
  - A skip count `:1` is rejected.
- **Watches and conditions:**
  - change-watch: `b ($addr).w ! ($addr).w :trace`;
  - conditions combine: `b VBL > N && pc = $X`.
- **Writes and loads:** `w $addr $xx $yy`, `loadbin file $addr`, `savebin file $addr $len`.
- **Long command lines are silently truncated**: a 300-char `loadbin` path just printed the usage text. Keep paths short.
- **A debugger write to the operand of the instruction at PC is ignored** (68000 prefetch). Redirect a `jsr` from a breakpoint on an EARLIER instruction.
- **A breakpoint armed while the CPU sits on its own address fires at once.** Arming a capture at the flip from the apply breakpoint (which stopped AT the flip) captured the apply instant, so "flips 1" compared nothing (huntab, mw1ab, abtest; fixed with a skip count of N+1, `reports/gate_audit.md`). Every gate needs a first-frame negative control.
- `--trace gemdos` logs every file a loader opens, seeks and reads.
- **Remote-control shortcuts:** `hatari-shortcut screenshot|savemem`, `hatari-event keypress N`, `hatari-option --cpuclock 16`. There is no `debug` shortcut; enter the debugger only via `:trace` breakpoints.

## Gotchas seen in practice
- **The first screenshot after a load may be black** (palette fade). That is not a crash; check game state.
- **Hatari draws a TT frame with one palette**, so mid-frame palette splits (HUD vs 3D) look wrong on a Hatari TT but are fine on real hardware. Judge visuals on ST/STE/Mega STE.
- **Concurrency:** keep to at most 2–3 cold boots at once, since wall-clock sleeps miss clicks under load. `/tmp` is a RAM disk; the scratch game copy is deleted on `close()`.
- **TT and Falcon screenshots differ:** TT 640×436 (picture at 0,0, statusbar below), Falcon 648×602 (picture at 2,64); `screen_matches` shifts both. A TT/Falcon "CPU halted: double bus error" dialog blocks the fifo for good (every later call: "no screenshot"). TT hard disk = `--acsi`; Falcon TOS 4.04 has no ACSI (IDE/SCSI only).
- **Silent by default:** the harness sets `SDL_AUDIODRIVER=dummy` for every Hatari it starts, so sound never plays on the host speakers (the user may be using them); emulated sound and WAV recording still work. Set `HATARI_AUDIBLE=1` to hear it. Any Hatari started outside the harness must set the same variable.
