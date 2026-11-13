# Hunter v1.2 visuals: STE palette, the Amiga's sky, the lit panel (HunterVisuals)

Tags: **[disasm]** `tools/m68dis.py` on `work/dumps/ram_foot_stand.bin` (ST, `a5 = $806`, `a6 = $ff8000`) or on the Amiga `main` file from the user's ADF (`tools/amiga_extract.py`; marked "Amiga"); **[obs]** raw tool output produced here (Hatari 2.6.1); **[INFERENCE]** not verified.
Patches (all `default: no`; gates below passed, the look awaits the user): `pal_fade pal_load` (palette), `sky_vbl sky_fill sky_clr sky_fdst sky_ldst sky2_aciax sky_vblx` (sky + panel).
Tools: `tools/huntvis.py` (snapshot gates, screenshots, cost), `tools/huntvis_cold.py` (cold boots). Raw gate outputs: `work/notes/visuals_gates/*.txt`. Screenshots: `work/shots/visuals_*.png`, contact sheets `work/shots/visuals_sheet.png` (v1.1 against v1.2) and `visuals_sheet_options.png` (palette only / + sky / + tint).
Builds used: `build/vis_hd`, `build/vis_fl` = the 8 default patches + the 9 above (`huntpatch.py build [--floppy] --only ... --samples build/hunter_snd.bin`). Both builds work; the floppy disk has 6,144 bytes free.

## 1. STE 4096-colour palette (`pal_fade`, `pal_load`)

**Original [disasm].** The palettes are the Amiga's 12-bit words (table `$602a`). The fade keeps each gun as a 4.4 byte and packs the high nibbles:
```
0067ea: clr.w d2 / moveq #2,d1 / 0067ee: move.b (a0)+,d0 / ror.w #4,d2 / andi.b #$f0,d0 / or.b d0,d2 / dbra d1,$67ee
0067fc: move.w d2,d0 / 0067fe: rol.w #3,d2 / 006800: andi.w #$777,d2 / 006804: rts          (Amiga $6aac: rol.w #4)
006200: move.w (a0)+,d1 / 006202: lsr.w #1,d1 / 006204: andi.w #$777,d1 / 006208: move.w d1,(a1)+   (direct loader $61f2)
```
Callers of `$67ea`: `$67a6`, `$67da` only; `$61f2` is called once, from `$5f3c` (screen-mode change, at IPL 7, `$5eae: move.w #$2700,sr`).

**Change.** Site `$67fc` (10 B) -> `jmp $8c014`; site `$6200` (8 B) -> `jsr $8c040`. With `FLAGS` bit 0 (STE-class hardware: STE, Mega STE, TT, Falcon) the value written is `((c >> 1) & $777) | ((c & $111) << 3)`; otherwise the two original instructions run. No state, no timing.

