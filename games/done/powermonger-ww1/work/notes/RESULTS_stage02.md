# Stage 2 results (PMWW1Stage02, 2026-11-23): noprot, key disk, tick, keys, cache cap / Retire, matrix

Evidence contract: **[obs]** = raw lines from a file named here; **[INFERENCE]** = reasoning only; failures are listed as failures.
Hatari 2.6.1, private HOME per run, work dirs `/tmp/pmww1s2/*`, one Hatari at a time. Gate logs: `work/runs/s2_*.txt`. Tools: `tools/wwpatch.py` (build), `tools/wwgate.py cell` (boot / map / saveload / lose / win / round3), `tools/wwtick.py` (snap / rate / ab), `tools/wwkeys.py`, `tools/wwgrid.py`.

## 1. noprot (`patches/pm_noprot.s` $15998, `pm_noprot_box.s` $bbd2)
Port of master's pair. WW1 addresses = master's + `$b4a` / `-$30e`; checked by instruction, not by shift: the flag long `$15998` (value `600015ea` = `bra.w $16f84`, the people-state jump table), written by the answer check `$b246` (`move.l d0,$242(a0)`, a0 = `$15756`) and cleared by the check start `$ae26` (`move.l #0,$15998`); readers `cmpi.l #$2c,$15998` at `$7202 $724c $a918 $a932 $14c2a` (SAVE / FORMAT labels and buttons, demo mode) and the trigger `cmpi.b #$60,$154($15844)` at `$12a8e` [obs: disassembly with `tools/m68dis.py`, byte search for the operands `$15998 $15844 $15756` found exactly these sites].
Gate lines (`work/runs/s2_noprot_nokeydisk_ste.txt`, STE TOS 1.62 1 MB):
```
GATE noprot noprot flag PASS $15998 = $0000002c (want $0000002c) before the first land
GATE noprot noprot: the check never ran PASS hits $acc4:0, $ae20:0, $b232:0, $b39c:0
GATE noprot noprot: 'Please wait' box skipped (stub reached) PASS $bbd2 reached 1x (an `rts` stub)
GATE noprot map view PASS counter 59, flag $15998 = $0000002c
```
Save / load (formatted blank save disk = the game's own sector 0 from `$1c860` + zeros, 409600 B; Hatari .st cannot be formatted by the game's write-track): SAVE button works (`$7202` demo-mode gate passed), slot A:
```
GATE noprot save/load: loaded state == saved state PASS 101376 B: 0 differ
GATE noprot save/load: the world moved between save and load PASS saved vs the state just before the load: 287 differ
GATE noprot save/load: save disk slot A == saved state PASS sectors 1-198 equal: True, slot flag $ff, image 409600 B
GATE noprot save/load: the game runs on after the load PASS
```
(state = `$44c3e`, `$c6` sectors, captured at the write call `$1cbc2` and right after the read returns `$1cb2a`; ejecting the save disk makes Hatari write the .st back). `work/shots/stage02/*` has the screens.
`work/runs/s2_noprot_ste_first.txt` = first run (kept): FAIL only on "the world moved" (my gate waited too little after the write: the dump was taken while the floppy write was still frozen), and its round-3 click typed an answer `0000` at (19,176) on the map because the gate did not pass noprot to `chart_to_map`; both gate bugs fixed, rerun above.

