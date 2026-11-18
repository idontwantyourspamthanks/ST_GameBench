# Release credit `v1.0 enhanced by dad_prg` (patch `mr_credit`)

User decisions: the screen is the title picture with "Moonshine Racers" at the top and the brown truck (hotrod) below; the text goes at the
BOTTOM of that screen. Text: `v@VERSION@ enhanced by dad_prg` with `patches/VERSION` = `1.0` (`python3 tools/msrpatch.py version` -> `1.0`,
`version --credit` -> `v1.0 enhanced by dad_prg`; the patch source holds the `@VERSION@` token, no second copy of the number).

## 1. Which screen, and which code (evidence)
Cold boot of the HD build, screenshots every 0.35-2.5 s (`work/credit/survey.py`, `survey_fl.py`; sheets `work/credit/sheet*.png`):
HW-detect screen -> red-truck cover (PP's slideshow, `FMR273.HST`) -> **the "Moonshine Racers" / hotrod picture with the MILLENNIUM and PEAK STAR logos** ->
sunrise intro animation -> (hook instant, `MSPO`) "Welcome partners" text -> title "Hi, I'm Ike" -> map -> race. The hotrod picture is drawn by **stage 1**
(`MSR_S1.FIC` unpacked at `$78000`; on the floppy the 25,600 B the boot sector reads from tracks 1-5 side 0 of disk A), i.e. BEFORE the existing trampoline:
the `MSPO` marker appears only at VBL ~5710 on the HD build (`work/credit/marker2.py`: `$b2700` = 0 at VBL 5108, `4d53504f` at 5711), the picture is
on screen at VBL ~2540-2630 (HD STE 1 MB 8 MHz) / ~340-900 (floppy: 12 s while the loader scatters 1,110 sectors).
Stage-1 main routine (disassembly of the unpacked image, `tools/m68dis.py work/credit/fl600.bin 784fa`):
```
0784fa: move.l #$70000,$78004 ; move.l #$70000,$78008      ; both screen-buffer pointers = $70000
07850e: jsr $7915e.l                                         ; (screen/VBL setup)
078514: lea $79496(pc),a0 ; movea.l $78004.l,a1 ; jsr $790b2.l   ; draw the picture into $70000
078524: lea.l $782ba.l,a0 ; jsr $7910e.l                      ; palette table (16 words) -> start the fade-in      <== HOOK SITE $78524 (6 B)
078530: ... jsr $78558.l                                      ; load the game ($1000..) while the picture is shown
078546: jsr $79124.l ; wait fade-out ; 07854c ... jmp $1000.w ; the game starts (RUNME's trampoline job on HD, `fl_hook` on floppy)
```
The picture is complete in `$70000` at `$78524` and nothing is shown yet (the fade-in starts at `$7910e`), so the text fades in with the picture, is
never redrawn, and the later screens (sunrise etc.) overwrite the buffer as they always did.
Picture analysis (`work/credit/truck_fl600*.png`, decoded from `$70000` with the table at `$782ba`): the frame's bottom line is screen row 192
(colour 5 = $654), rows 193-199 are black except the two logos (MILLENNIUM x 8-47, PEAK STAR x 289-311). Palette `$782ba`: `000 210 321 432 543 654 100 765 325 214 112 660 600 226 423 741`.

## 2. How the patch reaches the code (tool change, additive: `; phase: stage1`)
Stage 1 runs before the trampoline, so the existing `boot` phase cannot patch it. New phase `; phase: stage1` in `tools/msrpatch.py` (documented in `patches/README.md`):
* **HD**: RUNME's copy routine (`copy_routine(img_len, s1)`) verifies and applies the stage-1 sites right after it copies the payload (at that moment stage 1 is unpacked at
  `$78000` and has not run; the payload, incl. the blob at `$BFD00`, is already in RAM) and before the displaced `jmp $78000.l`: all-or-nothing, like the trampoline (pass 1 `cmpm.b`
  verify, pass 2 apply), table `s1tab` behind the code. Without a stage-1 patch the routine is byte-identical to the old one.
