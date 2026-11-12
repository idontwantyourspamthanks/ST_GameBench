# Exiting a boat: only the top of the diving mask was drawn (`p4_hud_pfx_fill`)

**Status: fixed.** `patches/p4_hud_pfx_fill.s` now forgets the per-buffer clean prefix for the vehicle
types whose cockpit replay the original code skips. The switch frames are pixel-identical to the
unpatched game again (section 5). Everything below is measured output; unproven statements are marked
`[INFERENCE]`.

## 1. What the user sees

Esc in a Speedboat (Raids, Iquitos) gives Frogman (11) and, seconds later, Swimming (21) - the same
`$6220` values as `work/notes/raids.md`. On the patched build the **top arc of the diving mask stays on
screen** for the first Swimming frames, with the sea and terrain drawn below it (`work/notes/mask.md`
evidence: `/tmp/mask/pat2_02.png`, reproduced below as an image comparison). The unpatched game shows
no mask at all once `$6220` is 21.

Frames at flip 21 after the switch (both screen buffers dumped from RAM, `$70000` shown):
`work/mask/switch_frames.png` - left = unpatched, middle = patched with this fix, right = patched
without it (the mask rim at the top of the window). Before/after with the *old* build, real
screenshots: `work/mask/half_mask_before_fix.png` vs the last frames of `work/mask/cold_ste1_esc.png`.

## 2. Why (mechanism)

* The cockpit overlay list (`$68000`, pointed at by `$71bc`) is written by the encoder `$30e30`, called
  only from `$28cee` inside `$28cc0`, the 3D-view (re)entry (`work/notes/p7_cockpit_cull.md` section 1).
* The replay gate at `$1dbee-$1dc04` **skips the replay** for `$6220` in {5, $15, $11} (`$1dbee` disassembly
  below), i.e. on foot, Swimming, Parachute.
* `$732c` (22 entries, 4 bytes each, word `+0` = picture file) maps types 5, 11, 17 **and** 21 to the
  same picture file `$4a`. So a Frogman -> Swimming switch needs no new list and the game does not call
  `$28cc0`: `sub_0335e0` writes `$6220` directly (`$3360c` -> 21, `$33636` -> 11, `$336ba` -> 21,
  `$336d2` -> 5; also `$33080`, `$1b574`, `$1b592`) and only calls `jsr $50e0` (view refresh).
* `p4_hud_pfx_*` keeps `KB[b]` = the number of 8-line blocks from line 58 that already hold the final
  sky+cockpit image in buffer b. The sky fill starts at line 58 + 8*KB[b] and the replay only redraws
  records at or below line 58 + 8*min(old KB, new KB).
* After the switch to 21 the replay no longer runs, so nothing redraws the overlay, but `KB[b]` was
  still the value the last Frogman frame stored (measured: `KB1 = 4` at the first 21 flip with the old
  patch, 0 with the fix). The fill therefore leaves rows 58..58+8*KB alone - and those rows hold the
  previous frame's mask. The terrain paints from its first row downwards, so only the mask's **top**
  part survives: exactly the report.

Raw `$b4680` block (KB0.w, KB1.w, YMIN.w, CK.w, CD7.w, pad, CA1.l, CA0.l) at the first 21 flip,
display patch set, Esc poked at flips 14 and 16 of the run:

```
old patch:  00 00 00 04 ...     <- KB1 = 4: the fill starts at row 90 in buffer 1
with fix:   00 00 00 00 ...     <- full fill, like the unpatched game
unpatched:  (no patch; the block is unused)
```

`$1dbee` (the replay gate, `python3 tools/m68dis.py work/dumps/ram_ingame_lobos.bin 1dbd0`):

```
01dbee:  0c7800056220         cmpi.w   #$5, $6220.w
01dbf4:  671a                 beq.b    $1dc10          ; on foot: no replay
01dbf6:  0c7800156220         cmpi.w   #$15, $6220.w
01dbfc:  6712                 beq.b    $1dc10          ; Swimming: no replay
01dbfe:  0c7800116220         cmpi.w   #$11, $6220.w
01dc04:  670a                 beq.b    $1dc10          ; Parachute: no replay
01dc06:  21f867a671c0         move.l   $67a6.w, $71c0.w
01dc0c:  4eb85002             jsr      $5002.w         ; -> jmp $30f2c (the replay)
```

