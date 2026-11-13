# Populous: the mouse pointer invisible in play on a TT (PopTTPtr, 2026-11-12)

User report: on the TT the pointer is visible in the menus, but after NEW GAME + typing a world name (and with START GAME: "about 1 frame in 5") it is gone once the map is in play.
Fix: `patches/pop_tt_ptr.s` + `patches/pop_tt_ptr2.s` (both `; default: yes`, `; machine: tt, falcon`; ST / STE / Mega STE untouched). Tags: observed = raw output quoted or in `work/gates/ttptr_*`; [INFERENCE] = not run.
Test scaffolding (not shipped): `work/scratch/ttptr/` (`ttp.py` boot, route, per-VBL sampler, buffer dumps + sprite search; `ttp2.py` full cell; `shotscan.py` screenshot counter; `run_ab.py`, `ste_*.py`). Hatari 2.6.1, TT = TOS 3.06 4 MB `--mmu true` VGA 32 MHz, Falcon = TOS 4.04 4 MB 16 MHz VGA (`mm.py` MACH table). Builds `build/PopTTPtr/{floppy_stock,floppy_def,floppy_fix,floppy_fix2,...}` (`poppatch.py build --floppy`): stock = no patches (payload only), def = the v1.0 default set (21 patches incl. `pp_*` HD-only ones not in a floppy), fix = def + `pop_tt_ptr`, fix2 = def + both.

## 1. Which build the user runs: the HD build on a Hatari TT (corrected in section 6)
First attempt (harness, 4 runs, with and without `--fast-boot`, `--monitor vga`): the HD image with PP's runme started by a DESKTOP.INF `#Z` autorun line (as `tools/test_hd_image.py` writes it) dies after the cover picture with `Bus error reading at address $70004c PC=$7270004e` / "CPU halted" (`work/shots/ttptr/x11_root.png`), the stock-PP crash of `machines.md` section 2. **That crash belongs to the autorun-at-boot start, not to the TT**: with exactly `dist/run_tt.sh`'s flags and RUNME.TOS started by double-clicking it from the TOS desktop the HD build boots and plays (section 6). All floppy numbers in sections 2-6 are floppy builds; section 6 repeats the key ones on the HD image.

## 2. Reproduction (floppy, route = the user's)
Route in the harness (`ttp2.full_cell`): book menu CONQUEST -> world page -> **NEW GAME** (click) -> type `genesis` -> Return -> START GAME -> play; and the START GAME route. Metric (`ttp.measure`): a breakpoint at every entry of the VBL routine (`pc = $16d70 + D`, D = relocation delta read from the payload `$B3104`: TT 15958 = `$3E56`, Falcon 21026 = `$5222`) prints the video base (`$ff8201/03`), `$16f12` (address of the last pointer draw), `$3c50c`, `$3c510`, `info video`. The frame that just ended showed the buffer at the base (the flip writes the base right after the VBL routine); it showed the pointer iff `$16f12` lies inside that buffer. 

Raw first records of the stock NEW GAME route in play (TT, `ttp.py` output):
```
{'vbl': 4924, 'base': 340992, 'f12': 400232, 'c50c': 340992, 'c510': 372992}      base 0x53400, last draw 0x61AE8 = inside the OTHER buffer
{'vbl': 4925, 'base': 372992, 'f12': 368232, 'c50c': 372992, 'c510': 340992}      base 0x5B100, last draw 0x59E68 = inside 0x53400's buffer
```
Frames showing the pointer / frames, flips in brackets (`work/gates/ttptr_matrix.txt`; `stock` = no patches, `def` = v1.0 default set, `fix2` = def + pop_tt_ptr + pop_tt_ptr2):