* **Floppy**: the same 6 bytes as an edit of disk A (`stage1_disk_off`: stage 1 = tracks 1.. side 0, 5,120 B each, in RAM order; site `$78524` = disk A `+$2d24`); the payload is already in RAM
  (stage-0 loader of the boot sector).
* `verify` checks the site's `; orig:` against the unpacked `MSR_S1.FIC` (`stage1_image()`, PP's LZ, 25,600 B) and, with the STX images present, against disk A (`+$02d24`, match);
  `live` skips stage-1 patches (a snapshot is long past stage 1); `list` shows `yes (stage1)`.
* Backward compatibility (before/after md5, builds into my own dirs, `mr_credit` not yet present, HEAD tool `tools/msrpatch_head_tmp.py` (deleted afterwards) vs the edited tool):
  HD folder `find . -type f | sort | xargs md5sum | md5sum` = `0d696665073642988181673ff0f39d3b` for both (`work/credit/base_hd.txt`, `new0_hd.txt`);
  floppy `disk_a.st` `ef14ba13255eadd39535c402457a338a`, `disk_b.st` `0d0be455e4d0389ed98401c0e02d21d9` for both (`base_fl.txt`, `new0_fl.txt`).
  With `mr_credit`: only `RUNME.TOS` differs on HD (`HAGA`, `FILES/*` unchanged); floppy: payload sectors + disk A `+$2d24`.

## 3. The patch (`patches/mr_credit.s`, default yes, blob `$BFD00-$BFF31`, 562 B, no `; ram:`: it needs no run-time RAM)
* Site `$78524`: `lea.l $782ba.l,a0` (`41f9 000782ba`) -> `jsr $bfd00.l` (`4eb9 000bfd00`); the blob replays the `lea` (a0 = `$782ba`) and returns.
* Draws `v1.0 enhanced by dad_prg` (24 characters) into `($78004)` = `$70000`, 8-pixel cells centred on 40 columns (x 64-255), glyph rows at screen rows 193-199; registers
  saved except a0; no hardware access, no game state (stack only, the stage-1 stack at `$78000` grows down), 68000 code, one run of about 70 k cycles (**[INFERENCE]** estimate).
* **Font**: the game's OWN 8x8 message font (the ticker/title text font: `$14fd4` draws it from `$190be`, 16 B per glyph = 8 x (edge byte, body byte), index = char - $20).
  It is not in RAM yet at this point (the game loads after the picture), so the 25 glyphs the line can need (all digits, for the version) are embedded, copied from disk A `$310be` by
  `work/credit/gen_glyphs.py` (cross-checks disk A against the RAM of three dumps for all 95 glyphs). Same drawing rule as the game's (glyph clears covered pixels; edge pixels one colour, body pixels one colour).
  Layout (option C, user-approved after the investigation in `evidence/old_optionA/` and `descender_options_3x.png`): the picture leaves rows 193-199 (7 rows) under its frame (bottom line = row 192), so each glyph is
  stored as the font cell's rows 0,2,3,4,5,6,7 (14 B per glyph, stride x14; row 1 repeats row 0 for every stem; row 7 holds the descenders of `p` and `y`, which the game's font has: the first version dropped them);
  the game's `_` (a bar in cell row 0 = an overline in this font) is drawn on the last row; the game's `g` has no descender, so its tail is HAND-COMPOSED from the font's own rows (stem row repeated, curl row moved down one row;
  `gen_glyphs.py`). The text now has no black gap row to the frame: tall letters (`h b d 0 1`) touch the frame line with their top row 193.