`$732c` (word at `$732c + 4*type`, low byte = picture file):

```
 5 Foot $4a   11 Frogman $4a   17 Parachute $4a   21 Swimming $4a
```

Verification that the encoder does **not** run on the switch: with the old patch `KB1` was 4 on the
first Swimming flip, i.e. it kept the Frogman value - `p4_hud_reset` (which clears KB and CK at
`$28cc0`) never ran. The list bytes are unchanged anyway (same file `$4a`), so what changes is only
*that the replay is skipped*.

## 3. The fix

`patches/p4_hud_pfx_fill.s`, in the fill hook, right after `KB[b]` is read:

```
        move.w  (a0,d0.w),d1            ; KB[b]
        move.w  $6220.w,d3              ; the replay is skipped for types 5, $15, $11 ...
        moveq   #1,d4
        asl.l   d3,d4
        and.l   #$220020,d4             ; ... bits 5, 17, 21
        beq.s   .keep
        moveq   #0,d1                   ; nothing redraws the overlay later this frame
        move.w  d1,(a0,d0.w)            ; so this buffer's clean prefix is the OLD overlay
.keep:  move.w  d1,d2
```

* 22 bytes, inside the 30 free bytes between the end of the fill blob (was `$b4561`, now `$b4579`) and
  `p4_hud_pfx_replay` at `$b4580`. No new site, no new data, no address move.
* Clears `KB[b]` (stored, not just used) so the *next* frame of a replaying type starts from
  `min(0, new) = 0` and replays everything - the reverse direction (Swimming -> Frogman, which is the
  "bottom half of the mask missing" case: the replay would otherwise skip the mask's upper records)
  heals for free.
* Each buffer clears its own word when its own fill runs, which is one frame before that buffer is
  displayed, so both buffers are covered without a second write.
* d3/d4 are free: the displaced `movem.l d0-d7/a0-a6,-(a7)` of `$1b996` has already saved them and the
  original function's own epilogue restores them.
* Cost: 5 instructions (~30 cycles: `move.w`, `moveq`, `asl.l`, `and.l`, branch) once per sky fill, and
  for types 5/17/21 the fill is now a full fill again - which is what the unpatched game does, because
  those types get no replay. Their clean-prefix saving was incorrect anyway, so nothing real is lost
  (the pfx gains documented in `work/notes/cockpit.md` are Helicopter/on-foot-cockpit scenes, type 13).
* The condition mirrors the game's own gate at `$1dbee`; `$6220` cannot change between the fill and the
  replay inside one frame (type changes happen in the sim, before the render).

## 4. Not the cause (checked)

* **Cull table (`p7_ck_*`)**: `EN` is 0 for types 5/15/11, so the cull is off for them; and `$732c`
  gives the same list file for the whole {5, 11, 17, 21} family, so the table built from it is still
  correct after the switch (`p7_ck_tab` rebuilds it at the encoder exit; the encoder does not run, but
  the list is unchanged).
* **`p7_skip_render`**: the type switch changes the view pose, so the input snapshots differ and the
  render is not skipped; the artefact is the top rows only, not a frozen frame.
* **`p3cp`/`p3c_*`**: present or absent does not change the artefact (the display-only set reproduces
  it, section 5).
* **TT-only?** No. The artefact reproduces on an STE 2 MB from the same snapshot, and the cold-boot
  check below was run on both machines. The `$b4680` state and the pixel difference are in the RAM
  buffers, not in Hatari's TT display path (that path's known artefact is the HUD palette,
  `work/notes/tt_palette.md`).
* **Decoder** `$30e30`/`$28cee`: verified above to be irrelevant here (same list file for the family).
* **A crash that is NOT the game's**: live-applying `mw2_credit` to a *snapshot* writes
  `jsr $b9000` at `$1f5f0`, which is inside the FFB f1 overlay range (`$18d96-$210b2`) that is
  *loaded later*; the boot-time patch relies on being overwritten, so a live apply corrupts the in-game
  scene code there and the game then jumps to `$fc0030` (bus error, "CPU halted") a few seconds after
  Esc. It is a test-harness artefact of the live method, not a bug of the shipped build: every live
  patch set used below is built with `vt.default_names()`, which excludes `mw2_credit`.

