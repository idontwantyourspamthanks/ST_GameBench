# Hunter v1.2: the Amiga dashboard (patch `sky2_pnl`, HunterPanel)

Tags: **[disasm]** `tools/m68dis.py` on `work/dumps/ram_foot_stand.bin` (ST, `a5 = $806`) or on the Amiga `main` from the user's ADF; **[obs]** raw tool output produced here (Hatari 2.6.1); **[INFERENCE]** not verified.
Patch `patches/sky2_pnl.s` is **`; default: no`** (all gates below passed; the lead flips it). It needs the changed `patches/sky_vbl.s` (which stays `default: yes`; with `sky2_pnl` absent its new code is never reached) and the bank from the changed `tools/snd_build.py` (**re-run `snd_build.py`**: the bank grows from 124,126 to 126,738 bytes, the samples are byte-identical).
Tools: `tools/pnl_data.py` (ADF -> panel block), `pnl_gate.py` (snapshot gates), `pnl_cold.py` (cold boots), `pnl_save.py`, `pnl_screens.py`. Screenshots: `work/shots/panel_sheet_2mb.png` (v1.2 above, Amiga panel below, day / night / dusk, STE 2 MB HD), `panel_sheet_1mb.png` (1 MB, unchanged), `panel_cold_*`.

## 1. What it is
On ST-class machines with **2 MB or more** the 60-row dashboard (rows 140..199 of the 3D view) is the Amiga's bitmap with the Amiga's 16 colours (`externs/panfile`: an ILBM; CMAP `010 266 6ac dee 35b d20 a10 ed2 e70 862 642 011 566 344 233 122`). Below 2 MB, on the TT and on the Falcon nothing changes. The user approved the look (probe `visuals_probe_amiga_panel_night.png`).
Option byte `SKY+28` (`$8F11C`): **bit 3 = Amiga panel**, set by `sky_vbl` at its first VBL when RAM >= 2 MB (section 3). No second option mechanism.

## 2. The data
**[obs]** `externs/panfile` is a 320x200 ILBM; the panel is its rows 0-59 (9,600 bytes in ST planar words, 160 B per row). The ST `FILES/8` holds the same two pictures as the Amiga's `panfile` + `storepic` (FORM at 0 and at 15360); rows 0-59 differ in 9,678 of 19,200 pixels (index scheme + redrawn art), so the ST bitmap cannot be remapped by a palette permutation (a single index map explains 16,512 of 19,200 panel pixels).
**[disasm]** The game decodes any loaded file that starts with `FORM` in place (`$d614 cmpi.l #'FORM',(a0)` / `$d61c jsr $10ea2`; CMAP words go to `$612a`). The panel setup `$8122` loads FILES/8 to `$2ad00` and copies rows 0-59 to the HUD master `$3682c` (`$8138 movea.l $7f7c(pc),a3 / $8140 lea (a0)../ bsr.b $8162`, 1,200 x 8 bytes); the 3D loop copies the master to the draw page every frame (`$c902 movea.l $14c(a5),a0`) and the dynamic panel (digits, bars, radar dots) is bit manipulation on the master (`$a034`, `$a09e`, `$a11a`, `$a15e`).
**Only the panel is replaced.** Rows 60-199 (STORES page `$38dac`, buttons) and the icon sheet (FILES/9 -> `$3b32c`) stay the ST art: they are shown by other screen modes with the ST palette. The weapon/item icons that are drawn INTO the panel are therefore ST art seen through the Amiga colours; **[obs]** `/tmp`-rendered comparison (ST icon sheet with the Amiga CMAP against the Amiga sheet): same icons, only the background dither differs; in the game (`work/shots/panel_sheet_2mb.png`, pistol in the item box) it looks right. The item table that opens at the top edge of the 3D window keeps its ST (green) look.
**Packing** (`pnl_data.py`): own byte LZ (`HLZ`: literal runs, 2-byte short and 3-byte long matches, optimal parse, 46-byte 68000 decoder) -> **2,570 B** (deflate would be 2,084 B but needs a 250-byte decoder; the free window is the issue, not the stream). Block `'HPAN' | word 9600 | word word-sum | 16 x $0RGB | stream` = **2,610 B at `PANDATA = $AE4E0..$AEF11`**, appended to the sample bank by `snd_build.py` (asserts: bank < `$AE4E0`, block < `$AF000`). Nothing from the ADF is in git (`build/hunter_snd.bin` is git-ignored, as the samples).
Why the bank tail: HD loads it with `FILES\P` (`$8BA00..$AEFFF`), the floppy stage reads `HNSOUND.BIN` whole to `$90000` by raw sectors (`SND_SECS = (len+511)//512`; the stage only accepts payload *code* below `$90000`, data in the bank file has no such limit). The tail `$AE4E0-$AEFFF` is inside the region proved free in `loading.md` section 5 (HD 1/2/4 MB) and `floppy.md` section 7 (floppy 1 MB). Plain-ST floppy never reads the bank, so the panel is off there; two-disk floppy: the block is on disk 2 with the bank [INFERENCE, not run].