* **Pixel verification of the font data against what the game itself draws** (`work/credit/font_cap.py`, `font_verify.py`, screen dumps `work/credit/fontcap/`): the game's title text
  "Hi, I'm Ike. Watching out for / Fat Sam the Sheriff ..." (HD build, displayed buffer `$78000`): 22 of 22 and 13 of 13 non-blank cells equal the coverage of the font glyphs from disk A
  and the two-colour rule (one edge colour, one body colour per cell) holds in all of them. Glyphs seen there: `H i , I ' m k e . W a t c h n g o u f F S r s`; of the credit's glyph set `a c e g h n r .` are covered by that text;
  `0-9 b d p v y _` are not drawn by any screen I reached (identical to the same table in RAM, but not seen drawn); the floppy's "Insert Disk 2 and press a key." prompt shows the same font with real `p`/`y` descenders. The built screen was also compared with the table pixel by pixel for all 24 characters (all match).
* Colours: body 7 ($765 cream, the lettering colour of the title), edge 5 ($654, the picture frame colour): visible on the black rows, no clash with the brown art. Palette fades act on the whole
  picture (the text fades in/out with it; screenshots at the fade-in, full and fade-out instants below).

## 4. Screenshots (`work/credit/evidence/`, 640x400 crops or exact 320x200 pictures, not committed)
| file | what |
|---|---|
| `credit_final_overview_1to1.png` | 1:1 (320x200): HD STE 1 MB (left) and floppy STE 1 MB (right), final build |
| `credit_final_hd_ste1m_1to1.png`, `_3x.png`, `credit_final_hd_strip_3x.png` | HD STE 1 MB at VBL 2596 (full palette), picture / 3x picture / 3x text strip (rows 184-199) |
| `credit_final_floppy_ste1m_1to1.png`, `_2x.png`, `credit_final_floppy_strip_3x.png` | floppy STE 1 MB, VBL 689 |
| `credit_final_fade_1to1.png` | 10 frames (1:1) at VBL 2568, 2572, 2576, 2580, 2584 (fade-in), 2596 (full), 2612, 2616, 2620, 2624 (fade-out), captured with one armed breakpoint per VBL (`vblmulti.py`) |
| `credit_final_fade_strips_3x.png` | the same frames, text strip at 3x with the palette values of entries 7 and 5: the cream text and the tan frame line keep their contrast at every level (both scale together; at the darkest levels text and frame are equally dim) |
| `variants_all_3x.png`, `descender_options_3x.png`, `glyph_table_v10bd_.png` | the options for the record: FINAL (C), OLD (A, 6 rows with a gap), D = stock 6-row glyphs shifted up one row (rows 193-198, mockup, not built), and the font table's own rendering of `v 1 . 0 b d _` |
| `old_optionA/` | the screenshots of the first version (6-row glyphs), all machines |
Text exactly: `v1.0 enhanced by dad_prg`. Remaining look trade-offs: the font's `1` is a plain 3-pixel bar, its `g` is hand-extended, the text touches the frame line.

## 5. Gates (raw files in `work/credit/`; first round with the 6-row version: kept in the git history of this note's earlier text, the round below is the final option-C build)
* `python3 tools/msrpatch.py verify`: `verify: ALL OK`.
* Picture screen, final build vs stock build (HD STE 1 MB, `vblshots.py`, `v_hd_ste1c` vs `v_hd_ste1_base`, buffer `$70000`, all 200 rows compared pixel by pixel): VBL 2400, 2520, 2640 identical (0 pixels); at 2560 and 2600 exactly **637 pixels** differ,
  all in rows 193-199 and x 64-255; **row 192 (frame line) 0 changed pixels, logo columns (x < 48 and x > 288) 0 changed pixels** (row 193 was black: the 637 are the glyph pixels).
