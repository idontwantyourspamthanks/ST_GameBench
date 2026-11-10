---
name: mw2-hatari-harness
description: Run, drive and measure Midwinter 2 in headless Hatari via tools/mw2harness.py. Covers snapshots, cold boot to the 3D view, mouse/keys/joystick input, fps/profile/world-rate measurement, deterministic A/B frame capture, and the Hatari debugger gotchas that silently break automation. Use for any emulator-based test, measurement or UI navigation in this project.
---

# Midwinter 2: Hatari harness

Everything goes through `tools/mw2harness.py` (class `Hatari`). Never drive Hatari by hand. Each instance gets its own scratch dir and its own Xvfb display, and never touches the user's desktop. The originals are never written: the game dir is copied to scratch, and the created campaign disk `work/disk_overlay/FILES/FFD` is overlaid.

```python
import sys; from pathlib import Path; sys.path.insert(0, 'tools')
from mw2harness import Hatari
h = Hatari(snapshot='work/snapshots/1mb_ingame_walking.sav')      # restore a state (deterministic)
h = Hatari(snapshot=None, memsize_kb=1024, game_dir=Path('build/game'))  # cold boot of a patched build
try:
    h.boot_to_game('M')          # cold boot only: intro -> M/J/K -> Lobos 3D view, ~5 min
    ...
finally:
    h.close()                    # ALWAYS: frees Xvfb + display claim
```

Other constructor arguments:
- `machine='st'|'ste'|'megaste'|'tt'|'falcon'`
- `tos=Path(...)`. TOS images are in `gamebench/tos/` (`TOS_1_62.img` is the default).
- `extra=['--joy1','keys']`: the host cursor keys act as joystick 1.

CLI equivalents: `python3 tools/mw2harness.py fps|profile|rate|shot|dump --snapshot S [--cpuclock 16]`.

## Snapshots (`work/snapshots/`)
The primary target is 1 MB, so use the `1mb_*` snapshots for anything measured.

| Snapshot | State |
|---|---|
| `1mb_ingame_walking` | On foot, mouse mode, walking. The standard benchmark. |
| `1mb_ingame_foot` | Standing at the mission start. |
| `1mb_mode_select` | The M/J/K control-mode screen. |
| `ingame_*`, `corridor_agent`, `warroom_campaign`, `control_map`, `lobos_brief` | Older 2 MB states. |

- A snapshot restore replays deterministically: the same flip counts every run.
- Patches are applied at boot or load time, so a snapshot contains UNPATCHED code. To test a patch on a snapshot, apply it live: `capture_frames(..., live=prefix)`, or the `loadbin`/`w` debugger commands.
- Switch control mode in a live snapshot by writing `$eb76/$eb78/$eb7a`:

| Mode | `$eb76` | `$eb78` | `$eb7a` |
|---|---|---|---|
| Joystick | ffff | 0000 | 0000 |
| Keyboard | 0000 | ffff | 0000 |
| Mouse | 0000 | 0000 | ffff |

  Example: `h.debug('w $eb76 $ff $ff $00 $00 $00 $00')`.

## Measuring
- `h.fps(vbls)` counts screen flips: the game toggles only `$ff8201`, double-buffered at $60000/$70000.
  - One flip is about 0.2 fps at 250 VBL. Use ≥1000 VBL for small effects.
  - Results vary with host load. Compare runs made under the same load, or use cycle profiles.
- `h.profile(vbls)` returns `[(addr, cycles)]`. Bucket them by call target with `tools/m68dis.py`.
  - Any fifo `hatari-debug` command resets the profiler. That is why the end breakpoint is armed first and `profile on` is sent last.
- `h.world_rate(addr=0x6888)` gives world units per second.
  - It is the authoritative check that game speed is independent of CPU speed.
  - Position `$66e6/$66ea` (long, 1/512 cell) is more precise than the HUD distance `$6888`.
