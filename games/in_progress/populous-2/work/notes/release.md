# Populous 2 v1.0: release test of the default set (2026-11-12, Pop2Release)

Default set = `pop2patch.py list` rows with `default yes`: pop2_clamp, pop2_credit, pop2_fal_ym, pop2_ntsc, pop2_ntsc2, pop2_ptr_a/b, pop2_spr, pop2_spr16,
pop2_tick (+ _anim, _dot_a/b, _flip incl. the command queue, _logic, _render, _snd), pop2_tooltip. Builds: `build/Pop2Release` (HD folder), `build/Pop2ReleaseF/Populous2_boot.st`
(720K floppy), both `pop2patch.py build` / `build --floppy` with no `--only`.
Hatari 2.6.1, headless, audio off. Scripts (scratch, kept): `work/scratch/release/p2rel.py` (one cold-boot cell), `play.py`, `restore.py`, `ste60.py`, `ingamesave.py`, `bytes.py`, `diag*.py`.
Raw outputs: `work/gates/rel_*.txt` / `rel_*.log` (Hatari logs), screenshots `work/shots/rel_*.png` (`rel_tooltip_sheet.png` = tooltips across machines).

**Verdict: every HD cell passes. The floppy passes on TOS 1.04/1.62 machines (STE 2 MB, STE 4 MB, Mega STE with TOS 1.62) and FAILS on Mega STE TOS 2.06, TT TOS 3.06 and Falcon TOS 4.04.
That failure is in PP's loader, not in our patches (same failure with PP's original RUNME.TOS on a Falcon floppy). Because a cell failed, `tools/package.sh` was NOT run (no md5s).**

Every cell: cold boot from the menu, `boot_to_game()` to the first conquest battle (`in_play`), marker `$7fff8` = `P2PO`, `$22f14` = `4ef900082000` (tick hook), turns/s by
`p2tick.py` helpers (1000-1800 VBL from a cold boot, Hatari fast-forward, per emulated second), the Hatari log scanned for bus/address errors, tooltip hover screenshots (Earth
category icon, strip icon 4, no hover).

## 1. HD cells

| Cell | in_play / marker | turns/s (cycles per VBL, refresh seen) | log bus/addr errors | tooltip |
|---|---|---|---|---|
| STE 2 MB TOS 1.62, 8 MHz | yes / P2PO | 6.229 (160,212 cyc/VBL, 49.93 Hz) | 1 = PP probe `$ffff8e21` read at RUNME PC `$1b992` (stock: PC `$13968`, below) | EARTH EFFECTS / KEY: F3 |
| STE 2 MB, 16 MHz (`set_cpuclock 16`) | | 6.262 (320,498, 49.92 Hz) | same line | |
| STE 4 MB TOS 1.62 | yes / P2PO | 6.229 (160,196) | same 1 probe line | EARTH EFFECTS |
| ST 2 MB TOS 1.04 | yes / P2PO | 6.262 (160,195) | 3 = PP probes `$ffff8e21`, `$ffff8924` (RUNME PC `$1b9b2`, `$1b9e0`; stock ST: PC `$13988`, `$139b6`) + `Bus Error writing at address $ffff8a28, PC=$84320` = pop2_spr's bus-error-safe blitter probe (`pop2_spr.s` line 127 `move.w #$5aa5,$ffff8a28.w`, "an ST has none") | tooltip shown |
| Mega STE 4 MB TOS 2.06, native 60 Hz (sync `$fc`) | yes / P2PO | 6.230 (267,131 cyc/VBL = 16.03 MHz x 1/60) | 0 | shown |
| Mega STE 4 MB, forced 50 Hz (`w $ff820a $02`) | yes | 6.229 (320,441 = 16.02 MHz x 1/50) | 0 | |
| TT 4 MB TOS 3.06 `--mmu true`, 60 Hz (sync `$01`) | yes / P2PO | 6.263 (534,208 cyc/VBL, 59.90 Hz) | 0 | shown |
| Falcon 4 MB TOS 4.04 (50 Hz) | yes / P2PO | 6.262 (320,437, 49.93 Hz) | 0 | FIGHT / KEY: KEYPAD / |

(The "refresh seen ... NOT 60 Hz" flags in `rel_megaste4_hd.txt` come from the helper's 8 MHz default for the Mega STE: the machine runs at 16 MHz, 267,131 x 60 = 16.03 MHz, so the refresh IS 60 Hz and
the rate 6.23/s is correct.)

Stock PP game, same probe (`work/gates/rel_stock_st_buslog.txt`, stock cold boot, ST TOS 1.04): `Bus Error reading at address $ffff8e21, PC=$13988` and `$ffff8924, PC=$139b6`; stock STE: `$ffff8e21, PC=$13968`. So these are PP's
hardware-detection reads, handled by the game, identical without our patches. Our code adds exactly one such line, the blitter probe on a machine without a blitter (ST).

## 2. Falcon sound (HD cold boot, 4 MB TOS 4.04)

