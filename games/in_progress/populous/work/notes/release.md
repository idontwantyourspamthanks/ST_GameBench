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
