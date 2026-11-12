# Map-screen pointer invisible on a Hatari TT (fix: `p8_tt_ptr`)

User report (v1.3): on the island MAP screen the pointer is visible for a few seconds, then disappears; clicks still land. User's setup (from the lead): Hatari TT, HD image, JOYSTICK (J) mode, Raids island map, "the pointer comes back on the next screen".
Scripts and raw logs/screenshots: `work/mapptr/` (git-ignored game data). All coordinates below are game coordinates (`$6fae` x, `$6fb2` y).

## 1. Reproduction matrix (cold boots of `build/MW2MapPtr` = current default, vs `build/MW2MapPtr_stock` = `build --only` with no patches)
v1.3's HD RUNME.TOS is byte-identical to the current default minus the jag patches (`md5 65f74ee97abd3aed670bec8fb34da658` for both; HAGA identical), so the jag set is not involved.

| Machine | Result (stock and patched identical in every row) |
|---|---|
| STE TOS 1.62, 1 MB, M mode, Raids map and campaign Control map, hover / SPACE / text page / book / `?` / boss page | pointer drawn in every sample; 30 screenshots over 65 s (still and moving), patched vs stock **pixel-identical** (`ste_*`, `camp_ste_*`, `flow_ste_*`) |
| STE 8 / 16 / 32 MHz, Mega STE 4 MB 16 MHz | arrow present 25/25, 40/40, 20/20 (`sample.py`; flips per 250 VBL: 84 at 8 MHz, 250 at 32 MHz) |
| **TT, TOS 3.06, `--mmu true`, 2 MB, M mode** | **pointer absent on the map in every frame, stock included** (`ttser_stock`, 17 samples, 80 s, still and moving) |
| **TT, 4 MB, J mode (`--joy1 keys`), Raids map** | same: absent on the map (`jtt_stock`, `jtt2_stock`: m001-m012, hover), present on corridor, level page, island text page, boss page |

Hatari TT's picture on the map screen has no pointer at all; it is there on every other 2D screen. Not a patch regression: the stock game does it.

