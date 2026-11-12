# Populous: the mouse pointer invisible in play on a TT (PopTTPtr, 2026-11-12)

User report: on the TT the pointer is visible in the menus, but after NEW GAME + typing a world name (and with START GAME: "about 1 frame in 5") it is gone once the map is in play.
Fix: `patches/pop_tt_ptr.s` + `patches/pop_tt_ptr2.s` (both `; default: yes`, `; machine: tt, falcon`; ST / STE / Mega STE untouched). Tags: observed = raw output quoted or in `work/gates/ttptr_*`; [INFERENCE] = not run.
Test scaffolding (not shipped): `work/scratch/ttptr/` (`ttp.py` boot, route, per-VBL sampler, buffer dumps + sprite search; `ttp2.py` full cell; `shotscan.py` screenshot counter; `run_ab.py`, `ste_*.py`). Hatari 2.6.1, TT = TOS 3.06 4 MB `--mmu true` VGA 32 MHz, Falcon = TOS 4.04 4 MB 16 MHz VGA (`mm.py` MACH table). Builds `build/PopTTPtr/{floppy_stock,floppy_def,floppy_fix,floppy_fix2,...}` (`poppatch.py build --floppy`): stock = no patches (payload only), def = the v1.0 default set (21 patches incl. `pp_*` HD-only ones not in a floppy), fix = def + `pop_tt_ptr`, fix2 = def + both.

