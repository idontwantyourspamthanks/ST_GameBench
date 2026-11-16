# Moonshine Racers: performance release plan

Status (integration wave, `work/notes/integration.md`): **the default patch set is integrated and gated.** HD and floppy builds default to `pp_bigram_cache` (HD), `mr_edge mr_map mr_digit` (pixel-identical render),
`rd_geom rd_draw rd_init` (pixel-identical road, tables generated at race load), `mt_clock mt_pre mx_pre mx_sync` (fixed tick, `TICK equ 30` = 10 passes/s, exact at 50 and 60 Hz, plus extra in-between frames where the CPU has spare time; `mt_sync` = the same pacer without extras, `play.sh --noextrap`); floppy additionally `fl_hook fl_deprot`.
Not default: `mt_sync`, `mr_negctl`, `test_*`. Evidence: `work/notes/{rendering,render_patches,road,tick,timing,extrap,integration}.md`.
Version/credit line (mandatory, user picks the screen): `v1.0 enhanced by dad_prg`, kept in one place in the patch source (`patches/VERSION`; the credit patch itself is not written yet).

## Decisions taken
- Fixed tick T=30 (user-approved): the game runs 20 % faster than the stock 8 MHz driving speed (8.33 -> 10 passes/s) and at that speed on every CPU clock and at 50/60 Hz; a pass slower than the tick runs late once and the pacer resyncs (`tick.md`, `integration.md`).
- The road patches ship by default; their one-off table generation (about 18 VBL) runs in `rd_init` at the race setup (`$78f6`), before the race loop, never in the first road frame.
- Patch tool: `; ram:` reserved work RAM (collision/layout-checked, not in the image), `; requires:` / `; conflicts:` enforced (build, live, `--only`, defaults, verify); `mx_sync` replaces `mt_sync` by declared conflict.
- No sprite patch (`work/notes/sprites.md`), no blitter road (`road.md` section 4), no repaint skipping (`road.md` section 5).

## Remaining
- Credit patch (`v1.0 enhanced by dad_prg` on a screen the user picks) and release version.
- User docs: README.TXT / PATCHES.TXT wording for the final set (the build already fills `{PATCHES}`), packaging (`build --zip`, `build --floppy --zip`, `dist/`).
- User decisions: the extra frames `mx_*` are default (approved); known tolerance: main frames differ from stock by <= 2 bytes of cloud-edge residue on some tracks (`integration.md` section 8; disappears with the clouds); blitter (rejected with numbers, unless the user wants a Mega STE/TT specific experiment); the clouds (12 cloud sprites ~9 % of a frame: removing them is a visible change).
- Not tested anywhere: real hardware (everything is Hatari 2.6.1), Falcon, a native 60 Hz boot, the tracks after the first (see `integration.md` for what was reached).

## Goals and preferences (carried over from `st-game-speedup`)
- Target: 1 MB 8 MHz STE (TOS 1.62). Must not break: ST, Mega ST, Mega STE (HAGA already runs it at 16 MHz + cache), TT, Falcon; 1 MB and 4 MB.
- Pixel-identical by default; any visible change needs before/after screenshots and approval.
- Deliverables: patched copies (never `originals/`), a patch tool that verifies original bytes, HD zip (+ floppy set if a floppy release exists: PP's only release is HAGA HD; see open question Q1), `play.sh` launcher.
- Game speed must not depend on frame rate (see P3, needs the user's decision Q2).

## Key facts that drive the plan (measured, `rendering.md` sections 3-5)
- 8 MHz STE: 8.3 fps driving (6.0 VBL/frame), 9.9 fps standing on the grid (5.06 VBL/frame). 16 MHz and 32 MHz both give exactly 16.67 fps (3.00 VBL/frame): the sync code has a **3-VBL floor** and a wasted wait after every flip.
- Pure CPU: no disk, no blitter, no DMA in the race. Frame = ~810-960 k cycles.
- Game speed is **frame-coupled**: world speed at 16 MHz is 2.03x the 8 MHz one (`$5ff8` 82.4 -> 167.0 units/s).
- Flat profile: sprites/objects 27 %, road draw 20-22 %, 12 cloud sprites ~9 %, road geometry 10-12 %, minimap 6 %, idle wait 5-12 %, HUD ~10 %, IRQ+sound ~5 %.

## Phases (each: gate = pixel A/B on snapshots, cycles/frame via `tools/msrstages.py`, cold boot of the default build)
- **P0 Harness (done in the study):** `tools/msr.py` (`Moonshine`, `boot_to_race`, `drive`), `msrbench.py` (fps + world rate at 8/16/32 MHz), `msrprofrun.py`/`msrprof.py`/`msrtree.py` (profile buckets), `msrstages.py` (per-call cycles of the frame loop), `msrframes.py` (consecutive frame capture), snapshots in `work/snapshots/`.
- **P1 Patch tool + delivery:** HAGA/RUNME hook, payload at `$B2700-$E8400` (1 MB), `verify`/`build`/`live` (copy `midwinter2/tools/mw2patch.py` design). Gate: marker set after cold boot at 1 MB and 4 MB on STE, Mega STE, ST.
- **P2 Sync (ranked #1, cheap):** remove the 3-VBL floor, move the post-flip VBL wait from `jsr $d206` in the flip routine to just before the first back-buffer write (`jsr $17c42`). Expected +2..12 % at 8 MHz, uncaps 16 MHz machines.
- **P3 Timing (needs Q2):** fixed-timestep world so speed no longer scales with fps.
- **P4 Redundant redraw skips (pixel-identical):** minimap `$f22c` (-50 k), clouds `$de1c/$de6c` (-80 k when unchanged), score digits `$f3b6` (-25 k driving), horizon scroll `$18318` (-40 k when scroll unchanged).
- **P5 Inner loops (pixel-identical, table-exact gates):** edge routine `$1058a` (-40 k), road geometry `$100b4` mulu to tables (-30 k), object dispatch `$e598`.
- **P6 Optional/visible:** STE hardware fine scroll for the horizon strip; fewer clouds; blitter only if measured (not expected).
- **P7 Regression:** every machine/TOS/RAM, 50/60 Hz, joystick/keys, save-state (`/` on keypad) and desktop exit (`*`), long play (race restart, game over), 4 MB cache mode.

## Estimated outcome at 8 MHz STE [INFERENCE: sums of measured routine costs, not measured end to end]
P2 + P4 + P5 together: ~170-180 k cycles removed from the 766 k / 846 k render cycles (grid / driving) plus most of the 43 k / 113 k idle wait: period 5.05 -> ~3.9 VBL (9.9 -> ~12.8 fps standing) and 5.98 -> ~4.3 VBL (8.3 -> ~11.6 fps driving), +30 % / +40 %. A big step beyond that needs sprite-work reduction (visible) or a span-level road repaint (high risk), see rendering.md section 6.

## Open questions for the user
See the end of `work/notes/rendering.md` (Q1..Q8).
