# Stage 3 results (PMWW1Stage03, 2026-11-23): hover tooltips that look and read like master's

Evidence contract: **[obs]** = raw lines from a file named here; **[INFERENCE]** = reasoning only; failures are listed as failures.
Hatari 2.6.1, private HOME per run, work dirs `/tmp/pmww1s3/*`, one Hatari at a time. Gate logs: `work/runs/s3_*.txt`. Tools: `tools/wwtt.py` (reference renderer, wording check, live pixel gate, sheet),
`tools/stage03_gates.sh` (the whole chain). Patch: `patches/pm_tooltip.s` (+ `patches/qol_keys.s`: 4 bytes of data and one `move.w #1,KF` added).

## 1. What was ported and what was verified for WW1 (nothing was taken on trust from master or from the DeepSeek branch)
Master's `pm_tooltip` (own glyph composer, background colour 1 -> 0, one-table wording with 1/3 effect strings, key labels, 32 ids, back-buffer-after-copy erase) is ported 1:1 in structure; every address was re-derived:

| item | master | WW1 | how checked [obs] |
|---|---|---|---|
| site | `$130a4 jsr $178ae` | `$13e18 jsr $18570` | loop pass `$13e04 jsr $e04 / $13e0a jsr $13a94 (window copy) / $13e10 tst.w $5a856 / bne $13e3c / $13e18 jsr $18570`, disassembly of the map-view RAM dump with `tools/m68dis.py`; the 6 bytes are the site's verified original (`4eb900018570`) |
| back buffer | `[$2df7c]` | `[$2ed9c]` | `$13dd2 movea.l $2ed9c,a1` is the destination of the `$13a94` copy |
| pointer | `$2df92/4` | `$2edb2/4` | `$13e92 movem.w $2edb2,d0-d1` (the click code), stage 2 |
| window open | `$7a36` | `$74c0` | stage 2 (`WINDOW_OPEN`) |
| line tables, cell table, rect table | `$12e6a $12ee4 $19bde $13250` | `$13bde $13c58 $1a89a $13fc4` | byte compare in the map-view RAM dump: rects 32 B, lines 122 B / 114 B, cell table 50 B all **identical to master's bytes** |
| posture word | `[$51538 + [$57fd2] + $3c]` | `[$5574e + [$5a834] + $3c]` | map-view dump: `$5a834 = 416`, word at `$5592a` = 3 (default neutral); real clicks on the posture icons set 4 / 3 / 2 (gate line `posture click`) ; the shift function `$30fe` of master exists at `$259e` (`48e70010 47f9 0005574e d6e9002a 302b003c 04400002`, 11 callers) |
| font | `$8976` | `$8406` | 1524 of 1536 bytes identical to master's, the 12 that differ are in glyph block 31 (characters 124..127, unused); glyph colours 1..5, colour 1 = background, as in master |
| palette | | | read from the shifter: colour 0 black, 1 `(68,68,34)`, 2..5 `(102,102,68) (136,136,102) (170,170,136) (204,204,170)` [obs `work/runs/s3_tt_ste.txt` line "palette"] |

