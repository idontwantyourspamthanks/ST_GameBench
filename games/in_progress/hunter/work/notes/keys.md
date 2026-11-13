# Hunter one-key items and weapon keys (patches/key_item.s)

Tags: **[disasm]** `tools/m68dis.py work/dumps/boot/ram_game.bin`, **[obs]** raw tool output pasted below, **[INFERENCE]** not proven.
Patch is `; default: no` until the lead flips it: **all gates below passed** (the keys do exactly the icon route's RAM effect; no effect outside the 3D loop; huntab IDENTICAL; pad buttons; cold boots).
Tool: `tools/hunkeys.py` (`table`, `menus`, `pad`, `chute`, `cold [--machine st|ste|tt] [--floppy]`). Build sets used: `huntpatch.py build [--floppy] --only hn_credit hn_hz jag_pad jag_stick p4_edge p4_ikbd p4_poly snd_core key_item` (build/key_hd, build/key_fl).

## 1. How it works [disasm]
```
00b0b6:  082d00070093   btst.b #$7, $93(a5)       ; key dispatch only while the 3D loop runs ($93 bit 7)
00b0bc:  6600f468       bne.w  $a526
00a526:  41faffee       lea.l  $a516(pc), a0      ; table 'c','r','l','m','f','a','~',$ff (ASCII of the key, d1)
00a52a:  7407           moveq  #$7, d2
00a52c:  b218           cmp.b  (a0)+, d1
00a52e:  670a           beq.b  $a53a
00a530:  51cafffa       dbra   d2, $a52c
00a534:  4ef900002686   jmp    $2686.l            ; a miss (Esc $01, Return $1c, Space $20, anything else): THE SITE
00a53a:  4240           clr.w  d0
00a53c:  10280007       move.b $7(a0), d0         ; item number from the table at $a51e
00a540:  222d024a       move.l $24a(a5), d1       ; owned mask
00a544:  0101           btst.l d0, d1
00a546:  671c           beq.b  $a564              ; not owned: rts
00a548:  3b400252       move.w d0, $252(a5)
00a54c:  47fafd3e       lea.l  $a28c(pc), a3      ; the icon rectangle table
00a550:  3400           move.w d0, d2 ... divu.w #$a ... lsl.w #5,d2 / lsl.w #4,d3   ; cell x = (n%10)*32, y = (n/10)*16
00a560:  60000866       bra.w  $adc8              ; the handler search a mouse click on that cell runs
```
`key_item` redirects only the miss at `$a534` (`jmp $8d820.l`) to a 12-entry table (blob `$8D820`); a hit sets d0 = item and jumps to `$a540` (the game's own ownership test and click handler). A miss goes on to `$2686` with d0/d1 untouched.
The item grid is the rectangle table at `$a28c` (16 B entries x0,x1,y0,y1,handler) [disasm]: row 0 x 0..288 handler `$a00a` (weapon 0-8: `lsr.w #5,d0 / bra $9fe6` = `move.w d0,$212(a5)` = current weapon), cell 14 (x128-160, y16-32) `$a3ae` (medical kit: `moveq #6,d0 / bsr $a09e / bra $9f04`), cell 15 `$a45e` (fuel can: needs `btst #$1a,$268`; `add.w #$2000,$296(a5)`), cell 18 `$a27c` (parachute: `btst.b #$f,$26a(a5) / bne; move.b #$7f,$281(a5)`).
Keyboard decoder: scancode to ASCII table `$b190+sc` [obs]: sc $02-$0a = '1'-'9', keypad `$6d $6e $6f $6a $6b $6c $67 $68 $69` = '1'..'9' too; `$22` g, `$23` h, `$24` j. The game's own keys (manual section 5 and `$a516`): C R L ? F A P Esc Return Space and cursor up/down: no digit, no g/h/j clash.

## 2. Keys
| key | item | effect |
|---|---|---|
| 1-9 (top row or keypad) | 0-8 | select weapon 0-8 (`$212`) |
| h | 14 | medical kit |
| g | 15 | fuel can |
| j | 18 | parachute |
| Jaguar `#` `0` `8` | h g j | `jag_pad.s` table entries `dc.b 0,$23 / 8,$22 / 9,$24`, mask `$000f0f0f` |
Shifted keys (capital letters) are not matched, as for the game's own keys.

## 3. Key vs icon route, [obs] `python3 tools/hunkeys.py table` (Hatari STE 1 MB, snapshot 1mb_foot_stand with the patch live, `--joy1 none`, NO pad config: the pad configs bind host digits to pad buttons)
The icon route = mouse up into the item table (it opens; `$93` bit 7 clear), hover the cell until `$252` = item, click. State before every trial is loaded with `loadbin`: all 20 counts 5, owned mask `$fffff`, life 32, weapon 0 (weapon 1 for key 1); "not owned" = that item's 32-byte record zeroed and its mask bit clear; fuel can: `$268` bit 26 set; parachute: `$26a` bit 7 clear. "effect" = fields count[20], cur `$212`, life `$23c`, disp `$294`, fuel `$296`, chute `$281` before to after; `sel` (`$252`, hover scratch) and `owned` (`$24a`, the table open recomputes it from the counts) are excluded.
Residual differences in the other bytes (`$8c0/$8c1`, `$a39`, `$a40`..) are the baseline noise bytes of an idle game (measured: three idle dumps differ there) and the hover/state of the click route: listed per row.
`disp` (`$294`, the HUD ammo number) shows 99 to 5 in the key trial of the first row of a run only because the click trial starts from the already updated value: both end at 5 (the end-state bytes are listed as equal in the "other bytes" line).
Messages: the medical-kit click (screenshot taken after it) showed no text in the HUD message box [obs, one screenshot]; the other items were not screenshotted [INFERENCE: same]. No game-variable byte differs between the routes (`other bytes` lines).
```
key 1 item  0 owned     key effect {'cur': (1, 0), 'disp': (99, 5)}
      click effect {'cur': (1, 0)}   identical: False
      other bytes where key-route and click-route end states differ: ['0x8c1']
key 1 item  0 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: []
key 2 item  1 owned     key effect {'cur': (0, 1)}
      click effect {'cur': (0, 1)}   identical: True
      other bytes where key-route and click-route end states differ: ['0x8c1']
key 2 item  1 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: []
key 3 item  2 owned     key effect {'cur': (0, 2)}
      click effect {'cur': (0, 2)}   identical: True
      other bytes where key-route and click-route end states differ: ['0x8c1', '0xa59']
key 3 item  2 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: []
key 4 item  3 owned     key effect {'cur': (0, 3)}
      click effect {'cur': (0, 3)}   identical: True
      other bytes where key-route and click-route end states differ: []
key 4 item  3 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: []
key 5 item  4 owned     key effect {'cur': (0, 4)}
      click effect {'cur': (0, 4)}   identical: True
      other bytes where key-route and click-route end states differ: []
key 5 item  4 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: []
key 6 item  5 owned     key effect {'cur': (0, 5)}
      click effect {'cur': (0, 5)}   identical: True
      other bytes where key-route and click-route end states differ: ['0x8c0', '0x8c1']
key 6 item  5 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: []
key 7 item  6 owned     key effect {'cur': (0, 6)}
      click effect {'cur': (0, 6)}   identical: True
      other bytes where key-route and click-route end states differ: ['0x8c0', '0x8c1']
key 7 item  6 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: []
key 8 item  7 owned     key effect {'cur': (0, 7)}
      click effect {'cur': (0, 7)}   identical: True
      other bytes where key-route and click-route end states differ: ['0x8c1']
key 8 item  7 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: []
key 9 item  8 owned     key effect {'cur': (0, 8)}
      click effect {'cur': (0, 8)}   identical: True
      other bytes where key-route and click-route end states differ: ['0x8c0', '0x8c1']
key 9 item  8 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: []
key h item 14 owned     key effect {'count': ([5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 5, 5, 5, 5, 5]), 'life': (32, 38)}
      click effect {'count': ([5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 5, 5, 5, 5, 5]), 'life': (32, 38)}   identical: True
      other bytes where key-route and click-route end states differ: []
key h item 14 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: []
key g item 15 owned     key effect {'count': ([5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 5, 5, 5, 5]), 'disp': (99, 5), 'fuel': (0, 8192)}
      click effect {'count': ([5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 5, 5, 5, 5]), 'fuel': (0, 8192)}   identical: False
      other bytes where key-route and click-route end states differ: ['0x8c0', '0x8c1']
key g item 15 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: ['0xa39']
key j item 18 owned     key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: ['0xa39']
key j item 18 not owned key effect {}
      click effect {}   identical: True
      other bytes where key-route and click-route end states differ: ['0xa39']
```
Parachute leaves no lasting RAM (the game consumes `$281` within a frame), so execution of `$a284 move.b #$7f,$281(a5)` was counted with a breakpoint on both routes (interactive run of the same code as `hunkeys.py chute`):
```
key (1, '00')
click (1, '00')
```
(breakpoint hits per route; with the precondition cleared in the table run above, neither route executed it: `j owned effect {}`, `click effect {}`.)

## 4. Keys do nothing outside the 3D loop, [obs] `python3 tools/hunkeys.py menus` (keys h g j 1 2 5 9 KP_3 pressed, 0.3 s each)
```
table    $93=00->00 keys ['h', 'g', 'j', '1', '2', '5', '9', 'KP_3']: counts/cur/life/owned unchanged = True   key ring $9c8=000a6f33
log      $93=00->00 keys ['h', 'g', 'j', '1', '2', '5', '9', 'KP_3']: counts/cur/life/owned unchanged = True   key ring $9c8=00096f33
options  $93=80->80 keys ['h', 'g', 'j', '1', '2', '5', '9', 'KP_3']: counts/cur/life/owned unchanged = False   key ring $9c8=00096f33
   BEFORE {'count': [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], 'cur': 0, 'life': 32, 'owned': 1048575} 
   AFTER  {'count': [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 5, 5, 5, 5, 5], 'cur': 2, 'life': 38, 'owned': 1048575}
pause    $93=20->20 keys ['h', 'g', 'j', '1', '2', '5', '9', 'KP_3']: counts/cur/life/owned unchanged = True   key ring $9c8=00096f33
control  $93=80->80 keys ['h', 'g', 'j', '1', '2', '5', '9', 'KP_3']: counts/cur/life/owned unchanged = False   key ring $9c8=00086f33
   BEFORE {'count': [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5], 'cur': 0, 'life': 32, 'owned': 1048575} 
   AFTER  {'count': [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 4, 5, 5, 5, 5, 5], 'cur': 2, 'life': 38, 'owned': 1048575}
```
The `options` and `control` rows of that log are from a first run whose Esc was injected wrongly (the game stayed in the 3D loop, `$93=80`: it is the CONTROL, keys DO act there: count 14 5 to 4, life 32 to 38, weapon 2). The real Esc run (xdotool Escape, screenshot shows GAME OPTIONS):
```
options (Esc) $93=00->00 unchanged=True ring=00096f33   (counts there read 0: the options screen replaces the table region, so "unchanged" is weak; the gate is $93 bit 7 = 0 and [disasm] `$b0b6 btst.b #7,$93(a5) / bne` never reaches `$a526`)
```
"table" = item table open (`$93`=0), "log" = log book (`l`: the location list, `$93`=0), "pause" = P (`$93`=`$20`). [INFERENCE] the same for every screen with `$93` bit 7 clear: the dispatch at `$b0b6` is guarded by it; the name entry and the log book read the key buffer, they never reach `$a526`.

## 5. Jaguar pad, [obs] `python3 tools/hunkeys.py pad` (Hatari pad emulation, `tools/jag_pad_a.cfg`: F6 = `#`, host 0 = pad 0, host 8 = pad 8; JAG_ST=01)
```
JAG state ce=00 cf=00 d0=00 d1=00 $93=80 lastkey sc/ascii=23/68  JAG_ST=01 JAG_DIR=00 S1=00000000 S2=0000
host F6     pad #  -> h medical kit (item 14)  effect {'life': (32, 38), 'disp': (99, 5), 'count': [(14, 5, 4)]}  last key scancode/ascii in the game's buffer = 23/68
host 0      pad 0  -> g fuel can (item 15)     effect {'fuel': (0, 8192), 'count': [(15, 5, 4)]}  last key scancode/ascii in the game's buffer = 22/67
host 8      pad 8  -> j parachute (item 18)    effect {'count': []}  last key scancode/ascii in the game's buffer = 24/6a
host h      keyboard h (reference)             effect {'life': (32, 38), 'count': [(14, 5, 4)]}  last key scancode/ascii in the game's buffer = 23/68
host g      keyboard g (reference)             effect {'fuel': (0, 8192), 'count': [(15, 5, 4)]}  last key scancode/ascii in the game's buffer = 22/67
host j      keyboard j (reference)             effect {'count': []}  last key scancode/ascii in the game's buffer = 24/6a
item table open: pad # 0 8 -> unchanged = True $93 = 0x0
```
`g`/`j` rows: g shows the fuel effect, j has no RAM effect on foot (same as the keyboard); the game's key buffer shows the pad produced the same scancode/ASCII (22/67, 24/6a).

## 6. huntab, key_item installed, no key pressed [obs] (`--flips 2 6 --lock`; the `--flips 1` capture bug is fixed in huntab.py)
```
python3 tools/huntab.py --only key_item --snapshot foot_stand foot_walk car_drive hills_stand --points 2 --flips 2 6 --lock --no-fps
python3 tools/huntab.py --only key_item jag_pad jag_stick --base jag_pad jag_stick --snapshot foot_stand car_stand --points 2 --flips 2 6 --lock --no-fps
foot_stand: IDENTICAL
foot_walk: IDENTICAL
car_drive: IDENTICAL
hills_stand: IDENTICAL
ALL IDENTICAL
EXIT=0
foot_stand: IDENTICAL
car_stand: IDENTICAL
ALL IDENTICAL
EXIT=0
```
Limit [INFERENCE]: with no key pressed the site `$a534` (a miss: Esc/Return/Space or a key not in the table) never runs, so this gate shows that the installed code and the pad table change nothing on their own; no negative control is possible without a key press.

## 7. Cold boots with the patch (key_item + the v1.1 set), [obs] `python3 tools/hunkeys.py cold ...`, rows: keyboard h g j, keypad 2, then pad `#` `0` `8`
STE HD 1 MB, ST HD 1 MB (TOS 1.04), TT HD 4 MB TOS 3.06 `--mmu true` (hunt_ttf's HD boot), STE floppy 1 MB:
```
== HD ste
machine=ste mem=1024K in_game=True MARKER=b'HNPO' FLAGS=00000003 $a534=4ef90008d820 $c616=4ef90008d620 $c64c=4ef90008d9c04e71
host h      keyboard h                         effect {'life': (32, 38), 'disp': (99, 5), 'count': [(14, 5, 4)]}  last key scancode/ascii in the game's buffer = 23/68
host g      keyboard g                         effect {'fuel': (0, 8192), 'count': [(15, 5, 4)]}  last key scancode/ascii in the game's buffer = 22/67
host j      keyboard j                         effect {'count': []}  last key scancode/ascii in the game's buffer = 24/6a
host KP_2   keypad 2 (weapon 1)                effect {'cur': (0, 1), 'count': []}  last key scancode/ascii in the game's buffer = 6e/32
host F6     pad #                              effect {'life': (32, 38), 'count': [(14, 5, 4)]}  last key scancode/ascii in the game's buffer = 23/68
host 0      pad 0                              effect {'fuel': (0, 8192), 'count': [(15, 5, 4)]}  last key scancode/ascii in the game's buffer = 22/67
host 8      pad 8                              effect {'count': []}  last key scancode/ascii in the game's buffer = 24/6a
== HD st
machine=st mem=1024K in_game=True MARKER=b'HNPO' FLAGS=00000006 $a534=4ef90008d820 $c616=08ad0003008f $c64c=102d00d11b4000d0
host h      keyboard h                         effect {'life': (32, 38), 'disp': (99, 5), 'count': [(14, 5, 4)]}  last key scancode/ascii in the game's buffer = 23/68
host g      keyboard g                         effect {'fuel': (0, 8192), 'count': [(15, 5, 4)]}  last key scancode/ascii in the game's buffer = 22/67
host j      keyboard j                         effect {'count': []}  last key scancode/ascii in the game's buffer = 24/6a
host KP_2   keypad 2 (weapon 1)                effect {'cur': (0, 1), 'count': []}  last key scancode/ascii in the game's buffer = 6e/32
host F6     pad #                              effect {'count': []}  last key scancode/ascii in the game's buffer = 38/00
host 0      pad 0                              effect {'count': []}  last key scancode/ascii in the game's buffer = 38/00
host 8      pad 8                              effect {'count': []}  last key scancode/ascii in the game's buffer = 38/00
== HD tt  (second run, first one failed in the harness: `no screenshot`)
== HD tt
title after 15 s
BOOT OK machine=tt tos=3.06 mem=4096K bus=acsi game=key_hd in_game=True MARKER=b'HNPO' FLAGS=00000003 fps=50.00  (53 s)
  peek $a534: 4ef90008d820
  peek $c616: 08ad0003008f
TT BOOT rc 0
machine=tt mem=4096K in_game=True MARKER=b'HNPO' FLAGS=00000003 $a534=4ef90008d820 $c616=08ad0003008f $c64c=102d00d11b4000d0
host h      keyboard h                         effect {'life': (32, 38), 'disp': (99, 5), 'count': [(14, 5, 4)]}  last key scancode/ascii in the game's buffer = 23/68
host g      keyboard g                         effect {'fuel': (0, 8192), 'count': [(15, 5, 4)]}  last key scancode/ascii in the game's buffer = 22/67
host j      keyboard j                         effect {'count': []}  last key scancode/ascii in the game's buffer = 24/6a
host KP_2   keypad 2 (weapon 1)                effect {'cur': (0, 1), 'count': []}  last key scancode/ascii in the game's buffer = 6e/32
host F6     pad #                              effect {'count': []}  last key scancode/ascii in the game's buffer = 38/00
host 0      pad 0                              effect {'count': []}  last key scancode/ascii in the game's buffer = 38/00
host 8      pad 8                              effect {'count': []}  last key scancode/ascii in the game's buffer = 38/00
== floppy ste (first runs with --blind failed to reach the 3D view; the second is the tool's default navigation as in work/notes/jagpad.md)
== floppy ste
in 3D view: True after 80 s
BOOT OK
machine=ste mem=1024K in_game=True MARKER=b'HNPO' FLAGS=00000003 $a534=4ef90008d820 $c616=4ef90008d620 $c64c=4ef90008d9c04e71
host h      keyboard h                         effect {'life': (32, 38), 'disp': (99, 5), 'count': [(14, 5, 4)]}  last key scancode/ascii in the game's buffer = 23/68
host g      keyboard g                         effect {'fuel': (0, 8192), 'count': [(15, 5, 4)]}  last key scancode/ascii in the game's buffer = 22/67
host j      keyboard j                         effect {'count': []}  last key scancode/ascii in the game's buffer = 24/6a
host KP_2   keypad 2 (weapon 1)                effect {'cur': (0, 1), 'count': []}  last key scancode/ascii in the game's buffer = 6e/32
host F6     pad #                              effect {'life': (32, 38), 'count': [(14, 5, 4)]}  last key scancode/ascii in the game's buffer = 23/68
host 0      pad 0                              effect {'fuel': (0, 8192), 'count': [(15, 5, 4)]}  last key scancode/ascii in the game's buffer = 22/67
host 8      pad 8                              effect {'count': []}  last key scancode/ascii in the game's buffer = 24/6a
DONE
```
ST and TT: the pad probe says no (`FLAGS` bit0 / SCU), the jag sites are restored (`$c616=08ad0003008f $c64c=102d00d11b4000d0`), the pad rows have no effect (F6 is not even a pad there), the keys work. `$a534=4ef90008d820` everywhere: the key patch is live on every machine.

## 8. Findings / limits
- Row 0 weapon keys act on any owned weapon like the strip click; selecting a weapon with no ammo behaves as the click does (same handler).
- `tools/huntjag.py` still lists `#`, `0`, `8` as "unassigned" in its BUTTONS table (not edited: another owner); with the patch they send h, g, j. Without key_item the three buttons inject h/g/j, which the game ignores [INFERENCE: not run].
- huntpatch.py got one line: `PREFIX_RANGES["key_"] = (0x8D816, 0x8D9BF)` (kept by the lead; HunterTriple confirmed the window).
- The icon route's mouse hover moves by less than about 16 host px are lost (Hatari/xdotool); `hunkeys.gmove` overshoots and comes back.