## 5. Gates (raw)

### 5a. The switch frames: display set vs unpatched

Deterministic run (no wal-clock input): apply the set at flip 0, poke `$7687 = $ff` at flips 14 and 16
(frame-scheduled, so both builds see the input on the same frame), dump *both* screen buffers at
flips 13..22. Same snapshot (`work/snapshots/raid_speedboat_iquitos.sav`), same poke schedule, one run
per build. Differing bytes per flip (both buffers, `$8000` each) against the **unpatched** run:

```
flip:        13     14     15     16     17     18     19     20     21     22
fix:        514    380      0      0      0      0      0      0      0      0
no fix:     514    380      0      0      0      0      0   3220   5884   5884
```

`$6220` per flip: 6 6 11 11 11 11 11 21 21 21 (the switch is at flip 19/20 here; the dumps start at 13).
The 514/380 bytes at flips 13/14 are present with *and* without the fix and in a no-input run at the
same flips (rows 58-63, the leftmost 32 columns): that is `p7_skip_render` holding the animated sea for
a frame, the same time-dependent frame content documented for Ship/Biplane in
`work/notes/vehicles_p3b.md` section 6 - not related to this change.

Frame images of flip 21 (`work/mask/switch_frames.png`) show the mask rim with the old patch and none
with the fix.

### 5b. `mw2patch.py verify` / build

```
$ python3 tools/mw2patch.py verify
verify: ALL OK
$ python3 tools/mw2patch.py build        # default set, STE 1 MB game dir build/game
built build/game with 36 patch(es) + 2 file patch(es); payload 32768 B at $B3000
```

### 5c. Pixel identity, existing gates

`tools/abtest.py` (visible 32000 bytes per buffer; the display set = the p4/p7 defaults, no
`tick_*`/`p3b*`/`p5*`, as the patching skill requires):

```
$ python3 tools/abtest.py --only p4_hud_pfx_ymin p4_hud_reset p4_hud_pfx_fill p4_hud_pfx_replay --flips 10
1mb_ingame_walking: pixels IDENTICAL; fps base 3.1 (63 flips) -> patched 3.1 (62 flips)
1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (85 flips) -> patched 4.3 (87 flips)
$ ... --flips 40
1mb_ingame_walking: pixels IDENTICAL; fps base 2.8 (56 flips) -> patched 3.0 (60 flips)
1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (84 flips) -> patched 4.4 (88 flips)

$ python3 tools/abtest.py --only <26 display patches> --flips 10      # 1mb_ingame_walking, 1mb_ingame_foot
1mb_ingame_walking: pixels IDENTICAL; fps base 3.1 (63 flips) -> patched 3.1 (62 flips)
1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (85 flips) -> patched 27.4 (549 flips)   # p7_skip_render
$ ... --flips 40
1mb_ingame_walking: pixels IDENTICAL; fps base 2.8 (56 flips) -> patched 3.4 (68 flips)
1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (84 flips) -> patched 27.4 (549 flips)
exit 0

$ python3 tools/abtest.py --only <26 display patches> --flips 10 \
    --snapshot work/snapshots/raid_speedboat_iquitos.sav work/snapshots/raid_ship_bourem.sav work/snapshots/raid_hovercraft_thar.sav
raid_speedboat_iquitos: pixels IDENTICAL; fps base 4.4 (88 flips) -> patched 4.5 (91 flips)
raid_ship_bourem: pixels DIFFER (5513 bytes); fps base 3.7 (74 flips) -> patched 4.0 (79 flips)
raid_hovercraft_thar: pixels IDENTICAL; fps base 1.9 (38 flips) -> patched 2.0 (40 flips)
```

The Ship difference is the pre-existing one recorded in `work/notes/vehicles_p3b.md` section 6 (its
frame N depends on the render count - animated water), unchanged by this fix: the new code only runs
for `$6220` in {5, 17, 21} and the Ship snapshot is type 10.