## 3. RAM size and RAM above 1 MB
**[obs] `$42e` (phystop) is useless under PP's loader**: `START.TOS` unpacked text `$a56 move.l $42e.w,d5` / `$a5a move.l #$80000,$42e.w` (bytes `2a38 042e 21fc 00080000 042e`) lowers it to `$80000` on HD whatever the RAM. Cold boot read-out (`pnl_cold.py`, game running):
```
HD  STE 1 MB  phystop=$00080000 memcntlr$424=$05 $ff8001=$05     HD  STE 2 MB  phystop=$00080000 $424=$08 $ff8001=$08
HD  MegaSTE 4 MB phystop=$00080000 $424=$0a                       HD  STE 4 MB  phystop=$00080000 $424=$0a
floppy STE 1 MB phystop=$00100000 $424=$05 | 2 MB $00200000 $08 | 4 MB $00400000 $0a   (the floppy loader does not touch $42e)
```
**Detection used: `memcntlr` `$424`** (TOS's copy of the memory controller byte, set before any loader runs; bits 3-2 / 1-0 = the two bank sizes, 1 = 512 K, 2 = 2 MB): `moveq #$a,d0 / and.b $424.w,d0 / beq` = at least one bank of 2 MB (`sky_vbl.s` `.good`). It is a 68000-machine test; the TT and Falcon never reach it (the sky is off there).
**RAM above 1 MB is not used, so there is nothing to prove there.** The Amiga panel is unpacked straight into the HUD master each time the game sets the panel up (`$8122`, also at every mission start); no unpacked copy, no palette table outside the sky state block (`SKYV+112`, 32 B). So `$AF000-$185FFF` (PP's D15R area at 4 MB), HAGA's size-dependent layout and the TT-RAM are never touched. [INFERENCE for later use: a free-RAM proof above 1 MB at 2 MB was not made.] What was checked: after boot + 3 screenshots + 10 s of walking (HD STE 2 MB, `pnl_cold.py`) `PANDATA 2610 B at $ae4e0 intact: True` (RAM dump against the bank file).

## 4. Design
- **Art hook** (`sky2_pnl.s`, site `$8142`, `lea $2580(a2),a0 / lea $2580(a3),a1` -> `jsr`): after the first picture copy; if option bit 3 and V_ST = `$7f` and the block's magic and length are right it unpacks to `a3` (bounded: stops at `a3+9600`), checks the word sum, sets `V_PAN` (`SKYV+15`, an unused byte of the state block) and `V_KEY = -1`; any failure re-copies the ST art with the game's own loop `$8162`. All registers preserved (`pnl_art`, 286 B blob `$8ED80..$8EE9D` for the whole patch, window `sky2_`).
- **Palette** (`pnl_pal`, called from `sky_colours`): the 16 CMAP words scaled `gun*level*17/256` (rounded: level 15 is exact, unlike the fade's `>>4`), packed by the game's own `$67fc` (STE form with `pal_fade`), into `V_PPAL`; panel level as the lit panel (`sky_ptab` table 0,2,4,6,9,11,13 below landscape level 7, 15 from 7 up), so a fade to black fades the panel too.
- **Arming** (`sky_vbl.s`): in screen mode 3 with `V_PAN` the terminal interrupt (`sky_tbp`, line-synchronous, all 16 colours inside the horizontal blank at the end of row 139) runs on EVERY frame, also when the sky has no horizon (`V_H = 0`: no bands, `.build` skips them) and by day (the lit panel skipped the split by day). Outside mode 3 nothing is armed (first version armed in every mode and put the Amiga colours on the title picture: found by the Mega STE cold boot, fixed by `bra .out` after the mode test; control run below).
- Coexistence: sky bands and Timer B list unchanged (same slots); the lit-panel path is untouched (taken when bit 3 or `V_PAN` is off); triple buffering and the page tracking are not involved (V_H = 0 path does not read the slots); the text box and pointer are page pixels with the same indices, so they take the Amiga colours (orange pointer); 50/60 Hz by the line counting that already exists.
- Sizes: `sky_vbl` blob now `$8F100-$8F7F1` (window ends `$8F7FF`), `sky2_pnl` `$8ED80-$8EE9D`.
- Tool changes: `snd_build.py` (+ block), `huntpatch.py` (floppy build: the stage size depends on the bank's LSN/length, the old single second pass asserted; now iterates to a fixed point; `HUNT_PATCHDIR` env to build from another patch tree), `huntab.py --base-patches DIR`, `hunthz.py rate --pokes`, `huntvis_cold.py` TT: `--monitor vga --cpuclock 32`.

## 5. Gates [obs]
**Raster, rows 0-139 as `huntvis.py raster`, rows 140-199: every (row, colour index) one colour and equal to the Amiga colour at the panel level** (`pnl_gate.py raster`, snapshot + the install replayed by pokes, paused frame + 3 more screenshots): 7 scenes (day, dusk, night, sea, low, high, nohorizon = horizon > 139) x 3 option sets (`amiga` tint on, `amiga_notint`, `amiga_nosky` = no bands) x 50/60 Hz = **42 of 42 PASS**; fade levels poked to 3 and 9 PASS:
```
RASTER 50 Hz night      amiga        H= 50 level= 7 V_PAN=1 panel-split=yes panel indices [0, 1, 2, 3, 7, 8, 9, 10, 11, 12, 13, 14, 15] colour-15 changes after rows [19, 35, 43, 47, 49]: PASS
RASTER 60 Hz nohorizon  amiga_nosky  H=  0 level=15 V_PAN=1 panel-split=yes ... colour-15 changes after rows []: PASS
RASTER 50 Hz fade3      amiga        H= 50 level= 3 V_PAN=1 ...: PASS            (panel level 6)
PANEL RASTER ALL PASS
```
**Jitter** (`pnl_gate.py jitter`, walking, unpaused, 25 s fast-forward, Hatari `LineCycles` at the `movem.l d1-d7/a1,$ffff8240.w` of `sky_tbp`; all hits on ONE raster line = row 139's end; the write starts at cycle 412-436 of the line, blank = 376..568, 16 colours take ~76 cycles):
```
JITTER 50 Hz +DMA mixer: 11018 frames, LineCycles min 416 max 436; raster line {202: 11018}      50 Hz: 11983 frames, 416..436, {202: 11983}
JITTER 60 Hz +DMA mixer: 11491 frames, LineCycles min 412 max 432; raster line {173: 11491}      60 Hz: 12409 frames, 412..432, {173: 12409}
```
(2 looping voices injected as in `huntvis.py jitter`; 0 frames off the line.)
**Frames at 1 MB** `huntab_serial.py --base <v1.2 sky set, patches of build/v12/patches = the tree as HunterRelease froze it> --only <same + sky2_pnl, new sky_vbl> --flips 2 6 --lock --no-fps`: all 7 snapshots **IDENTICAL**, `ALL IDENTICAL`. Negative control (`--only pal_fade pal_load` against the sky base): `foot_stand: DIFFER {'b23000': 204}` / `MISMATCH`.
**World rate** `hunthz.py rate --snapshot foot_walk --hold up --secs 10`, v1.2 sky set against + `sky2_pnl` with the install pokes (u/s, 50 Hz 8/16 MHz, 60 Hz 8/16 MHz): v1.2 100.75 / 100.43 / 100.86 / 100.35, with panel 100.75 / 100.44 / 100.85 / 100.35; clock 50.000 / 50.000 / 50.011 / 49.987 and 50.000 / 50.000 / 50.015 / 49.987 ticks/s.
**Cost** `pnl_gate.py prof` (STE 8 MHz, game paused, interrupt work per VBL of 152,400): v1.2 day 24,786, **Amiga panel day 25,508 (+723 = +0.47 %)**; night 25,500 -> 25,509 (+9: the lit panel already split); `sky2_pnl` at 1 MB (bit 3 off) 24,786 -> 24,792 (**+6**); fill `$c84a` unchanged (-12). Install (once per mission start): about 10,000 cycles for the unpack + word sum [INFERENCE from the byte count, not profiled].
**Cold boots** (`pnl_cold.py`, marker `HNPO`, 3D view reached, day/night/dusk screenshots, 10 s of walking):
| Cell | memcntlr | cfg | SKY_ST | V_PAN | Result |
|---|---|---|---|---|---|
| HD STE 2 MB | `$08` | `0f` | `7f` | `ff` | on; PASS (3 runs) |
| HD STE 4 MB | `$0a` | `0f` | `7f` | `ff` | on; PASS |
| HD Mega STE 4 MB | `$0a` | `0f` | `7f` | `ff` | on; PASS |
| HD STE 1 MB | `$05` | `07` | `7f` | `00` | off = v1.2 lit panel; PASS |
| floppy STE 2 MB / 4 MB | `$08` / `$0a` | `0f` | `7f` | `ff` | on; PASS |
| floppy STE 1 MB | `$05` | `07` | `7f` | `00` | off; PASS (run with the first build: the arming bug needs `V_PAN`, so 1 MB is unaffected [INFERENCE]; not repeated) |
| HD TT 4 MB (`--mmu true --monitor vga --cpuclock 32`) | `$0a` | `07` | `ff` | `00` | **does not apply** (sky off on the TT: 68020 test) |
| floppy Falcon 4 MB | `$0a` | `07` | `ff` | `00` | does not apply |
Control for the arming bug: the build before the fix on HD Mega STE 4 MB reached `V_PAN=ff` at the title and showed the title in the Amiga colours (palette `080 133 356 e77 ...` at mode 0, `title2` crop mismatch, `fail_title2_*.png`); the old build there shows `000 00a 08b ... eee ccc bbb` and passes.
**Save and Load** (`pnl_save.py`, HD STE 2 MB, the sav_ patches): before the save, after it and after the load: `V_PAN=ff cfg=0x0f`, master `e000e000ffffffff` each time, position (40526, 10175) restored: `ROUNDTRIP+PANEL PASS`.
Not run: plain ST (TOS 1.04) 2 MB [the ST-form palette path is the game's `$67fc`], 2-disk floppy, real hardware; Save game with a **save made on an ST-art build loaded under the panel** [INFERENCE: the save holds no panel bitmap, section of `save.md` lists the RAM ranges].
**Other screens** (`pnl_screens.py`, snapshot + install): game options, drone map, log book and the main menus (mode 0) show the normal ST look; radar, clock, flare, overlay map, pause stay in the Amiga panel; the item table keeps the ST camouflage look.

## 6. Limits
- Hatari only. 2 MB or more only (the 1 MB machine keeps the exact v1.2 behaviour, +6 cycles/VBL).
- Icons drawn into the panel are the ST art in Amiga colours; the item table, STORES page and buttons are ST art/palette.
- Floppy: the bank file grows 2.6 KB; free space on the one-disk set 5,120 -> 3,072 B (`pnl_fl3`, 82x11).
- Needs `snd_build.py` re-run; without the block the feature stays off by itself (magic check).