Real in-game sample, no injection: after play start, F3 and a click on the map (raise land) from `p2rel.py --sound`:

```
SOUND: $2aa74 = 0x4eb90008 0x10804e71 (jsr $81080 ; nop = 4eb9 00081080 4e71)   $134=0x2aa4e
round 0: matched breakpoints so far: 2        <- b pc=$81080 (the hook) and b pc=$2aa4e (the handler) both fired, from a real in-game sample
after: ... turn 551; in_play True
LOG: 170 lines; bus/address-error/halt lines: 0
```

Forced `$ff8007 = $65` (HwScan's method: handler entry patched to `jmp $f0000` whose stub does the three displaced pushes, `move.b #$65,$ff8007` as a CPU write, then `jmp $2aa54`):

```
forced: handler entry 0x4ef9000f; every IRQ does CPU write $ff8007:=$65
round 0: matched breakpoints so far: 2   (hook $81080 + handler)    after: turn 387; in_play True    LOG ... lines: 0   RESULT ok=True errors=0
```

Negative control (same build minus pop2_fal_ym, `build/Pop2ReleaseNoFal`, same forced `$65`): `$2aa74 = 0x03c88df1 0x01888df1` (the original movep pair), and

```
WARN : Bus Error writing at address $ffff8804, PC=$2aa74 addr_e3=2aa74 op_e3=3c8
WARN : Address Error reading at address $dc00e00f ... (machine dies, debugger stops answering)
```

So the fix is what holds the game when the bus-error bit is set. **Falcon floppy sound: could not be run, the floppy does not boot on a Falcon (section 3).**

## 3. Floppy cells (720K `Populous2_boot.st` via `--disk-a`, TOS boots AUTO\RUNME.PRG)

| Cell | in_play / marker | turns/s | errors in log | |
|---|---|---|---|---|
| STE 2 MB TOS 1.62 | yes / P2PO | 6.244 (160,237 cyc/VBL) | 1 PP probe (`$ffff8e21`, PC `$172b6`) | PASS; boot 176 s |
| STE 4 MB TOS 1.62 | yes / P2PO | 6.318 | 0 + probe | PASS |
| Mega STE 4 MB TOS 1.62 (8 MHz, 50 Hz) | yes / P2PO | 6.226 | 0 + probe | PASS |
| **Mega STE 4 MB TOS 2.06 (60 Hz)** | **no**: black screen, turn 0, `$70 = $18fa`, marker P2PO | 0 | `Bus Error reading at address $fffc7d2f, PC=$2d484` (reproduced 3x: `rel_megaste4_floppy*.txt`) | **FAIL** |
| **TT 4 MB TOS 3.06 (60 Hz)** | **no**, turn 0, marker P2PO | 0 | 0 | **FAIL** |
| **Falcon 4 MB TOS 4.04 (50 Hz)** | **no**: PP hardware screen -> space -> `Bus Error writing at address $e09527, PC=$3f94b8` then `... $7, PC=$e0fbe2`; machine dead | | 2 | **FAIL** |

Diagnosis (evidence, not a fix):
* The payload is delivered on every failing machine (marker `P2PO`), RUNME and P2M.FIC load fine, the failure is later.
* GEMDOS trace (`--trace gemdos`): STE floppy `Fopen("P2D") at PC=0x3F9022` is followed by `Fread(6, 418679, 0x101000) at PC 0x3F910E`. On Falcon the trace ends at `Fopen("P2D")`, no `Fread`.
* The code at `$3f8000+` (HAGA's file service, dumped from RAM, capstone): `3f900c moveq #$3d,d0 / 3f9020 trap #1 / 3f9024 move.w d0,d7 / 3f9026 bpl.b $3f9032 / 3f9028 ... bra.w $3f9122` (error path:
  store d0, `$3f9122 move.w #$2700,sr / bsr.w $3f9372` the fade routine, whose `rts` is followed by palette data at `$3f94b8` = the PC of the Falcon bus error). Breakpoint at `$3f9024` on the Mega STE: `D0 FFFFFFFF` (STE TOS 1.62: `D0 00000006`, a handle); Falcon: `D0 FFFFFFD2`.
  So **TOS 2.06 / 4.04's own Fopen of `P2D` from the floppy returns an error**, the stub takes its error path and the game dies. At that moment the MFP interrupt registers read `$fffa07/09/13/15 = 00` (all masked), `$4ba` (hz_200) is not ticking.
  Poking IERB/IMRB (`$20`, `$a0`) and IERA/IMRA before the `trap #1` did NOT change `D0` (still `$FFFFFFFF`): the MFP hypothesis is refuted. Cause unknown beyond "TOS >= 2.06 floppy Fopen fails in this state".
* Not our patches: PP's ORIGINAL `RUNME.TOS` + `HAGA` + `FILES\` put on the same 720K floppy (`build/Pop2ReleaseFstock`) on a Falcon 4 MB ends identically (`Fopen("P2D") ... to TOS`, `Bus Error writing at address $e09527, PC=$3f94b8`, `$7, PC=$e0fbe2`), also with 14 MB. (Mega STE with PP's original on floppy hits the known 60 Hz crash `Bus Error writing at address $2, PC=$2022` first, so it cannot isolate the floppy problem; a floppy build with the 60 Hz fixes but TOS 1.62 passes.)
* Same loader from the HD works on every machine (GEMDOS HD emulation answers the `trap #1`).
* Not an obvious fix (it is inside PP's loader on a TOS-native file system path); no `default: no` patch written. Floppy support is therefore real on TOS 1.xx machines only; FLOPPY.TXT should say so (README text is not changed by this pass).

## 4. STE byte check (sample handler)

`work/gates/rel_ste_bytes.txt`: cold boot STE 2 MB TOS 1.62, dump `$2a900`-`$2aa9f` after reaching play, our default set vs the untouched PP game (`originals/POPUL2`, same boot):

```
differing offsets: ['0x2a938', '0x2a939', '0x2a93b', '0x2a93c', '0x2a93d', '0x2a93e', '0x2a93f']
ours  $2a938: 4eb9000810004e71  stock: 21fc0002aa4e0134
sample handler $2aa4e..$2aaa0 identical: True
ours $2aa74: 03c88df101888df1     (the original movep pair)
```

Only the 8-byte install site `$2a938` differs (byte `$2a93a` is `00` in both, so 7 of the 8 bytes differ), the handler bytes `$2aa4e`-`$2aaa0` are the original ones on the STE.

## 5. Play test, STE 2 MB HD (about 5 min wall incl. boot, `play.py`, `rel_play.txt`)

Mouse and keys: F1-F6, earth category icon + effect + clicks on the map, strip icons 2-6 each with a tooltip shot (`rel_play_tooltip_strip2..6.png`), four rounds of "click strip 3, nudge, click strip 4 within about 0.3 s wall",
three rounds of F3 immediately followed by a click, idle until about 170 s. (First attempt clicked strip icon 1, which is the Game requester `?`; the game then sat in the requester, so that run's low turn rate is not a result.)

```
in_play True marker P2PO turn 122
queue QPUSH/QPOP/QDROP before ['0x0', '0x0', '0x0']
executor dispatches (b pc=$292f8, d0): 43 [2, 2, 4, 2, 4, 18, 2, 20, 14, 4, 16, 4, 18, 20, 18, 20, 4, 18, 20, 18, 20, 18, 4, 18, 18, 4, 4, 4, 4, 4, 2, 2, 2, 4, 4, 2, 2, 4, 2, 2, 2, 2, 2]
queue after ['0x4', '0x4', '0x0'] delta push/pop/drop [4, 4, 0]
turn 1216 in_play True marker P2PO      (turn 122 -> 1216 in about 300 s of scripted play incl. the statesave)
bus/address errors in log: 1  (the PP probe `$ffff8e21`, PC $1b992)
```
All 43 executed commands ran, the queue pushed 4 and popped 4 (the quick pairs), 0 dropped, game stayed in play. Tooltips appeared on category, effect and strip icons (sheet above).

60 Hz STE (STE, TOS 2.06, 2 MB, sync `$fc`, `ste60.py`, `rel_ste60.txt`): pointer swept along the bottom edge 6 times (y=199):

```
STE TOS 2.06 2 MB: in_play=True marker='P2PO' sync=$fc (60 Hz) turn=126 $70=0x18fa
  pass 0: pointer 300,199 turn 168 ... pass 5: pointer 150,199 turn 371
turn 137 -> 404 in_play True        bus/address errors: 1  (PP probe $ffff8e21, PC $2120e)
```
No crash (the old bottom-edge crash does not occur).

## 6. HAGA statesave / restore (HD) and in-game SAVE

* Statesave: KP_Divide in play: `statesave: GS00.TOS 1049310 turn at save 1252 in_play after True turn 1310` (game continues).
* Restore: new Hatari with `--auto C:\GS00.TOS`: `restore: 12s, $70=0x18fa marker='P2PO' turn at save 1252 -> after restore 1269 -> +4 s 1299 in_play=True`, 1 PP probe line, no other errors (`rel_restore.txt`, `rel_restore.png`).
* In-game SAVE GAME click (requester via strip icon 1, then SAVE GAME): ours and the untouched PP game die the same way: `Bus Error reading at address $5c40c82, PC=$5c40c82` followed by `Address Error writing at address $84007c67, PC=$e09598` x1,000+ and `Bus Error writing at address $fffffffe, PC=$fa5a` (identical sequences in `rel_ingamesave_ours.txt` / `rel_ingamesave_stock.txt`). Not worse than stock.

## 7. Not done

* `tools/package.sh` (HD + floppy zips, md5s): not run because the floppy cells fail on TOS >= 2.06; no change made to dist/. The HD zip would be unaffected.
* Falcon floppy sound.
* No new patch written (the floppy failure is not an obvious fix).