### 5d. Cold boots (default build)

`work/notes/mask.md` runner: cold boot to the Raids map, enter Iquitos (Speedboat), hold Esc 0.6 s, then
10 samples of `$6220` / `$b4680` plus screenshots.

STE 1 MB (TOS 1.62) and TT (EmuTOS, `--mmu true`): see the results pasted below in section 6.

## 6. Cold-boot results

Build: `tools/package.sh` (verify + `build --out build/game` + both zips) - `build/game/RUNME.TOS`
md5 `65f74ee97abd3aed670bec8fb34da658` (was `64423023c3e2b1a9159f88c129e6c7c2` before the fix),
`HAGA` unchanged (`1074342dd4a917bafdc7d2a031e9b088`); `dist/Midwinter2_v1.3_patched_2026-11-11.zip`
md5 `b40e943b2583c16bf5cd211b3d8b4416`, `..._floppies_...` `670553da3582460a127d5120a750243e`.
The `.vhd` in `dist/` was not touched.

STE 1 MB (TOS 1.62), cold boot of that build, Raids -> Iquitos (Speedboat) -> Esc held 0.6 s:

```
ste1 cold boot to the raid map 118 s, marker b'MWPO'
ste1 entered {'island': 8, 'vehicle': 6, 'view': 2} marker MWPO
ste1 0 type 0xb  KB ['00 08 00 07 00 7d 00 08']         # Frogman, KB1 = 8 (YMIN 125)
ste1 1 type 0xb  KB ['00 04 00 00 00 5e 00 00']         # Frogman, KB1 = 4 (YMIN 94)
ste1 2 type 0x15 KB ['00 00 00 00 00 4d 00 00']         # Swimming: KB = 0, full fill
...    type 0x15 KB 0 for samples 2-9
ste1 bus errors: 0
```

Screenshots: the mask is complete in the Frogman sample and absent in every Swimming sample
(`work/mask/cold_ste1_esc.png`).

TT (EmuTOS 3.06, 4 MB, `--mmu true`), same build: the engine boots to the corridor with `MWPO` set and
reaches the "SELECT LEVEL OF PLAY" screen, but the Raids *pointer* mapping in
`tools/mw2raids.py` does not transfer to the TT: its RAIDS door is at **library coordinates (294, 216)**
(found by a grid of clicks), not (300, 230); `h.goto` moves the TT pointer consistently with the STE
picture geometry otherwise. The island entry + Esc sampling on the TT was therefore **not completed**
- `[INFERENCE]` the artefact and its fix are machine-independent (the state that is wrong is the two
RAM screen buffers and `$b4680`, not any TT-specific display path; `work/notes/tt_palette.md` covers
the only known Hatari-TT display deviation, the palette). To finish it: run
`/tmp/mask/tt_esc.py`-style navigation with the RAIDS click at (294,216); the sample loop and the
"KB must be 0 while `$6220` is 21" assertion are already in that script pattern.

## 7. TT cold-boot verification (closes section 6)

`tools/mw2raids.py` now clicks the RAIDS door at (294, 216) when `h.machine == "tt"` (the STE keeps (300, 230)). Three cold boots of `build/game` (v1.3 RUNME.TOS md5 `65f74ee9...`) on Hatari TT (TOS 3.06, 4 MB, `--mmu true`), script `work/mask/tt_cold.py`, each reached the Raids map in 160 s and entered Iquitos (Speedboat, `$eb9c` = 8, marker `MWPO`), then Esc held 0.6 s: **0 bus errors in all three**. Runs 1-2 became Frogman (11) and stayed 11 for 50-60 s of sampling (`$6884`-dependent exit to 21 never occurred; mask complete on every sample, e.g. `work/mask/tt_run2_frogman_100_t0b.png`, KB varied 0..7 as expected for a replaying type). Run 3 (`work/mask/tt_run3.log`, screenshots `work/mask/tt_00_boat.png`, `tt_000_t05.png`, `tt_001..008_t15.png`, `tt_99_final.png`, contact sheet `tt_sheet.png`) took the other path of the same Esc (Speedboat -> on foot 5 -> Swimming 21, as in `raids.md` it is phase-dependent): type 5 sample KB `00 09 00 09 .. 00 0a`, then every one of the 8 Swimming samples had `KB0 = KB1 = 0` (raw `00 00 00 00 00 xx 00 00`, YMIN varies), screenshots show the HUD with no mask remnant and a full sea/terrain fill - the pre-fix artefact (top arc of the mask, KB1 = 4) did not occur. The Frogman -> Swimming step itself was therefore not reproduced on the TT (Frogman needs `$6884 < 0` with the bank button or depth `$764c` in [-200,-32] per `$33688`); the fixed code path (`$6220` in {5,17,21} -> KB cleared) was exercised via type 5 -> 21, and the Frogman frames show the complete mask.