| cell | world page | name entry (empty) | name entry (typed) | world page after name | play still (panel) | play moving (panel) | play, pointer over the map | GAME SETUP dialog | end-of-world dialog |
|---|---|---|---|---|---|---|---|---|---|
| TT stock NEW | 112/112 (0) | 0/180 (0) | 0/119 (0) | 75/75 (0) | **0/331 (331)** | **0/360 (360)** | 56/56 (0)* | 73/73 (0)* | 93/93 (0)* |
| TT stock START | 113/113 (0) | - | - | - | **0/360 (360)** | **0/361 (361)** | 55/55* | 75/75* | 95/95* |
| TT def NEW | 70/70 (0) | 0/131 (0) | 0/88 (0) | 47/47 (0) | **0/358 (358)** | **0/348 (348)** | 0/118 (118) | 0/89 (89) | 0/147 (147) |
| TT def START | 69/69 (0) | - | - | - | **0/353 (353)** | **0/323 (323)** | 0/116 (116) | 0/87 (87) | 0/138 (138) |
| TT fix2 NEW | 125/125 (0) | 114/172 (0) | 50/119 (0) | 88/88 (0) | **359/359 (359)** | **363/363 (363)** | 120/120 (120) | 107/107 (107) | 136/136 (0) |
| TT fix2 START | 127/127 (0) | - | - | - | **351/351 (351)** | **367/367 (367)** | 119/119 (119) | 119/119 (119) | 132/132 (0) |
| Falcon stock NEW | 87/87 (0) | 0/57 (0) | 0/61 (0) | 80/80 (0) | 104/295 (191) | 95/235 (140) | 99/99* | 99/99* | 149/149* |
| Falcon stock START | 150/150 (0) | - | - | - | 105/299 (194) | 123/301 (178) | 99/99* | 99/99* | 117/117* |
| Falcon def NEW | 149/149 (0) | 0/149 (0) | 0/100 (0) | 99/99 (0) | 75/299 (224) | 74/303 (229) | 22/93 (70) | 23/90 (67) | 149/149 (0)** |
| Falcon def START | 149/149 (0) | - | - | - | 76/299 (223) | 73/299 (226) | 22/92 (69) | 22/92 (70) | 140/140 (0)** |
| Falcon fix2 NEW | 149/149 (0) | 94/149 (0) | 32/99 (0) | 99/99 (0) | **298/298 (220)** | **305/305 (228)** | 99/99 (72) | 99/99 (74) | 149/149 (0)** |
| Falcon fix2 START | 149/149 (0) | - | - | - | **300/300 (222)** | **306/306 (229)** | 98/99 (72) | 99/99 (74) | 149/149 (0)** |

