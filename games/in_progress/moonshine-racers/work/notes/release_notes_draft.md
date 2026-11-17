# Moonshine Racers - release notes draft (user-facing)

Status: draft for the shipped build (patches/VERSION). Numbers are Hatari 2.6.1, STE TOS 1.62 1 MB unless a machine is named; no real hardware was available for any of them.

## What changed in this build

Already in the previous default set (unchanged): the new top-bar HUD and no clouds, the faster road (tables generated at race load), the fixed tick at 10 game steps per second (`TICK 30`, exact at 50 and 60 Hz, 20 % faster than the original 8 MHz speed, and now the same speed on every CPU clock), and the "tightening" patches (`ta_*` speech/ticker, `tc_*` logic stage, `tb_car`/`tb_carph` player car).

New by default in this build (all user-approved):

1. **Extra in-between pictures, drawn earlier (`mg_sync` + `mg_pace`, replacing `mx_sync` + `mx_pre`).** The extra pictures are now drawn before the collision/debris stage of the pass, which is much cheaper: on an 8 MHz STE the game now draws an extra picture in **63 % of the racing steps (16.0 pictures per second)** instead of 29 % (12.7). At 16 MHz: 2.0 extras per step (28.8 pictures/s), at 32 MHz 4.0 (47.9). The game speed is unchanged (10.000 steps/s measured).
   - Two small, visible differences of the extra pictures themselves (never of the normal pictures): an extra picture shows the top bar of its own step (the old machinery showed it one step ahead, e.g. the turbo gauge after a crash slowdown), and in a collision bounce the two extra pictures of that step still show the car before the bounce displacement.
   - Frame spacing is more uneven than before at the default margin: 8.5 % of the 8 MHz steps end more than one frame (5 VBL) late (old default 5.6 %). `--safex 3` (build-time `SAFE=3`) is smoother: 15.3 pictures/s with 1.5 % late steps (the earlier draft said 14.6 / 2.2; measured on the final set now).
2. **Raster-list trimming (`ta_rb`, `ta_rb0`).** Timer B interrupts that re-write the sky colour it already has are removed; the same colour on every scanline and the same palette switch (verified in Hatari's palette-write trace). About 4.9 k cycles per step.
3. **No mouse query during the race (`ta_nomouse`).** The VBL handler no longer interrogates the IKBD mouse position while the race runs; the joystick and keyboard are unaffected, and the race never reads the mouse variables. About 8.2 k cycles per step. Menus outside the race keep the query.
4. **STE blitter for the big shifted sprites (`tb_blit`, `tb_blit11/13/15`).** Only the 1-3 column sprites that are wide enough, only on a plain STE/ST with a real blitter, and only between two raster interrupts (the Timer B guard waits until the next raster interrupt is at least two scanlines away). About 9.7 k cycles per step (0.06 frame). This is the item with the least margin on real hardware: it is the one to A/B first.
5. **Talking face drawn once per message (`ta_facestat`).** The face no longer moves its mouth while a message is typed or held; the rest of the face (eyes, blink frames of the message) is unchanged. About 1.4 k cycles per step.

Measured effect at 8 MHz STE, tick off, same passes: a driving step goes from **2.796 to 2.661 VBL** without a message and from 2.903 to 2.757 with one (`race_up`: 2.970 -> 2.812 / 2.751 -> 2.631). With the tick on that is what buys the extra pictures.

### Speed numbers (one definition each, `integration.md` 12.14 is authoritative)

| figure | build / scene | definition |
|---|---|---|
| **16.0 pictures/s, 63 % of steps with an extra** | this release, 8 MHz STE, steered driving (race_drive, 130 s) | displayed fps over steered racing ticks (after the time-out/restart; `ext_X_8.json`) |
| 15.3 pictures/s, 56 % | same, built with `--set SAFE=3` | same |
| 12.7 pictures/s, 29 % | previous release build (`mx_sync` + old options) | same |
| 15.2 pictures/s | this release, whole 137 s window incl. time-out and standing start | whole-window average |
| 28.8 / 47.9 pictures/s | 16 / 32 MHz, steered racing ticks | displayed fps over steered racing ticks |
| 17.1 pictures/s (8 MHz), 28.5 (16 MHz) | cold boot, 'up' held, **no steering**, 10.5 s window | cold-drive window - not the same metric as the 16.0 above |
| 15.48 fps / 57.6 % (earlier note) | `mg_sync` on the *previous* patch set | same as 16.0 but a different build (pass 2.80 vs 2.66 VBL) |

Nothing else of the game changed: per-step game state is equal to the original game on every compared pass (start, driving with the time-out and restart, and steered driving), and the normal pictures are identical outside the face box (the only exception is one message-text cell in the time-out sequence at 16 MHz, which the previous default shows as well).

## Game speed

10 logic steps per second, exactly, on every machine and CPU clock (50 and 60 Hz). That is 20 % faster than the original release's 8 MHz speed (8.33 steps/s) and no longer scales with the CPU. A machine too slow for one step per tick simply runs late and resyncs - it never skips steps.

## Real-hardware check list

Run each item, then switch the patch off (`tools/play.sh --no-...`, see below) and compare. Builds for a real machine: `python3 tools/msrpatch.py build --out <dir>` (add `--set SAFE=3` for the smoother margin), then copy the folder.

| what | how to look | switch off |
|---|---|---|
| `tb_blit*` | STE only: drive 2-3 minutes with the sky in view at the horizon and over hills. The sky must show clean colour bands with no flicker or a band jumping one line; the sprites (cars, scenery objects) must look exactly as before. This is the risk item: the guard assumes the raster interrupt is never delayed - Hatari says it is not, a real STE bus is not modelled. | `tools/play.sh --no-blit` |
| `ta_rb`, `ta_rb0` | same drive: sky bands and palette split; no colour flashing at the horizon on any track (the table has 8 sky colours on track 1). | `tools/play.sh --no-rb` |
| `ta_nomouse` | the menus after a race and the race-setup screens: the mouse must still move the pointer and click; in the race the joystick/keyboard must steer and accelerate as before. | `tools/play.sh --no-nomouse` |
| `ta_facestat` | a radio message while driving: the face should be drawn, hold the first mouth frame and not animate the mouth; everything else (message text, box, colours) unchanged. | `tools/play.sh --no-facestat` |
| `mg_sync` + `mg_pace` | driving: the top-bar gauges should step once per logic step, and the extra pictures should show the car/road slightly behind the next normal picture; in a collision bounce the two extra pictures of that step show the pre-bounce position. Nothing should flicker or tear. | `tools/play.sh --noextrap` (fixed tick, no extras) or `--safex 3` (fewer, more even extras) |
| frame spacing | at 8 MHz with the default margin some steps take two frames; if that looks uneven on a real machine, use `--safex 3`. | `--safex N` |

## Machines tested (Hatari)

STE TOS 1.62 1 MB and 4 MB, Mega STE TOS 2.06 1 MB, both HD and floppy builds, cold boot into the race and a 2-minute drive (`ste` at 8 then 16 MHz: 17.1 / 28.5 pictures/s; Mega STE at 60 Hz: 22.5 / 21.0). Real hardware: not tested. TT/Falcon: the previous set booted; this exact default set was not re-booted there (the player car always uses the stock kernel on those machines).