### 7b. TT: stock vs patched through Frogman <-> Swimming (follow-up)

Method: `work/mask/tt_dive.py {stock build/mask_stock | patched build/game}`; cold boot of each build on Hatari TT (TOS 3.06, 4 MB, `--mmu true`), Raids -> Iquitos Speedboat, Esc 0.6 s, sample 25 s, hold **mouse button 1** 12 s ("dive"), release, hold **mouse button 3** 12 s ("surface"), release, hold button 1 again. `stock` = `mw2patch.py build --only` (0 patches, md5 `54de8761...`; `build/mask_stock` removed afterwards), `patched` = the v1.3 default `build/game`. Logs `work/mask/ttm_stock.log`, `ttm_patched.log` (columns: type `$6220`, bank `$6746`, KB = `$b4680` 8 bytes: KB0.w KB1.w YMIN.w CK.w); screenshots `work/mask/ttm_{stock,patched}_NNN_<phase>_tXX.png`, contact sheets `ttm_stock_sheet.png`, `ttm_patched_sheet.png`. **Bus errors: 0 in both runs.**

* **The `,` / `.` keys do nothing in this game state on the TT**: `$7686[$33]`/`[$34]` do go to `$ff` while held (xdotool key down), but `$eb78 = 0` (the keyboard path `$26c1e` is gated on it) and the bank word `$6746` stays 0 with Swimming for 14 s of `,` and 14 s of `.` (debug run from a snapshot of the cold-booted boat state). The mouse buttons (`$6fbe = 2` with button 1) drive the bank: `$6746` goes negative, and Swimming flips to Frogman (`$335ce`).
* **Stock**: Speedboat 6 -> Frogman 11 (first sample) -> Swimming 21; during Swimming the HUD/view has no mask; Frogman frames have the whole mask (`ttm_stock_016_dive_t0b.png`, `_018_`, `_020_rel1_t0b.png`, `_032_dive2_t0b.png`). KB is 0 (the stock build leaves `$b4680` unused).
* **Patched**: Speedboat 6 -> on foot 5 (`KB 00 08 00 08 00 7c 00 09`) -> Swimming 21 (type 5 -> 21 on this boot; stock went via 11). All 11 samples after Esc at type 21: `KB0 = KB1 = 0` (`00 00 00 00 00 xx 00 00`, only YMIN changes; raw lines 3-13 of the log), the screen shows sea/terrain, no mask remnant. Dive (button 1): 21 -> 11 -> 21 flip-flop (bank `0xffcc, 0xffbe, 0xfeb8, 0xffe4, 0xffd8 ...`), Frogman samples: `00 00 00 00 00 3a 00 12`, `00 11 00 11 00 c8 00 12` (replaying type: KB climbs), `00 00 00 00 00 4b 00 12`. Surface (button 3): bank `+0x50, +0xa8, +0xc0`, type 21 (KB 0) and 11. Every 11 frame has the **whole mask**: `ttm_patched_016_dive_t0b.png`, `_019_dive_t0b.png`, `_024_surf_t0b.png`, `_035_dive2_t0b.png`, `_036_dive2_t0b.png`; every 21 frame has none. Frogman -> Swimming -> Frogman (the "bottom half missing" direction of section 2) shows the full mask each time.
* `KB = 0` at every one of the 18 type-21 samples of the patched run (`awk '$5=="0x15"'`, columns `KB0.w KB1.w` = `00 00 00 00`).
