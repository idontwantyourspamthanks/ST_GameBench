# Hunter pause screen: controls guide (patches/help_pause.s, tool tools/help_gate.py)

Tags: **[disasm]** `tools/m68dis.py work/dumps/boot/ram_game.bin` (ST, `a5 = $806`), **[obs]** raw tool output pasted below, **[INFERENCE]** not proven.
Patch is `; default: no` until the lead flips it (all gates below passed). `; requires: key_item jag_pad` (the panel documents those keys; the pad column reads jag_pad's state).
Prefix range `help_ = $8CBBE-$8CFFF` (lead's `PREFIX_RANGES`). Blobs: code + list A `$8CBBE-$8CDF3` (566 B), font + list B `$8CE80-$8CFF8` (377 B); spare 12 and 7 bytes. Site `$260a`, 8 bytes.
Builds used: `build/help_hd`, `build/help_fl` = the 24 default patches + `help_pause` (`--samples build/hunter_snd.bin`).

## 1. The pause [disasm]

```
00b0a8:  b23c0070    cmp.b    #$70, d1               ; key 'p' (the pad's Pause injects the same key through $b048)
00b0ae:  086d00050093 bchg.b  #$5, $93(a5)           ; bit 5 of $93 = paused (toggle)
00b0b6:  082d00070093 btst.b  #$7, $93(a5)           ; the key dispatch only runs in the 3D loop
00254c:  082d00050093 btst.b  #$5, $93(a5)           ; 3D loop, once per frame after the flip ($5f6a) and $6000
002554:  610000b0     bsr.w    $2606
002606:  610008e6     bsr.w    $2eee                 ; $2ef8: clear 3 words at ($7f44)+$3da, bra $aaa2 (wait one VBL); then bclr #7,$93 (3D-loop gate off)
00260a:  082d00050093 btst.b   #$5, $93(a5)          ; THE SITE (8 bytes with the next line): spin until the bit is clear
002610:  66f8         bne.b    $260a
002612:  08ed00070093 bset.b   #$7, $93(a5)          ; back in the 3D loop
002618:  4e75         rts
```
`$2606` has one caller (`$2554`; `m68dis.py --xref 2606`). While paused the game draws nothing: the frame loop is blocked in the spin at `$260a`; the shown page is the frame that was just flipped (`$148(a5)`), the draw page (`$144(a5)`) holds an older frame that the next pass redraws completely (the sky fill `$c84a` and the panel copy write the whole page; `triple.md` section 3 says the same).
Only the VBL handler runs: the pointer (`$c69a tst.b $1ce(a5) / bmi.w $a65c`), the sky raster (colour 15 only), sound, pad poll. The pointer restores its saved rows and redraws itself every VBL on the shown page:
```
00a648:  47fa00d0     lea.l    $a71a(pc), a3 ; 00a64c: bclr.b #$7,$1ce(a5)  ; 00a652: bclr.b #$0,$1ce(a5) / bne.b $a6cc    ; pointer off + restore the pixels under it (the game's own hide, used at $d204)
00a638:  bclr.b #$0,$1ce(a5) / bset.b #$7,$1ce(a5) / bra.w $b306                                                        ; pointer on (the game's own show, used at $d262)
```

## 2. What the patch does

`jmp $8cbbe.l / nop` replaces the 8-byte spin (`082d00050093 66f8`). The blob, in order:
1. if bit 5 is already clear (a second press before we got here) it falls out like the original loop;
2. `movem.l d0-d7/a0-a4,-(sp)`; `d7 = $1ce(a5)`; if bit 7 (pointer on) `jsr $a648.l`: pointer off, pixels restored. Without this the VBL's `$a65c` would write its saved rows (the picture under the pointer) over the panel after it moved, and on unpause our restore would paste a stale pointer;
3. copy the rectangle (288 x 88 px = 18 groups from x = 16, rows 24..111, 144 B per row) from the SHOWN page `$148(a5)` to the same place in the DRAW page `$144(a5)`: scratch, redrawn by the game's next pass (proved in section 4: every page after the unpause is identical to the control, including that scratch page);
4. clear the rectangle in the shown page to colour 0, 1-pixel frame in colour 8 (plane 3 only), then draw the script with a 4x5 font in colour 8 (plane 3 only; advance 5, line pitch 7). Colour 0 is black and index 8 the brightest grey in every palette: day `ddd` (STE, `555` on a plain ST), dusk `444`, night `aaa` (visuals.md section 1 readout), and the rectangle ends at row 111, above the panel palette split (row 140). Colour 15 (the sky raster's only colour) is never used;
5. spin on bit 5 exactly like the original loop;
6. copy the saved rectangle back (byte exact), `jsr $a638.l` if the pointer was on, `movem.l (sp)+`, `jmp $2612.l`.
Nothing of the world is written (section 4). While paused the VBL handler redraws nothing in the rectangle: the overlay is drawn once and survives (section 4.3).
Draw cost [INFERENCE from instruction counts, measured as 112,000 cycles from the unpause to `$2612` in section 4.1]: the restore is about 2 frames of 8 MHz time; the draw at pause start about 3 frames.

**Pad column.** Pad cells are script records flagged `y bit 7` and drawn only when `JAG_ST` (`$8D9E0`, jag_pad) = 1. That byte says the machine has the enhanced joystick ports (STE, Falcon); a plugged pad cannot be told from none (`jagpad.md` section 6 item 6), so every STE and Falcon shows the pad column, the ST, Mega ST, Mega STE and TT (probe says no: `JAG_ST = $ff`) do not.

**Text.** Script records `x/2, y (bit 7 = pad only), text, 0`; lists A (`$8CBBE` blob) and B (`$8CF10`); font table `$8CE80` = codes 43..90 (`+` draws `#`, `,` draws `*`, `:` draws `?`; a space is skipped), 3 bytes per glyph (5 rows x 4 pixels). Every control is listed:

| left block | pad | right block | pad |
|---|---|---|---|
| STICK  MOVE | D-PAD | R  RADAR | 1 |
| BUTTON  FIRE | A B | ?  MAP | 2 |
| RETURN  NEXT WEAPON | C | L  LOG BOOK | 3 |
| 1-9  WEAPON | | A  DRONE | 4 |
| H  MEDICAL KIT | # | F  FLARE | 5 |
| G  FUEL CAN | 0 | C  CLOCK | 6 |
| J  PARACHUTE | 8 | UP  REAR ZOOM | 7 |
| SPACE  GET OUT | OPTION | DOWN  FRONT ZOOM | 9 |
| ESC  OPTIONS | * | P  RESUME | PAUSE |
Title: `PAUSED   PRESS P TO RESUME`. The wording follows the manual (`work/manual.txt` section 5: Esc options, R radar, P pause, Return next weapon, A drone, F flare, L log book, C clock, ? overlaid map, Space leave vehicle, arrow up rear zoom, arrow down forward zoom) and `keys.md` / `jagpad.md` (1-9, H, G, J; pad map).

## 3. Screens [obs]
`work/shots/help/`: `help_{day,dusk,night}_a_50hz.png` (snapshot foot_stand, live set, paused by pad Pause: host `p` with `jag_pad_a.cfg`; `JAG_ST=01`), `help_night_a_60hz.png` (60 Hz, triple buffering, shown page `$81000` = the third page), `help_hold_day_{6,10}s.png`, `help_cold_<machine>_{paused,unpaused}.png`.
Each paused rectangle holds exactly two colours, 0 and 8 (`box colours {0: 22241, 8: 3103}` with the pad column, `{0: 22629, 8: 2715}` without). "Without a pad" = the ST / TT cold boots (the STE has the ports: its panel always shows the pad column).

## 4. Gates [obs]
Tool `tools/help_gate.py` (own file). Live set `pal_* sky_* key_item jag_pad jag_stick [tb_*] help_pause` on the 1 MB snapshots; control = the same set without `help_pause`.

### 4.1 After the unpause the frames are identical to a pause without the overlay (`help_gate.py ab`)
Deterministic: at the first flip after VBL 5100 the live set, the frame lock (`$9ad = $0e`, huntab `--lock`) and the pause bit (`w $899 $a0`) are applied; at the first spin-loop hit after VBL 5160 the pages are saved and the bit is cleared (`w $899 $00`); at the next 3 flips the three pages and the game's variables `$800..$1fff` (6 KB) are saved. Both runs unpause in VBL 5161.
**Phase.** The overlay's restore takes 102,240 cycles, so the help run reaches `$2612` at FrameCycles 112,112 and the control at 9,872 (`e FrameCycles` at `$2612` in each run). A frame that starts 100,000 cycles later can end one VBL later and then the world legitimately steps by a different VBL count (`huntab.py` docstring). The gate therefore unpauses the control when `FrameCycles > 112090` so that both reach `$2612` at the same cycle (+-30). Proof that this is what separates the runs and not the overlay (the control against itself):
```
ab --selftest                  (same control twice)        ALL IDENTICAL   (paused, f1, f2, f3: pages A, B and var 0 bytes differ)
ab --selftest --shift 1        (second control 1 VBL later) ALL IDENTICAL
ab --selftest --cyc 60000      (second control 60,000 cycles later in the VBL)
   f1 var: 3 bytes differ at ['0x9af', '0x9b1', '0x9b9']      f2 page A: DIFFER 2 bytes rows 55..55      f2 var: 31 bytes differ at ['0x9af', '0x9b3', '0x9b9', '0xcc6', '0xd33', ...]      MISMATCH
ab --selftest --cyc 120000     the same lists
ab (help vs control, NO phase match)                       f1 pages IDENTICAL, f1 var: 3 bytes at ['0x9af', '0x9b1', '0x9b9'], f2 page A DIFFER 2 bytes rows 55..55, f2 var 31 bytes (the same bytes as the 60,000-cycle control)
```
Phase-matched, 1 MB STE, foot_stand, double buffering (`ab --cyc 112090`):
```
paused page A: DIFFER 8114 bytes rows 24..199                         (the overlay + the hidden pointer, rows 192..199)
paused page B: DIFFER 4 bytes rows 54..54                             (the draw page: our scratch copy of the current frame instead of the previous frame; 4 animated bytes)
paused var: 1 bytes differ at ['0x9d4']                              ($9d4 = $1ce(a5): the pointer flags)
f1 page A: IDENTICAL 0 bytes   f1 page B: IDENTICAL 0 bytes   f1 var: 0 bytes differ
f2 page A: IDENTICAL 0 bytes   f2 page B: IDENTICAL 0 bytes   f2 var: 0 bytes differ
f3 page A: IDENTICAL 0 bytes   f3 page B: IDENTICAL 0 bytes   f3 var: 0 bytes differ
shown page at the pause: 0x23000
help run, page A: entry vs exit: 8 bytes differ, rows [192, 193, 194]..[199], window rows 0..139 differing: 0
help run, page B: entry vs exit: 4 bytes differ, rows [54]..[54], window rows 0..139 differing: 1     (the draw page, redrawn by the next pass)
ALL IDENTICAL
```
"entry vs exit" = the shown page at the first instruction of the blob against the page at `$2612`: the 3D window (rows 0..139) is byte-identical; only the pointer rows (192..199) differ (the pointer is drawn again by the next VBL).
Triple buffering (`tb_*` live, `--tb --cyc 112150`; all three pages A `$23000`, B `$2ad00`, C `$81000`):
```
paused page A: DIFFER 8114 bytes rows 24..199   paused page B: IDENTICAL 0 bytes   paused page C: DIFFER 12300 bytes rows 24..111   (the draw page C holds the scratch copy)
paused var: 1 bytes differ at ['0x9d4']
f1 page A/B/C: IDENTICAL   f1 var: 0 bytes differ      f2 page A/B/C: IDENTICAL   f2 var: 0 bytes differ      f3 page A/B/C: IDENTICAL   f3 var: 0 bytes differ
help run, page A: entry vs exit: 8 bytes differ, rows [192, 193, 194]..[199], window rows 0..139 differing: 0
ALL IDENTICAL
```
The same `ALL IDENTICAL` with triple buffering on the snapshots `1mb_car_drive` (`--cyc 112170`) and `1mb_hills_stand` (`--cyc 112150`) and at 60 Hz (`--hz 60 --tb --cyc 112150`, `w $ff820a $00` as in `huntvis.py`; FrameCycles at `$2612`: help 112,184, control 9,952).
**Negative control** (a copy of the patch without the restore copy, removed afterwards; `ab --cyc 112090 --neg`):
```
f1 page A: DIFFER 8106 bytes rows 24..111      f1 var: 3 bytes differ at ['0x9af', '0x9b1', '0x9b9']      f2 page A: DIFFER 2 bytes rows 55..55
help run, page A: entry vs exit: 8114 bytes differ, rows [24, 25, 26]..[199], window rows 0..139 differing: 88
MISMATCH
```
The gate fails on a missing restore, and the world variables also move because without the 100,000-cycle restore the phase differs (same three bytes as the phase control).

### 4.2 Never paused: huntab `--lock`
```
python3 tools/huntab_serial.py --only help_pause key_item jag_pad jag_stick --base key_item jag_pad jag_stick --snapshot foot_stand foot_walk car_stand car_drive hills_stand --points 2 --flips 2 6 --lock --no-fps
foot_stand: IDENTICAL   foot_walk: IDENTICAL   car_stand: IDENTICAL   car_drive: IDENTICAL   hills_stand: IDENTICAL   ALL IDENTICAL
```
[INFERENCE] by construction: the site `$260a` is only reached through `bsr $2606` when bit 5 is set.

### 4.3 It survives a long pause (`help_gate.py hold`)
```
day, pad a, double buffering, 10 s:
t=  4.5s VBL +396 shown=0x23000 rows0..139 md5 89472b1c0274c7d3813306aa47b8b7f6 same-as-first=True $93=20
t= 10.3s VBL +686 shown=0x23000 rows0..139 md5 89472b1c0274c7d3813306aa47b8b7f6 same-as-first=True $93=20
screenshot rows 0..139 at t=0 and t=11.7s: summed RGB difference 0 (VBLs run: 757)
night, pad a, 60 Hz, triple buffering, 10 s (the third page shown):
t=  4.5s VBL +475 shown=0x81000 ... same-as-first=True $93=20
t= 10.3s VBL +824 shown=0x81000 ... same-as-first=True $93=20
screenshot rows 0..139 at t=0 and t=11.7s: summed RGB difference 0 (VBLs run: 909)
```
Hundreds of VBLs (pointer code, sky raster, sound, pad poll) run while paused and nothing writes the rectangle: the page and the screenshot do not change. No per-frame redraw is needed because the game itself draws nothing during the pause.

### 4.4 Cold boots (`help_gate.py cold`: pause with P, 3 s, read the shown page, screenshot, P again; keyboard P, no pad config)
```
STE 1.62 1 MB HD:  FLAGS=00000003 JAG_ST=01 tb mode=0001 $260a=4ef90008cbbe4e71 $93=80
  PAUSED  : $93=20 JAG_ST=01 shown=0x23000 box colours {0: 22241, 8: 3103}     UNPAUSED: $93=80 in_game=True shown=0x23000 box colours {0: 1162, 1: 241, 2: 75, 3: 18, 4: 3129, ...}   fps 4.6
STE floppy 1 MB (real FDC): FLAGS=00000003 JAG_ST=01 tb mode=0001
  PAUSED  : $93=20 JAG_ST=01 shown=0x23000 box colours {0: 22241, 8: 3103}     UNPAUSED: $93=80 in_game=True ... box colours {0: 792, 4: 3147, 5: 45, ...}   fps 4.8
ST 1.04 1 MB HD:   FLAGS=00000006 JAG_ST=ff tb mode=0001
  running : box colours {0: 1158, 1: 241, 2: 75, 3: 18, 4: 3129, 5: 62, 7: 35, 8: 376, 9: 199, 10: 89, 11: 473, 12: 8548, 13: 5828, 14: 727, 15: 4386}
  PAUSED  : $93=20 JAG_ST=ff shown=0x23000 box colours {0: 22629, 8: 2715}
  UNPAUSED: $93=80 in_game=True shown=0x23000 box colours {0: 1158, 1: 241, 2: 75, 3: 18, 4: 3129, 5: 62, 7: 35, 8: 379, 9: 199, 10: 89, 11: 472, 12: 8549, 13: 5829, 14: 727, 15: 4382}   fps 4.8
TT 3.06 4 MB HD, --mmu true --monitor vga --cpuclock 32: FLAGS=00000003 JAG_ST=ff tb mode=0002 (off)
  PAUSED  : $93=20 JAG_ST=ff shown=0x2ad00 box colours {0: 22629, 8: 2715}     UNPAUSED: $93=80 in_game=True shown=0x23000 box colours {0: 1300, 1: 232, 4: 3129, ...}   fps 48.2/50.0 (flips 241-250 of 250 VBL)
Falcon 4.04 4 MB floppy: FLAGS=0000000b JAG_ST=01 tb mode=0002 (off)
  running : box colours {0: 1324, 1: 241, 2: 75, 3: 18, 4: 3129, 5: 62, 7: 35, 8: 376, 9: 199, 10: 89, 11: 472, 12: 8549, 13: 5831, 14: 724, 15: 4220}
  PAUSED  : $93=20 JAG_ST=01 shown=0x23000 box colours {0: 22241, 8: 3103}
  UNPAUSED: $93=80 in_game=True shown=0x2ad00 box colours {0: 1324, 1: 241, 2: 75, 3: 18, 4: 3129, 5: 62, 7: 35, 8: 376, 9: 199, 10: 89, 11: 472, 12: 8549, 13: 5831, 14: 724, 15: 4220}   fps 16.6
```
(The first Falcon / STE floppy / TT runs were discarded: concurrent runs shared one page-dump file in `/tmp/huntvis`, so some readings came from another machine; the dump names now carry the pid and the runs above were repeated with no other `help_gate` running. The ST and Falcon "UNPAUSED" colour tables equal the "running" ones exactly: the screen was restored to the same picture.)
Screenshots: `work/shots/help/help_cold_*_{paused,unpaused}.png`.

## 5. Limits and notes
- A plugged pad cannot be detected: the pad column shows on every STE/Falcon (section 2). A pad-less STE user sees column cells "PAD ...". If that is unwanted, drop the pad records (`$80|y` flags) or gate on a pad having been used [INFERENCE: not done].
- While paused the mouse pointer is hidden (`$a648`) and comes back on unpause. [INFERENCE] a mouse click during pause does nothing in the original either (no handler runs: the gate `$93` bit 7 is clear).
- The overlay is drawn into the visible page over 2-3 frames at the pause (draw ~46 ms, restore ~14 ms at 8 MHz [INFERENCE: cycle counts, one measured: 102,240 cycles for the restore]); on a 32 MHz TT it is a single frame.
- The panel blobs use 566 + 377 bytes of the 578 + 384 free: only 12 and 7 bytes spare. A longer text needs the `sav_` window's `$8CA80-$8CB2B` (172 B) added to the prefix range.
- Not run: real hardware, plain ST floppy, Mega STE, the TT with the pad, a pad plugged in a cold boot (the pad Pause was exercised on the snapshots only: `shots --pad a`, host `p` = pad Pause, `$93=20` and the overlay in each of the 3 `shots` runs, the 60 Hz shot and the two `hold` runs that used `--pad a`).
- Not touched: `patches/README.md` (the lead's): add `help_pause` to the blob map: `$8CBBE-$8CDF3` code + list A, `$8CE80-$8CFF8` font + list B, site `$260a` (8 B).