## 1. Which build the user runs: the HD build does not run on a Hatari TT here
The task asked to check the HD image first. `AtariST_enhanced_games_2026-11-12.img` (autorun `C:\POPULOUS\RUNME.TOS` via DESKTOP.INF as `tools/test_hd_image.py` writes it), TT TOS 3.06, `--mmu true`, `--monitor vga`, with and without `--fast-boot`, 4 runs: PP's hardware screen, the cover picture, then after about 40 s Hatari shows `Detected double bus/address error => CPU halted!` (screenshot `work/shots/ttptr/x11_root.png`). `--trace cpu_exception` at that point:
```
Bus error writing at address $fffc3b PC=$3e3866.            (PP's RTC probe, caught)
Bus error reading at address $70004c PC=$7270004e.
cpu exception 2 currpc 7270004e ... newpc 23e24a2
Bus error writing at address $7340e5 PC=$3eab64.
```
= exactly the stock-PP crash of `machines.md` section 2 (HAGA's 68030 path, `D15RF.FIC`; unresolved, independent of our patches: the same on the stock image). So I could not run the HD build on a TT; every TT/Falcon number below is the floppy build (same game code, same payload, same relocation; the HD build carries the same `pop_tt_ptr*` blobs). If the user's HD image runs on his machine the fix applies there the same way [INFERENCE: not observed].

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
- **The mechanism is the same on both routes and in every flipping screen; START GAME and NEW GAME differ only in nothing I could find**: both give 0 frames in play on the TT (the user's "1 in 5" was not reproduced: on my Hatari TT def has a flip in every frame: 353 of 353). The Falcon shows it in 1/4 to 1/3 of the frames (stock 104/295, def 76/299), which is the "flickery" description. I have not seen anything that depends on the route: the pointer state after the name entry is the same (`$16d26` back to 0 on the world page after it: 75/75 visible; the pointer is hidden by the game itself during the name entry: `$16d26` = 1 at 143 of 180 VBL entries, 0 at 37, raw `Counter({'00 01': 143, '00 00': 37})` on def; so "gone after typing" is play, not the entry).
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

## 6. Raw gate output

### poptick.py ab --release with pop_tt_ptr + pop_tt_ptr2 in both runs (STE snapshots, live image: the TT/Falcon sites are not applied)
```
base test_pwalk pop_noprot pop_credit pop_land_mul pop_land_score pop_ptr pop_bgcopy pop_fal_ym pop_fal_ym_demo pop_ptrfix pop_keys pop_keys2 pop_keys3 pop_keys4 pop_tooltip pop_tt_ptr pop_tt_ptr2
patched +pop_tick pop_tick_render pop_tick_logic pop_tick_flip pop_tick_cmd pop_tick_dot
snapshot busy_castles turn 870, 130 turns, 8 MHz, 50 Hz
busy_castles @8 MHz 50 Hz: IDENTICAL | world at pass tops: 170 compared (0 differ) over 130 turns, max 2 tops/turn | T frames 128 compared (0 differ; 0 excluded) | R frames: 42 (0 stability pairs, 0 unstable; 31 minimap compares, 0 differ, 11 turns excluded (minimap cell redrawn by the world)) | pass kinds T 129 R 42 S 0 | turns/s base 6.006 patched 4.973
base test_pwalk pop_noprot pop_credit pop_land_mul pop_land_score pop_ptr pop_bgcopy pop_fal_ym pop_fal_ym_demo pop_ptrfix pop_keys pop_keys2 pop_keys3 pop_keys4 pop_tooltip pop_tt_ptr pop_tt_ptr2
patched +pop_tick pop_tick_render pop_tick_logic pop_tick_flip pop_tick_cmd pop_tick_dot
snapshot genesis_start turn 263, 130 turns, 16 MHz, 50 Hz, view still
genesis_start @16 MHz 50 Hz: IDENTICAL | world at pass tops: 556 compared (0 differ) over 130 turns, max 5 tops/turn | T frames 128 compared (0 differ; 0 excluded) | R frames: 432 (301 stability pairs, 0 unstable; 374 minimap compares, 0 differ, 16 turns excluded (minimap cell redrawn by the world); 428 render-only compares vs the original render, 0 differ) | pass kinds T 129 R 432 S 0 | turns/s base 20.156 patched 5.031
```

### popuitest.py gate --away (13 non-tick patches + pop_tt_ptr + pop_tt_ptr2), exit 0
```
script: 305 rows, rows on an icon: 0
== busy_castles: T0 870; reference run 305 flips, 610 samples
busy_castles         pop_noprot+pop_credit+pop_land_mul+pop_land_score+pop_ptr+pop_bgcopy+pop_fal_ym+pop_fal_ym_demo+pop_keys+pop_keys2+pop_keys3+pop_keys4+pop_tooltip+pop_tt_ptr+pop_tt_ptr2 IDENTICAL: flips compared 305 (both buffers + world each), mid-frame samples 610, bad flips 0, bad samples 0, world 0; samples in one run only: ref 0, new 0; excluded pre-script frames: 4 diffs ['252 bytes in 5 range(s), rows 2..6, first at row 2 byte 40', 'back(old frame + pointer) 252 bytes in 5 range(s), rows 2..6, first at 
== busy_quake_volcano: T0 2136; reference run 305 flips, 610 samples
busy_quake_volcano   pop_noprot+pop_credit+pop_land_mul+pop_land_score+pop_ptr+pop_bgcopy+pop_fal_ym+pop_fal_ym_demo+pop_keys+pop_keys2+pop_keys3+pop_keys4+pop_tooltip+pop_tt_ptr+pop_tt_ptr2 IDENTICAL: flips compared 305 (both buffers + world each), mid-frame samples 609, bad flips 0, bad samples 0, world 0; samples in one run only: ref 1, new 0; excluded pre-script frames: 4 diffs ['252 bytes in 5 range(s), rows 2..6, first at row 2 byte 40', 'back(old frame + pointer) 252 bytes in 5 range(s), rows 2..6, first at 
== genesis_start: T0 263; reference run 305 flips, 608 samples
genesis_start        pop_noprot+pop_credit+pop_land_mul+pop_land_score+pop_ptr+pop_bgcopy+pop_fal_ym+pop_fal_ym_demo+pop_keys+pop_keys2+pop_keys3+pop_keys4+pop_tooltip+pop_tt_ptr+pop_tt_ptr2 IDENTICAL: flips compared 305 (both buffers + world each), mid-frame samples 381, bad flips 0, bad samples 0, world 0; samples in one run only: ref 227, new 0; excluded pre-script frames: 4 diffs ['252 bytes in 5 range(s), rows 2..6, first at row 2 byte 40', 'back(old frame + pointer) 252 bytes in 5 range(s), rows 2..6, first a
GATE IDENTICAL (exit 0)
```

### Cold boots of the packaged default set (`tools/package.sh` output, `ttptr_package.txt`)
```
96c5a01874ccf8250f496c3a3b85ae4a  build/dist_hd/RUNME.TOS
4dc289a7f1ef169f8ba7360914e301a5  build/dist_hd/FILES/POLA
1074342dd4a917bafdc7d2a031e9b088  build/dist_hd/HAGA
8bfbb3ad2f4aad9ddc6e544e6f159f2d  build/dist_floppy/Populous_boot.st
af93f79a467c48583608189eaff5f9d3  build/dist_floppy/Populous_save.st
2e81eb2eb05dec64d4b608dfe1e205eb  dist/Populous_v1.0_patched_hd_2026-11-12.zip
ce3dbb64a52f2aa2a24e45dda86f6dbe  dist/Populous_v1.0_patched_floppy_2026-11-12.zip
```

```
--- ttptr_cold_ste_hd.txt
menu seen: True
payload header: 50 4f 50 50 50 4f 50 4f 00 00 00 03 01 00 00 00  D = 0
turn 63 -> 76; $b632 4ef9000ba000; tick marker 50 54 49 4b
$ff820a = $fe -> 50 Hz
RESULT cold ste gemdos dist_hd 8 MHz 50 Hz: 1501 VBL = 30.02 s, 160201 cycles/VBL (refresh seen 49.94 Hz), world turns 149 = 4.963/s | ticks 150 = 4.997/s; passes T 150 R 153 S 0 P 0
ERRORS {'Bus Error': 1, 'Address Error': 0, 'double bus': 0, 'CPU halted': 0} log /tmp/strun-il_a3i2i/log.txt
  ERRLINE WARN : Bus Error reading at address $ffff8e21, PC=$1789e addr_e3=1789e op_e3=1238
--- ttptr_cold_ste_floppy.txt
menu seen: True
payload header: 50 4f 50 50 50 4f 50 4f 00 00 00 02 01 01 00 00  D = 0
turn 19 -> 32; $b632 4ef9000ba000; tick marker 50 54 49 4b
$ff820a = $fe -> 50 Hz
RESULT cold ste floppy Populous_boot.st 8 MHz 50 Hz: 1501 VBL = 30.02 s, 160240 cycles/VBL (refresh seen 49.93 Hz), world turns 151 = 5.030/s | ticks 150 = 4.997/s; passes T 150 R 159 S 0 P 0
ERRORS {'Bus Error': 0, 'Address Error': 0, 'double bus': 0, 'CPU halted': 0} log /tmp/strun-3_tc_9vl/log.txt
--- ttptr_cold_tt_floppy.txt
menu after 16.0364887714386
start page after 38.47941732406616
payload header: 50 4f 50 50 50 4f 50 4f 00 00 00 02 01 02 01 00  D = 15958
turn 27 -> 40; $b632 4ef9000ba000; tick marker 50 54 49 4b
$ff820a = $01 -> 60 Hz
RESULT cold tt floppy Populous_boot.st default MHz 50 Hz: 1501 VBL = 30.02 s, 640760 cycles/VBL (refresh seen 49.94 Hz), world turns 150 = 4.997/s | ticks 150 = 4.997/s; passes T 150 R 1350 S 0 P 0
ERRORS {'Bus Error': 0, 'Address Error': 0, 'double bus': 0, 'CPU halted': 0} log /tmp/strun-agjn8hta/log.txt
--- ttptr_cold_falcon_floppy.txt
menu after 19.250630378723145
start page after 59.346673011779785
payload header: 50 4f 50 50 50 4f 50 4f 00 00 00 02 01 03 01 00  D = 21026
turn 26 -> 39; $b632 4ef9000ba000; tick marker 50 54 49 4b
$ff820a = $02 -> 50 Hz
RESULT cold falcon floppy Populous_boot.st default MHz 50 Hz: 2001 VBL = 40.02 s, 320472 cycles/VBL (refresh seen 49.93 Hz), world turns 200 = 4.998/s | ticks 200 = 4.998/s; passes T 200 R 1290 S 0 P 0
ERRORS {'Bus Error': 0, 'Address Error': 0, 'double bus': 0, 'CPU halted': 0} log /tmp/strun-n9d3aspt/log.txt
--- ttptr_ste_site.txt
in_play False marker b'POPO' $16f32: e04823c0ffff8200 (original e04823c0ffff8200) $16d66: 6c06427900016d264e75 (original 6c06427900016d264e75) blob $b8000: 4a7900016d266626
```
The STE HD cell's one Bus Error is PP's boot probe of `$ffff8e21` (`release.md` section 5); the HD build could not be booted on a TT / Falcon (section 1), the floppy builds were.