## 2. The key-disk request is part of the protection (lead's question)
[obs] The first START NEW CONQUEST of a session calls `jsr $1cf7c` (`$13cec`). `$1cf7c`: requester "PLEASE INSERT ORIGINAL POWERMONGER DISK" (`$1cc26`), then `$1cfa6` loads the FILE named `DATA\SPRITE8.DAT` (string at `$1cfb8`) from drive A: into the scratch buffer `$320c0` with the game's FAT loader `$d962`; a failure shows "DISK IN DRIVE A: IS NOT THE ORIGINAL POWERMONGER DISK" (`$1cc2e`) and asks again. (The Powermonger floppy IS FAT12-readable: `mdir -i games/done/powermonger/disks/protected.st ::DATA` lists SPRITE8.DAT 8724 B.) The later "INSERT THE POWERMONGER DATA DISK" request comes from the resource loader's wrong-disk path (`$d932 -> $1cc1a`).
[obs] FDC trace (`--trace fdc`, the whole request, `/tmp/pmww1s2/fdc1_cmds.txt` not kept: 100 MB): while the Powermonger disk is in the drive the controller sees 16 type-II multi-sector reads (command `$90`: boot sector, FAT sectors 1-9, directory at track 1 sector 3 and track 50, then sectors 1-8 of track 0 ...) with seeks (`$03`, `$13`) and force-interrupts (`$d0`); no read-address (`$c0`), read-track (`$e0`) or write command: an ordinary FAT file read, no track-level key-disk check.
[obs] `pm_nokeydisk` (`patches/pm_nokeydisk.s`, 3 nops at `$13cec`): the WHOLE scenario of the cell above (new conquest, map, save / load, lose, win, third land) runs with the WW1 disk only; `$1cf7c` is never executed, `$13cf2` (the next instruction) is, "ORIGINAL" never appears in the window text; the lose / win pictures, cache cursors (`$9fc58 -> $a7958`, `$af658`) and payload region are identical to the stage-1 runs with the disk swap:
```
GATE noprot nokeydisk: the key-disk routine never ran, the flow went on PASS $1cf7c hit 0x, next instruction $13cf2 hit 1x; the Powermonger disk was never inserted
GATE noprot lose picture PASS non-black 0.69, 16 colours, seen stable x3; cache cursor $9fc58 -> $a7958
GATE noprot win picture PASS non-black 0.99, 15 colours, seen stable x3; cache cursor $af658
CELL DONE noprot/ste-1.62-1024K: OK (439s)
```
So the release needs only the WW1 disk [obs for everything the scenario reaches; the loaded file is a scratch-buffer fill nobody reads back: $320c0 is reused by `$e4d6 $f5ea $119b8 $12882 $1301a`]. NOT done: how the Fuzion crack bypasses it (its game is packed, LFB).