* Cold boot HD to the race (`$1021` = 2, `$100e` advancing), marker `MSPO`: STE 1 MB (the state captures), Mega STE 1 MB TOS 2.06 at 16 MHz (`race_cold.py`, `c_gates.txt`).
* Cold boot FLOPPY STE 1 MB, disk A alone, SPACE, disk-2 prompt, swap, race (`msrfloppy gate`, build without `fl_driveb`: `build/credit_fl_nodb`): prompt at VBL 2409, race `$100e` 214, marker `MSPO`, `RDG1` road tables ok.
  **With the default floppy set of the current tree (new `patches/fl_driveb.s`, another agent's, created after my first gates) the gate does NOT reach the prompt: with that patch the game looks at drive B when A holds no disk 2
  (FDC trace `fdc_C.log`: reads with `drive=1` at VBL 3321) and starts the race without asking, in this one-disk harness. This is independent of `mr_credit`: the same happens with the first (6-row) credit version and with delay variants of
  the blob; a build with `mr_credit` and without `fl_driveb` passes. The harness (`tools/msrfloppy.py gate`) needs the disk-2 prompt: for `fl_driveb` it needs an adaptation (owner of that patch).**
* Per-pass game state, cold boot HD STE 1 MB, 151 passes (6,716 B per pass = `$1000-$13ff $29c8-$34ff $4500-$4fff $dae6`), final build vs stock build of the same tree (`credit_curbase_hd`): 3 differing addresses `$1006`, `$100a`, `$12f2` in the first
  runs. **Control experiment (`work/credit/ctl_chain.sh`, `ctl_report.py`, raw `ctl_report.txt`, `ctl_parity_at100.txt`, `st_ctl_*.json`; builds `--only <default minus mr_credit> test_delay`, `test_delay.s` = the stage-1 hook with NO drawing, only the displaced `lea`
  plus N `dbra` iterations (10 cycles each; the real blob is about N = 6,000), copied into `patches/` only while building and removed again):**
  `$1004/$1008` are the draw/display screen-buffer pointers (low words `$0000`/`$8000` = `$70000`/`$78000`), they swap every pass, and `$12f2` is a byte derived from the buffer address (203 vs 75 = differ by `$80`, the mid byte of `$78000`); the three addresses therefore only say
  **which buffer the race loop is on at a given pass counter** (two classes P: `$1006`=0 `$100a`=128 `$12f2`=75 and Q: 128 / 0 / 203; the passes are compared by the counter `$100e`).
```
reference stock_a: class P. Value at pass counter 100:
stock_b (stock, 2nd boot)  Q     stock_c (stock, 3rd boot)  P
real_a  Q    real_b  P    real_c  P                                  (final credit build, 3 boots)
delay_0 Q  delay_500 Q  delay_1500 Q  delay_3000 Q  delay_6000 Q  delay_9000 P  delay_12000 Q  delay_20000 Q  delay_30000 Q     (no drawing at all)
```
  Per run against stock_a (`ctl_report.txt`): **no address other than `$1006`, `$100a`, `$12f2` ever differs, in any of the 14 comparisons (151 passes each)**; those three differ exactly when the run is in the other class.
  Conclusions: (a) the STOCK build itself falls in both classes (stock_b is class Q, stock_a/c class P: 1 of 3 boots swapped), the final credit build did 1 of 3, and the pure-delay builds without any drawing did 8 of 9 (N = 0 included, i.e. the hook alone): the class is a boot-timing
  artefact (the cold boot's SPACE presses are wall-clock driven and the number of flips before the race start changes by one), not caused by what the credit draws or by the hook. (b) The only state that differs is the double-buffer role (which of the two screen buffers the pass uses) and
  the byte derived from that address; nothing gameplay-relevant (`$1000-$13ff` other bytes: pass counter, speed, position, RNG `$dae6`, road/object tables `$29c8-$34ff`, `$4500-$4fff`) differs in any run. The stock `$1221` byte (timing, seen differing between two stock boots earlier) was identical in all of these runs.
  (The snapshot-based recipe `msrabtest.py` cannot apply a stage-1 patch live.)
* Not run for the final build: Mega STE floppy, STE 4 MB (the code path is the same as the first round, all passed then), TT/Falcon, real hardware.

## 6. Reproduce
`python3 tools/msrpatch.py build --out build/credit_hd` / `build --floppy --out build/credit_fl`; captures `work/credit/*.py` (headers say how). Hook summary: stage 1 `$78524` (HD: RUNME copy routine edit; floppy: disk A `+$2d24`), blob `$BFD00`.
