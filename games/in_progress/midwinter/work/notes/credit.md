# MW1 release credit (`patches/mw_credit.s`, v1.1)

Requirement (user): a small, discreet `v1.1 enhanced by dad_prg` on the MAIN MENU = the Game Options screen (PLAY and the option
toggles), not the title; in an unobtrusive colour already in that screen's palette; palette unchanged. Tags: **[obs]** observed
(Hatari 2.6.1, 1 MB, STE TOS 1.62 unless stated), **[disasm]** from `tools/m68dis.py work/dumps/ram1mb_options.bin`.
Screens/dumps are in the git-ignored `work/credit/` (`grab2.py`, `diff.py`, `gate_play.py`).

## 1. How the screen is drawn [disasm]
```
010884  clr.w $ff8240.l           ; start of the options loop (colour 0 black)
01088a  bsr.w $1099e              ; <== SITE (8 bytes with the next instruction)
01088e  move.w #0,d0
010892  jsr $bf0c.l               ; palette select (table $22ee2) ; 010898 bsr $bd9a = flip ; then the click dispatch via $250d2
```
- `sub_01099e` (the only caller is `$1088a`): `a2b8` copies the picture `$70000` (32000 B) into the draw buffer `$0(a6)` (a6 = `$2C376`),
  then draws MOUSE/STICK/KEYS (the selected one), MORTARS/BOMBERS/TRAINING (when their word is non-zero) and PLAY / GAME OPTIONS with
  `sub_00a958`: a1 = string, a2 = glyph-index table (`$26323` small font, `$262a2` large), `$18(a6)` colour index, `$16(a6)` y,
  `$48(a6)` centre x; it centres the string and falls into `sub_00a99c`/`a9aa` (per glyph `ab40` -> `a36c`).
- `a36c` writes only where the glyph has a bit (`and.l mask,(a1)` then `or.l colour,(a1)`), clipped to `$26..$2c(a6)` = 0..319 x 0..199,
  colour planes from the table `$236b4` (8 bytes per colour index).
- Every mode/toggle handler (`$10960`, `$10970`, `$10986..$10996`) is `jsr (a0)` from `$108ce` followed by `bra.w $10884`, so every
  click redraws the whole screen through `$1099e`; one hook there covers the first draw and all redraws. [obs: screenshots after each
  of the 6 clicks below all carry the 844 text pixels]
- Nothing branches into `$1088e` / `$10890` (`m68dis --xref`: no hits), so the 8-byte site is safe: `jsr $B9000.l` (+ nop pad) replaces
  `bsr.w $1099e ; move.w #0,d0`.

## 2. Free area [obs]
Decoded displayed buffer (`$78000`, 4 bitplanes, 320x200): the PLAY frame spans x 77..242 and ends at row 196; rows 197..199 are black
but only 3 rows high. Columns 0..76 and 243..319 are black from row 130 to row 199 (no pixel at all). The text therefore goes in the
bottom-left corner, in two lines, because the one-line string is 112 px wide in the game font ("v1.1 enhanced" 58, "by dad_prg" 50):
centre x = 38, y = 178 and 187 (pitch 9; the glyph cell is 9 rows, descenders g/p/y 11).

## 3. Colour [obs]
Palette of the screen (`m $ff8240`): `000 777 157 023 134 245 467 210 310 421 643 020 030 530 510 660`. The labels use index 2 (`157`).
The credit uses index 5 (`245`, a muted slate blue, also used in the PLAY frame art); the palette is not touched.

## 4. Gates
Builds: `build/cr_hd` = `--only mw_credit pp_nofade pp_bigram_cache`, `build/cr_fl` = `build --floppy --only mw_credit floppy_secbypass`;
unpatched references: `.` (HD) and `build/cr_fl0` (`--floppy --only floppy_secbypass`, the same floppy build without the credit).
- **Diff of the displayed screen against the unpatched screen** (`work/credit/diff.py`, decoded from a full RAM dump after the screen
  settled; the displayed buffer's base is read from `$ff8201/03`):
  ```
  hd    STE 1.62 : pixels differ: 211  bbox x 9..65 y 180..197  orig colours under the text [0]  new colours [5]  all inside x9..65 y178..198: True
  floppy STE 1.62: pixels differ: 211  bbox x 9..65 y 180..197  orig colours [0]  new colours [5]  True
  plain ST (TOS 1.04, HD build) vs the STE original: 211 pixels, same bbox, colours [0] -> [5]
  full default set (final_fl vs the unpatched floppy): 211 pixels, same bbox
  ```
- Screenshots (STE): `work/credit/cr_hd_ste.png`, `cr_fl_ste.png`, `cr_hd_st.png` (plain ST, TOS 1.04), `final_fl.png`; originals `orig_*.png`.
  The `at_options` reference box (screenshot x 250..580) does not overlap the text (x 114..230).
- `mw1patch.py verify`: ALL OK; the site `$1088a` original `61000112303c0000` matches the image and the RAM dump.
- Toggle + PLAY (`work/credit/gate_play.py`; cold boot, click JOYSTICK, KEYBOARD, MOUSE icons, then MORTARS, BOMBERS, TRAINING, PLAY ->
  Team -> Stark -> Decisions -> Skiing), credit-only HD set and the final default set:
  ```
  marker 000B2FF8: 4d 57 50 4f  MWPO
  after click J: credit px 844 ... J      after click K: 844 ... K      after click M: 844 ... M
  after click mortars: 844 {'mortars': False, 'bombers': True,  'training': False}
  after click bombers: 844 {'mortars': False, 'bombers': False, 'training': False}
  after click training: 844 {'mortars': False, 'bombers': False, 'training': True}
  marker MWPO   gstate {'x': 25600, 'z': 25600, 'speed': 0, 'heading': 0, 'action': 0, 'exit': 0}   in_ski True
  ```
  (844 = non-black screenshot pixels in the credit rect, i.e. the 211 ST pixels at 2x2 on every screenshot.)
- Floppy, full default set (`python3 tools/mw1floppy.py credit_fl ste 1.62 1024 build/floppy --team`):
  ```
  'Insert graphics disk' prompt after 51 s: drive A -> MWB.st
  Game Options screen reached: True after 65 s      [options] marker: 000B2FF8: 4d 57 50 4f  MWPO
  THE TEAM screen reached: True                      [team] marker: 000B2FF8: 4d 57 50 4f  MWPO
  ```

## 5. Notes
- The blob (`$B9000`) saves and restores `$14..$49(a6)` (the text routine's scratch fields) and d0-d7/a0-a5, so the game state after the
  call equals the unpatched one; only the screen differs.
- Version flow: `; version: 1.1` in `mw_credit.s` is the only place. `mw1patch.py` replaces `@VERSION@` in that file, in PATCHES.TXT /
  FLOPPY.TXT (`doc`, the floppy README), and `package.sh` names the zips with `mw1patch.py version`.
