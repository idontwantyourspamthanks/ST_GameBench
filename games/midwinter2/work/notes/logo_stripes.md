# Coloured stripes under the pictures on a Mega STE (TOS 2.06) in Hatari — root cause and fix (`patches/sync_blip.s`, both games)

Report (user): Hatari Mega STE (`dist/run_megaste.sh`: TOS 2.06, 4 MB, 16 MHz, rgb) shows coloured garbage stripes along the bottom of
the window under the orange MIDWINTER II logo screen (`reports/img/mw_logo_garbage.png`, 829x556, x 107-738).
Tools: `/tmp/mwlogo/run.py` (cold boot of the all-games image through `tools/test_hd_image.py`'s `test_image`/`hd_args`, screenshot + `m $ff8200`
every few seconds; the stripe metric = non-black pixels of the screenshot rows 512..551 = the 17 lines under the 200+30 visible lines), Hatari 2.6.1,
`dist/AtariST_enhanced_games_2026-11-10.vhd` before the fix.

## 1. Where they are
Window 832x588 (Hatari, statusbar on): the picture is at x 96-736, y 58-458 (320x200 at 2x). The stripes are at **x 106-737, y 518-551**, i.e. in the
**bottom border**, 60 px below the picture; they are NOT inside the 200 visible lines. They are identical on every screen and every video base:
`$78000` (black), `$50000` (FLAMES), `$60000`/`$70000` (logo, island intro, M/J/K screen), `$68000`/`$58000` (MW1): the same 20624 non-black screenshot
pixels, md5 `42fabb75` of the region on 40 consecutive screenshots of the static M/J/K screen. So they are not video RAM past `base+32000`.
Cleared only by a few 50 Hz frames (below).

## 2. Cause: 60 Hz TOS mode + PP's 50 Hz overscan picture, drawn by Hatari
- PP's intro-picture viewer (inside RUNME.TOS, the FLAMES OF FREEDOM / MIDWINTER picture, runs before the boot stub; code at `$21c00-$25278` of the
  TPA on the Mega STE run) saves `$ff820a` at start (`move.b $820a.w,$251d7`, `$21c36`), then runs 50 Hz **top and bottom border removal** every frame
  (`clr.b $820a` at `$21dfc` / `move.b #2,$820a` at `$21e06`, `$24910`/`$2491a`), and at its end restores the saved mode (`move.b $251d7(pc),$820a.w` at `$2523a`).
- Hatari `--trace video_sync` (1000 frames, then): `sync=0x00 ... nHBL=308 pc=2523a` = the restore, no sync write afterwards.
- TOS 2.06 in Hatari boots in **60 Hz** (`$ff820a` = 0, statusbar "RGB 60 Hz"; TOS 1.62 = 50 Hz, `$ff820a` = 2), so the restore puts the machine back to 60 Hz.
  Hatari's window is 29 + 200 + 47 lines (`screen.h`: `OVERSCAN_TOP 29`, `MAX_OVERSCAN_BOTTOM 47`) and a 60 Hz frame has only 263 lines (18 fewer than the
  50 Hz window needs), so the lowest 17-18 border lines are not part of any 60 Hz frame and keep what the last overscan frame drew there: the last picture rows.
  (Hatari's `memset` of the unused lines in `Video_DrawScreen` clears only the ST line buffer, not the SDL window rows; and stripes appear/disappear with
  palette fades — frame samples of 0 between screens — but come back, so the exact redraw logic is not worth reverse engineering.)
- **It is not ours.** Evidence:
  ```
  A  unpatched PP files (RUNME.TOS+HAGA, test_hd_image --original), Mega STE 2.06 4 MB 16 MHz: stripes 20624 px from the viewer's end (11 of 22 shots: rows 518-551 x 106-737)
  B  STE TOS 1.62 1 MB 8 MHz (50 Hz), patched image:                                         border clean on every shot after the picture (no stripe frame)
  C  STE TOS 1.62 1 MB, `w $ff820a $00` (60 Hz) before the viewer saves the mode, patched:     20624 px stripes from the end of the viewer on, all screens (same as Mega STE)
  D  Mega STE 2.06 1 MB 16 MHz / 4 MB 8 MHz, patched:                                        20624 px from the viewer's end on (RAM size and CPU clock do not matter)
  E  Mega STE 2.06 4 MB 16 MHz, patched, stripes present, `w $ff820a $02` for 0.05 s and back:  0 px afterwards, for the rest of the run
  ```
  So: credit patches, `pp_bigram_cache`, `pp_nofade`, RAM size, 8/16 MHz: all irrelevant. Only the sync mode TOS booted with matters.
- TT (TOS 3.06, `--mmu true`): no stripes in Hatari (TT frames are drawn by `Video_RenderTTScreen`, no ST border emulation); without `--mmu true` the patched
  and unpatched game stop after the title picture (black screen), see MWTT's notes. MW1: the stripes are visible ~5 s (after the viewer, black screen and the MW1
  title pictures) and then vanish by themselves (a Hatari full redraw at the game start), unchanged by the fix.
- The credit buffers are not involved: the credit rows 188-196 and the buffers `$60000`/`$70000` are inside the 32000 bytes (`$ff8201/03/0d` read = `060000`/`070000`).

## 3. Fix (default patch `sync_blip`, HD and floppy builds, MW1 and MW2)
First thing at game entry (MW2 site `$3104` `jmp $312a8`, MW1 site `$800` `lea $2d446.l,a7`; blob `$B9400` / `$B9200`): if bit 1 of `$ff820a` is clear (60 Hz)
write 50 Hz, wait 4 frame starts (`movep.w` of the video counter `$ff8205/07` falls back to the base; no interrupts needed; each poll is bounded to 20000 reads),
let the next frame run ~50 display lines, write the booted mode back. At 50 Hz (TOS 1.x): nothing. d0-d4/a0 are saved. The game's picture/code is untouched.
Tried and discarded: a blip inside the viewer (RUNME `$2523a`/vsync: 2 or 40 frames at 50 Hz) and one in the RUNME staging routine (before the boot stub;
SR `$2700`): both leave the stripes (they only worked when run after the black game screen was up).
Residual: the stripes are visible from the end of the viewer until the game starts (black screen while the boot stub loads, ~5 s); the logo screen and everything after is clean.

## 4. Verification
Raw: `/tmp/mwlogo/*.log` (stripe counts per screenshot). Patched MW2, Mega STE 4 MB: `f2.log` shot 16 (before game entry) 20624, shots 18-34 = 0 (logo,
intro, M/J/K); STE 1.62 1 MB + 60 Hz poke: stripes 20624 -> 0 from the game entry. Gates: see the task report (verify ALL OK, cold boots).