**Result [obs]** (`huntvis.py palette`, `$ff8240` read-out; the day row of the live run is not converted because a live-applied patch only acts at the next fade, so day is from the cold boot):
```
PALETTE before day   000 020 031 253 575 400 300 540 555 200 310 420 010 120 130 004  distinct 16
PALETTE before dusk  000 020 021 242 454 300 200 430 444 200 210 320 010 120 120 003  distinct 14
PALETTE before night 000 010 010 121 232 200 100 220 222 100 100 210 000 010 010 002  distinct 10
PALETTE pal    dusk  000 028 8a1 24a 454 300 a00 438 444 280 a10 320 810 120 1a0 003  distinct 16
PALETTE pal    night 000 010 098 1a9 a3a 200 900 a20 aaa 100 980 210 080 810 890 002  distinct 16
cold boot STE, day   000 0a8 8b9 adb d7d c00 b00 dc8 ddd a80 b90 ca0 890 9a0 9b0 00c           (STE nibble = bit 3 is the low bit)
cold boot ST,  day   000 020 031 253 575 400 300 540 555 200 310 420 010 120 130 004           (unchanged)
```
By day the picture is half a step brighter (the Amiga's values); menus and title pictures go through the same two routines and shift the same way.
**Frame buffers** unchanged: `huntab_serial.py --only pal_fade pal_load --flips 2 6 --lock --no-fps` -> `ALL IDENTICAL` (7 snapshots); `huntvis.py pix --set pal` -> 12 of 12 page captures byte-identical on each of the 7 snapshots.

## 2. The Amiga's sky (`sky_*`)

**Amiga [disasm, Amiga].** `$ca96` clears the window to colour 15. The copper list `$5dd8` holds `019e:0118, 022a, 033a, 044c, 055f` and then `019e:0136`; `$62b4..$62f6` computes the horizon row (`$e(a5) << 8 / $2b00 + $2e` -> `$1534(a5)`) and rewrites the six wait lines: horizon, and 2, 6, 14, 30, 62 lines above it (table `$62f8` = 2, 4, 8, 16, 32), each clamped to the window. Above the first wait colour 15 is the palette's own (`$00a`). The copper colours are faded with the palette.
**ST [disasm].** Same horizon: `006000: move.w $c(a5),d1 / ext.l / lsl.l #8 / divs.w #$2b00,d1 / addi.w #$2e,d1 / move.w d1,$1544(a5)`. `$c(a5)` is the camera HEIGHT (`0037e2: addi.w #$5a,d2 / add.w $1542(a5),d2 / move.w d2,$c(a5)`), so the horizon follows height (hills, aircraft), not a pitch angle; the study's "pitch" was a misreading. The fill `$c84a` writes `$aaaaaaaa/$55555555` rows below the horizon (`$c85c`, `$c868`) and solid `$ffffffff` above (`$c8b8 moveq #$ff,d0 / bra $c8d0`).

**What the patches do.**
- `sky_fill` (`$c84a`, 8 B): in screen mode 3 (`$13e(a5)`, set by `$5eae`; mode 3 = 140-row window + 60-row panel, table `$5cfe`), horizon 1..139, draw page not the `$481c` loop's template (`$7fac`): 140 rows of solid colour 15 through the game's own loop `$c8d0`, and the page's horizon is stored in a 4-slot table {page, horizon, fresh}. Anything else takes the original code at `$c852`.
- `sky_vbl` (`$c5f0`, the first 8 B of the VBL handler): reads the video base `$ff8201/03` (as the pointer code `$a66c` does). When the base changed, the new page gets a sky only if it was filled since it was last shown ("fresh"); the mode must be 3. Then it programs MFP Timer B (event count, one count per display line): up to 6 colour-15 changes and one terminal interrupt at the first panel row. Each handler leaves the count for the interrupt after the next in the timer's data latch (reload at underflow), so the rows do not drift when one interrupt is served late.
- Band colours = Amiga values scaled like the fade does (gun x level >> 4, level = `$18c(a5)`), packed by the game's own `$67fc` (so they follow `pal_fade`). Plain ST: 3 bits per gun (at night bands 2-4 are one colour: `bands 001 002 002 002 113 001`, cold boot ST).
- `sky_fdst` (`$6790`), `sky_ldst` (`$61fa`): the game's two palette writers write to a shadow palette; the VBL hook copies it to the shifter when it changed (or after a panel frame). Both writers run at IPL 7 or inside the VBL handler, so no write is ever half done. The other direct writes (`$55c8`, `$a49c`: `move.w #$fff,$240(a6)`; `$ab1c`, `$ab34`, `$d5d2`) are debug/error paths and stay direct.
- `sky_clr` (`$c8c2`, in the clear `$c8bc/$c8c0`): the cleared page loses its sky (dialogue screens drawn on the shown page, `$d1ae..$d1c2`).
- Outside mode 3 (menus, game options), on a page without a fresh fill (the `$481c` loop) and on excluded machines nothing is armed: Timer B stays stopped. Pause keeps the sky (the page stays; `$93` bit 7 is NOT the condition: `$2ef0 bclr #7,$93(a5)` on pause).

**Interrupt safety.**
- MFP is in software end-of-interrupt mode (`00a9f4: move.b #$48,$7a17(a6)`); the game clears IERA/IMRA bit 0 at start (`$aa06`, `$aa0c`) and never uses Timer B again; vector `$120` = `$aa6e` (stub). Every handler ends with `move.b #$fe,$fffffa0f.w`; the hook re-arms vector, IERA, IMRA every VBL.
- **IKBD.** The handler `$afde` runs at IPL 6 with two 13-register `movem` (112/116 cycles); the joystick reply arrives every VBL. `sky_vbl` points `$118` at a wrapper (IPL 5, registers pushed in two halves, then `$afe2`) and `sky2_aciax` (`$b004`) pops in two halves: Timer B (higher MFP priority) nests. Control without it: 12.0 % of colour writes late, up to 600 pixels (section 4).
- **VBL handler.** It runs `ori #$700,sr` for its whole length; with the DMA mixer it reaches into the picture (control: first band up to 21 lines late at 50 Hz, 2168 of 3765 VBLs late at 60 Hz). On an armed frame `sky_vbl` masks the IKBD in the MFP (IMRB bit 6) and continues at IPL 5; `sky_vblx` (`$c61c`, before `movem/rte`) restores both. So only the Timer B stubs can interrupt the handler body (hn_hz, snd_core mixer, jag_pad poll, tb_vbl: none shares state with them).
- **Late colour writes.** A direct handler writes colour 15 about 60 cycles after the interrupt is taken; when the interrupted instruction is a divide (`$8c16c` p4_edge, `$52aa`, `$52ac`, `$3b84`) the write lands up to 112 pixels into the row for one frame: 1.3 % of direct band interrupts (walking, driving), 2.4-3.5 % in the worst scene measured. The horizon line (sea against sky, the only strong contrast) therefore uses a line-synchronous handler: entered one line early, it waits for the counter to move, then writes: 0 late in every run. `SKY+29` is the mask of synchronous bands (default `$20` = horizon only; `$3f` = all six, 0 late writes, +1,520 cycles per VBL). The panel palette handler is synchronous too (16 colours inside one horizontal blank).
- **TT / Falcon.** `sky_vbl` tests the CPU once (`lea (a0,d1.w*2)`: a 68000 ignores the scale) and then counts the Timer B events of one frame; unless it is a 68000 and the count is 200, state = `$ff`: all seven sites run the original instructions, Timer B and the vectors are never touched, the fill stays dithered. `pal_` still applies there (STE-format palette). Cold boots: TT `SKY_ST=$ff IERA=00 vec$118=0000afde vec$120=0000aa6e`, Falcon `SKY_ST=$ff`.

**Options** (`SKY+28` = `$8f11c`, read every frame): bit 0 sky bands + solid sea, bit 1 dawn/dusk tint, bit 2 lit panel. Default 5.

## 3. Panel with its own palette (bit 2)
At the end of row 139 the terminal handler loads 16 colours = the current base palette (`$602a`, where `$6210` copies the mode's palette) at level 15, i.e. the day palette, whenever the landscape level is below 15 (night 7, dusk/dawn 9-13). By day the split is skipped (identical palettes) and only colour 15 is put back. During a fade to black the panel follows below level 7 (table 0,2,4,6,9,11,13), so screen changes still fade completely.
**Amiga panel colours: not shipped; probed.** The Amiga panel is an ILBM too (`externs/panfile`, CMAP `010 266 6ac dee 35b d20 a10 ed2 e70 862 642 011 566 344 233 122`), same layout as the ST's `FILES/8`, other colour indices (9,678 of 19,200 panel pixels differ). Live probe (Amiga rows 0-59 written over the panel master `$3682c`, panel palette = that CMAP): `work/shots/visuals_probe_amiga_panel_night.png`: the game's own digits come out right. It needs the 9,600-byte bitmap (5,104 B run-length packed, 2,341 B deflated) in RAM and the split on every frame; no payload window has that room in 1 MB. It would fit a disk file or the 2 MB layout. [INFERENCE: icons and the other panel states were not checked.]

## 4. Gates [obs] (full outputs in `work/notes/visuals_gates/`)

**Frame buffers** (`huntvis.py pix`, both pages after 5 patched frames, frames locked to 15 VBL, 3 teleport views per snapshot, base = unpatched):
```
PIX sky foot_stand: OK: 12 page captures, 6 byte-identical, 77500 changed pixels in the others      (foot_walk, hills_stand, 4mb_foot_stand the same; car_stand 76108; car_drive 12027)
PIX sky car_turn: OK: 12 page captures, 6 byte-identical, 11126 changed pixels in the others
     view 0 flip 5 b23000: 1997 pixels 0 -> 15 on rows 56..125, all at (x+y) even; frames base [8, 14, 15, 15, 15] patched [8, 14, 15, 15, 15]
PIX panel <all 7>: OK: 12 page captures, 12 byte-identical, 0 changed pixels          (panel option only, cfg 4)
PIX pal   <all 7>: OK: 12 page captures, 12 byte-identical, 0 changed pixels
```
Every changed pixel is a colour-0 pixel of the dither ((x+y) even, rows horizon..139) that became 15; nothing else differs. (The first `car_turn` lines in `pix.txt` say FAIL: a base capture cached before the lead fixed `huntab.py`; `pix_car_turn.txt` is the re-run.) Finding on the way: `huntab.py --flips 1` captured at the apply flip itself (0 patched frames); the lead fixed it.

**Raster exactness** (`huntvis.py raster`: paused frame; the shown page is dumped and compared with Hatari's screenshot: every (row, colour index) shows one colour; colour 15 changes only on the expected rows, the other 15 only between rows 139 and 140; 5 frames each): 8 scenes x 7 option sets x 50/60 Hz = 112 runs, **109 PASS**. The 3 FAIL (all 60 Hz: `night sky_tint`, `low sky_nopal`, `high sky`) report `row 192..199 index 0: 2 colours` (text-box rows, not the sky; the band rows of those runs are right) and did not recur in 12 repeats; cause not found [INFERENCE: screenshot taken across a frame change].
```
RASTER 50 Hz night      sky         H= 50 panel-split=yes colour-15 changes after rows [19, 35, 43, 47, 49, 59]: PASS
RASTER 60 Hz higher     sky_syncall H= 90 panel-split=no  colour-15 changes after rows [27, 59, 75, 83, 87, 89, 139]: PASS
```
Negative control (IKBD wrapper at IPL 6): 6 of 16 frames `index 15 changes between rows 50 and 51` / `no change at boundary row 50`.

**Sky follows the shown page** (`huntvis.py pages`: every fill and every armed VBL logged while the camera height is poked):
```
PAGES 1mb_hills_stand double buffering: 111 fills on pages ['0x23000', '0x2ad00'], horizons 57..76, 602 armed VBLs, 110 page changes (5.50 VBL/frame), wrong horizon: 0: PASS (control: 430 VBLs would be wrong with the game's single horizon variable $1544 instead of the per-page table)
PAGES 1mb_hills_stand triple buffering: 124 fills on pages ['0x23000', '0x2ad00', '0x81000'], horizons 57..76, 601 armed VBLs, 123 page changes (4.89 VBL/frame), wrong horizon: 0: PASS (control: 443 ...)
```
(HunterTriple's `tb_flip tb_frame tb_vbl` applied at the loop top `$253e`.)

**Late writes** (`huntvis.py jitter`, unpaused, default patches + pal + sky; Hatari `LineCycles` at each colour write):
```
JITTER 1mb_foot_walk keys=Up 50 Hz smask=default: direct handlers  26434, late writes   348 = 1.32 % (worst: 112 pixels into the row)
JITTER 1mb_foot_walk keys=Up 50 Hz smask=default: sync   handlers   6572, late writes     0 = 0.00 %
JITTER 1mb_car_drive keys=Up 50 Hz smask=default: direct handlers  28426, late writes   361 = 1.27 % ; sync 7071, 0
JITTER 1mb_foot_walk keys=Up 50 Hz smask=0x3f: sync   handlers  33977, late writes     0 = 0.00 %
JITTER 1mb_foot_walk keys=Up 50 Hz smask=default NO-ACIA-FIX (control): direct handlers  26992, late writes  3240 = 12.00 % (worst: 600 pixels into the row)
```
Top rows under the DMA mixer (two looping voices injected, horizon 64 so the first band is on row 2; raster line of the first handler):
```
50 Hz           slot 0 direct:  3022 entries on raster lines {64: 2656, 65: 365, 72: 1}: more than one line from line 64: 1
50 Hz control   slot 0 direct:  2995 entries on raster lines {64: 2583, 65: 381, 70: 1, ... 85: 5}: more than one line from line 64: 31
60 Hz           slot 0 direct:  3993 entries on raster lines {35: 3825, 36: 168}: more than one line from line 35: 0
60 Hz control   slot 0 direct:  3765 entries on raster lines {35: 1318, 36: 279, ... 85: 1}: more than one line from line 35: 2168
```
(control = the VBL handler left at IPL 7. One handler 8 lines late in 3,022 VBLs remains at 50 Hz; not explained.)

**World speed** (`hunthz.py rate`, default set against default + pal + sky; full rows in `hunthz.txt`):
```
foot_walk  50 Hz 8/16 MHz: 100.83 / 100.40 u/s -> 100.71 / 100.41     60 Hz: 100.81 / 100.34 -> 100.96 / 100.34     clock 50.000 / 49.98-50.01 ticks/s in every run
car_stand  clock ticks 50.000 (50 Hz), 49.97-50.04 (60 Hz) in both sets; the speed column is an accelerating car (58.8-75.0 u/s in both sets) and is not a rate test
```

**Cold boots** (`huntvis_cold.py`; `cold.txt`): marker `HNPO` on all.
| Cell | FLAGS | Sky | Result |
|---|---|---|---|
| HD STE 1.62 1 MB | 03 | on | PASS; raster day/night PASS, 10 of 10 frames clean with mouse traffic; fps 4.8 |
| HD ST 1.04 1 MB | 06 | on (ST palette) | PASS; same checks |
| HD Mega STE 2.06 4 MB | 03 | on | PASS; fps 8.4 |
| HD TT 3.06 4 MB `--mmu true` | 03 | off (`$ff`), MFP and vectors untouched, STE palette | PASS |
| Floppy STE 1.62 | 03 | on | PASS |
| Floppy ST 1.04 (fast FDC) | 06 | on | PASS; fps 5.0 |
| Floppy Falcon 4.04 4 MB | 0b | off (`$ff`), STE palette | PASS |
Each cell: 3D view reached, day and night screenshot (`work/shots/visuals_cold_*`), 10 s of walking, still in game.

## 5. Cost [obs] (`huntvis.py prof`, 8 MHz STE; interrupt work per VBL with the game paused, patched minus original; fill per frame unpaused)
| Set | Per VBL | Fill `$c84a` per frame |
|---|---:|---:|
| sky, all bands direct | +1,821 (1.23 %) | -6,005 |
| **default: horizon synchronous, day** | **+2,196 (1.48 %)** | **-6,024** |
| default, night (panel palette) | +2,879 (1.94 %) | -6,039 |
| two / all six bands synchronous | +2,570 / +3,717 (1.73 / 2.50 %) | -6,03x |
| panel only, night | +1,832 (1.23 %) | -33 |
The solid fill gives back 6,000 cycles per frame (about 600 per VBL at 10 VBL per frame), so the net is about +1.1 % by day and +1.5 % at night. `pal_`: under 40 cycles per colour written, only during fades. In the cold boot the STE stands at the HQ at 4.8 fps (10.4 VBL per frame) against 5.0 in v1.1: the frame there sits on a refresh boundary.

## 6. Limits and open points
- Hatari only. On hardware the Timer B event and the palette write timing are the usual raster technique, but nothing was run on a real machine.
- Faint one-row streaks on the five sky bands (1.3 % of interrupts, section 2); `SKY+29 = $3f` removes them for +1,520 cycles per VBL.
- Above horizon-62 colour 15 is the palette's own `$00a`, the first band `$118` is slightly darker: the Amiga's values, kept.
- Any polygon drawn in colour 15 takes the band colour of its rows, as on the Amiga.
- The tint (bit 1) is new art, not Amiga data: three colour sets for ambient 13-14, 11-12, 9-10 (`sky_base` in `sky_vbl.s`). Off by default.
- Not tested: PP's F9 Gamex freeze with the sky armed; the two-disk floppy set; Falcon HD (not bootable here, ttfalcon.md); the `$481c` loop (never met; it takes the original fill by construction).
- With `pal_` the harness's stage crops (v1.1 pictures) need a looser tolerance (`huntvis_cold.py harden`).
- sky_ code `$8F100-$8F7BB` (window to `$8F7FF`), state `$8ECEA-$8ED7F` (window sky2_), pal_ `$8C014-$8C065`.
