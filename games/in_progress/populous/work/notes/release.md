# Populous: release integration (PopRelease, 2026-11-12)

Release set = the default set (`pop_noprot pop_credit pop_land_mul pop_land_score pop_ptr pop_bgcopy pop_ptrfix pop_fal_ym pop_fal_ym_demo`, HD also `pp_bigram_cache`) + the six tick patches
(`pop_tick pop_tick_render pop_tick_logic pop_tick_flip pop_tick_cmd pop_tick_dot`) + `pop_keys pop_keys2 pop_keys3 pop_keys4` + `pop_tooltip` (20 patches).
Builds: `build/PopRelease/{hd, hd_nofade, hd_def, floppy_full, floppy_def}` (`poppatch.py build --hd|--floppy --only ...`). Hatari 2.6.1, everything below is Hatari, nothing on real hardware.
Raw outputs: `work/gates/release_*.txt`; scratch drivers (not shipped): `work/scratch/release/` (`pexec_probe*.py pdpoll.py loadn.py flsave.py ttshot.py bisect_low.py ...`).

## 1. Falcon floppy with the tick: cause and fix

Symptom (PopTiming): after the DEMO stage `Pexec(3,"populous.tos")` and the fallback `Pexec(0,...)` fail. Evidence (all raw in `work/gates/release_falcon_diag.txt`):

