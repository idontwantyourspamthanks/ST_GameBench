---
name: st-hatari-harness
description: Run, drive and measure Atari ST games in headless Hatari with gamebench/tools/stharness.py. Covers private Xvfb displays, snapshots, cold boots, mouse/key/joystick input, fps/profile/world-rate measurement, deterministic A/B frame capture, and the Hatari debugger traps that silently break automation. Use for any emulator test, measurement or UI navigation of a game under gamebench/games/.
---

# Atari ST games: Hatari harness

`tools/stharness.py` (class `Hatari`) is the only way to drive Hatari here.
- Each instance gets its own scratch dir (`/tmp/strun-*`) and its own Xvfb display, so it never touches the user's desktop and runs in parallel safely.
- The game folder is copied to scratch as drive C:, so the originals are never written.
- Game-specific navigation (`boot_to_game` etc.) goes in `games/<game>/tools/<game>.py` as a `Hatari` subclass. Worked example: `games/in_progress/midwinter2/tools/mw2harness.py`.

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
- `memsize_kb`: 1024 is the usual target.
- `extra=['--joy1','keys']`: cursor keys act as joystick 1.
- `files=[...]`: what to copy as C:. The default is the whole game dir minus scaffolding.
- `overlay=`: a dir copied over C: afterwards. The default is `<game>/work/disk_overlay`, e.g. a created save/campaign disk.
- `flip_reg`: the register whose change marks a presented frame. The default is `($ff8201).b`. Check the game's flip code first: a game whose buffers differ only in `$ff8203` needs that register instead.

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
- `--trace gemdos` logs every file a loader opens, seeks and reads.
- **Remote-control shortcuts:** `hatari-shortcut screenshot|savemem`, `hatari-event keypress N`, `hatari-option --cpuclock 16`. There is no `debug` shortcut; enter the debugger only via `:trace` breakpoints.

## Gotchas seen in practice
- **The first screenshot after a load may be black** (palette fade). That is not a crash; check game state.
- **Hatari draws a TT frame with one palette**, so mid-frame palette splits (HUD vs 3D) look wrong on a Hatari TT but are fine on real hardware. Judge visuals on ST/STE/Mega STE.
- **Concurrency:** keep to at most 2–3 cold boots at once, since wall-clock sleeps miss clicks under load. `/tmp` is a RAM disk; the scratch game copy is deleted on `close()`.
- **TT and Falcon screenshots differ:** TT 640×436 (picture at 0,0, statusbar below), Falcon 648×602 (picture at 2,64); `screen_matches` shifts both. A TT/Falcon "CPU halted: double bus error" dialog blocks the fifo for good (every later call: "no screenshot"). TT hard disk = `--acsi`; Falcon TOS 4.04 has no ACSI (IDE/SCSI only).
- **Silent by default:** the harness sets `SDL_AUDIODRIVER=dummy` for every Hatari it starts, so sound never plays on the host speakers (the user may be using them); emulated sound and WAV recording still work. Set `HATARI_AUDIBLE=1` to hear it. Any Hatari started outside the harness must set the same variable.
