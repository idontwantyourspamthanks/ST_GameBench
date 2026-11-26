## 11. Tightening integration (MSRTightIntegrate): the ta_*/tc_*/tb_car patches as defaults, gates, measured result
Machine: Hatari 2.6.1, headless harness (cycle-exact, `--fast-boot yes`), STE TOS 1.62 1 MB unless named. Scripts: `work/tint/` (`mxlib_int.py` builds every variant with the REAL `tools/msrpatch.py live` from its own default selection, so the gates test exactly what `build` ships; `exp_state_int.py`, `cmpstate_int.py`, `pix_int.py`, `steer_int.py`, `cyc` via `steer_int.py mode=cyc`, `cold_int.py`, `play5_int.py`, `ext_summary.py`, `cmp_cyc.py`, queues `run_q6.sh run_q7.sh run_q8.sh`); raw outputs `work/tint/res/`. `[INFERENCE]` marks what no output here proves. Nothing here touches `originals/`.

### 11.1 The default set, `list`, `verify`, sizes, the RAM map
Defaults flipped (`; default: yes` in the patch headers): `ta_erase ta_init ta_face ta_glyph ta_ymw`, `tc_clr tc_proj tc_dist tc_hit1 tc_hit2 tc_ord`, `tb_car tb_carph`; `hd_init` is now `default: no` (`ta_init` replaces it: declared `conflicts: hd_init` in `ta_init.s`; the tool refuses both together). Not default (documented as options): `ta_rb ta_rb0` (raster timing unproven on real hardware), `ta_nomouse` (behaviour risk, needs the user's approval), `ta_facestat` (visible), `tc_clrx`, `tb_blit tb_blit11 tb_blit13 tb_blit15` (not worth it), `hd_init`; `mx_*` stay default.
```
verify: ALL OK
fl_deprot          yes (floppy) disk A+$e3d0  (floppy disk patch, 4 B)
fl_hook            yes (floppy) disk A+$c350  (floppy disk patch, 10 B)
hd_clouds          yes      $07b3a     6 - / - / ram -
hd_nomap           yes      $0f9dc     4 - / - / ram -
hd_nomap2          yes      $120d6     6 - / - / ram -
hd_stage           yes      $0ef7a     6 $bb000,$bb800,$bc200,$bca40,$bcd00,$bcd20,$bd000 / $bcf00+160 / ram -
mr_edge            yes      $17c4a     6 $b3040 / - / ram -
mt_clock           yes      $0d128     6 $b8000 / $b8f00+4,$b8f08+4 / ram -
mt_pre             yes      $07b0a     6 $b8200 / - / ram -
mx_pre             yes      $07b46     6 $b8300 / $b9e00+2752 / ram -
mx_sync            yes      $07b74     6 $b8100,$b8380,$b8400 / $b8f04+4,$b8f20+224,$b9000+3584 / ram -
rd_draw            yes      $17c42     6 $b5000 / - / ram $cb000-$d7fff (rd_draw window tables (2 x 24 KB), colour table
rd_geom            yes      $100b4     6 $b4000 / - / ram $c0000-$cafff (rd_geom tables (magic, cached $1316, standing-f
rd_init            yes      $078f6     6 $b6000 / - / ram -
ta_erase           yes      $1209c     6 $be000 / $bef00+16 / ram -
ta_face            yes      $0f994     6 $be100 / - / ram -
ta_glyph           yes      $14fd4     6 $be600,$bec00,$be800 / - / ram -
ta_init            yes      $0edea     6 $be200 / - / ram -
ta_ymw             yes      $08e2c     6 $be400 / $bef40+16 / ram -
tb_car             yes      $039ac     4 $bf500 / $bf000+1280 / ram $d8000-$e2bff (generated player-car code cache (44,0
tb_carph           yes      $0ed90     8 $bfc00 / - / ram -
tc_clr             yes      $17c24     6 $b6d40 / $b6ff0+2 / ram -
tc_dist            yes      $0e2e8     6 $b6a00 / - / ram -
tc_hit1            yes      $18bf4     6 $b6a80 / - / ram -
tc_hit2            yes      $18c86     6 $b6b40 / - / ram -
tc_ord             yes      $0e406     8 $b6820 / - / ram -
tc_proj            yes      $0e316     8 $b6c00 / - / ram -
pp_bigram_cache    yes      HAGA+$3228  (file patch, 2 B)
hd_init            no       $0edea     6 $bb700 / - / ram -
ta_init            yes      $0edea     6 $be200 / - / ram -
tb_car             yes      $039ac     4 $bf500 / $bf000+1280 / ram $d8000-$e2bff (generated player-car code cache (44,032 B, written at run time))
tc_clr             yes      $17c24     6 $b6d40 / $b6ff0+2 / ram -
  hd_init            requires hd_stage
  ta_face            requires hd_stage ta_erase ta_init  conflicts ta_facestat
  ta_facestat        requires hd_stage ta_erase ta_init  conflicts ta_face
  ta_init            requires hd_stage ta_erase  conflicts hd_init
  tb_car             requires tb_carph
  tc_clr              conflicts tc_clrx
  $b6d40-$b6dd9    154 B  tc_clr       blob
  $b6ff0-$b6ff1      2 B  tc_clr       data
  $be200-$be21d     30 B  ta_init      blob
  $bf000-$bf4ff   1280 B  tb_car       data
  $bf500-$bf93b   1084 B  tb_car       blob
  $d8000-$e2bff  44032 B  tb_car       ram generated player-car code cache (44,032 B, written at run time)  [not in the image]
  valid layouts for this set: 1MB, 4MB; free run(s) $b2800-$e2bff
built /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/tight_hd with 25 patch(es) + 1 file patch(es); payload 54568 B at $b2700-$bfc27
floppy: disk A 819200 B, disk B 819200 B; payload 54568 B (107 sectors) at t0.0s2x9, t50.0s1x10, t51.0s1x10, t52.0s1x10...
```
Payload 47,360 B (HUD build) -> **54,568 B** (`$B2700-$BFC27`, 107 floppy sectors). RAM map at 1 MB (and 4 MB, TOS 2.06 1 MB ceiling `$E2BFF`): `$B6800-$B6FFF` tc_*, `$BE000-$BEFFF` ta_*, `$BF000-$BFFFF` tb_car/tb_carph, `$C0000-$CAFFF` rd_geom RAM, `$CB000-$D7FFF` rd_draw RAM, **`$D8000-$E2BFF` tb_car code cache = 44,032 B (0xAC00; the task text said 43,008 B, which is a miscount of the same range: `$E2C00 - $D8000 = $AC00`)**. `verify` ALL OK includes the whole-free-run zero check against the six STE 1.62 dumps and the three Mega STE 2.06 1 MB dumps and `; ram:` zero in all of them; `POOLEND` in `tb_car.s` is `$E2C00`. 4 MB layout: same addresses (`pp_bigram_cache` default).

### 11.2 Per-pass game state equal to stock (Hatari, `$7b86` after the flip, keyed by `$100e`; `m` counts DECIMAL: `$1000-$13ff` (1024) `$29c8` (2872) `$4500` (2816) `$dae6` (4) `$1bb0` (12) `$23bc` (16) `$27c8` (38) `$3500` (512) `$dafe` (4) `$6100` (24) `$b8f38` (12) = 7,334 bytes per pass)
A = stock game, T = the real default set with `mt_sync` (tick ON, no extras), X = the real default set (tick ON + extras). Stock vs T, race_start (driving, 220 passes asked) and race_drive (300 asked; the time-out and the restart are inside: keys 0..1706), mask = the documented HUD-private/display-scratch list, **`TC_GEOM` (road geometry output `$4724-$4f77`) NOT applied (`--nogeomask`)**:
```
res/st_start_A8.json (220 passes) vs res/st_start_T8.json (223): common 211 (keys 98..308); 1544942 bytes compared; mask=on (masked differing bytes 13666); differing addresses 0, differing bytes 0
   masked: 417 differing bytes in buffer parity/pointer $1004-$100d
   masked: 538 differing bytes in cloud counters $27de-$27ed (dd50 removed)
   masked: 10546 differing bytes in cloud slots $29c8-$2c67 (dd50 removed)
   masked: 625 differing bytes in dial cache $10d4-$10d7
   masked: 1039 differing bytes in minimap variables $10dc-$10e3
   masked: 140 differing bytes in position cache $10cc-$10cd
   masked: 1 differing bytes in position flag $11cc
   masked: 346 differing bytes in score cache/flag $11c4-$11c5 $11c7
   masked: 11 differing bytes in thermometer cache/flag $10bc-$10bd $11c9
   masked: 3 differing bytes in thermometer flag $11c9

res/st_drive_A8.json (306 passes) vs res/st_drive_T8.json (301): common 298 (keys 0..1706); 2181956 bytes compared; mask=on (masked differing bytes 21452); differing addresses 0, differing bytes 0
   masked: 1 differing bytes in IKBD mouse reply bytes $6106-$6117 (written by the ACIA interrupt, asynchronous to the pass)
   masked: 590 differing bytes in buffer parity/pointer $1004-$100d
   masked: 17624 differing bytes in cloud slots $29c8-$2c67 (dd50 removed)
   masked: 1138 differing bytes in dial cache $10d4-$10d7
   masked: 298 differing bytes in dial flag $11cd
   masked: 203 differing bytes in minimap variables $10dc-$10e3
   masked: 507 differing bytes in position cache $10cc-$10cd
   masked: 7 differing bytes in position flag $11cc
   masked: 542 differing bytes in score cache/flag $11c4-$11c5 $11c7
   masked: 53 differing bytes in score flag $11c7
   masked: 488 differing bytes in thermometer cache/flag $10bc-$10bd $11c9
   masked: 1 differing bytes in thermometer flag $11c9
```
Final mask set (all in `cmpstate_int.py`, each a named range with a per-category count of masked differing bytes printed): IKBD mouse reply bytes `$6106-$6117` (written by the ACIA interrupt, asynchronous to the pass: ONE byte differed once in race_drive pass key 0 without the mask: `$0610e 00 -> 03`; this range is new in this gate and was not in the earlier HUD gate), buffer parity/pointer `$1004-$100d`, raster scratch `$12f0-$1307`, raster bands `$12fe-$1301`, object order list scratch `$36e8-$36ff`, HUD kernel scratch `$100c-$100d`, the HUD caches/flags the removed old HUD items used to update (`$10bc-$10bd $11c9`, `$10c2-$10c9`, `$10cc-$10cd $11cc`, `$10d4-$10d7 $11cd`, `$10dc-$10e3`, `$11c4-$11c5 $11c7`, `$11ca-$11cb`, `$11da-$11dc`) and the cloud slots/counters `$29c8-$2c67`, `$27de-$27ed` (`dd50` removed with the clouds). **`TC_GEOM` is not needed with `tc_clr`** (the 'start'/'drive' blocks above); it is still needed in the extras gates, because an extra frame re-runs the road geometry at an extrapolated pose and the region holds the last extra's output at `$7b86` (below).

Extras at 16 and 32 MHz, same keys (`X` vs stock, mask + `TC_GEOM` as documented for the extras gates; the unmasked-by-TC_GEOM counts are printed to show that the ONLY other difference is that region):
```
-- start_A8 vs start_X16: with TC_GEOM:
res/st_start_A8.json (220 passes) vs res/st_start_X16.json (222): common 196 (keys 113..308); 1435112 bytes compared; mask=on (masked differing bytes 66258); differing addresses 0, differing bytes 0
   masked: 79 differing bytes in IKBD mouse reply bytes $6106-$6117 (written by the ACIA interrupt, asynchronous to the pass)
   masked: 52024 differing bytes in TC_GEOM (inherited display-scratch mask: road geometry output $4724-$4f77; NOT needed with tc_clr/rd_*: pass --nogeomask; needed only with tc_clrx = stale records below the stream start, see tighten_c.md section 5)
-- without TC_GEOM:
res/st_start_A8.json (220 passes) vs res/st_start_X16.json (222): common 196 (keys 113..308); 1435112 bytes compared; mask=on (masked differing bytes 14234); differing addresses 1362, differing bytes 52024
   $04724: 3 passes, e.g. pass 154: 00 -> ff
-- start_A8 vs start_X32: with TC_GEOM:
res/st_start_A8.json (220 passes) vs res/st_start_X32.json (223): common 197 (keys 112..308); 1442434 bytes compared; mask=on (masked differing bytes 75701); differing addresses 0, differing bytes 0
   masked: 61187 differing bytes in TC_GEOM (inherited display-scratch mask: road geometry output $4724-$4f77; NOT needed with tc_clr/rd_*: pass --nogeomask; needed only with tc_clrx = stale records below the stream start, see tighten_c.md section 5)
   masked: 787 differing bytes in buffer parity/pointer $1004-$100d
-- without TC_GEOM:
res/st_start_A8.json (220 passes) vs res/st_start_X32.json (223): common 197 (keys 112..308); 1442434 bytes compared; mask=on (masked differing bytes 14514); differing addresses 1385, differing bytes 61187
   $04724: 4 passes, e.g. pass 121: 00 -> ff
-- drive_A8 vs drive_X16: with TC_GEOM:
res/st_drive_A8.json (306 passes) vs res/st_drive_X16.json (305): common 285 (keys 0..1706); 2086770 bytes compared; mask=on (masked differing bytes 20662); differing addresses 0, differing bytes 0
   masked: 79 differing bytes in TC_GEOM (inherited display-scratch mask: road geometry output $4724-$4f77; NOT needed with tc_clr/rd_*: pass --nogeomask; needed only with tc_clrx = stale records below the stream start, see tighten_c.md section 5)
   masked: 564 differing bytes in buffer parity/pointer $1004-$100d
-- without TC_GEOM:
res/st_drive_A8.json (306 passes) vs res/st_drive_X16.json (305): common 285 (keys 0..1706); 2086770 bytes compared; mask=on (masked differing bytes 20583); differing addresses 79, differing bytes 79
   $04725: 1 passes, e.g. pass 1666: 21 -> 22
```
Extras counts in those windows (`$b8f38` over the recorded passes, from `res/state_log.txt`): X ste1m_race_start.sav 16 hits 222 extra frames in window 334;X ste1m_race_start.sav 32 hits 223 extra frames in window 888;X ste1m_race_drive.sav 16 hits 305 extra frames in window 0; The race_drive scene itself draws **0** extras at 16 MHz in those 300 passes (time-out and the standing start dominate: skip reasons, 11.6), so the steered gates below are the strong extras gate.

Steered state gates (input = a pure function of the pass key `$100e`, identical in every run: from key 140 (race_start) / 470 (race_up) 15 passes each of up, up+left, up, up+right; the player car changes bitmap constantly, so `tb_car` generates and uses code), mask as above, `TC_GEOM` only for X:
```
-- zig_start_A8 vs zig_start_T8: NOT RUN
-- zig_up_A8 vs zig_up_T8: NOT RUN
-- zig_start_A8 vs zig_start_X16: NOT RUN
-- zig_start_A8 vs zig_start_X32: NOT RUN
-- zig_up_A8 vs zig_up_X16: NOT RUN

```

### 11.3 Pixels
**(a) Full-buffer A/B** (`pix_int.py`: R = the HUD-build default `mr_edge rd_* hd_stage hd_init hd_clouds hd_nomap hd_nomap2`, C = the default set minus the pacer, both live-applied at the same instant, both 32,000-byte buffers, 7 render controls on the SAME capture; flips after the apply as listed; `$11ab` = ticker state). Summary over the captures, then the raw lines of the message-active captures:
`16` captures (race_start flips 10 55 90 100 150, race_grid 10 120 150, race_up 10 40 90 150, race_drive 10 40 90 150): **C identical to R in 16/16** (both buffers). Ticker message active (`$11ab != 0`): 7 captures. Negative controls (C + one poke), captures in which each control DIFFERS: car_nophase 1, erase_short 7, face_same 7, face_wrong 7, glyph_bad 6.
```
== race_start flip 55: $100e=170 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   3032  (face box     0, text box  3032)  -> DIFFER
   car_nophase  vs R: differing pixels total     20  (face box     0, text box     0)  -> DIFFER
== race_start flip 90: $100e=205 $11ab=0 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_wrong   vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   erase_short  vs R: differing pixels total    642  (face box     0, text box   642)  -> DIFFER
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_start flip 150: $100e=265 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total    484  (face box     0, text box   484)  -> DIFFER
   glyph_bad    vs R: differing pixels total   1322  (face box     0, text box  1322)  -> DIFFER
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_grid flip 10: $100e=3647 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total    581  (face box     0, text box   581)  -> DIFFER
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_up flip 90: $100e=512 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   1184  (face box     0, text box  1184)  -> DIFFER
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_up flip 150: $100e=572 $11ab=1 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total    604  (face box     0, text box   604)  -> DIFFER
   glyph_bad    vs R: differing pixels total    119  (face box     0, text box   119)  -> DIFFER
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_drive flip 10: $100e=1696 $11ab=2 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
== race_drive flip 90: $100e=69 $11ab=2 (ticker state: 0 none, 1 typing, >=2 held) $11b0=0 (erase pending) $10f8=0
   C            vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   face_same    vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   face_wrong   vs R: differing pixels total   2840  (face box  2840, text box     0)  -> DIFFER
   erase_short  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
   glyph_bad    vs R: differing pixels total   2826  (face box    64, text box  2762)  -> DIFFER
   car_nophase  vs R: differing pixels total      0  (face box     0, text box     0)  -> IDENTICAL
```
The controls: `face_same` (ta_face always 'same': `be112=600e`), `face_wrong` (draws sprite+1: `be11a=b0e4`), `erase_short` (`be042=0040`), `glyph_bad` (`be660=0002`), `car_nophase` (the `tb_carph` hook removed: `ed90=302a0006d06a0008`, i.e. the wheel-animation state is not tracked: the bank alternates and a stale compiled frame is drawn). `car_nophase` fires in 1 capture(s) only (the XOR toggles every other pass; the earlier tighten-B gate also saw it in a single capture); the three face/erase/glyph controls fire exactly where a message is on screen.

**(b) Masked gate against the real stock/HUD reference** (`tools/msrmask.py`, explicit rectangles, pixels compared AND excluded printed): cand = the default set, ref = `test_hdref hd_clouds mr_edge rd_*`, stock side = `mr_edge rd_*`, 4 scenes x flips 10 40 90 x both buffers = 24 frames (message active on several: `speech=Y` rows):
```
race_start  flip  40 b70000 (drawn=no ) speech=Y differing pixels A:0, B:0, C:0, D:0
race_start  flip  40 b78000 (drawn=yes) speech=Y differing pixels A:0, B:0, C:0, D:0
race_grid   flip  10 b70000 (drawn=yes) speech=Y differing pixels A:0, B:0, C:0, D:0
race_grid   flip  10 b78000 (drawn=no ) speech=Y differing pixels A:0, B:0, C:0, D:0
race_grid   flip  40 b70000 (drawn=yes) speech=Y differing pixels A:0, B:0, C:0, D:0
race_grid   flip  40 b78000 (drawn=no ) speech=Y differing pixels A:0, B:0, C:0, D:0
candidate: hd_stage ta_init ta_erase ta_face ta_glyph ta_ymw hd_clouds hd_nomap hd_nomap2 mr_edge rd_geom rd_draw rd_init tb_car tb_carph tc_clr tc_dist tc_hit1 tc_hit2 tc_ord
  A rows65-199 vs ref        frames   24  pixels compared    1036800  excluded         0  differing      0  -> IDENTICAL
  B sky rows16-64            frames   24  pixels compared     244608  excluded    131712  differing      0  -> IDENTICAL
  C strip rows0-15           frames   24  pixels compared     122880  excluded         0  differing      0  -> IDENTICAL
  D rows85-199 vs stock      frames   24  pixels compared     798336  excluded     84864  differing      0  -> IDENTICAL
RESULT: IDENTICAL
```
Negative controls (`--neg nopaint`: the first strip/sky paint is skipped, `--neg nowipe`: the sky wipe is skipped; each MUST differ):
```
-- res/mask_neg_nopaint.txt
candidate: hd_stage ta_init ta_erase ta_face ta_glyph ta_ymw hd_clouds hd_nomap hd_nomap2 mr_edge rd_geom rd_draw rd_init tb_car tb_carph tc_clr tc_dist tc_hit1 tc_hit2 tc_ord
  A rows65-199 vs ref        frames    2  pixels compared      86400  excluded         0  differing      0  -> IDENTICAL
  B sky rows16-64            frames    2  pixels compared      31360  excluded         0  differing   5902  -> DIFFER
  C strip rows0-15           frames    2  pixels compared      10240  excluded         0  differing   6668  -> DIFFER
  D rows85-199 vs stock      frames    2  pixels compared      66528  excluded      7072  differing      0  -> IDENTICAL
RESULT: DIFFER
-- res/mask_neg_nowipe.txt
candidate: hd_stage ta_init ta_erase ta_face ta_glyph ta_ymw hd_clouds hd_nomap hd_nomap2 mr_edge rd_geom rd_draw rd_init tb_car tb_carph tc_clr tc_dist tc_hit1 tc_hit2 tc_ord
  A rows65-199 vs ref        frames    2  pixels compared      86400  excluded         0  differing      0  -> IDENTICAL
  B sky rows16-64            frames    2  pixels compared      31360  excluded         0  differing   5032  -> DIFFER
  C strip rows0-15           frames    2  pixels compared      10240  excluded         0  differing      0  -> IDENTICAL
  D rows85-199 vs stock      frames    2  pixels compared      66528  excluded      7072  differing      0  -> IDENTICAL
RESULT: DIFFER
```

### 11.5 MEASURE: cycles per pass at 8 MHz, tick OFF (loop top `$796a` -> flip `$d1ca`, interrupts included; 1 VBL = 160,256 cycles; same Hatari session and recipe as `work/hud/build/res_cyc3.txt`)
Rows: N = the HUD-build default (`mr_edge rd_* hd_stage hd_init hd_clouds hd_nomap hd_nomap2`, re-measured now: the baseline), F = the new default minus the pacer (the cycle recipe needs the tick off). `speech` = `$11ab != 0` at the end of the pass (as in the earlier tables); both rows are matched on the same pass key `$100e` (same snapshot, same instant), so `delta` compares the same passes. race_start = driving (up held, no steering), race_grid = standing.
```
scene       passes         n   N cycles     VBL   F cycles     VBL      delta      VBL
race_start  no speech     83     491172   3.065     444497   2.774     -46675   -0.291
race_start  speech       146     517169   3.227     463676   2.893     -53493   -0.334
race_start  all          229     507747   3.168     456725   2.850     -51022   -0.318
race_grid   no speech     74     414960   2.589     362576   2.262     -52384   -0.327
race_grid   speech       158     417803   2.607     362531   2.262     -55272   -0.345
race_grid   all          232     416896   2.601     362546   2.262     -54350   -0.339
```
Unmatched window means (all passes of each 230-pass run, `res/cyc_log.txt`): N race_start none 8MHz no speech  n 83 mean 491172 = 3.065 VBL min 444540 max 552268 | N race_start none 8MHz speech     n 150 mean 516378 = 3.222 VBL min 444244 max 610324 |    all passes n 233 mean 507399 = 3.166 VBL; last 100 mean 517324 |    VBL per pass (end-to-end, incl. wait):  3.841 | F race_start none 8MHz no speech  n 88 mean 448449 = 2.798 VBL min 398460 max 529840 | F race_start none 8MHz speech     n 157 mean 467325 = 2.916 VBL min 392744 max 587452 |    all passes n 245 mean 460545 = 2.874 VBL; last 100 mean 475275 |    VBL per pass (end-to-end, incl. wait):  3.258 | N race_grid none 8MHz no speech  n 74 mean 414960 = 2.589 VBL min 394556 max 461460 | N race_grid none 8MHz speech     n 158 mean 417803 = 2.607 VBL min 400684 max 461344 |    all passes n 232 mean 416896 = 2.601 VBL; last 100 mean 415244 |    VBL per pass (end-to-end, incl. wait):  3.0 | F race_grid none 8MHz no speech  n 74 mean 362576 = 2.262 VBL min 342376 max 395512 | F race_grid none 8MHz speech     n 159 mean 362493 = 2.262 VBL min 342024 max 412640 |    all passes n 233 mean 362520 = 2.262 VBL; last 100 mean 361926 |    VBL per pass (end-to-end, incl. wait):  3.0 |

Per-agent savings overlap (shared stages): the sum of the three agents' stand-alone claims (A 7-20 k, B 39-42 k, C 7.3-9.2 k) is 53-71 k; the integrated, matched result is **-46.7 k / -53.5 k driving (no speech / speech) and -52.4 k / -55.3 k standing**.

**Steering and the pool (key-matched, 8 MHz, tick OFF, race_start, input = zig = up / up+left / up / up+right, 15 passes each from key 140; 520 passes; `steer_int.py mode=cyc zigk=140`).** N = HUD build, nocar = the default set minus `tb_car tb_carph`, pK = the default set with the `tb_car` pool limit poked (`cmpi.l #POOLEND,d0` immediate at `$BF772`) to `$D8000 + K KB`; compiled-draw fraction = executions of the generated-code hit path `$BF5E6` / executions of the stub `$BF500` (the stub is entered by every 4-column nibble-7 sprite, the car, its second layer and other objects; 'hits' also counts the draw right after a generation), counted by trace breakpoints in the same run:
```
variant                 mean cyc     VBL     vs nocar      vs N  compiled-draw fraction (hits / stub entries)
N (HUD build)             501791   3.131           +0        +0  -   (pool used up to $0, 0 entries)
default w/o tb_car        489249   3.053           +0    -13798  -   (pool used up to $0, 0 entries)
default, pool 8 KB        483975   3.020        -5274    -18815  328 / 1367 = 24.0 %   (pool used up to $d95, 29 entries)
default, pool 16 KB       477695   2.981       -11673    -25477  557 / 1316 = 42.3 %   (pool used up to $db8, 29 entries)
default, pool 24 KB       469829   2.932       -19420    -32953  733 / 1330 = 55.1 %   (pool used up to $dd7, 29 entries)
default, pool 32 KB       462171   2.884       -27078    -40522  967 / 1348 = 71.7 %   (pool used up to $df5, 29 entries)
default, pool 44 KB       459585   2.868       -29664    -43006  1057 / 1352 = 78.2 %   (pool used up to $e1d, 29 entries)
```
(`vs nocar` / `vs N`: mean over the matched passes of the 520-pass window, i.e. including the cold generation of every variant in the first ~100 passes; steady state from key +250 is 1-2 k better, see `res/pool_log.txt`.) The entry table (39 entries) never binds at 44 KB: 29 entries are used; an experimental 120-entry table (Unicorn census, `work/tightB/census.py`, not kept) changed the compiled fraction by -1..-2 points only, so the table was not enlarged. **Raising the pool from 24 KB to 44,032 B lifts the compiled-draw fraction from 55.1 % to 78.2 % under constant steering and saves a further 10.3 k cycles per pass (-0.064 VBL); against the 24 KB version's 47-68 % Unicorn estimate the Hatari measurement is 55 % at 24 KB** (the estimate was a model, this is the live count).

### 11.6 MEASURE: extra frames per tick (mx counters), tick ON (T=30), extras ON, STE, driving with steering
`steer_int.py mode=pass`: a persistent trace breakpoint at the race-pass top `$7a88` dumps, per pass, `NEXTRA $b8f32` (the extras drawn in the PREVIOUS pass's tick), the pass key, the counters `$b8f38/3c/40` (frames / ticks with >= 1 extra / ticks that entered the group code), the skip-reason words `$b8f54`, `$11ab`, `$1226`, `$1021`, the VBL; input = zig steering as a pure function of the key (up / up+left / up / up+right, 15 passes each, also after the restart). Scene race_drive: ~65 passes of the time-out sequence (`$1226 = 5`), the race restart (pass 1707 -> 0), 94 standing passes of the start sequence (skip reason 2 = standing), then racing. 1,300 passes = 6,500 VBL = 130 s emulated per run. Per-run raw: `res/ext_*.json`, summary `ext_summary.py`.
**Frames per tick = 1 main + extras. Racing phase only (after the restart, pass >= 130; the first lap of the new race):**
```
run                         ticks VBL/tick  pass/s  extras per tick histogram {extras: ticks}     mean ex. 2-frame disp fps
HUD build (NX) 8 MHz         1114    5.001   9.998  {0: 943, 1: 171}                                 0.154   15.4%    11.53
NEW default 8 MHz            1115    4.999  10.002  {0: 793, 1: 322}                                 0.289   28.9%    12.89
NEW default 16 MHz           1121    5.000  10.000  {0: 8, 1: 386, 2: 618, 3: 87, 4: 22}             1.758   34.4%    27.58
NEW default 32 MHz           1112    5.000  10.000  {0: 1, 1: 3, 2: 20, 3: 8, 4: 1080}               3.945    0.3%    49.45
```
`2-frame` = share of ticks with exactly one extra (main + 1 = 2 pictures); `disp fps` = (passes + extras) per second of the racing window (the game itself runs 10 logic steps per second in every row). With the tick ON the passes stay at 10.00/s in all rows, so the game speed is not affected by the extras.
Full-window view incl. the time-out sequence, the restart and the 94 standing passes (`ext_summary.py`; this is what an observer sees over 2 minutes):
```
== ext_X_8.json: set X 8 MHz, 1314 pass records over 6840 VBL (137 s @50Hz): 9.598 passes/s, 5.21 VBL/pass
   counters over the window: extra frames 349, ticks with >=1 extra (groups) 349, ticks that entered the group code 614; displayed fps (passes+extras)/time = 12.15
   extras per tick histogram (pass records): {0: 963, 1: 349}  -> frames per tick (main+extras): {1: '73.4%', 2: '26.6%'}
   mean extras/tick 0.266; ticks with >= 1 extra 26.6 %; with exactly 1 extra (2 frames) 26.6 %
   speech passes: n 1048 mean extras 0.247  hist {0: 789, 1: 259}
   no-speech passes: n 264 mean extras 0.341  hist {0: 174, 1: 90}
   restart at record 67 (pass 1707 -> 0, VBL 15378): extras of the passes around it [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; $1226 around: [5, 5, 5, 5, 5, 0, 0]
   passes with $1226 != 0 (time-out sequence): 58; non-race mode ($1021 != 2) records 0
   skip reasons RSN (0 no slot copy, 1 off, 2 standing, 3 too fast, 4 $1024, 5 $1021) first/last: [11, 0, 0, 0, 0, 0] [615, 0, 94, 0, 0, 0]
== ext_X_16.json: set X 16 MHz, 1320 pass records over 6739 VBL (135 s @50Hz): 9.786 passes/s, 5.11 VBL/pass
   counters over the window: extra frames 2121, ticks with >=1 extra (groups) 1213, ticks that entered the group code 1220; displayed fps (passes+extras)/time = 25.52
   extras per tick histogram (pass records): {0: 105, 1: 436, 2: 668, 3: 87, 4: 22}  -> frames per tick (main+extras): {1: '8.0%', 2: '33.1%', 3: '50.7%', 4: '6.6%', 5: '1.7%'}
   mean extras/tick 1.609; ticks with >= 1 extra 92.0 %; with exactly 1 extra (2 frames) 33.1 %
   speech passes: n 1052 mean extras 1.589  hist {0: 83, 1: 364, 2: 527, 3: 58, 4: 20}
   no-speech passes: n 266 mean extras 1.688  hist {0: 22, 1: 72, 2: 141, 3: 29, 4: 2}
   restart at record 67 (pass 1707 -> 0, VBL 15378): extras of the passes around it [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; $1226 around: [5, 5, 5, 5, 5, 0, 0]
   passes with $1226 != 0 (time-out sequence): 58; non-race mode ($1021 != 2) records 0
   skip reasons RSN (0 no slot copy, 1 off, 2 standing, 3 too fast, 4 $1024, 5 $1021) first/last: [1, 0, 0, 0, 0, 0] [5, 0, 94, 0, 0, 0]
== ext_X_32.json: set X 32 MHz, 1312 pass records over 6636 VBL (133 s @50Hz): 9.878 passes/s, 5.06 VBL/pass
   counters over the window: extra frames 4763, ticks with >=1 extra (groups) 1209, ticks that entered the group code 1216; displayed fps (passes+extras)/time = 45.77
   extras per tick histogram (pass records): {0: 101, 1: 6, 2: 24, 3: 8, 4: 1170, 5: 1}  -> frames per tick (main+extras): {1: '7.7%', 2: '0.5%', 3: '1.8%', 4: '0.6%', 5: '89.3%', 6: '0.1%'}
   mean extras/tick 3.636; ticks with >= 1 extra 92.3 %; with exactly 1 extra (2 frames) 0.5 %
   speech passes: n 1046 mean extras 3.630  hist {0: 79, 1: 6, 2: 23, 3: 8, 4: 929, 5: 1}
   no-speech passes: n 264 mean extras 3.659  hist {0: 22, 2: 1, 4: 241}
   restart at record 68 (pass 1707 -> 0, VBL 15377): extras of the passes around it [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; $1226 around: [5, 5, 5, 5, 5, 0, 0]
   passes with $1226 != 0 (time-out sequence): 58; non-race mode ($1021 != 2) records 0
   skip reasons RSN (0 no slot copy, 1 off, 2 standing, 3 too fast, 4 $1024, 5 $1021) first/last: [2, 0, 0, 0, 0, 0] [2, 0, 94, 0, 0, 0]
== ext_NX_8.json: set NX 8 MHz, 1313 pass records over 6837 VBL (137 s @50Hz): 9.595 passes/s, 5.21 VBL/pass
   counters over the window: extra frames 183, ticks with >=1 extra (groups) 183, ticks that entered the group code 409; displayed fps (passes+extras)/time = 10.93
   extras per tick histogram (pass records): {0: 1128, 1: 183}  -> frames per tick (main+extras): {1: '86.0%', 2: '14.0%'}
   mean extras/tick 0.140; ticks with >= 1 extra 14.0 %; with exactly 1 extra (2 frames) 14.0 %
   speech passes: n 1047 mean extras 0.127  hist {0: 914, 1: 133}
   no-speech passes: n 264 mean extras 0.189  hist {0: 214, 1: 50}
   restart at record 67 (pass 1707 -> 0, VBL 15378): extras of the passes around it [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]; $1226 around: [5, 5, 5, 5, 5, 0, 0]
   passes with $1226 != 0 (time-out sequence): 58; non-race mode ($1021 != 2) records 0
   skip reasons RSN (0 no slot copy, 1 off, 2 standing, 3 too fast, 4 $1024, 5 $1021) first/last: [17, 0, 0, 0, 0, 0] [825, 0, 94, 0, 0, 0]
```
- X_8: ticker active (`$11ab != 0`, 926 ticks) mean 0.267 extras, ticker idle (189 ticks) 0.397.
- X_16: ticker active (`$11ab != 0`, 930 ticks) mean 1.724 extras, ticker idle (191 ticks) 1.927.
- X_32: ticker active (`$11ab != 0`, 923 ticks) mean 3.940 extras, ticker idle (189 ticks) 3.968.
Other scenes at 8 MHz (steered, 700 passes, `res/ext8_*.json`; the amount of spare time depends on the scene: objects, speech):
```

```
Time-out restart: no extras during the time-out sequence (skip reason 5 / `$1024 != 0`) and none in the standing start sequence (skip reason 2 = standing, 94 passes), both unchanged by the tightening; the extras resume when the car moves. In the full-window summaries above the lines `restart at record ...` show the extras of the 20 passes around the restart: all 0.

**Reading for the STE at 8 MHz [measured above, the interpretation is an INFERENCE]:** after the tightening the pass costs ~2.8-2.9 VBL of a 5-VBL tick, but an extra frame needs the whole road/object path again (about the same cost minus the logic stage and the HUD work), so only part of the ticks have room for one: the new default draws one extra picture in about 29 % of the racing ticks (the HUD-build default: 15 %), ~12.9 displayed fps instead of 11.5; it can never draw two. The deadline rule (`wantnext`) only starts an extra when it is predicted to flip before the next tick; 79 of the 349 extra-drawing ticks in the 137-s window still ended one or two VBL late (the next tick is then shortened: passes per second stay 10.00), see the VBL histogram: `VBL between pass starts: 3 x3, 4 x77, 5 x1153, 6 x76, 7 x3` (`res/ext_X_8.json`).

### 11.7 Cold boots, floppy, 5-minute plays, native 60 Hz
HD: `work/tint/cold_int.py` (cold boot of `build/tight_hd` = the default HD build, SPACE navigation into the first race, marker `$b2700`, patched sites, HUD strip pixels == shadow render in both buffers, road tables `RDG1`/`WPTR`, `tb_car` probe byte `INIT $bf000` (1 = generated path on, 2 = stock kernel), `tc_clr` flag `$b6ff0`, then rate windows at the native clock and at 16 MHz (68000 machines boot at 8 MHz and the clock is raised after the boot, as `play.sh --cpu 16` does), `up` held, then 124 s of play; `$ff820a` read for the refresh rate). Raw `res/cold_hd.txt`:
```
=== HD cold ste 1024 1.62 0,16
ste 1024 KB TOS 1.62 build build/tight_hd: boot_to_race True vbl 5811
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_ste_1024_a pass>=86: $100e=86 $11ab=2 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_ste_1024_b pass>=397: $100e=397 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1750 (raw), shadow==model(RAM) False | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1793 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 1 (1 generated path on, 2 off) NENT $bf008 = 8 POOLP $bf004 = 000db052  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT ste 1024 TOS 1.62 clock native: window 526 VBL, passes 105 (9.981/s @50Hz), extra frames 0, displayed fps 9.981, $ff820a=fe00, pos 3677->4474
RESULT ste 1024 TOS 1.62 clock 16: window 525 VBL, passes 105 (10.000/s @50Hz), extra frames 174, displayed fps 26.571, $ff820a=fe00, pos 4967->5690
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 2, hatari alive: True
TB_CAR at end: INIT 1 NENT 2 POOLP 000d904a
=== HD cold ste 4096 1.62 0,16
ste 4096 KB TOS 1.62 build build/tight_hd: boot_to_race True vbl 5810
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_ste_4096_a pass>=88: $100e=88 $11ab=2 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_ste_4096_b pass>=399: $100e=399 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1868 (raw), shadow==model(RAM) False | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1901 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 1 (1 generated path on, 2 off) NENT $bf008 = 8 POOLP $bf004 = 000db052  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT ste 4096 TOS 1.62 clock native: window 526 VBL, passes 105 (9.981/s @50Hz), extra frames 0, displayed fps 9.981, $ff820a=fe00, pos 3677->4474
RESULT ste 4096 TOS 1.62 clock 16: window 525 VBL, passes 105 (10.000/s @50Hz), extra frames 173, displayed fps 26.476, $ff820a=fe00, pos 4974->5697
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 2, hatari alive: True
TB_CAR at end: INIT 1 NENT 2 POOLP 000d9046
=== HD cold megaste 1024 2.06 0,16
megaste 1024 KB TOS 2.06 build build/tight_hd: boot_to_race True vbl 6047
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_megaste_1024_a pass>=110: $100e=110 $11ab=0 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_megaste_1024_b pass>=421: $100e=421 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1626 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1675 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 2 (1 generated path on, 2 off) NENT $bf008 = 0 POOLP $bf004 = 00000000  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT megaste 1024 TOS 2.06 clock native: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 116, displayed fps 21.048, $ff820a=fc00, pos 3677->4474
RESULT megaste 1024 TOS 2.06 clock 16: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 112, displayed fps 20.667, $ff820a=fc00, pos 4967->5690
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 0, hatari alive: True
TB_CAR at end: INIT 2 NENT 0 POOLP 00000000
=== HD cold megaste 2048 2.06 0,16
megaste 2048 KB TOS 2.06 build build/tight_hd: boot_to_race True vbl 6046
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_megaste_2048_a pass>=111: $100e=111 $11ab=0 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_megaste_2048_b pass>=422: $100e=422 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1841 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1817 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 2 (1 generated path on, 2 off) NENT $bf008 = 0 POOLP $bf004 = 00000000  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT megaste 2048 TOS 2.06 clock native: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 115, displayed fps 20.952, $ff820a=fc00, pos 3670->4467
RESULT megaste 2048 TOS 2.06 clock 16: window 630 VBL, passes 106 (10.095/s @60Hz), extra frames 112, displayed fps 20.762, $ff820a=fc00, pos 4960->5690
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 0, hatari alive: True
TB_CAR at end: INIT 2 NENT 0 POOLP 00000000
=== HD cold megaste 4096 2.06 0,16
megaste 4096 KB TOS 2.06 build build/tight_hd: boot_to_race True vbl 6047
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_megaste_4096_a pass>=111: $100e=111 $11ab=0 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_megaste_4096_b pass>=422: $100e=422 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1675 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1699 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 2 (1 generated path on, 2 off) NENT $bf008 = 0 POOLP $bf004 = 00000000  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT megaste 4096 TOS 2.06 clock native: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 115, displayed fps 20.952, $ff820a=fc00, pos 3677->4474
RESULT megaste 4096 TOS 2.06 clock 16: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 111, displayed fps 20.571, $ff820a=fc00, pos 4967->5697
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 0, hatari alive: True
TB_CAR at end: INIT 2 NENT 0 POOLP 00000000
=== HD cold st 1024 1.04 0,16
st 1024 KB TOS 1.04 build build/tight_hd: boot_to_race True vbl 5808
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_st_1024_a pass>=86: $100e=86 $11ab=2 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 2743 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_st_1024_b pass>=397: $100e=397 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1750 (raw), shadow==model(RAM) False | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1793 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 1 (1 generated path on, 2 off) NENT $bf008 = 8 POOLP $bf004 = 000db052  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT st 1024 TOS 1.04 clock native: window 526 VBL, passes 105 (9.981/s @50Hz), extra frames 0, displayed fps 9.981, $ff820a=fe00, pos 3677->4474
RESULT st 1024 TOS 1.04 clock 16: window 526 VBL, passes 105 (9.981/s @50Hz), extra frames 174, displayed fps 26.521, $ff820a=fe00, pos 4967->5690
PLAY DONE: 124 s at 16 MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 3, hatari alive: True
TB_CAR at end: INIT 1 NENT 2 POOLP 000d904a
=== HD cold tt 4096 3.06 0
tt 4096 KB TOS 3.06 build build/tight_hd: boot_to_race True vbl 5879
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_tt_4096_a pass>=129: $100e=129 $11ab=0 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_tt_4096_b pass>=439: $100e=439 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1974 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1974 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 2 (1 generated path on, 2 off) NENT $bf008 = 0 POOLP $bf004 = 00000000  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT tt 4096 TOS 3.06 clock native: window 630 VBL, passes 105 (10.000/s @60Hz), extra frames 526, displayed fps 60.095, $ff820a=0100, pos 3677->4474
PLAY DONE: 124 s at native MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 0, hatari alive: True
TB_CAR at end: INIT 2 NENT 0 POOLP 00000000
=== HD cold falcon 4096 4.04 0
falcon 4096 KB TOS 4.04 build build/tight_hd: boot_to_race True vbl 5806
marker $b2700: b'MSPO' stage site $ef7a: 4ef9000bb004 $edea: 4eb9000be200 palette A col 14 $3cf0: 0000
STRIP CHECK cold_tint_falcon_4096_a pass>=116: $100e=116 $11ab=0 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 0 (message/face excluded? no: raw), shadow==model(RAM) True
STRIP CHECK cold_tint_falcon_4096_b pass>=426: $100e=426 $11ab=1 $70000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1964 (raw), shadow==model(RAM) True | $78000: strip pixels != shadow render 0, non-sky pixels rows 16-64 1964 (message/face excluded? no: raw), shadow==model(RAM) True
TB_CAR INIT $bf000 = 2 (1 generated path on, 2 off) NENT $bf008 = 0 POOLP $bf004 = 00000000  TC_CLR flag $b6ff0 = 0100  sites: $17c24 4ef9000b6d40 $e406 4ef9000b68204e71 $39ac 000bf500
RESULT falcon 4096 TOS 4.04 clock native: window 526 VBL, passes 105 (9.981/s @50Hz), extra frames 181, displayed fps 27.186, $ff820a=0200, pos 3677->4467
PLAY DONE: 124 s at native MHz, $1021=2, magic b'RDG1', Bus/Address Error lines in the log: 0, hatari alive: True
TB_CAR at end: INIT 2 NENT 0 POOLP 00000000
```
All eight machines boot to the race with marker `MSPO`, the new sites patched (`$17c24 -> $b6d40`, `$e406 -> $b6820`, `$39ac -> $bf500`), road tables intact, `$1021 = 2` after 124 s of play, and 0 Bus/Address Error lines on Mega STE/TT/Falcon (2-3 on ST/STE are PP's `$ff8e21`/`$ff8924` probes, as in the stock game, `integration.md` 10.6). **`tb_car` probe: `INIT = 1` (generated path ON) on STE 1.62 1 MB/4 MB and ST 1.04; `INIT = 2` (stock kernel) on Mega STE 2.06 (1/2/4 MB), TT 3.06 and Falcon 4.04, exactly the declared rule.** STRIP CHECK lines (the HUD pixel/shadow check) are identical to the HUD-build default's (`mste/m_hd.txt`: e.g. `non-sky pixels rows 16-64 2743` / `1750`/`1793`, the 'shadow==model False' flag at pass 397 appears in the HUD-build run as well, a timing artefact of the check) = the render with all patches equals the earlier default's. At the native 8 MHz clock the STE windows show 0 extras (the first lap right after the start light: ticker message active, objects, start sequence: no room), the 16 MHz windows 173-174 extras in 105 passes (26.5 fps); the 60 Hz boots (Mega STE 2.06 `$ff820a = fc`, TT 3.06 `$ff820a = 01`) run 10.000 passes per second at 60 Hz; the Mega STE draws 112-116 extras in 105 passes, the TT 526 (60 fps displayed).

Floppy (`tools/msrfloppy.py gate build/tight_floppy/disk_a.st --disk-b build/tight_floppy/disk_b.st`, disk A alone, story screens, disk-2 swap, race, clock raised to 16 MHz, `up` held; raw `res/cold_floppy.txt`):
```
=== FLOPPY gate megaste 1024 2.06 16
disk-2 prompt True t 46 vbl 2901 story screen seen True screens saved 7 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_tint_megaste_1024
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4925 $1021/$100e (2, 215)
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
road magic $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $d7040: 000D7040: 00 01 02 ba                                      ...´
extra-frame counters at 16 MHz, up held, $100e 692: frames/groups/ticks $b8f38: 000B8F38: 00 00 02 d6 00 00 01 99 00 00 01 9d              ...ש...Ö...¥  skip reasons $b8f54: 000B8F64: 00 00                                         
=== FLOPPY gate megaste 4096 2.06 16
disk-2 prompt True t 46 vbl 2900 story screen seen True screens saved 7 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_tint_megaste_4096
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4923 $1021/$100e (2, 216)
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
road magic $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $d7040: 000D7040: 00 01 02 ba                                      ...´
extra-frame counters at 16 MHz, up held, $100e 693: frames/groups/ticks $b8f38: 000B8F38: 00 00 02 d8 00 00 01 9a 00 00 01 9d              ...ן...Ü...¥  skip reasons $b8f54: 000B8F64: 00 00                                         
=== FLOPPY gate ste 1024 1.62 16
disk-2 prompt True t 46 vbl 2409 story screen seen True screens saved 6 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_tint_ste_1024
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4096 $1021/$100e (2, 217)
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
road magic $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $d7040: 000D7040: 00 01 02 ba                                      ...´
extra-frame counters at 16 MHz, up held, $100e 695: frames/groups/ticks $b8f38: 000B8F38: 00 00 02 89 00 00 01 9b 00 00 01 9e              ...ë...¢...ß  skip reasons $b8f54: 000B8F64: 00 00                                         
=== FLOPPY gate ste 4096 1.62 16
disk-2 prompt True t 46 vbl 2408 story screen seen True screens saved 6 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_tint_ste_4096
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4095 $1021/$100e (2, 215)
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
road magic $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $d7040: 000D7040: 00 01 02 ba                                      ...´
extra-frame counters at 16 MHz, up held, $100e 693: frames/groups/ticks $b8f38: 000B8F38: 00 00 02 8c 00 00 01 9b 00 00 01 9d              ...î...¢...¥  skip reasons $b8f54: 000B8F64: 00 00                                         
=== FLOPPY gate st 1024 1.04 16
disk-2 prompt True t 46 vbl 2407 story screen seen True screens saved 6 in /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/build/shots/floppy_tint_st_1024
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after swap: vbl 4094 $1021/$100e (2, 216)
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
road magic $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1....  WPTR $d7040: 000D7040: 00 01 02 ba                                      ...´
extra-frame counters at 16 MHz, up held, $100e 693: frames/groups/ticks $b8f38: 000B8F38: 00 00 02 8e 00 00 01 9a 00 00 01 9d              ...Ä...Ü...¥  skip reasons $b8f54: 000B8F64: 00 00
```

5-minute plays, default HD build, STE 1.62 1 MB (`work/tint/play5_int.py`: cold boot, SPACE, `up` held plus a wall-clock left/right toggle every 6 s, 16,700 VBL = 334 s, samples every 10 s, a screenshot 6 s after each restart; the 8 MHz run is the native clock, the 16 MHz run switches the clock after the boot). Raw `res/play5_8.txt`, `res/play5_16.txt`; screenshots `work/tint/shots/play5_ste_1024_{8,16}_after_restart1.png` (HUD strip, message and face, road, car and objects intact after the restart: viewed):
```
-- play5_8
in_race True vbl 5809
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
RESTART seen: pass 1707 -> 0 at VBL 8779
shot after restart taken
extras (frames, groups, ticks) at start (0, 0, 0) at end (1078, 1078, 1868) -> extra frames 1078 in 17117 VBL
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....  CLK/NEXT/PEND: 000B8F00: 00 01 a6 c4 00 01 a6 dc 00 00 00 00              ..ªג..ªץ....
alive, fc advancing: 1698
road $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1.... WPTR: 000D7040: 00 01 02 ba                                      ...´ restarts 1 tb_car INIT/NENT/POOLP 000BF000: 01 00 06 ab 00 0e 19 80 00 1d 02 a0              ...½...Ç...á
(261, 2, 79, 0, (3, 3, 11), 4) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(3265, 2, 680, 0, (185, 185, 348), 21) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(6270, 2, 1281, 0, (383, 383, 654), 25) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(9325, 2, 129, 0, (540, 540, 948), 9) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(12330, 2, 730, 0, (720, 720, 1301), 22) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(15334, 2, 1331, 0, (949, 949, 1643), 26) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
-- play5_16
in_race True vbl 5810
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
RESTART seen: pass 1696 -> 29 at VBL 8629
shot after restart taken
extras (frames, groups, ticks) at start (0, 0, 0) at end (5666, 3191, 3198) -> extra frames 5666 in 17117 VBL
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....  CLK/NEXT/PEND: 000B8F00: 00 01 a8 0e 00 01 a8 1a 00 00 00 00              ..¿...¿.....
alive, fc advancing: 20
road $c0000: 000C0000: 52 44 47 31 00 0a 00 00                          RDG1.... WPTR: 000D7040: 00 01 02 ba                                      ...´ restarts 1 tb_car INIT/NENT/POOLP 000BF000: 01 00 00 2a 00 0d 90 46 00 02 00 30              ...*..ÉF...0
(261, 2, 112, 0, (84, 55, 58), 4) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(3265, 2, 713, 0, (1144, 657, 659), 23) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(6270, 2, 1314, 0, (2259, 1257, 1260), 24) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(9325, 2, 189, 0, (3036, 1731, 1736), 11) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(12330, 2, 790, 0, (4077, 2332, 2337), 25) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
(15334, 2, 1390, 0, (5210, 2933, 2938), 26) (vbl, mode, pass, $1226, extras (frames, groups, ticks), NENT)
```

### 11.8 Not done / unproven / for the user
- **Steered state gates (zig) and the other-scene 8 MHz extras runs (race_start/race_up) were NOT completed** (queued `run_q7.sh`, `run_q8.sh`, stopped for time; the rows above say NOT RUN). The state evidence for `tb_car` with a constantly changing bitmap is therefore: the tighten-B gates (8/8, incl. extras at 8/16/32 MHz and race_drive restart), the pixel gate here (16/16 identical, steering input in the race_up/race_drive snapshots is the snapshot's), and the 5-minute plays (steered by wall clock, 1 restart, no crash); NOT a per-pass state gate under steering on the integrated build. Re-run: `work/tint/run_q7.sh` (waits for `res/all.done`: `touch` it).
- race_drive extras gate at 16 MHz saw 0 completed extras (time-out/standing dominate); the extras state gate is carried by race_start X16/X32 (334 / 888 extras).
- Hatari only; no real hardware; the Mega STE cache is not emulated (tb_car is off there by rule). `ta_rb*`, `ta_nomouse`, `ta_facestat`, `tc_clrx`, `tb_blit*` stay options.
- The 8 MHz extras statement 'draws none' in older notes is superseded: measured 15 % of ticks (HUD build) and 29 % (new default) in the race_drive scene; 0 in the first lap right after the start light (cold windows).
- Decision for the user: none blocking. Optional: ta_nomouse (-8.3 k/pass), ta_rb/rb0 (-4.5 k) would take driving to about 2.7 VBL.