* The Pexec result in d0 (break at `$fce4`, the `lea.l ($0010,a7),a7` after the trap; `$fce6` is the middle of that instruction, so it never fires): **`D0 FFFFFFDD` = -35 = ENHNDL (no more file handles)**, not a memory error. `Malloc(-1)` at that moment: `D0 003CA8BC` (3.97 MB free). `_membot` (`$432`) = `$0000f99c`, `_memtop` (`$436`) = `$00400000`, phystop (`$42e`) = `$00400000` in every run (`m $432 8` / `m $42e 4`, Falcon only; not compared with STE/TT: the failure turned out not to be about memory).
* Cross-check (task item: compare the machines; `pexec_probe.py`, the same Malloc(-1) injection; on the TT the breakpoint address `$fce4` is the Falcon's, so the injection ran at an arbitrary point after the menu click and only shows the order of magnitude): TT TOS 3.06 `_membot` `$E6FC`, `_memtop` `$003DA700`, phystop `$00400000`, Malloc(-1) = `$00310D00` (3.2 MB; the injection ran with the loader at `$E804`); Falcon TOS 4.04 `_membot` `$F99C`, `_memtop` `$00400000`, Malloc(-1) = `$003CA8BC`. STE (TOS 1.62) not probed (machines.md: `_membot` below `$A952`). No machine is short of memory, consistent with the ENHNDL result.
* Three builds fail the same way with `D0 FFFFFFDD`: default + `pop_tick` only (payload block `$B3000-$C7400`), default + a 4 KB dummy data block, the full release set (`Malloc(0x16600)`); the default set alone (`Malloc(0x12600)`, `$B3000-$C5400`) gives `D0 0000FEAC`. The tick patches themselves are innocent: a dummy data block of the same size breaks it.
* Where -35 comes from (ROM `$E1B0AE`, the GEMDOS open): `bsr.w $e1a724` (find a free handle: `move.w $3a(a0),d7` = the handle count of the current process descriptor, table at `$3c(a0)`) returned -1.
* The loader's descriptor at `$FB6C`: `+$30..$3f` = `00 .. 00 19 00 00 fb 06` (count `$0019`, table `$FB06`) in the working run, `00 .. 00 00 00 00 ff ff` (count 0, table `$0000FFFF`) in the failing ones. `pdpoll.py` shows it change between 8.6 s (`... 00 19 00 00 fb 06`) and 13.9 s (`... 00 00 ff ff`), i.e. during the loader's payload read for the DEMO stage.
* Writer: a condition breakpoint `a7 < $fbc0 && a7 > $fb6c` armed at the loader's first instruction fires in XBIOS `Floprd` (ROM `$E03C62`, `A6 = $FFFF8606`) with `A7 = $0000FBBA`, `USP = $0000FC4C`; the first descriptor hit has `A7 = $FBA4`. TOS 4.04's trap 13/14 handler does `btst.b #$d,d0 / bne / move usp,a7` (ROM `$E00D9E`), so **the BIOS runs on the caller's user stack**. The loader's stack is the 128-byte command-line area of its own base page (`lea $100(a3),a7`), directly above the descriptor's reserved words (`$30-$7F`): a deep `Floprd` plus the interrupts that nest on it ($A8 bytes seen) runs through them. How deep it gets depends on interrupt timing, which is why the default set (fewer/shorter reads) happened to survive. [INFERENCE: STE (TOS 1.62) and TT (TOS 3.06) cells passed with the same loader; I did not look at their descriptors.] [INFERENCE: why exactly the larger payloads hit the deeper nesting; the writer and the victim words are observed, the timing dependence is the explanation that fits "same code, only the read length and Malloc size differ".]
* **Fix** (`patches/loader.s`, floppy only): `readpay` and the payload's `apply` run on a stack inside the payload block (1 KB below the directory buffer, old SP saved on it); `poppatch.py` adds 1 KB to PSPAN. Loader text `$1d6` -> `$1e4` (the Mshrink block stays below the STE limit `$2F8`).
* Proof: `pdpoll.py` on the dummy build (failed 3 times before): descriptor stays `00 19 00 00 fb 06`, one `Pexec(3, "populous.tos")`, no `Pexec(0)` fallback. Falcon floppy cold boot with the full release set: see the table (`POPO`, 4.998 turns/s, 0 errors, reproduced twice).
* The HD build's loader is byte-identical to before (POLA md5 `4dc289a7f1ef169f8ba7360914e301a5`).

## 2. A second regression found and fixed: "Too much low RAM occupied" (STE 1 MB, TOS 2.06)

With the release set the HD build on a 1 MB STE with TOS 2.06 stopped at PP's RUNME message `Too much low RAM occupied. Read usage how to fix it.` (the stock game and the default-set HD build boot fine: hardware screen). The check is RUNME text `$ca-$d0` (`cmpa.l #$4baf0,a1 / bcc` for 1 MB; `a1` = the bss pointer + `$8000` + `$16c00`) and the bss moved by the whole payload image (88 KB: the image is contiguous from `$B3000` to `$C8964`, mostly zeros between the blob groups). Bisect with a dummy data block (`bisect_low.py`, same build, 1 MB STE TOS 2.06): payload 82,056 B passes, 86,056 B fails.
Fix (`poppatch.py`, `runme_segments` + new `stage_code`): RUNME carries only the used parts of the image (segment table + segments, gaps < 256 B merged) and its stage routine copies each segment to its address: **16,904 B in 12 segments instead of 88,420 B** for the release set (7,432 B / 7 segments for the default set), RUNME.TOS 33,673 B (was 105,109 B). The same function exists for the floppy (`payload_segments`). The release build now boots on that cell. Gaps between segments are no longer zeroed by the copy (they were zero in the old image): every cold boot below was run with the sparse RUNME.

## 3. Build acceptance (IMG_LIMIT)

`poppatch.py build` accepts the release set on HD and floppy. `IMG_LIMIT = $C8000` is only the limit for blob `org`s (the UI blobs end at `$C7901`); the data blocks (`$C8000+32`, `$C8200+1184`) and the relocation list lie above it and are covered by the separate check "relocation list ends past `$CFC36`" (the image spans `$B3000-$C8964`, 88,420 B). Nothing to change.

## 4. Gates (raw: `work/gates/release_*.txt`)

World by turn, tick vs original, both runs carrying the release set (`poptick.py ab SNAP MHZ 130 --release`; `--release` = defaults + `pop_ptrfix` + keys + tooltip in both runs, new flag), `release_ab.txt`:
```
busy_castles @8 MHz 50 Hz: IDENTICAL | world at pass tops: 170 compared (0 differ) over 130 turns, max 2 tops/turn | T frames 128 compared (0 differ; 0 excluded) | R frames: 42 (0 stability pairs, 0 unstable; 30 minimap compares, 0 differ, 12 turns excluded ...) | pass kinds T 129 R 42 S 0 | turns/s base 6.000 patched 4.973
genesis_start @8 MHz 50 Hz: IDENTICAL | world at pass tops: 262 compared (0 differ) over 130 turns, max 3 tops/turn | T frames 128 compared (0 differ; 0 excluded) | R frames: 135 (7 stability pairs, 0 unstable; 117 minimap compares, 0 differ, 16 turns excluded ...) | pass kinds T 129 R 135 S 0 | turns/s base 9.729 patched 5.012
busy_castles @16 MHz 50 Hz: IDENTICAL | world at pass tops: 437 compared (0 differ) over 130 turns, max 4 tops/turn | T frames 128 compared (0 differ; 0 excluded) | R frames: 311 (182 stability pairs, 0 unstable; 216 minimap compares, 0 differ, 38 turns excluded ...) | pass kinds T 129 R 311 S 0 | turns/s base 12.476 patched 5.016
genesis_start @16 MHz 50 Hz, view still, --render: IDENTICAL | world at pass tops: 557 compared (0 differ) over 130 turns | T frames 128 compared (0 differ) | R frames: 432 (302 stability pairs, 0 unstable; 376 minimap compares, 0 differ ...; 429 render-only compares vs the original render, 0 differ) | pass kinds T 129 R 432 S 0 | turns/s base 20.156 patched 5.023
```
Keys under the tick (`popuitest.py final --path build/PopRelease/hd --orders-pc 1e750`, cold-booted release HD build, real keys through IKBD/ACIA; the order is read at the executor `$1e750` because `pop_tick_cmd` moved the call site `$bbfa`; `key->order` = VBLs from the key store `$2008c` to the executor entry with the order set; `release_ui_final_sparse.txt`):
```
in play: True marker 0x504f504f
knight       [(14, 0, 5)]   {'mana': -7472}   | click [(14, 0, 5)]  | key->order 5 VBL
view_knight  []  {'view': ((0, 0), (2, 18))}  | click view (2,18)->(8,18)
view_battle  []  {} ... query {'mode': (2, 1)} raise {'mode': (1, 2)} magnet_mode {'mode': (2, 6)}
to_magnet    [(14, 0, 1)]   {'beh': (1, 0)}   | click [(14, 0, 1)]  | 1 VBL      settle [(14, 1, 1)] 4 VBL    gather [(14, 2, 1)] 5 VBL    fight [(14, 3, 1)] 6 VBL
view_leader / view_magnet / view_house: view changes;  music, effects (each twice): {'music': (1, 0)} / {'fx': (1, 0)}, the click toggles back
swamp        []  {'mode': (6, 10)}
earthquake   [(3, 12, 7)]   {'mana': -2472}   | click [(3, 12, 7)]  | 0 VBL      volcano [(6, 12, 7)] {'mana': -9960} 1 VBL      flood [(14, 0, 4)] {'mana': -39962} 1 VBL
pause (x2)   [(14, 0, 6)]   {'pause': (0, 1)} | click [(14, 0, 6)]  | 12 VBL, 2 VBL   armageddon (A twice) [(14, 0, 3)] | click [(14, 0, 3)] | 2 VBL
```
Every key acts, with the same orders as the click (same as `ui_final_keys.txt` of PopUI: identical order tuples except the third byte of earthquake/volcano, 7 here and 6 there, equal for key and click in both runs); latency 0-12 VBL (the executor runs in turn passes, 10 VBL apart; the 12 is the first `pause` press) = at most about one turn (0.24 s).

Tooltip in a render-only pass (`ttshot.py`, genesis_start, 16 MHz, live release + tick set, pointer on icon 1): a breakpoint after the flip (`pc = $b946 && ($c6010).w = 1`, the tick's RON flag) saved the displayed buffer `$57200`, palette and flag: `{'R': ('0x57200', 1, ...release_tooltip_Rpass_icon1.png), 'T': ('0x4f500', 0, ...release_tooltip_Tpass_icon1.png)}`. The R frame shows `FLOOD (F)` / `COST 40K` in the two tooltip rectangles (`work/shots/release_tooltip_Rpass_icon1.png`, `_top.png` = 4x crop; the T-pass frame is next to it).

Pixel gate (popabtest machinery), pointer away from every icon, the whole non-tick set vs unpatched, 305 flips x 3 snapshots, both buffers + world every flip + mid-frame samples (`popuitest.py gate --away`, `release_gate_away.txt`):
```
busy_castles         <13 patches> IDENTICAL: flips compared 305, mid-frame samples 610, bad flips 0, bad samples 0, world 0; samples in one run only: ref 0, new 0
busy_quake_volcano   <13 patches> IDENTICAL: flips compared 305, mid-frame samples 608, bad flips 0, bad samples 0, world 0; samples in one run only: ref 2, new 0
genesis_start        <13 patches> IDENTICAL: flips compared 305, mid-frame samples 380, bad flips 0, bad samples 0, world 0; samples in one run only: ref 228, new 0
GATE IDENTICAL (exit 0)
```
(the 13 = defaults without `pop_ptrfix` + keys + tooltip; `pop_ptrfix` cannot be in this gate: popabtest's input scaffolding owns the IKBD handler, so it is gated in popabtest's own set:) `popabtest.py gate --set pop_noprot pop_land_mul pop_land_score pop_ptr pop_bgcopy pop_ptrfix` (with its garbage packets): `release_gate_display.txt`: IDENTICAL on busy_castles, busy_quake_volcano, genesis_start, 305 flips each, bad flips 0, `GATE IDENTICAL (exit 0)`.
Two fixes to the tools on the way: `popuitest.py gate` named its live image after the whole set, and the debugger silently truncated the long `loadbin` line (13 names: the image never loaded, the game jumped to 0: `Bus Error reading at address $0, PC=$0`); the name is now a hash. Its verdict no longer counts mid-frame samples that exist in one run only (a faster patched frame has fewer VBLs; popabtest never counted them).
**popabtest with the tick: cannot run**: its comparison pairs flip i of one run with turn T0+i of the other ("the world is frame-coupled, one turn per pass"), and with the tick a flip is not a turn (S passes have no flip, R passes flip without a turn). The by-turn equivalent is `poptick.py ab` above (R-pass frames vs the original render: 429 compares, 0 differ).

## 5. Cold boots (release set, marker `POPO`, `$b632` = `4ef9 000c5000` = pop_tick; `cell.py`; turns per emulated second over 1500-2000 VBL)

| cell | build | clock / Hz | world turns/s (tick) | passes T / R / S | Bus / Address errors in log |
|---|---|---|---|---|---|
| STE 1 MB TOS 1.62 | hd | 8 MHz, 50 | 4.997 | 150 / 156 / 0 | 1 (caught boot probe, see below) |
| STE 1 MB TOS 1.62 | hd | 16 MHz, 50 | 5.030 (ticks 4.997) | 150 / 493 / 0 | same 1 |
| STE 4 MB TOS 1.62 | hd | 8 MHz, 50 | 4.997 | 151 / 155 / 0 | same 1 |
| ST 1 MB TOS 1.04 | hd | 8 MHz, 50 | 4.997 | 150 / 154 / 0 | 3 (boot probes) |
| Mega STE 4 MB TOS 2.06 | hd | 16 MHz, 50 | 4.997 | 151 / 297 / 0 | 0 |
| STE 1 MB TOS 2.06 (60 Hz) | hd | 8 MHz, 60 | 4.964 (ticks 4.997) | 150 / 151 / 0 | 1 |
| STE 1 MB TOS 1.62 | floppy_full | 8 MHz, 50 | 4.997 | 150 / 159 / 0 | 0 |
| TT 4 MB TOS 3.06 `--mmu` | floppy_full | 32 MHz, 50 | 4.997 (D = $3E56) | 150 / 1350 / 0 | 0 |
| Falcon 4 MB TOS 4.04 | floppy_full | 16 MHz, 50 | **4.998** (D = $5222, `POPO`) | 200 / 1309 / 0 | 0 |

The caught bus errors are all PP's hardware probes at boot, before the game (lines 4, 5, 17 of 129 log lines on the ST): `Bus Error reading at address $ffff8e21` (Mega STE cache register), `$ffff8924` (STE DMA sound) and `$ffff8a00` (blitter, `PC=$d0926`); none after the game starts. Raw: `release_cold_hd_sparse.txt` (STE 1/4 MB, ST, Mega STE), `release_loadn_sparse.txt` (STE 60 Hz first line), `release_cold_stefloppy.txt`, `release_cold_ttfloppy.txt`, `release_cold_falcon_floppy.txt`. `D` values: payload `RELDLT` after the loader change (TT `$3E56`, Falcon `$5222`).
Note: the 1 MB STE with TOS 2.06 only boots since the sparse RUNME (section 2).

## 6. In-game SAVE and LOAD

* STE HD (release set, `loadn.py`, Section 7 for the repeated version): SAVE "tst", LOAD, MOVE TO NEXT MAP all work (turn 108 saved -> 127/128 six seconds after each LOAD; next map turn 51).
* STE floppy (`flsave.py`, `release_floppy_saveload.txt`): cold boot, play (turn 16 -> 29), GAME SETUP -> SAVE A GAME "tst" with `Populous_save.st` in A: -> the game asks `INSERT THE ORIGINAL POPULOUS DISK IN A:` (shot `release_fl_save_prompt.png`), boot disk back, OK -> back in play; save disk root: `('TST     GAM', 29646)`; LOAD with the save disk in A:, the file TST, LOAD -> the same prompt (`release_fl_load_prompt.png`, one OK button at the right), boot disk back, OK:
```
'(VBL, turn) after the load': [(14624, 46), (14944, 64), (15265, 95), (15585, 127)], 'turns per VBL (expect 0.100 at 50 Hz)': 0.0843   (the first interval includes the load settling; the last two: 31 and 32 turns per 320 VBL = 0.0997)
'bus/address errors in log': [], 'payload': '50 4f 50 50 50 4f 50 4f 00 00 00 02', 'ee16': '60 52', 'b632': '4e f9 00 0c 50 00'
```

## 7. pp_nofade with repeated LOADs (HD only; the HAGA fade patch; lead's question)

`loadn.py`: cold boot the HD build (release set + `pp_nofade`, `build/PopRelease/hd_nofade`), SAVE "tst", then **5 LOADs in a row** (each: GAME SETUP globe, LOAD A GAME, TST, LOAD, 6 s run), then a 6th LOAD + **MOVE TO NEXT MAP**. Counters: bus / address errors after the game started (boot probes at `$ffff8...` excluded; the total with probes is in the last column), `pop_ptrfix` drop events (breakpoint at the blob's drop `rts` `$c283c` with a bad button/x/y byte; each event prints the dropped packet):

| cell | marker / play | 5 LOADs (turn before the click, 6 s after) | LOAD + NEXT MAP (turn after) | errors in game | dropped packets | errors incl. boot probes |
|---|---|---|---|---|---|---|
| STE 1 MB TOS 1.62 | POPO / playing | (132,127) (150,128) (151,127) (150,128) (151,127) | 51, playing | 0 | 0 | 1 |
| STE 4 MB TOS 1.62 | POPO / playing | (136,127) (150,128) (151,128) (151,128) (151,128) | 51, playing | 0 | 5 (`00 00 6e f7 08 0c` x4, `00 00 f7 08 00 0c`) | 1 |
| ST 1 MB TOS 1.04 | POPO / playing | (131,127) (150,128) (151,127) (150,127) (151,127) | 50, playing | 0 | 0 | 3 |
| Mega STE 4 MB TOS 2.06, 16 MHz | POPO / playing | (135,134) (157,135) (158,135) (158,135) (158,135) | 56, playing | 0 | 6 (`00 f7 00 00 6e 0c`, `00 00 6e 00 f7 0c` x5) | 0 |

Control (`hd`, same set WITHOUT `pp_nofade`, STE 1 MB, pre-sparse build, `release_loadn_ste1mb_nofade_off.txt`): 5 LOADs + next map, no error, 4 packets dropped (`00 00 6e f7 00 0c` x4): the misframed IKBD packets exist with and without the fade patch; `pop_ptrfix` drops them. Without `pop_ptrfix` the history is `work/notes/display.md` section 9 (STE crashed on every LOAD with `pp_nofade`, Mega STE without it too).
**Recommendation: `pp_nofade` ON, only together with `pop_ptrfix`** (it is `; default: no` in its header; flipping it is the lead's edit). 0 bus / address errors in 4 cells x 6 LOADs + 4 next-map loads (Hatari); 11 misframed packets seen, all dropped by `pop_ptrfix`. Not covered: real hardware (the packet framing depends on real ACIA timing), floppy (no HAGA there), TT/Falcon (HD does not boot there in Hatari).

## 8. Open

* `popabtest` itself with the tick (section 4: impossible by design; `poptick.py ab --render` is the by-turn equivalent).
* Falcon HD, TT HD: not bootable in Hatari with stock PP (machines.md).
* The cause of the Falcon failure is proven down to the overwritten words and the stack the BIOS runs on; why the default set's shorter run escaped is [INFERENCE] (timing of interrupts inside Floprd).

## 9. All-games image, Populous on an STE with TOS 1.62 (ACSI + HDDRIVER): marker `POPF`, "Starting GOS ...", bombs (PopRelease, later the same day)

Repro (lead): `python3 tools/test_hd_image.py dist/AtariST_enhanced_games_2026-11-12.img pop --machine ste --tos 1.62 --mem 1024` -> `MARKER=POPP+POPF ... turn=0 meta=000c86a0 00000000`. Raw: the lead's line above; my probes in `work/scratch/release/imgpop_*.py`.

**Two different things hide behind that line.**

1. **`POPF` is mostly a harness artefact.** `POPF` is the marker the payload is built with; `POPO` is only written when the POPULOUS.TOS sites were applied. `test_hd_image.py pop` uses `boot_to_game()` with fixed waits (16 + 22 + 9 + 10 s). Through HDDRIVER the game needs longer (menu at 41 s on an STE, 118 s on the Mega STE) so the check runs before START GAME: only the DEMO apply (`$b3010` hit once, `D0 = 0` = DEMO, `A1 = $AC96` = base page `$AC96`, delta 0) has happened; `meta = 000c86a0 00000000` is just "reloc list at `$C86A0`, delta 0". At 4 MB the unpatched-by-timing image played fine: patient driver, STE 1.62 4 MB, old image: `marker POPP POPO`, hook `4ef9 000c5000`, 5.0 turns/s. The new tool `tools/pop_image_test.py` waits for the menu and for the hook.
2. **At 1 MB it really crashed, and the cause is a memory overlap with PP's own code.**
   * GEMDOS trace: `Mshrink(0xA892, 0x88A0)` (HDDRIVER ends at `$B1132`), `_memtop` = `$F8000` while phystop = `$100000` (HDDRIVER keeps `$F8000-$FFFFF`); HAGA still goes to `$F8000`.
   * A CPU breakpoint on the first `pc > $fffff` (a jump out of RAM) with `history 60`: the last instructions are HAGA's `$FAEA6 movea.l $f80a6(pc),a1 / lea $faeb4(pc),a2 / move.l a2,-$ca(a1) / jmp (a1)`, `A1 = $000C4000`, and what executes at `$C4000` is **our blob** (`4841 0388 8800 ... 4e75`, pop_fal_ym_demo): `00c4000 4841 swap d1 / 0388 8800 movep.w d1,-$7800(a0)`; then the CPU runs through zeroed RAM up to `$3ffffc` (`Bus Error reading at address $400000, PC=$3ffffc`).
   * In the stock image (and any build whose payload ends below `$C4000`) the same breakpoint shows `jmp (a1) == $000c4000` with `m $c4000` = `60 2e 01 04 00 0c 40 30 00 0c 40 00 00 00 61 1c ...`: **PP's "GOS" code (unpacked by HAGA from `D15RH.FIC`, header says it runs to `$D6CC0`) is loaded at `$C4000`** and our copy at `$C4000-$C4054` overwrote its entry. HAGA's header words at `$F80A0`: `00 0f 7f 26 | 00 00 00 0c 40 00 | 00 08 23 88 ...` hold the address. It is `memtop - $34000` on a 1 MB machine (`$C4000` with HDDRIVER, `$CC000` without [INFERENCE: the GEMDOS-drive value was not measured]); at 4 MB the same jump is `$3A8C00`, which is why 4 MB never collided.
   * Bisect that proves it (`mkvar.py`, stock image + a RUNME that copies only the first N segments): N = 1, 2, 3, 6 (last segment ends `$C2840`) run; N = 7 (adds `$C4000-$C4054`), 8, 9, 12 crash the same way. RUNME sizes 24,045 B pass, 24,135 B fail: nothing to do with RUNME's own end.
   * The old claim "`$B1D40-$CFC36` is free" (delivery.md) was measured on a GEMDOS drive at 1 MB where the GOS block sits higher; with HDDRIVER it begins at `$C4000`.

**Fix: the payload now lives entirely in `$B3000-$BDFFF`.** Every payload address in `$C0000-$C8FFF` moved down by `$B000` (`$C0000` -> `$B5000`, `$C8000` -> `$BD000`; one rule, applied to `patches/*.s`, the tools and the README; older notes and gate files keep the old numbers: add `$B000` -> subtract it): land score `$B5000`, land mul `$B6000`, ptr `$B7000` (data `$B7400`), bgcopy `$B7600`, ptrfix `$B7800`, Falcon YM `$B9000/$B9040`, tick `$BA000` (data `$BB000`, test data `$BBF40`), keys/tooltip `$BC000-$BC904` (data `$BD000`, `$BD200`), relocation list `$BD6A0`. `poppatch.py`: `IMG_LIMIT = $BD000` (blob orgs), new `PAYLOAD_END = $C4000` (the build refuses a payload that reaches it; this replaces the old `$CFC37` check). Span `$B3000-$BDB64` (43,364 B), 16,904 B in 12 segments copied by RUNME. The tick hook is now `4ef9 000ba000` at `$b632`.
Margin below PP's GOS block on 1 MB + HDDRIVER: `$C4000 - $BDB64` = about 5 KB; another resident program that lowers `_memtop` further would reach the payload again [INFERENCE, not tested].

### Proof (image rebuilt: `python3 tools/make_hd_image.py`, md5 `f95cee6e5d439e266ba464b18ec13551`; Populous files in it: RUNME.TOS `51abf53db665c2f888c6c24219cec587`, HAGA `1074342dd4a917bafdc7d2a031e9b088`, FILES\POLA `4dc289a7f1ef169f8ba7360914e301a5`)
`python3 tools/pop_image_test.py dist/AtariST_enhanced_games_2026-11-12.img MACHINE TOS MEM [CPU]`:
```
RESULT ste 1.62 1024 {'menu': True, 't_menu': 41, 'hook': '4e f9 00 0b a0 00', 'marker': '50 4f 50 50 50 4f 50 4f 00 00 00 03', 't_play': 65, 'Hz': 50, 'turns/emulated s': 4.995, 'cycles/VBL': 160119, '$ff8e21': 'ff', 'ee16': '60 52', ...}
RESULT ste 1.62 4096 {'menu': True, 't_menu': 41, ..., 'marker': '50 4f 50 50 50 4f 50 4f ...', 't_play': 65, 'Hz': 50, 'turns/emulated s': 4.995, 'cycles/VBL': 160111, 'ee16': '60 52', ...}
RESULT st 1.04 1024 {'menu': True, 't_menu': 46, ..., 'marker': 'POPP POPO', 't_play': 69, 'Hz': 50, 'turns/emulated s': 4.995, 'cycles/VBL': 160217, ...}
RESULT megaste 2.06 4096 (16 MHz) {'menu': True, 't_menu': 118, ..., 'marker': 'POPP POPO', 't_play': 142, 'Hz': 60, 'turns/emulated s': 5.035, 'cycles/VBL': 267040, '$ff8e21': '03', ...}
```
(the Mega STE's TOS 2.06 boots at 60 Hz: 16 MHz / 60 = 266,667 cycles per VBL; an earlier line of 4.2 "turns/s" was my tool dividing by 50.) The `errors` of every image cell are only boot probes by HDDRIVER and PP: `$fff00039/79/b9/f9` (SCSI probe, PC in HDDRIVER), `$ffff8781`, `$ffff8e21`, on the ST also `$ffff8924`, `$ffff8a00`.
GEMDOS-drive regression, `build/dist_hd` (= the zip content), STE 1 MB TOS 1.62: `RESULT cold ste gemdos dist_hd 8 MHz 50 Hz: ... 4.997/s | passes T 150 R 155 S 0 P 0` and `16 MHz: ... 4.997/s | T 150 R 485`, hook `4ef9000ba000`, 1 bus error (`$ffff8e21`, PP's probe).
Gates re-run after the address move (the tools were moved with it): `poptick.py ab --release` busy_castles 8 MHz IDENTICAL (170 tops, 0 differ, 4.973 turns/s) and genesis_start 16 MHz `--still --render` IDENTICAL (557 tops, 429 render-only compares, 0 differ, 5.023), `popuitest.py gate --away` (13 non-tick patches) IDENTICAL on 3 snapshots, `popabtest.py gate` (display set with `pop_ptrfix`) IDENTICAL on 3 snapshots, `poppatch.py verify: ALL OK` (`work/gates/release_ab_shifted.txt`, `release_gates_shifted.txt`). Floppy (`build/dist_floppy`): STE `4.997/s`, `POPO`, hook `4ef9000ba000`, 0 errors.

Tool changes: `tools/pop_image_test.py` (new: patient image driver, reads Hz from `$ff820a`, sets the Mega STE clock after HAGA's screen, samples VBL / turn / cycles at one breakpoint), `work/ref/menu_buttons.png` (git-ignored crop used by it). `tools/test_hd_image.py pop` (lead's) still has the fixed waits: its `POPF` / `turn=22574` result means "not there yet", not a failure.
`tools/package.sh` after the move: RUNME `51abf53d…`, POLA `4dc289a7…`, HAGA `1074342d…`, Populous_boot.st `1fc422beed5a29f624518a1007f3d8c4`, Populous_save.st `af93f79a467c48583608189eaff5f9d3`, `dist/Populous_v1.0_patched_hd_2026-11-12.zip` `40a9d02f325245a014a8c811ea117e53`, `dist/Populous_v1.0_patched_floppy_2026-11-12.zip` `cbe906e0aa6c81ace53a55ef3256742a`. Floppy cells with this build: Falcon `4.997/s` (D = $5222), TT `4.997/s` (D = $3E56), STE `4.997/s`, 0 bus errors each.