\* the stock game (no tick, 78 turns/s on a TT) loses its empty Genesis world within about 25 s emulated, so these three phases are the GAME LOST dialog (no flips: the dialog code does not flip, the pointer is drawn by the VBL routine as on an STE); they are not "setup / end" of a long game.
\** the "end-of-world" phase of the def / fix2 cells is the GAME LOST dialog reached by fast-forward until the turn word stops. Whether the tick's render-only passes still flip behind a dialog differs from cell to cell (TT def: 147 flips, pointer in 0 frames; TT first fix build: 177 flips, 179/179 visible; TT fix2: 0 flips, 136/136; the GAME SETUP dialog on the TT def / fix2: flips every frame, 0/89 before, 107/107 after). With flips the dialog behaves like play; without, like an STE.
- **The mechanism is the same on both routes and in every flipping screen; START GAME and NEW GAME differ only in nothing I could find**: both give 0 frames in play on the TT (the user's "1 in 5" is the HD build, section 7: 85 of 359 frames; on the floppy TT def has a flip in every frame: 353 of 353). The Falcon shows it in 1/4 to 1/3 of the frames (stock 104/295, def 76/299), which is the "flickery" description. I have not seen anything that depends on the route: the pointer state after the name entry is the same (`$16d26` back to 0 on the world page after it: 75/75 visible; the pointer is hidden by the game itself during the name entry: `$16d26` = 1 at 143 of 180 VBL entries, 0 at 37, raw `Counter({'00 01': 143, '00 00': 37})` on def; so "gone after typing" is play, not the entry).
- `pop_ptr` skip and `pop_ptrfix`: stock vs def make no difference on the TT (0/331 vs 0/358). pop_ptr's skip never fires in play on a TT (a flip every frame changes `$3c50c`: its first test); it is not part of the cause. `pop_ptrfix` is the IKBD packet filter, no video access.

## 3. Mechanism (listing lines)
```
016d70  movem.l d0-d7/a0-a6,-(a7)     VBL routine (TOS VBL queue; pop_ptr's site is 016d80)
016d78  tst.w $16d26.l / 016d7e bne.b $16d88          hide count
016d80  bsr.w $16dea                  restore the saved 16 rows at [$16f12]
016d84  bsr.w $16e20                  draw: address = [$3c50c] + y*160 + (x&~15)/2  -> $16f12; save to $2478c
016dd6  move.w #$1,$16d28.l           flag "VBL happened"
016f16  bsr.w $16f48                  wait for $16d28 != 0
016f1a  move.l $3c510.l,d0 / 016f20 move.l $3c50c.l,d1 / 016f26 move.l d1,$3c510.l / 016f2c move.l d0,$3c50c.l    swap
016f32  lsr.w #$8,d0 / 016f34 move.l d0,$ffff8200.l   new base            016f3a clr.w $16d28.l
```
`--xref ffff8200`: `016f34` is the only video base write; `--callers 16f16`: `00b5fa`, `00b940` (main loop), `01249c`, `01d630`. An ST / STE latches `$ff8201/03` at the next frame start, so the buffer the VBL routine drew into is the one shown in that frame; Hatari's TT / Falcon video follows the register at once. Raw event trace, def + pop_tt_ptr (first version of the fix; breakpoints at VBL entry, at the blob, at `016f34`; `ev` parse):
```
VBL   4626 hbl 0 base 0x53400 f12 0x59888 c50c 0x53400
HOOK  4626 hbl 3 base 0x53400 f12 0x59888 c50c 0x53400        (the blob: restore + draw into 0x5b100)
BASEW 4626 hbl 5 base 0x53400 f12 0x61588 c50c 0x5b100        (before the base write: last draw is now in the NEW buffer)
VBL   4627 hbl 0 base 0x5b100 f12 0x61588 c50c 0x5b100
```
Without the fix the draw at `VBL` goes into the buffer that the flip, 5 scan lines later, takes off the screen. Everything is the same bug as Powermonger `tt_ptr` (`games/done/powermonger/REPORT.md` section 13) and Midwinter 2 `p8_tt_ptr`.
Second cause (found when the first fix still showed no arrow over the map): the hover marker over the map hides the pointer in every pass (`$11c9e jsr $16d2e` ... `$11cc6 jsr $16d5e`, measured: `Counter({'0x11ca4': 90})` hide calls from `$11ca4` in 1.5 s with the pointer over the map, none over the book/panel), the hide (`016d2e`) restores the saved image into `[$16f12]` and clears it, the show (`016d5e`) draws nothing. On an STE the next VBL (within the 5-6 VBL pass) draws the arrow again: arrow + cross over the map (`work/shots/ttptr/ste_map.png`; `ttptr_ste_map.txt`: `map VBL entries 251 with a drawn pointer (f12 != 0): 211`); on a TT with a pass per frame the show is followed by a flip, so the arrow was never in the shown buffer over the map (0/118 with pop_tt_ptr alone).

## 4. The fix
* `pop_tt_ptr` (site `$16f32`, the base write; 8 bytes -> `jsr $b8000` + `nop`; blob `$b8000-$b8037`): unless `$16d26` != 0, with `ori.w #$0400,sr` kept to the end: `jsr $16dea` (restore into the buffer being left), `jsr $16e20` (draw into `$3c50c` = the buffer about to be shown; records `$16f12` etc.), then the displaced `lsr.w #8,d0 / move.l d0,$ffff8200.l`, then the old SR. First version put the site on the swap (`$16f2c`, before the base write): a VBL due during the 12 k-cycle draw then ran between draw and write, Falcon: 6 frames of ~300 without a pointer (`NOVIS at vbl 5853 ... base 0x54800 f12 0x62c40 c50c 0x5c500`, 293-295/299 in three runs); with the write inside the masked window 299/299 four runs in a row.
* `pop_tt_ptr2` (site `$16d66`, the tail of the show, 10 bytes -> `jmp $b8040`; blob `$b8040-$b806d`): the displaced `bge/clr` clamp, then if the count is 0 the same masked restore + draw. A nested show (count > 0) and the name entry's own hide (count 1) draw nothing. `$16dea` is a no-op after the outermost hide (`$16f12` = 0), and removes the old image after an unbalanced show, so no second pointer.
* Both use only the game's own routines, hence the same draws as the VBL routine; the next VBL routine restores/redraws in the same buffer. Cost on a TT: two extra 12 k-cycle draws per pass at most (0.4 ms of a 16.7 ms frame at 32 MHz).
* **ST / STE / Mega STE**: `; machine: tt, falcon` = the sites are neither verified nor applied there. STE cold boot of the packaged HD build, `$16f32` = original, marker `POPO` (`work/gates/ttptr_ste_site.txt`: `$16f32: e04823c0ffff8200 (original e04823c0ffff8200)`).
* pop_ptr interplay: its skip compares `$16f12`, `$3c50c`, the rectangle on screen and the shape with what its own last draw left; a draw by the blobs either changes `$16f12` / `$3c50c` (mismatch -> original path) or, at the same address, leaves exactly merge(`$2478c`, shape) on screen, which is what the skip condition certifies [INFERENCE by reading pop_ptr.s; no pixel gate drives it on a TT; the TT runs with both patches show 1 pointer/0 stale in all samples below].
* Open / by design: during the name entry the game's own text-field redraw hides the pointer in most passes (`$16d26` = 1 at 143 of 180 VBL entries even in the stock game), so the pointer shows in about half the frames there with the fix (114/172, 94/149 Falcon), in none without it. Over the map the arrow is hidden between the hover marker's hide and show (a VBL entry can fall in that window: Falcon 98/99 once).

## 5. Gates (all with the fixed floppy builds unless marked)
1. **Statistics**: the table in section 2 (raw: `work/gates/ttptr_matrix.txt`, `ttptr_<cell>.json`, per-cell prints). TT play, panel, still/moving: 0 of 331..360 before, 351..367 of 351..367 after, on both routes; Falcon 74..76 of ~300 before, 298..306 of 298..306 after.
2. **Pixel check, no double pointer** (`ttp.sample_dump`: once-breakpoints at the VBL entry dump both 32,000-byte buffers; the 16x16 pointer shapes 0-6 are searched pixel-exactly over the whole picture): displayed buffer holds exactly 1 pointer at the position of `$24786/8` and the other buffer none, in 6 of 6 samples at each of five areas (book, left panel, right panel, minimap, map) with the pointer still, and 14 of 14 with the pointer moving (7..10 distinct positions), on TT and Falcon, both routes (all in `ttptr_matrix.txt`; 120 more moving samples on the Falcon: `120 of 120 other (non-7): 0`). Before (def): `pixel_still ... shown1 0, shown0 6` at every area on the TT. Shape 7 is not counted: it matches static art of the dialogs (`(7, 216, 128..140)` in the GAME LOST dialog; also found in unpatched runs).
3. **Screenshots over 34 s in play, still and moving** (`ttp2.shots_run`: NEW GAME route, 26 screenshots at 0.8 s for each; counted by `shotscan.py`, the pointer sprite found pixel-exactly with the palette learnt from the fixed screenshots; `ttptr_shots_counts.json`): TT before 0/26 still, 0/26 moving; after 26/26, 26/26. Falcon before 6/26, 7/26; after 26/26, 26/26. Sheets: `work/shots/ttptr/BEFORE_AFTER_{tt,falcon}_{still,moving}.png` (top = v1.0 default set, bottom = fixed), the individual frames in `work/shots/ttptr/sh_*/`.
4. **STE gates** (pop_tt_ptr + pop_tt_ptr2 are in the sets; the live image drops their sites): `poptick.py ab busy_castles 8 130 --release` and `genesis_start 16 130 --still --render --release` (via `work/scratch/ttptr/run_ab.py`), `popuitest.py gate --away`: `work/gates/ttptr_ab_busy_castles_8.txt`, `ttptr_ab_genesis_16.txt`, `ttptr_gate_away.txt` (pasted in section 6).
5. **Cold boots of the packaged default set** (`work/scratch/poptick/cell.py`; `ttptr_cold_*.txt`; section 6).
6. `poppatch.py verify`: ALL OK; `tools/package.sh`: section 6.

## 6. The HD build under exactly `dist/run_tt.sh`'s flags (second round, after the lead's report)
Launcher `work/scratch/ttptr/rawtt.py`: `hatari --machine tt --tos TOS_3_06_uk.img --memsize 4096 --cpuclock 32 --monitor vga --mmu true --gemdos-drive skip --acsi 0=<image> --confirm-quit no` + only `--cmd-fifo/--screenshot-dir`; no `--harddrive`, `--fast-boot`, `--sound off` (sound is dummy via SDL), `--grab` is switched on after the desktop with `hatari-shortcut mousegrab` (the host mouse is absolute on the desktop, relative in the game). Image `dist/AtariST_enhanced_games_2026-11-12.img` md5 `79ff7d1a870ee8d5ae64dd8287dfa265` (rebuilt by the lead with pop_tt_ptr + pop_tt_ptr2), unmodified, no DESKTOP.INF: desktop -> C: -> POPULOUS -> RUNME.TOS (double-click).
* It boots: HW screen, cover, credits, book menu (about 65 s), CONQUEST, world page, play. The screenshots `raw_run_*.png`.
* **But the fix was not applied on it.** Payload header on the HD TT: `50 4f 50 50 50 4f 50 4f 00 00 00 03 01 00 00 00`: marker `POPO`, `D = 0` (the HD loader puts the text at `$AD96` also on the TT), and MACHV = `01 00 00 00`: machine class 0, CPU class 0. `core.s` read `_MCH` / `_CPU` from the cookie jar `$5a0`, which on a TT booted through PP's HAGA is not TOS's (HAGA remaps low RAM with the PMMU: the Midwinter notes said so; no jar found), so every `; machine: tt, falcon` site was skipped (and the cache flush, which needs CPU class >= 1, was skipped too). Raw, same image, user's route, `ttptr_hdimg_tt_*.json`:
  `play, pointer in the left panel, still: {'frames': 359, 'visible': 85, 'flips': 274}`, moving `85/360`, over the map `43/179`, GAME SETUP `42/180`; pixel check still `book 3/6, panel 0/6, right 2/6, minimap 1/6`, moving `7/14`. Screenshots 26 over 34 s: still 8/26, moving 6/26 (before; `ttptr_hd_shots_counts.json`). That is "visible about 1 frame in 4-5": the user's description. [INFERENCE: the user's earlier test predated an image with the fix, or ran with a jar; the lead reports the latest image looks good on his TT - I could not reproduce that on image 79ff7d1a.]