## 3. tick (`tick_head $13da0`, `tick_pass $13de8`, `tick_wx $13e24`, `tick_men $13e36`, `tick_click/2/3 $7e6 $842 $144b4`; blobs `$72900-$72a7f`, data `$72a80`)
Port of master's seven-site fixed-rate world tick (semantics in `patches/tick_head.s`; TK = 75 units of 1/300 s = 0.25 s = **4.00 world steps/s**, 50 and 60 Hz by the shifter sync bit, catch-up clamp 3 ticks, resync after > 1 s). WW1 differs from master in ONE place: the pass head has no `lea $14e20,a2` to hook; its site is the displaced `tst.w $5a856` (pause) whose flags the hook returns, so a render-only pass returns NZ and the game's own `bne.b $13dcc` skips exactly the world logic (`addq $2ed90`, `addq $50fd8`, `jsr $1359a $576a $d712 $3276`). The other six sites map 1:1 (`work/notes/addrmap.md`, operands re-read from the image: world clock `$2ed90`, click stamp `$2ed94` at `$7e4`/`$840`/`$144b2`, VBL counter `$71b7c`, speed countdown `$5a854`). [obs: `wwpatch.py verify` derives every `orig` from the resident image]
The loop top for the dumps is `$13d58` (first instruction of a pass, after the start routine's `jsr $bbd2`), the flip routine `$e0e`.

**Rates** (`tools/wwtick.py rate`, snapshot `map1` = the first map view of the ORIGINAL disk, STE TOS 1.62 1 MB, emulated seconds from the VBL counter and the CPU cycle counter, 800 VBL; `work/runs/s2_tick_rate_snapshot.txt`):
```
RATE map1 8 MHz 50 Hz sync $02 orig: 801 VBL = 16.02 s emulated, 160111 cycles/VBL, world clock +39 = 2.434/s
RATE map1 8 MHz 50 Hz sync $fe patched: 801 VBL = 16.02 s emulated, 160124 cycles/VBL, world clock +63 = 3.933/s; tick passes 63, R passes 0, S passes 26
RATE map1 16 MHz 50 Hz sync $02 orig: 801 VBL = 16.02 s emulated, 320397 cycles/VBL, world clock +100 = 6.242/s
RATE map1 16 MHz 50 Hz sync $fe patched: 801 VBL = 16.02 s emulated, 320318 cycles/VBL, world clock +64 = 3.995/s; tick passes 64, R passes 36, S passes 0
RATE map1 8 MHz 60 Hz sync $00 orig: 801 VBL = 13.35 s emulated, 133585 cycles/VBL, world clock +31 = 2.322/s
RATE map1 8 MHz 60 Hz sync $fc patched: 801 VBL = 13.35 s emulated, 133499 cycles/VBL, world clock +53 = 3.970/s; tick passes 53, R passes 0, S passes 23
RATE map1 16 MHz 60 Hz sync $fc patched: 801 VBL = 13.35 s emulated, 267016 cycles/VBL, world clock +54 = 4.045/s; tick passes 54, R passes 29, S passes 0
```
(the 60 Hz runs poke `$ff820a` bit 1 clear at the flip; the cycles per VBL prove the refresh: 133.5 k = 8 MHz / 60 Hz.) Compare master's figures (`games/done/powermonger/work/notes/timing.md` section 6): map_idle 8 MHz orig 2.326/s -> patched 3.970/s; 16 MHz orig 6.255/s -> patched 4.009/s. WW1: orig 2.434 / 6.242, patched 3.933 (8 MHz, 26 S passes of 89: the machine cannot render 4 frames/s, the logic catches up without a render) / 3.995 (16 MHz, 36 R passes). The original WW1 idle scene is as slow as master's (2.3-2.4 passes/s on an 8 MHz machine; "9/s" in the stage-0 note was the first seconds of the map view), so the 4.00/s world of master's TT-like choice is 1.6x the STE pace and 0.64x the 16 MHz pace, same as in master. The lead's "TT-like speed" = this 4.00/s (the original game at 32 MHz TT would go about 12/s [INFERENCE: scales with the 6.24/s at 16 MHz, not run]).
Cold boot rates of the built floppy (STE and Mega STE 8 / 16 MHz) are the `rate` lines of the cell logs in section 6.

**Per-tick state equality** (`tools/wwtick.py ab`): the snapshot is restored twice (unpatched = `e VBL` at the flip stop; patched = the tick blobs `loadbin`ed and the seven sites written at the same stop), every loop top dumps RAM `$0-$71fff` (the whole game; the payload is outside), pairing key = world clock `$2ed90`, compared word by word. The masks were found with a CONTROL run (unpatched vs unpatched, `work/runs/s2_tick_control_map1_8.txt`: IDENTICAL with the masks) and are: screens `$1d500-$2d1bf`, the stack scratch above them `$2d6c0-$2d77f`, the IKBD packet state `$1d2a0-$1d2bf`, the timer-C sound sequencer pointer `$1bc80-$1bc9f` and state `$2d7b2-$2d7bf` (interrupt-driven, real time), the click stamp and screen pointers `$2ed94-$2eda7` (patched: the stamp is the pass counter), flip-wait flag `$2edac`, right-button latch `$2edbe`, the composer's self-modified screen address `$82c6`, the draw pointer scratch `$e7c2`, the render flag `$13ccc`, the VBL counter `$71b7c-$71b83`, plus the seven patched sites (`tools/wwtick.py MASKS`). Everything else in `$0-$71fff` (all tables, people, the RNG, season / weather state, camera, the code) is compared. Results:
```
AB map1 8 MHz: unpatched 37 loop tops (world clock 45..81), second run 23 loop tops (clock 48..86) / compared 20 loop tops over 20 distinct world ticks / negative control differs in 19 of 19 / RESULT IDENTICAL
AB map1 16 MHz: unpatched 179 loop tops (world clock 58..236), second run 111 loop tops (clock 54..124) / compared 105 loop tops over 67 distinct world ticks / negative control differs in 106 of 106 / RESULT IDENTICAL
```
(`work/runs/s2_tick_ab_map1_8.txt`, `_16.txt`. The 16 MHz run has render-only passes interleaved: 111 loop tops over 71 ticks.) Negative control = patched tick k against unpatched tick k+1.
Gate-tool findings kept honest: the first patched 8 MHz run reported DIFFERENT in exactly the six ranges later masked (`$82c6 $e7c2 $13ccc $2d7b2-$2d7bb`): flip-parity scratch and the real-time sound sequencer, not world state; the run after masking them is IDENTICAL (the diff list of the first run is the 'unmasked' list in this paragraph).

Addendum to section 2 (lead's question: END_PIC1.PAK / END.PAK / BITMAP.PAK): [obs] these names, with CAP_SPR.PAK, are entries of the game's resource-id table at `$e586-$e640` (TEXTURES QAZ SPRITE16 SPRITE8 SPRITE24 SPRITE32 CAP_SPR BITMAP CAPGRAPH FX MAP MAPDATA END_PIC1 END LOSE WIN), loaded by id through the normal loader `$e344`; CAP_SPR, BITMAP, END_PIC1 and END are not on the EA disk. The key-disk request (`$1cf7c`) loads exactly ONE file, `DATA\SPRITE8.DAT` (a `.DAT` name that is not in that table; FDC trace: ordinary FAT reads), so it is NOT the path by which those four resources would be read. Whether the game asks for them (campaign end / BITMAP) and from which disk is NOT determined: no scenario run here (new conquest, save / load, retire = lose, forced win, third land, 5 min soak) loaded any of them [INFERENCE: they are the campaign-end pictures and the loader would show its own disk request]. Flagged for the lead / user: if the end sequence needs END*.PAK, shipping them is a separate (legal) decision; `pm_nokeydisk` does not make that worse.

## 4. keys (`qol_keys $13e70`, `qol_keys2 $f30`; blobs `$72c00`, `$73100`, data `$73000-$730c7`)
Port of master's `qol_keys` / `qol_keys2` including the phantom-click gate (LASTV / WIN), minus the tooltip key labels (stage 3). WW1's grid is pixel-identical to master's: `python3 tools/wwgrid.py points` reads WW1's own tables `$13bde / $13c58 / $1a89a` (+ rects `$13fc4`) and resolves all 33 KT points to the intended icon ids (master's table unchanged, `POINTS 33 entries, 0 problems`); `wwgrid.py handlers`: the 24 entries of the click jump table `$14340` reach handlers with the same instruction sequence as master's `$135cc` (`24 jump-table entries, 0 with a different instruction sequence`). Variable map = master + `$e20` (`$2df8e -> $2edae`, latches `$2edb6 $2edb8 $2edbe`, Shift `$2edaa`, key table `$2ec8c`, VBL `$71b7c`, typing flag `$d424`, window `$74c0`, pause `$5a856`, dispatcher `jsr $6c16`); the ACIA handler saves the same registers [obs: disassembly].
Gate (`tools/wwkeys.py`, built default floppy, STE 1 MB; `work/runs/s2_keys_ste.txt`): for every KT entry the click state at the dispatch point (`$13e82`: click words `$2edae/$2edb0`, latches `$2edb6 $2edb8 $2edbe`) is captured for a REAL mouse click (pointer closed in on the exact point, tolerance 0) and for the REAL key (xdotool, Shift for the right-button variants) and compared:
```
KEYS 39 of 39 key/click pairs identical        (e.g. GATE keys key bracketleft +Shift == click (28,158) PASS click words [28, 158, 0, 1, 1] key words [28, 158, 0, 1, 1])
GATE keys key o opens the same window as the click PASS / keys are swallowed while a window is open (h) PASS / window closed PASS
GATE keys command word through click/key/key/click: f (icon 3) PASS $5a836 = [6, 0, 6, 0] want [6, 0, 6, 0]     (10 command icons, all PASS)
CELL DONE keys: OK
```
(Transfer Men / `x`: neither click nor key sets `$5a836` on the start position, same words for both, so it is excluded from the toggle check.) Phantom click (`work/runs/s2_phantom_gated.txt`, `_nogate_control.txt`): name `RHFGMAIYST` typed at the name prompt:
```
GATE phantom phantom: name 'RHFGMAIYST': no command replayed PASS $5a836 = 0, pending key bytes set: []
GATE phantom_nogate ... no command replayed FAIL $5a836 = 32, pending key bytes set: ['0x1c']     (negative control: WIN = $7fffffff build, WW_PATCHDIR copy)
```
First full keys run (`work/runs/s2_keys_ste.txt` was overwritten by the final chain run): 17 keys failed only because my gate left the option window open after `o`; fixed (the window closes with the tick at ST (57,4)), final run above.
Not done: master's `pmqol_state` whole-RAM key == click equality over ticks (the click words + the game's own command word were gated instead).

## 5. Cache cap / Retire (item 4): NOT needed in stage 2; left for stage 4
The payload `$72000-$77fff` is below the resource cache start `$80000` (`placement.md`: the cursor `$2cfda` only grows from `$80000`), so master's v1.1 failure (cache copy over the payload) cannot happen: the pattern-fill build (every free long of `$72000-$77fff` non-zero) with the full stage-2 set resident passes Retire (lose), forced win, third land, save + load, 5 min soak with the region unchanged (`s2_fill_ste.txt`, `s2_fill_megaste.txt`, section 6). No `pm_cachecap` was written. If stage 4 puts blobs above `$80000`, the lead's memory design applies (CAPLIM = `$B0000`, blob below `$78000`); the hook point is `$e3f2 movea.l $2cfda,a1`.

## 6. Full stage-2 set: gate lines (all from `work/runs/s2_*.txt`)
STE TOS 1.62 1 MB (default = all 13 sites; `tools/stage02_gates.sh`):
```
CELL DONE default/ste-1.62-1024K: OK (772s)    marker PMPO, 13 sites PASS, credit, noprot, nokeydisk, RATE 4.057/s, soak 308 s 4.01/s no stall no exception, save/load 0 differ, lose (cache $9fc58 -> $a7958), win ($af658), 3rd land, payload@* unchanged
CELL DONE fill/ste-1.62-1024K: OK (775s)       same + pattern fill: payload@options/map/soak/saveload/lose/win/round3 PASS unchanged; RATE 3.933/s, soak 4.01/s
CELL DONE corrupt/ste-1.62-1024K: OK (185s)    PMPF, game original (question asked, disk requested), payload unchanged
CELL DONE core_only/ste-1.62-1024K: OK (245s)  boot, map (disk swap), lose
CELL DONE original/ste-1.62-1024K: OK (476s)   unpatched ea.st, region $72000-$77fff all zero through the whole scenario
```
Mega STE TOS 2.06 4 MB (the machine boots at 60 Hz in Hatari: cycles/VBL 133.5 k = 8 MHz / 60 Hz, a real 60 Hz run):
```
CELL DONE fill/megaste-2.06-4096K: OK (774s)     RATE 3.970/s at 8 MHz 60 Hz, soak 4.00/s, all payload@ lines PASS
CELL DONE default8/megaste-2.06-4096K: OK (146s) RATE default8/megaste 8 MHz cold boot map view 60 Hz: 54 ticks in 13.35 s = 4.045/s; tick passes 54, R 0, S 10
CELL DONE default16/megaste-2.06-4096K: OK (148s) RATE 16 MHz 60 Hz: world clock +53 = 3.970/s; tick passes 53, R passes 62, S 0
```
`work/runs/s2_default_megaste.txt` (the full default cell, kept unedited) is `FAIL (775s)` on exactly ONE line: `world rate = 4.00/s FAIL 3.246` - a gate bug: it divided 801 VBL by 50 Hz, but this machine runs 60 Hz (13.35 s, not 16.02 s: 52 ticks / 13.35 s = 3.90/s). Every other line of that cell (boot, noprot, nokeydisk, soak 4.00/s, save/load, lose, win, round 3, payload@*) is PASS; the rate step now reads the sync mode (`wwtick.rate_numbers(h, None, ...)`) and the rerun `s2_rate8_megaste.txt` is OK.
ST TOS 1.04 1 MB (once): `CELL DONE default/st-1.04-1024K: OK (183s)` (boot, map, lose).
Cold-boot rate summary (ticks per emulated second; master's patched figures 3.97-4.009): STE 8 MHz 4.057 / 3.933 (default / fill runs), Mega STE 8 MHz 60 Hz 4.045 / 3.970, Mega STE 16 MHz 60 Hz 3.970; snapshot runs (section 3) 3.933-4.045.
Not done: 16 MHz Mega STE with the cache register (`pm_mste` is stage 4), TT / Falcon cells, the tick `ab` on a second snapshot / forced season change (RNG address in WW1 not located; the equality covers `$0-$71fff` so the RNG is included but not reported separately), Mega STE retire with `--fill` at 16 MHz.
