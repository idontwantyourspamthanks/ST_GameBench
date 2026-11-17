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

## 3. The patch (`patches/mr_credit.s`, default yes, blob `$BFD00-$BFEFF`, 512 B, no `; ram:`: it needs no run-time RAM)
* Site `$78524`: `lea.l $782ba.l,a0` (`41f9 000782ba`) -> `jsr $bfd00.l` (`4eb9 000bfd00`); the blob replays the `lea` (a0 = `$782ba`) and returns.
* Draws `v1.0 enhanced by dad_prg` (24 characters) into `($78004)` = `$70000`, 8-pixel cells centred on 40 columns (x 64-255), glyph rows at screen rows 194-199; registers
  saved except a0; no hardware access, no game state (stack only, the stage-1 stack at `$78000` grows down), 68000 code, no timing effect beyond ~60 k cycles once (**[INFERENCE]** estimate).
* **Font**: the game's OWN 8x8 message font (the ticker/title text font: `$14fd4` draws it from `$190be`, 16 B per glyph = 8 x (edge byte, body byte), index = char - $20).
  It is not in RAM yet at this point (the game loads after the picture), so the 25 glyphs the line can need (all digits, for the version) are embedded, copied from disk A `$310be` by
  `work/credit/gen_glyphs.py` (cross-checks disk A against the RAM of three dumps for all 95 glyphs). Same drawing rule as the game's (glyph clears covered pixels; edge pixels one colour, body pixels one colour).
  Two layout adaptations (the picture leaves only rows 194-199 under the frame, row 193 stays black as a gap): each glyph is stored as the cell rows 0,2,3,4,5,6 (row 1 repeats row 0 for all stems; row 7 only holds the
  tails of `p` and `y`, which lose their last row), and the game's `_` (a bar in cell row 0 = an overline in this font) is drawn in the last row as an underscore.
* **Pixel verification of the font data against what the game itself draws** (`work/credit/font_cap.py`, `font_verify.py`, screen dumps `work/credit/fontcap/`): the game's title text
  "Hi, I'm Ike. Watching out for / Fat Sam the Sheriff ..." (HD build, displayed buffer `$78000`): 22 of 22 and 13 of 13 non-blank cells equal the coverage of the font glyphs from disk A
  and the two-colour rule (one edge colour, one body colour per cell) holds in all of them. Glyphs seen there: `H i , I ' m k e . W a t c h n g o u f F S r s`; of the credit's glyph set `a c e g h n r .` are covered by that text;
  `0-9 b d p v y _` are not drawn by any screen I reached (identical to the same table in RAM, but not seen drawn).
* Colours: body 7 ($765 cream, the lettering colour of the title), edge 5 ($654, the picture frame colour): visible on the black rows, no clash with the brown art. Palette fades act on the whole
  picture (the text fades in/out with it; screenshots at the fade-in, full and fade-out instants below).

## 4. Screenshots (`work/credit/evidence/`, 640x400 crops of the picture, not committed)
| file | what |
|---|---|
| `overview.png` | 8 frames: credit HD STE 1 MB (left) / BEFORE (right); credit HD STE 4 MB / HD Mega STE 1 MB 8->16 MHz; credit floppy STE 1 MB / BEFORE floppy; credit floppy STE 4 MB / Mega STE 1 MB |
| `credit_hd_ste1m.png`, `before_hd_ste1m.png` | HD STE 1 MB, VBL 2600 (palette 5/6 faded in) credit vs stock |
| `credit_hd_ste4m.png` | HD STE 4 MB, full palette |
| `credit_hd_mste1m_16mhz.png` | HD Mega STE 1 MB TOS 2.06 (boots at 8 MHz, 16 MHz from VBL 200 like `tools/play.sh --cpu 16`) |
| `credit_floppy_ste1m.png`, `before_floppy_ste1m.png`, `credit_floppy_ste4m.png`, `credit_floppy_mste1m_8mhz.png` | floppy build, VBL ~686-689 |
| `hd_ste1m_fade_sequence_2560_2600_2640_2680_2720.png` | HD STE 1 MB: fade-in, near full, fade-out (black), sunrise screen, sunrise: the text is gone with the picture, later screens untouched |
| `zoom_credit_*.png` | bottom rows, 3x |
Text exactly: `v1.0 enhanced by dad_prg`.
Trade-offs (visible): the game's `1` is a plain 3-pixel bar (reads `v1.0` like the game's own digits), its `g` has no descender (`dad_prg` reads like `pr9` at 1:1), `p`/`y` lose the last row; the text sits directly under the frame's bottom line (row 194 vs frame row 192), in the black band between the logos.

## 5. Gates (all raw files in `work/credit/`)
* `python3 tools/msrpatch.py verify`: `verify: ALL OK` (stage-1 site matches `MSR_S1.FIC` and disk A).
* Pixels of the picture screen, credit vs stock build at the same VBLs (`vblshots.py`, `v_hd_ste1` vs `v_hd_ste1_base`, buffers `$70000`/`$78000`): VBL 2400-2520 identical (0 bytes); VBL 2560/2600 `$70000` differs in
  rows 194-199 only (315/316 bytes = the text) plus bytes behind the screen (rows 200-204 of the 32,768-byte dump = the stage-1 stack just below `$78000`), `$78000` +5..8 bytes at `$78000-$78010` (stage-1 variables); at 2680 the sunrise is drawn 1-2 frames apart (timing); from 2720 identical (0 bytes).
* Per-pass game state, cold boot HD STE 1 MB, SPACE to the race, 151 passes (counter 95-245, 6,716 B per pass = `$1000-$13ff $29c8-$34ff $4500-$4fff $dae6`, the msrabtest STATE ranges; `state_cold.py`, `state_cmp.py`):
  stock vs credit build **0 differing addresses**; control stock vs stock (second boot) 0 differing addresses (`st_base1.json`, `st_base2.json`, `st_credit.json`).
  (The snapshot recipe `msrabtest.py` cannot apply a stage-1 patch live: a snapshot is past stage 1; hence the cold-boot variant.)
* Race frame pixels, cold boot, both buffers `$70000`/`$78000` (32,000 B each) at the first `$7b86` with `$100e = 200` (`pix_cold.py`): stock vs credit **0 differing bytes** in both buffers.
* Cold boot HD to the race, `$1021` = 2, `$100e` advancing, marker `MSPO` (`race_cold.py`, `hd_cold_gates.txt`): STE 1 MB TOS 1.62; STE 4 MB; Mega STE 1 MB TOS 2.06 at 16 MHz (8 MHz boot, switch at VBL 200); Mega STE 4 MB. All reached the race.
* Cold boot FLOPPY (`tools/msrfloppy.py gate`: disk A alone, SPACE through the screens, disk-2 swap, race, `fl_gates.txt`): STE 1 MB, STE 4 MB, Mega STE 1 MB at 16 MHz: story screens, disk-2 prompt, race (`$100e` 215-219), marker `MSPO`, `RDG1` road tables ok.
* Not run: TT/Falcon (68030 caches: the patched stage-1 bytes and the blob are written as data before they execute for the first time, **[INFERENCE]** no stale line possible), real hardware, a negative control for the cold-boot state/pixel gate
  (the picture-screen compare above does show the text rows as differences, i.e. the compare can fail).

## 6. Reproduce
`python3 tools/msrpatch.py build --out build/credit_hd` / `build --floppy --out build/credit_fl`; captures `work/credit/*.py` (headers say how). Hook summary: stage 1 `$78524` (HD: RUNME copy routine edit; floppy: disk A `+$2d24`), blob `$BFD00`.