* **Fix** (`patches/core.s` probe, `$B3E00`): the CPU class is now found without the jar (the index-register scale test of `cpulib.s cl_detect`, no exception), refined by `_CPU` when a jar exists; when no `_MCH` cookie is found on a 68020+ the machine class is 4 = "TT or Falcon" (`sel`: mask & $0c), so the TT sites apply, and the cache flush runs. A 68000 without a jar stays class 0, an STE/ST untouched (MACHV +3 = 1 when `_MCH` was found, +1 = 4 only for 68020+ without it). Nothing else changed; STE HD cold boot: `MACHV 01000000` as before.
* Result (HD image with RUNME.TOS, HAGA, FILES\POLA of `poppatch build --hd` replaced by mcopy in a scratch copy; payload header `... 03 01 04 01 00` = class 4, CPU 1): NEW route `play still 359/359 (270 flips)`, moving `360/360`, over the map `177/179`, GAME SETUP `180/180`; pixel check still 6/6 at all five areas, moving 14/14; START route `359/359`, `361/361`, map `177/180`, setup `179/179`, pixel 6/6 x5, moving 14/14 (`ttptr_hdcls_tt_{new,start}.json`). Screenshots 26 over 34 s: still 25/26, moving 25/26 (the one missing shot each is a frame caught inside the VBL routine's own restore-redraw window: 1 of 26 = the 0.4 ms it takes of a 16.7 ms frame, the same as the original on an STE).
* Floppy under the same flags (`rawtt.py` with `--disk-a`; header `... 02 01 02 01 01` = class 2, jar found): NEW route play still 360/360, moving 365/365, map 179/179, setup 179/179, pixel 6/6 x5 + moving 14/14; START route 359/359, 352/352, map 179/179, setup 179/179, pixel 6/6 x5, moving 14/14 (`ttptr_flraw_tt_{new,start}.json`).
* Falcon: HD cannot be mounted by Hatari's Falcon (`machines.md` section 3); the floppy has the jar, class 3 as before.

## 8. Raw gate output (STE gates were run before the `core.s` probe change; the live gate images do not contain core.s, so they are unaffected: `ttptr_ab_*.txt`, `ttptr_gate_away.txt`, all IDENTICAL, exit 0; the cold boots below are after it)

### Cold boots of the packaged default set (after the probe change)
```
836c09262432c43e61038ae256dc5e22  build/dist_hd/RUNME.TOS
4dc289a7f1ef169f8ba7360914e301a5  build/dist_hd/FILES/POLA
1074342dd4a917bafdc7d2a031e9b088  build/dist_hd/HAGA
52e56037b35932eecefe829570739a5e  build/dist_floppy/Populous_boot.st
af93f79a467c48583608189eaff5f9d3  build/dist_floppy/Populous_save.st
31c9089dccedb11eb0893fa511ebc2a2  dist/Populous_v1.0_patched_hd_2026-11-12.zip
3ec81a3397ecdc5f36e97d2bd401cdac  dist/Populous_v1.0_patched_floppy_2026-11-12.zip
```
```
--- ttptr_cold_ste_hd.txt
menu seen: True
payload header: 50 4f 50 50 50 4f 50 4f 00 00 00 03 01 00 00 00  D = 0
turn 63 -> 76; $b632 4ef9000ba000; tick marker 50 54 49 4b
$ff820a = $fe -> 50 Hz
RESULT cold ste gemdos dist_hd 8 MHz 50 Hz: 1501 VBL = 30.02 s, 160216 cycles/VBL (refresh seen 49.93 Hz), world turns 150 = 4.997/s | ticks 150 = 4.997/s; passes T 150 R 154 S 0 P 0
ERRORS {'Bus Error': 1, 'Address Error': 0, 'double bus': 0, 'CPU halted': 0} log /tmp/strun-7_cmzh_p/log.txt
  ERRLINE WARN : Bus Error reading at address $ffff8e21, PC=$17912 addr_e3=17912 op_e3=1238
--- ttptr_cold_ste_floppy.txt
menu seen: True
payload header: 50 4f 50 50 50 4f 50 4f 00 00 00 02 01 01 00 01  D = 0 core2: 48 7a 00 0c 3f 3c 00 26 4e 4e 5c 8f 4e 75 13 fc
turn 22 -> 35; $b632 4ef9000ba000; tick marker 50 54 49 4b
$ff820a = $fe -> 50 Hz
RESULT cold ste floppy Populous_boot.st 8 MHz 50 Hz: 1501 VBL = 30.02 s, 160248 cycles/VBL (refresh seen 49.92 Hz), world turns 150 = 4.997/s | ticks 150 = 4.997/s; passes T 150 R 158 S 0 P 0
ERRORS {'Bus Error': 0, 'Address Error': 0, 'double bus': 0, 'CPU halted': 0} log /tmp/strun-u11jqhw5/log.txt
--- ttptr_cold_tt_floppy.txt
menu after 16.03514266014099
start page after 38.4794819355011
payload header: 50 4f 50 50 50 4f 50 4f 00 00 00 02 01 02 01 01  D = 15958
turn 29 -> 41; $b632 4ef9000ba000; tick marker 50 54 49 4b
$ff820a = $01 -> 60 Hz
RESULT cold tt floppy Populous_boot.st default MHz 50 Hz: 1501 VBL = 30.02 s, 640855 cycles/VBL (refresh seen 49.93 Hz), world turns 150 = 4.997/s | ticks 150 = 4.997/s; passes T 150 R 1350 S 0 P 0
ERRORS {'Bus Error': 0, 'Address Error': 0, 'double bus': 0, 'CPU halted': 0} log /tmp/strun-33dmq_u4/log.txt
--- ttptr_cold_falcon_floppy.txt
menu after 19.250396490097046
start page after 60.95296621322632
payload header: 50 4f 50 50 50 4f 50 4f 00 00 00 02 01 03 01 01  D = 21026
turn 27 -> 40; $b632 4ef9000ba000; tick marker 50 54 49 4b
$ff820a = $02 -> 50 Hz
RESULT cold falcon floppy Populous_boot.st default MHz 50 Hz: 2001 VBL = 40.02 s, 320490 cycles/VBL (refresh seen 49.92 Hz), world turns 200 = 4.998/s | ticks 200 = 4.998/s; passes T 200 R 1291 S 0 P 0
ERRORS {'Bus Error': 0, 'Address Error': 0, 'double bus': 0, 'CPU halted': 0} log /tmp/strun-62064ue4/log.txt
--- ttptr_ste_site.txt
in_play False marker b'POPO' $16f32: e04823c0ffff8200 (original e04823c0ffff8200) $16d66: 6c06427900016d264e75 (original 6c06427900016d264e75) blob $b8000: 4a7900016d266626
```
STE HD: `MACHV 01000000` (no jar through HAGA, 68000: class 0 as before); STE floppy header `... 01 01 00 01` (class 1, jar found); TT floppy `... 01 02 01 01`; Falcon floppy `... 01 03 01 01`. One earlier STE floppy run showed `01 01 00 00` (class 1 with the found flag 0) which I could not explain and did not see in two reruns.
The STE HD cell's one Bus Error is PP's boot probe of `$ffff8e21` (`release.md` section 5).