## 2. Mechanism (evidence)
Per frame (60 Hz TT), measured with `evt.py` (breakpoints `pc=$266d4` = pointer draw, `pc=$26ea2` = first instruction of the flip's base write; `info video` + memory in the hit files), STOCK, map snapshot:
```
draw  $266d4  VBL 13146 HBL line   2  Video base 0x60000  $67aa = 0x60000   (pointer drawn into the buffer on display)
flip  $26ea2  VBL 13146 HBL line 220  Video base 0x60000  $770e = 0x70000,0x60000   (base is about to become 0x70000)
draw  $266d4  VBL 13147 HBL line   2  Video base 0x70000  $67aa = 0x70000
flip  $26ea2  VBL 13147 HBL line 220  Video base 0x70000  $770e = 0x60000,0x70000
```
- The VBL handler's mode 0/1 routine (`$264f0` -> `$266d4`, `$264f0: move.w #$ffff,$6fc2.w`) draws the pointer into `$67aa`, which the flip `$26e98` sets to the buffer it has just put on display (`$26eae move.l (a6),d0 ... $26ebc move.l 4(a6),$67aa.w`).
- The map's main loop (`$24a64`/`$24a96: jsr $4f36.w` -> `jmp $26e98`) flips once per frame, at line 220, right after the handler's draw at line 2 (60 flips per 50 VBL counted by `fps`, i.e. >= 1 per frame at 32 MHz). The base register is written with `movep` BEFORE the swap (`$26eaa`).
- An ST/STE latches `$ff8201/03` at the next frame start, so the buffer the handler draws into is the one displayed in that frame (STE at 8/16/32 MHz: pointer always present, above). Hatari's TT/Falcon video takes the new base at once (Powermonger `tt_ptr`, games/done/powermonger/REPORT.md s.13), so every frame shows the buffer that has no pointer yet. In memory the pointer is in exactly one buffer (dump of the TT map snapshot: ring+arrow pixels at x 170-190, y 66-80 in `$60000` only, none in `$70000`).
- **Why "a few seconds, then it disappears" [INFERENCE from the time series, not from the user's words]:** the pointer is drawn on the page BEFORE the map (level-of-play page, flips 0) and stays visible while the island map loads (`$700a = 2`, `flips/50vbl = 0` for the first sample, `ttser_stock` k=0, `jtt_stock` m000). When the map's main loop starts (flips/50vbl = 60) the pointer is gone, and it stays gone until the next screen (text page: no flip loop, pointer present from s003). J vs M mode changes nothing on this path: J mode only changes who writes `$6fae/$6fb2` (`$26b58`/`$26b18`); flips/50vbl = 60 in both, pointer absent in both. No timer, redraw-skip or patch is involved: no default patch has a site on the 2D screens' flip or pointer code (patches touching the VBL handler: tick_vbl, p5_ctl_vbl, jag_poll: none draws or flips).

## 3. Fix: `patches/p8_tt_ptr.s` (default yes, 68020+ only)
Site `$26ea2` (`lea $ff8201.l,a0`, 6 B, first instruction of the base write; d0 = buffer to be shown, not yet shifted) -> `jsr $b4f00.l`. In modes 0/1 (`$700a < 2`) on a 68020+ the blob, with the VBL masked (`ori #$0400,sr`, the handler's own level): `$67aa := d0`; `tst.w $6fc2 / jsr $2684e / clr.w $6fc2` (the handler's restore of the saved lines); `jsr $264f0` (the handler's mode 0/1 routine: sets `$6fc2`, clamps, saves, draws; ends in `rts`). Then the displaced `lea` and `rts`. The pointer is in the buffer before the base register points at it; the next VBL handler restores and redraws as usual. Mode 2 (3D view): plain path (a mode word compare). All 15 registers saved.
- CPU test on first call: the index-register scale trick of `cpulib.s cl_detect` (no exception, no cookie jar: on a HD TT, HAGA remaps low RAM so `$5a0` is not TOS's jar). `TT_F` byte `$B4F80`: 0 unprobed, 1 68000/68010, 2 68020+.
- **ST / STE / Mega STE (68000):** the first call writes the 6 original bytes back to `$26ea2` and returns: the unpatched flip afterwards, 0 cycles (the same trick as `jag_poll`). Falcon is covered by the 68020+ test but MW2 does not run on a Hatari Falcon (not tested).
- Cost on a TT: one pointer restore + draw per 2D flip (~12 k cycles at 8 MHz, 0.4 ms at 32 MHz).

## 4. Results with the fix (same scripts; `*_fix` dirs)
TT, M mode, 2 MB (`ttser_fix`): arrow pixels (`arrow_px`) 164 in 16 of 17 samples (the 17th is the first one, taken while the map was still loading; stock: 0 of 17), flips/50vbl still 60, still and moving, 80 s.
TT, J mode, 4 MB, Raids map (`jtt2_stock` / `jtt2_fix`, `detect.py`; ring = 160 white px, arrow = 164 orange px; m003-m007 are over Agora, orange arrow is not distinguishable there, the ring is: stock white 0, fix white 160):
```
frame   stock  fix        frame   stock  fix
m001    none   PTR        m008-12 none   PTR (5/5)
m002    none   PTR        hover   none   PTR
m003-7  ring 0 ring 160   corridor0-2, level, s003-s019 (text page), b* (book), q* (boss): same in both (pointer present, pixel counts equal except s* text-page white count 352 vs 312 = different island/pointer position text overlap)
```
Side-by-side montages: `work/mapptr/jtt2_stock_montage.png`, `jtt2_fix_montage.png`, `jtt_m004.png` (stock left, fix right), `tt_before_after_010.png`.
Other 2D screens on the TT (corridor, level page, text page, book, boss page): the pointer is present in stock and fix; no extra or doubled pointer visible in the montages.
Direct proof of the new order (`evt_fix.txt`): at VBL 13107 line 222, `$266d4` is entered from the flip hook with Video base 0x60000 and `$67aa = 0x70000` (the pointer is drawn into the buffer that is about to be shown).

## 5. Gates
- `mw2patch.py verify`: ALL OK. `build` default set includes p8_tt_ptr (`$26ea2  boot  6 41f900ff8201 -> 4eb9000b4f00  [p8_tt_ptr]`).
- abtest (STE snapshots `1mb_ingame_walking`, `1mb_ingame_foot`, live): `--only p8_tt_ptr --flips 10` and `--flips 40`: all four IDENTICAL, flips 63/63, 85/85, 55/55, 84/84. Display set (`p4_*`, `p7_*`, `p8_tt_ptr`, without tick/p3b/p5/jag) `--flips 10` and `--flips 40`: all IDENTICAL, exit 0 (`abtest_set_10.txt`, `abtest_set_40.txt`; the foot fps rise is p7's own static skip).
- Cold boots: see section 6.

## 6. Cold-boot checks (default build with p8_tt_ptr; `cold3d.py`, logs `work/mapptr/cold_ste.log`, `cold_tt.log`)
```
STE TOS 1.62, 1 MB, boot_to_game('M') (campaign, Lobos):  vehicle $6220 = 0xd, view $700a = 0x2
  MWPO 4d 57 50 4f ; site $26ea2 = 41 f9 00 ff 82 01 (ORIGINAL bytes restored by the first flip) ; TT_F $b4f80 = 01
  walking (rel(0,-200) twice): world rate {'units_per_sec': 22.78}
TT TOS 3.06 --mmu true, 4 MB, Raids -> Dhafra (446,177):   vehicle $6220 = 0x1 (Jeep), view $700a = 0x2
  MWPO 4d 57 50 4f ; site $26ea2 = 4e b9 00 0b 4f 00 (blob stays) ; TT_F $b4f80 = 02 ; 3D view renders (85 flips / 250 VBL)
```
The TT 3D run only proves the 3D view is reached with the blob installed (mode 2 takes the plain path); the jeep was standing, so no world rate was measured there.
Not done: floppy-build TT/STE cold boot, Falcon (MW2 does not run on a Hatari Falcon), a second TT run in M mode with the fixed build through the book/boss pages (J-mode run covers them).
