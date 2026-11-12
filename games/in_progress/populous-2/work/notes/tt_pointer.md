# Populous 2: pointer missing on the TT / Falcon (fix: `pop2_tt_ptr`)

2026-11-12, Pop2TTPtr. Hatari 2.6.1, TT TOS 3.06 `--mmu true` 60 Hz and Falcon TOS 4.04, 4 MB, GEMDOS HD builds (the pointer path does not depend on ACSI vs GEMDOS [INFERENCE: not run on the user's ACSI image]).
Raw: `work/gates/tt_ptr_stages.txt` (every stage line), `tt_ptr_abtest.txt`, `tt_ptr_tickab_busy1.txt`, `tt_ptr_abtest_neg.txt`. Sheets: `work/shots/tt_pointer_sheet_tt.png`, `tt_pointer_sheet_falcon.png`. Scripts/shots: `work/scratch/ttptr/`.

## 1. Reproduction (TT, cold boot)
The stock game on a 60 Hz TT stops at "SORRY PAL MACHINES ONLY" (pointer drawn there, top-left, work/scratch/ttptr/t0_tt_0.png). So "stock" below = PP's game + `pop2_ntsc`/`pop2_ntsc2` only (`build/TTPtr_ntsc`), "v1.0" = default set (`build/TTPtr_def`), "fix" = default + `pop2_tt_ptr` (`build/TTPtr_defix`).
Metric (`lib.py ptr_score`): the pointer's mask pixels are taken from RAM (`$393fa/$393fc`, shape `$682d0+[$11d50]`) and the screenshot is checked at those pixels: every colour class (shape index) must be one constant colour and the classes must differ; a frame passes at >= 0.95. Pointer parked ("still", 12 shots ~1 s apart) and stepped to 12 positions ("moving"), as visible shots / total:

| screen | TT stock | TT v1.0 | TT v1.0 + fix | Falcon v1.0 | Falcon v1.0 + fix |
|---|---|---|---|---|---|
| main menu | 0/12, 0/12 | 0/12, 0/12 | 12/12, 12/12 | 0/12, 0/12 | 12/12, 12/12 |
| CONQUEST sheet (first click) | 0/6, 0/6 | 0/6, 0/6 | 6/6, 6/6 | 2/6, 2/6 | 6/6, 6/6 |
| menu again (after PROCEED) | 0/4, 0/4 | 0/4, 0/4 | 4/4, 4/4 | 3/4, 3/4 | 4/4, 4/4 |
| battle sheet | 0/12, 0/12 | 0/12, 0/12 | 12/12, 12/12 | 5/12, 8/12 | 12/12, 12/12 |
| manual question | 3/6, 3/6 | 4/6, 3/6 | 6/6, 6/6 | 5/6, 3/6 | 6/6, 6/6 |
| play, map | 9/12, 7/12 | 7/12, 5/12 | 12/12, 12/12 | 6/12, 9/12 | 12/12, 12/12 |
| play, panel | 7/12, 8/12 | 8/12, 6/12 | 12/12, 12/12 | 5/12, 4/12 | 12/12, 12/12 |
| game requester (strip icon 1) | 0/8, 0/8 | 0/8, 0/8 | 8/8, 8/8 | 1/8, 1/8 | 8/8, 8/8 |
| CREATE YOUR DEITY (name screen) | not run | not run | 8/8, 8/8 (`f4_defix_tt_deity_raw.png`) | not run | not run |

The "v1.0 vs stock" rows are the same within noise: our pop2_ptr_a/b skip does not make it worse (its first VBL after a flip is a full draw; the skip needs the buffer unchanged). The partial scores in play are the tick/flip timing (a flip every 9 VBL in v1.0, so 1 of 9 frames lacks the pointer; the stock 32 MHz TT flips about every VBL in the menus, so the pointer is never on screen there). Falcon runs at 50 Hz and flips less often, hence the partial values.
Not run: end-of-game screens (no cheap way to reach them), the stock Falcon (original game, no PAL problem there; v1.0 stands in for it, [INFERENCE] same behaviour), the TT stock for CREATE YOUR DEITY.

## 2. Mechanism
VBL handler `$18fa` (listing: `$1a1a` restore of the saved rectangle `[$202e]` from `$2032`; `$1a4e`-`$1b30` save + draw into `[$392dc]`; `$1b34 move.w #1,$392cc.l` VBL flag). The flip `$1bfe`: `move.l $392e0.l,d0 / move.l $392dc.l,d1 / move.l d1,$392e0.l / move.l d0,$392dc.l / lsr.w #8,d0 (1c16) / move.l d0,$8200.w (1c18)`. 15 callers of `$1bfe` (`--callers`), the only other `$ffff8200` write is `$1c3a` (routine `$1c26`, no static caller; no hit at all on TT through menu -> sheet -> play, `dyn.py`: "1c26/1c3a mentions 3 3" = only the three lines listing the breakpoints, no `matched`).
Trace on the TT menu (stock set, `evt_ntsc.txt`, breakpoints `pc=$1a1a`, `$1c18`):
```
Video base 0xa000  VBL 1945 HBL line 0   pc=$1a1a (pointer draw)   $392dc = 0xa000     <- drawn into the buffer on display
Video base 0xa000  VBL 1945 HBL line 25  pc=$1c18 (flip)           $392dc = 0x2300     <- base is about to become 0x2300 (no pointer in it)
Video base 0x2300  VBL 1946 HBL line 0   pc=$1a1a                  $392dc = 0x2300
Video base 0x2300  VBL 1946 HBL line 25  pc=$1c18                  $392dc = 0xa000
```
`fps(250)` on the menu: 241 flips / 250 VBL. The menu flips every VBL, the draw goes into the shown buffer at line 0, the flip at line 25 switches to the other buffer, which has no pointer until the next VBL: the pointer is never in the frame Hatari's TT/Falcon video shows (it takes the base at once; an ST/STE/Mega STE latches it at the next frame, so the VBL's draw is in the shown frame; the user confirms the Mega STE is fine). Same class as Powermonger `tt_ptr`, Midwinter 2 `p8_tt_ptr`.

## 3. Fix: `patches/pop2_tt_ptr.s` (default yes, 68020+ only)
Site `$1c16` (`e04821c08200` = `lsr.w #8,d0 / move.l d0,$8200.w`) -> `jsr $86600.l`; blob `$86600`, data byte `TT_F` `$86fa0` (0 unprobed, 1 68000/68010, 2 68020+). In the flip, with the VBL masked (`ori #$0400,sr`): copy `$2032` (256 B) + `[$2234]`,`[$2232]` + `[$202e]`; the handler's save+draw into the new `[$392dc]` (verbatim `$1a4e-$1b30`, without the 60 Hz test `$1a68` which `pop2_ntsc2` removes); then the displaced base write; then restore the OLD rectangle from the copy. Skipped while hidden (`$2246 != 0`). CPU test: index-register scale trick of `p8_tt_ptr` (no cookie jar). 68000/68010: the first call writes the six original bytes back and does the displaced instructions: ST/STE/Mega STE then run the unpatched flip. Cold boots:
```
COLD ste 2048KB TOS 1.62: in_play=True marker='P2PO' turn 115->137 site $1c16=e04821c08200 TT_F($86fa0)=01
COLD megaste 4096KB TOS 2.06: in_play=True marker='P2PO' turn 120->143 site $1c16=e04821c08200 TT_F($86fa0)=01
COLD tt 4096KB TOS 3.06: in_play=True marker='P2PO' turn 123->145 site $1c16=4eb900086600 TT_F($86fa0)=02
```
Falcon: the cold boot to play is the `f_defix_fal` run (`in_play True`, stages 6-8 in `tt_ptr_stages.txt`); its site/`TT_F` bytes were not read.
Design note: the first version restored the old rectangle BEFORE the base write (what the handler does); the TT panel then lost the pointer in 1 of 12 shots (`f_fix_tt_7panel` still 11/12, shot `s01`: the pointer's 11x11 px are absent there while the pointer-parked neighbours have it): the restore erased the pointer from the still-displayed buffer for ~0.3 ms (the blob runs while the beam can be on the pointer rows). The copy-then-restore-after-write order gave 40/40 + 40/40 + 40/40 (`g_fix2_tt`: panel, map, top rows y=0) and 12/12 everywhere in the final table.
Interplay: pop2_ptr_a/b compare the screen and the recorded inputs; the blob's draw leaves the record untouched and a skip after it is still exact (restore+redraw would write the same bytes: [INFERENCE from the code, gated below]). The tick's R passes flip through the same `jsr $1bfe`, so they carry the pointer; S passes do not flip. Cost: one draw (~12k cycles) per flip on a TT/Falcon only.

## 4. Gates
```
p2abtest.py --only pop2_spr pop2_spr16 pop2_ptr_a pop2_ptr_b pop2_clamp pop2_tt_ptr --mhz 8      (work/gates/tt_ptr_abtest.txt)
busy1 @8 MHz: IDENTICAL | turns compared: back 128, world 128, shown@S1+pointer 127, shown@flip+pointer 120 ...
game_start @8 MHz: IDENTICAL | turns compared: back 128, world 128, shown@S1+pointer 127, shown@flip+pointer 120 ...
ALL IDENTICAL   EXIT 0
p2tick.py ab busy1 16 130 --extra pop2_tt_ptr                                                       (tt_ptr_tickab_busy1.txt; --extra added to p2tick.py)
busy1 @16 MHz 50 Hz: IDENTICAL | world at pass tops: 325 compared (0 differ) over 131 turns ... pass kinds T 130 R 198 S 0   EXIT 0
```
(The STE path is the 68000 path: inert after the first call.) Forcing the TT path on the STE (`--poke 86fa0:02`, so the blob really runs) with the correct blob is also IDENTICAL on game_start (60 turns; the early draw is healed by the VBL's restore + redraw), and with a deliberately broken blob (`--poke 86fa0:02 --poke 86714:3cc1`, the first save `move.w (a4),(a6)+` -> `move.w d1,(a6)+`) it fails:
```
SHOWN@S1 DIFFER turn 397 (pointer 96,170 / 96,170, shape 0x0/0x0): 25 B differ, first at offset 27249 (row 170), rows 170-185
MISMATCH   EXIT 1                                                                                   (tt_ptr_abtest_neg.txt)
```
The earlier negative-control attempt (a draw into `$392e0`) was IDENTICAL: that draw is self-healing too, so it is not a control.
Not rerun: the busy1/game_start 16 MHz p2abtest rows, game_start tick ab, the floppy TT/Falcon cells (floppy still fails there for the old, unrelated reason, release.md section 3).

## 5. Release
`pop2patch.py verify`: ALL OK; `PATCHES.TXT` has the user line; `tools/package.sh` rebuilt `dist/Populous2_v1.0_patched_2026-11-12.zip` and the floppy zip (md5 in the lead's report).