- `h.capture_frames(out, live=prefix, at_vbl=ABS, nth_flip=N)` is a deterministic A/B capture.
  - At the first flip after an ABSOLUTE VBL, it optionally applies a live patch set, then saves both screen buffers N flips later.
  - Only valid while the simulation is per frame, i.e. without tick, p3b or p5 patches in the set.
  - `tools/abtest.py` wraps it as the pixel-identity gate.
- `h.peekw(a)`, `h.debug('m $addr n')`, `h.dump(path)`, `h.vbl()`, `h.set_cpuclock(16)`.

## Input and navigation facts
- **Mouse:** `h.rel(dx, dy)` sends relative X motion, about 1 host px per screenshot px (2× ST px).
  - The pointer is NOT grabbed: motion past the window edge (about ±400 x, ±290 y from centre) is lost.
  - `h.center()` warps the pointer back, but the game sees the warp as motion. Use it only in menus.
- **Clicks** need a hold: `h.click()` does mousedown, 0.25 s, mouseup. `xdotool click` alone is ignored.
- **Map screens select islands with SPACE while hovering**, not a click: `h.goto(x,y); h.key('space')`.
- `h.goto(x, y)` takes screenshot coordinates. It homes the pointer to the top-left (about (114,75)) and then moves relative.
- **Keys:**
  - `h.key('KP_4')` etc. sends a key via xdotool to the window.
  - `h.cmd('hatari-event keypress <scancode>')` also works: space = 57, M = 50, J = 36, K = 37.
  - At the M/J/K screen the key is ignored while the screen fades in. Retry until the screen changes.
- **Joystick mode:**
  - The joystick drives the menu pointer and the mouse is ignored.
  - With `--joy1 keys`, `Left`/`Right`/`Up`/`Down` are the joystick directions.
- **In-game controls** (manual: `work/controls.md`):
  - Mouse Y is throttle and must leave the deadzone; use two `rel(0,-200)` calls.
  - Mouse X turns. Mouse buttons tilt the nose.
  - Esc leaves a vehicle.
- **`boot_to_game`** waits for reference images (`work/ref/`) and confirms the 3D view via game state: `$6220 == $d` (the on-foot player type) and `$700a == 2`.
  - It can still miss a click on the mission screens. Retry once, then inspect with `h.shot()`.
  - The first screenshot after arrival may be black because of the palette fade. That is not a crash.

## Hatari debugger gotchas (each one cost hours)
- **Every breakpoint needs `:trace`.** A non-trace breakpoint drops into the interactive debugger on stdin and the run hangs forever.
- Clear breakpoints with **`b all`**. `bc all` is not a command; it silently leaves breakpoints armed, which doubled flip counts.
- To capture state at a hit, put the commands in a file: `b pc = $X :trace :once :file cmds.txt`, where `cmds.txt` contains `r` and `m $addr n` lines.
  - Never re-arm a `:once :file` breakpoint from inside its own file: it re-fires at the same PC forever.
- A skip count of `:1` is rejected. Omit the count for the first hit.
- Watch for a memory change with `b ($addr).w ! ($addr).w :trace`.
- Conditions combine, e.g. `b VBL > 21460 && pc = $26e98`.
- Memory writes and loads: `w $addr $xx $yy ...` and `loadbin file $addr`.
- **`savemem`** writes to the `--memstate` path and blocks on an "overwrite?" dialog if the file exists. The harness always restores from a scratch copy and deletes it before saving. Never pass a project snapshot path straight to `--memstate`.
- `--trace gemdos` logs every file the loader opens (`Fopen`/`Fseek`/`Fread`).
- **Long debugger command lines are truncated silently.** Example: `loadbin <300-char path>` printed only the usage text, so the payload was never loaded and the game crashed into zeroed code. Keep paths short (abtest now hashes its dir names).

## Concurrency
- Several harness instances can run at once. Displays are reserved atomically via `/tmp/.mw2harness-display-N`, and stale locks are reclaimed.
- Keep it to at most 2–3 concurrent cold boots: `boot_to_game` uses wall-clock sleeps and misses clicks under load.
- **Vehicle test states:** Raids -> pick an island (Space -> question icon -> thumbs-up -> In); islands start with different vehicles. Save snapshots there to test vehicles.