WW1 names (the game's own strings, RAM dump): the job list reads `Waiting / Get Food / Get Men / Meeting / Going To / In Camp / Go Home / Attack / **Build** / Equip / Pickup / Supply / Fighting / Alliance / Trading / Spying`
(master: `Invent`), the item table (`$9cd0`, same layout as master's `$a242`, 9 words + strings) is `a bayonet, a pike, a sword, a rifle, a plough, a boat, a pot, a plane, a tank`
(master: Nothing, Pike, Sword, Bow, Plough, Boat, Pot, Catapult, Cannon: bow -> rifle, catapult -> plane, cannon -> tank), the captain panel says `Rations` / `Stores` / `Troops` (master: Food / Stock), the settlement list `towns`.
The command icons are the same 20 ids (the cell table is identical, the 24 jump-table handlers have the same instruction sequences, stage 2); the 3 posture icons show 1, 2 and 3 swords (screenshot crop, `/tmp/pmww1s3/left_grid_ww1.png`).
Wording changes against master: `Invent` -> `Build`; `rifles, planes; iron: swords, tanks` (aggressive Build) and `tanks, planes first` (aggressive Trade); `food` -> `rations` in the Get/Drop/Supply Food effects,
`stock` -> `stores` in Drop Items, `village` -> `town`, `settlement` -> `town` (Spy, map icon 3 `town rations`, map icon 2 `towns and roads`). Everything else is master's text, same 52-character limit, same key labels.
[INFERENCE] The amounts per posture (25 / 50 / 100 %, Trade / Build priorities) are master's traced rules; WW1 runs the same code (same shift function, same handlers), but the WW1 numbers were not re-traced.
Not ported here (stage 4, as in `PLAN.md`): the village hover (`qol_hover` / `qol_hover2`); `pm_tooltip` keeps master's export jump table (`$73400 hook, $73406 compose_sb, $7340c blit`) and the liveness word `'PTIP'` at `$7480e` for it.

## 2. Layout, bytes used of `$72000-$77FFF` (22.5 KB payload area; build `build/default`)
| span | what | bytes |
|---|---|---:|
| `$73400-$73845` | pm_tooltip code (hook, hit test, wording composer, glyph composer, blit; 1094 B) | 1094 |
| `$74000-$7473b` | pm_tooltip wording table (33 words + strings, 1852 B) | 1852 |
| `$74800-$74adf` | pm_tooltip state (`; data:` zero span; BUF 624 B, SB 64 B, words) | 736 |
| `$730c8` | KF word inside qol_keys' data block (block `$73000` grew from 200 to 204 B) | +4 |
Stage-2 payload 1954 B; with the tooltip **5656 B of 24576 B (23.0 %)**, 18920 B left (`$74ae0-$77fff` and the gaps). The record stream on the floppy grew from 3572 B (core + credit + tooltip only) / the stage-2 size by the 2946 non-zero bytes; WW1.PRG 81133 B, 31744 B free on the disk.

## 3. Design points that differ from master
* The key-label flag lives in qol_keys' own data block (`KF = $730c8`, written by qol_keys' hook every pass, read by the tooltip) instead of a word inside the tooltip's block that qol_keys writes: a build without qol_keys never writes to the payload area outside its own blocks, and the tooltip then shows no labels (gate: `key labels flag follows qol_keys`; the `tt_nokeys` build).
* No other behavioural change: the hook is entered by `jsr`, leaves by `jmp $18570` (tail call, no stack fixup needed), saves and restores d0-d7/a0-a6 (gate line `registers and stack pointer preserved`).

## 4. The tooltip gate (`tools/wwtt.py gate`, real pixels; every line `GATE <tag> <name> PASS|FAIL <evidence>`)
Reference: `tools/wwtt.py` composes the expected line in Python from the font of the FILE-derived resident image (`wwpatch.resident_image()`, glyph block 48 B at `$8406 + 48*(ch>>2)`, column `ch&3`, colour 1 -> 0, planar 4 bpp = 6 rows x 104 B) and the wording table parsed from `patches/pm_tooltip.s`; the machine's font is first compared with the same image (`font in RAM == the file-derived resident image PASS 0 bytes differ`).
For each probe (cold boot of the BUILT floppy, pointer moved with the game's own pointer words, posture set by real clicks on the posture icons):
1. hit test: the machine's hover id / key (`$74804 / $74806`) == the id the Python hit test gives for the pointer the machine really has (`wwgrid` = the game's own tables);
2. one-shot breakpoints at the hook's entry `$73400` and exit `$18570` dump BOTH screen buffers and the registers: exactly one buffer changes, every changed byte is inside rows 0-5 / byte 56..159, the bar was black before the hook, the region after the hook equals the reference byte for byte (624 B), d0-d7/a0-a6/a7 are preserved;
3. the displayed buffer (shifter base read at the exit breakpoint) holds the same 624 B;
4. a Hatari screenshot of the line (palette read from the shifter; `$ff8240`) equals the reference pixel for pixel (1248 ST pixels, 2x2 host blocks uniform) and no pixel in the area has a colour other than black or the text's own colours (this is what a khaki box or junk pixels would break).
Raw lines (`work/runs/s3_tt_ste.txt`, STE TOS 1.62 1 MB, default build, neutral posture, Get Food):
```
GATE tt_ste id  3 Get Food level 2 swords hover state PASS pointer (202,181) id 3 want 3, KEY $10d want $10d (posture word 3, level 1, keys True)
GATE tt_ste id  3 Get Food level 2 swords footprint PASS 242 bytes changed, 0 outside rows 0-5 / byte 56..159
GATE tt_ste id  3 Get Food level 2 swords the line was composed on a clean bar PASS region before the hook is all colour 0
GATE tt_ste id  3 Get Food level 2 swords pixels == reference rendering PASS text "Get Food (F): take 50% of a town's rations": 0 of 624 bytes differ
GATE tt_ste id  3 Get Food level 2 swords registers and stack pointer preserved PASS differences {}
GATE tt_ste id  3 Get Food level 2 swords displayed buffer pixels == reference PASS base $25200, 0 bytes differ
GATE tt_ste id  3 Get Food level 2 swords screenshot == reference (colours of the machine's palette) PASS 0 of 1248 pixels differ, 2x2 blocks uniform True
GATE tt_ste id  3 Get Food level 2 swords no stray colours (khaki box, junk) in the line area PASS 0 pixels outside black + the text's own colours
```
Coverage of the full run (`TOOLTIP GATE tt_ste: 584 lines PASS, 0 FAIL`): all 29 ids with a text at the neutral posture; the 11 posture-dependent ids (2 3 4 6 7 8 9 10 12 13 14) also at 3 swords (posture word 2) and 1 sword (word 4), the word set by REAL clicks on the posture icons (`posture click (97,157) sets the captain's posture word PASS word 2 want 2`, same for 3 and 4) = 58 full pixel probes; erase (`erase after id 3 -> (150,100)`: no hook write, both buffers' region black, screenshot black); a long -> short text sequence (Attack, Go Home, Get Food, Send Captain, Map): each line equals the reference over the whole 624 B, so no residue of a longer previous text; a LIVE posture change while the pointer rests on Get Food (word 4 / 2 / 3 -> key `$10c / $10e / $10d` within 20 s); an open Option window suppresses the map-icon tooltip (`$74c0 = 0x17c`, hover id 0, hook writes nothing; the point is `(24,2)`); 50 hit-test samples (first and last pixel of the 20 grid cells + 10 points outside every zone: overview map, 3D view, top bar right of x 64, between the zones): `hit ... PASS` 50 of 50.
Key labels (`wwtt.py check`, no Hatari): 29 ids x 3 postures x with/without labels <= 52 characters (longest 51: `Passive (1 sword) (1): takes a quarter, spares most`), the ET word table matches the entries, and the labels of every entry equal the keys qol_keys' own table KT maps to that icon, computed through the game's hit test: `WORDING 29 ids, 203 checks ..., 0 problems`. The default build shows `Get Food (F): ...`, `Rotate left ([): 90 deg; right-click/Shift+[: fine` (keys-only variant); the build WITHOUT qol_keys (`build/tt_nokeys`, KF = 0) shows `Get Food: take 50% of a town's rations` and `Rotate left: click 90 deg, right-click fine` (`work/runs/s3_tt_nokeys_ste.txt`: `key labels flag follows qol_keys PASS KF = 0`).
Other machines, reduced run (`--quick`: Get Food / Attack / Map / Rotate left / Compass at the neutral posture, erase, live level change, window rule): `tt_nokeys_ste` 116 lines PASS 0 FAIL, `tt_megaste` (Mega STE TOS 2.06 4 MB, 60 Hz) 116 PASS 0 FAIL, `tt_st` (ST TOS 1.04 1 MB) 116 PASS 0 FAIL.
**Negative control** (`work/runs/s3_tt_negative_control.txt`): the same patch with the 4 background-mapping instructions replaced by `nop` (what the DeepSeek branch's composer effectively did: the khaki glyph background stays) is built (`WW_PATCHDIR` copy) and run through the quick gate:
```
GATE tt_neg id  3 Get Food level 2 swords pixels == reference rendering FAIL text "Get Food: take 50% of a town's rations": 120 of 624 bytes differ
GATE tt_neg id  3 Get Food level 2 swords screenshot == reference (colours of the machine's palette) FAIL 679 of 1248 pixels differ, 2x2 blocks uniform True
GATE tt_neg id  3 Get Food level 2 swords no stray colours (khaki box, junk) in the line area FAIL 679 pixels outside black + the text's own colours
TOOLTIP GATE tt_neg: 76 lines PASS, 40 FAIL
```
(the 76 PASS are the hit test, hook footprint, registers, state lines that this defect does not touch.)
Screenshots (git-ignored `*.png`, in `work/shots/stage03/`): `sheet_ww1_vs_master.png` (4 pairs, master's own with-key-labels screenshots above the WW1 ones: Get Food 2 swords, Invent / Build 3 swords, Rotate left, Compass; master's rotate-left shot predates its keys-only wording), `tt_ste_id{3,6,2,14,7}_lv{0,1,2}.png` (full screenshots: icon x posture), `tt_ste_id28_lv1.png`, `tt_ste_id30_lv1.png`, `tt_ste_id32_lv1.png`, `tt_ste_erase.png`, `tt_ste_end.png`, `ww1_posture_icons_zoom.png` (the three sword icons).

## 5. Stage-2 matrix with the tooltips in (`tools/stage03_gates.sh`, logs `work/runs/s3_*.txt`)
```
CELL DONE default/ste-1.62-1024K: OK (774s)       marker PMPO, RATE 3.995/s (8 MHz 50 Hz), soak 308 s 4.00/s no stall no exception, save/load 0 differ, lose (cache $9fc58 -> $a7958), win ($af658), round 3, payload@options/map/soak/saveload unchanged
CELL DONE fill/ste-1.62-1024K: OK (778s)          pattern-filled free payload area: same, payload@* unchanged, RATE 3.995/s, soak 4.01/s
CELL DONE corrupt/ste-1.62-1024K: OK (180s)       PMPF, game original, payload unchanged
CELL DONE default/megaste-2.06-4096K: OK (774s)   Mega STE 60 Hz: RATE 3.970/s, soak 4.01/s, save/load, lose, win, round 3, payload unchanged
CELL DONE default/st-1.04-1024K: OK (184s)        boot, map, lose
KEYS 39 of 39 key/click pairs identical           CELL DONE keys: OK  (10 command icons, click/key/key/click word checks PASS; 0 FAIL lines)
```
Every cell has 0 FAIL lines (counted with `grep -c FAIL`). The payload checks compare `$72000-$77fff` with the build's expect.bin, the tooltip's state block `$74800-$74adf` is masked (declared `; data:`), everything else (code, wording table, KF word's neighbours) must stay byte for byte. The keys gate ran with the changed qol_keys (the `move.w #1,KF.l` at the start of its hook): unchanged result (39 of 39).
Not run in this stage (not asked): 16 MHz Mega STE cells, TT / Falcon, HD, the whole-RAM tick-state equality with the tooltip up (master's `pmtt_state`; the tick patches are unchanged and the hook's footprint gate shows it writes one buffer region only), master's frame A/B with the pointer held (replaced by the entry/exit dumps of both buffers: footprint exactly rows 0-5, byte 56..159, registers preserved).

## 6. Files
New: `patches/pm_tooltip.s`, `tools/wwtt.py`, `tools/stage03_gates.sh`, `work/notes/RESULTS_stage03.md`, `work/runs/s3_*.txt` (12 logs). Changed: `patches/qol_keys.s` (KF word, data block 204 B, comment), `PLAN.md` (stage 3 marked). Screenshots are git-ignored.
