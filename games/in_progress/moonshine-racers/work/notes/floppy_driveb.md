# Moonshine Racers floppy: disk 2 in drive B (2026-11-17)

Request (user, from the ORIGINAL disks): "only loads the first drive; can we add drive 2 support like we did for Midwinter 1?" - disk 2 in the second drive
must work (two-drive STs, MiSTer ST core), disk 1 from A, disk 2 from B; one drive (disk swap in A) must behave as before.
Tools: `work/fdb/fdb.py` (Hatari 2.6.1 cells, **real FDC timing `--fastfdc no`**, `--trace fdc`; a copy of the `msrfloppy.py gate` logic with drive-B modes),
`work/fdb/msrpatch_priv.py` (private copy of `tools/msrpatch.py`, re-synced after MSRCredit's stage-1 phase landed: byte-identical except the `ROOT` line; the early cells (`db_*`) were built with the earlier copy + an env hook that forced `default: yes`), patch `patches/fl_driveb.s`. Raw cell outputs: `work/fdb/out/*.log` (+ `*_prompt.png`, `*_race.png`, `*_fdc_after_insert.txt`).
[INFERENCE] marks what was not proven. Real STE / real drives / MiSTer: NOT tested.

## 1. Decision gate: does the shipped/our floppy set already load disk 2 from drive B?  NO (all six cells FAIL)

Cells: `insB` = disk 1 (A) only until the game's own "Insert Disk 2 and press a key." prompt, then `hatari-option --disk-b <copy of disk 2>` and SPACE;
`startB` = disk 2 in drive B from power-on. STE TOS 1.62, 1 MB, real FDC timing, 40 s watched after the key. Pass = the prompt goes away, `$100e` advances,
FDC trace shows `drive=1` reads. Raw: `work/fdb/out/{our,orig,stale}_{insB,startB}_ste*`.

```
cell               disk A (md5)                                       result
our_insB_ste       fresh build work/fdb/build   (ef14ba13...)         FAIL: prompt stays, $100e 46 -> 46, fdc reads: drive=0 1236, drive=1 0 (after insert: 1 read of drive 0)
our_startB_ste     same                                              FAIL: prompt, $100e 42 stuck, drive=1 reads 0
orig_insB_ste      unpatched original conversion work/floppy/disk_a.st (25145b01...; manual question answered by the harness from RAM, "HOT") FAIL: prompt stays, drive=0 1129 reads, drive=1 0
orig_startB_ste    same                                              FAIL (answer "WHO"), drive=1 0
stale_insB_ste     dist/MoonshineRacers_floppy_v1.0.zip disk A (c5450094...)  FAIL, drive=1 0 (the zip's disk B is byte-identical to the original: 0d0be455...)
stale_startB_ste   same                                              FAIL, drive=1 0
```
So the observation holds for the original game AND for every build of ours: the game never touches drive B (our build leaves the game's code as it is).

## 2. The game's disk code (disassembly of `work/floppy/ram_answered.bin`, the original floppy game after the protection)

* **One FDC driver, own code** (no TOS Floprd): `sub_00cac0` (movem; link) with the sole entry `sub_00d6fa` (`jmp $cac0` twice; no other caller of `$cac0`).
  `d6fa`: `cmpi.w #$320,d1 / bcc`: `d0 = 0` (sector < 800) or `d1 -= 800; d0 = 4`. Device word d0: **bit 0 = unit (drive)**, bit 2 = side 1 (`rol.l #1` of the rotated word, read by `$cef4`), bit 3 = a sides flag (`ror.l #3`). Both callers pass bit 0 = 0, so the unit is always 0 = drive A. `d3` low byte = command (0 read; all 12 callers
  in the dump pass `moveq #0,d3` / `move.w #0|$8000,d3`; the write/format code exists in the driver (`$cc9c`/`$cd1e`) but nothing calls it for the floppy release [INFERENCE: overlays loaded later were not searched]).
* The driver is already two-drive aware: `sub_00cece` (drive select) = PSG port A bits `(unit+1)*2` (2 = A, 4 = B) | side bit, written by `sub_00cf0e` (`$ff8800` reg 14, `$ff8802`),
  deselect (`moveq #7,d0`) at the end of every command (`sub_00ce96`); **per-unit head position table at `$cfac`** (word per unit, `$ffff` = unknown): `sub_00ce64` loads the track register from it
  (`$ffff >> 1 = $7fff >= $a0` => restore first, `sub_00ce4e`) and `sub_00ce96` stores the position back. That is the "one FD1772 track register, two drives" bookkeeping of
  Midwinter 1 (`work/notes/floppy_driveb.md` there), here already in the game.
* **Bounded waits** (why an absent drive cannot hang the game's own reads): restore/seek `sub_00cf2c` waits `$60000` loops for the FDC interrupt (GPIP bit 5) then forced interrupt `$d0`
  (`sub_00cf5a`), the sector read loop `$cc48` `$40000` loops then forced interrupt and returns `$ff`. No unbounded loop in the path.
* **The game identifies disks only by their boot sector** (no label/serial check beyond this): `sub_00d798` reads sector 1 (d1 = 0, d2 = 1) of the disk in the drive into `$68000`;
  `sub_00d788` (disk 2) compares the long at `$6800e` with `$66055505`, `sub_00d778` (disk 1) the long at `$68002` with `'MOON'`. Callers of `d788`: the "Insert Disk 2 and press a key."
  loops at `$751c`, `$75e8`, `$76f4` (race load, text `$6143`, `jsr $735a` = wait for a key) and `$16718`. `d778` has no direct caller in the dump
  (the "Insert Disk 1" flow is presumably in code loaded later) [INFERENCE]; the patch treats it the same way as disk 2.

## 3. The patch `patches/fl_driveb.s` (`media: floppy`, site `$d6fa`, 26 bytes -> `jmp $B8E00.l`, blob `$B8E00-$B8EA3`, 164 B, variables `unit`@`$B8E9E`, `pref[2]`@`$B8EA0`)

```
d6fa (orig 0c41 0320 6408 7000 4ef9 0000cac0 0441 0320 7004 4ef9 0000cac0)  ->  4ef9 000b8e00 + 10 nops
blob: cmpi.l #$d7b2,(sp) ; beq probe   ; $d7b2 = the return address inside sub_00d798: this is a disk-check boot sector read
      bsr rd ; rts                      ; every other read: unit of the last successful check
rd:   d0 = (d3.b == 0 ? unit : 0); d1 >= $320 -> d1 -= $320, d0 += 4; jmp $cac0   ; = the original d6fa with the unit ORed into the device word; writes stay on drive A
probe: slot = (4(sp) == $d78a) ? disk 2 : disk 1    ; 4(sp) = return address into sub_00d788 / sub_00d778
       unit = pref[slot]  (A at power-on)
       2 tries: clear the two probe longs ($68002, $6800e), read the boot sector with the game's own driver (rd),
                compare the slot's long; match -> pref[slot] = unit, return; else unit ^= 1 (flips back after the 2nd failure)
```
Behaviour:
* **one drive, swap route** (disk 2 into A at the prompt): unchanged results; the first failing check (disk 1 in A) also probes B (below), then the prompt; after the swap A matches at once, `pref[1] = A`.
* **two drives**: first check A (disk 1: mismatch, readable) -> B (disk 2: match) -> `pref[1] = B`, `unit = B`: the race load (100 sectors) is read from B, every later disk 2 check starts on B.
  Disk 1 stays in A (`pref[0] = A`). Disk 2 already in B at power-on: the prompt never appears (the first check finds it).
* **absent / empty / wrong disk in B**: the probe of B is bounded by the driver's own waits (restore `$60000` x2 + read `$40000` loops, forced interrupts): no hang. The probe never trusts a status code: the two compared
  longs are zeroed before each read, so only data that really arrived in the buffer can match (the role of the DMA-pointer test in MW1; Hatari and the real FD1772 leave status "ok" after a forced interrupt).
  After both drives fail `unit` is back at the preferred drive and the caller shows its original prompt; the next key press repeats the check (cost: see 5).
* **FDC track register**: the driver's per-unit `$cfac` table does it (first use of B: restore, since `$ffff`); the blob does no FDC access of its own.
* **Writes** (`d3.b != 0`: none exist for the floppy release) are pinned to drive A.
* The `$B2700` payload/trampoline is untouched; one site, one blob (`msrpatch.py verify` pairs it with every other patch: ALL OK, blob `$B8E00` lies in the gap between `mg_sync`'s blob and its data `$B8F00`).
* Merge note for MSRCredit's `tools/msrpatch.py` change: `fl_driveb.s` uses only existing headers (`name default media site orig doc note`, no `phase`), nothing in `tools/` was edited; `work/fdb/msrpatch_priv.py` = the current `tools/msrpatch.py` (with `phase: stage1`) with its `ROOT` fixed; `verify` ALL OK in both.

Headers as written:
```
; name: fl_driveb
; default: yes
; media: floppy
; site: $d6fa
; orig: 0c410320640870004ef90000cac00441032070044ef90000cac0
```

## 4. Gates (build `work/fdb/build_db`: all default patches + `fl_driveb`; Hatari 2.6.1, `--fastfdc no`; each success cell = prompt gone, `$100e` advancing, marker `MSPO` at `$b2700`, FDC `drive=1` reads)

```
cell (work/fdb/out/NAME.log)  machine, drive B           mode    disk-2 prompt            result   $100e advancing   fdc reads (whole run)     fl_driveb vars (unit; pref0,pref1)
db_swapA_ste                  STE 1.62 1 MB, B empty     swapA   shown                    OK       329 -> 399        drive0 1335 / drive1 0    (see _v cell)
db_swapA_ste_v                STE 1.62 1 MB              swapA   shown                    OK       343 -> 417        1335 / 0                  unit=0 pref=0,0 (blob state untouched)
db_swapA_nob_ste              STE 1.62 1 MB, --drive-b false (ONE drive)  swapA  shown   OK       347 -> 418        1335 / 0
db_swapA_ste4m                STE 1.62 4 MB              swapA   shown                    OK       321 -> 391        1335 / 0
db_swapA_mste4m               Mega STE 2.06 4 MB         swapA   shown                    OK       347 -> 419        1335 / 0
db_swapA_st104                ST 1.04 1 MB               swapA   shown                    OK       329 -> 400        1335 / 0
db_insB_ste                   STE 1.62 1 MB              insB    shown                    OK       338 -> 409        1236 / 100 (first: addr=0x68000 drive=1 track=0 sect=1 VBL 3672, last addr=0x62400 drive=1 track=22 sect=3 VBL 3910)
db_insB_ste_v                 STE 1.62 1 MB              insB    shown                    OK       321 -> 392        1236 / 100                unit=1 pref0=0 pref1=1
db_insB_ste4m                 STE 1.62 4 MB              insB    shown                    OK       323 -> 392        1236 / 100
db_insB_mste4m                Mega STE 2.06 4 MB         insB    shown                    OK       368 -> 452        1236 / 100
db_insB_st104                 ST 1.04 1 MB               insB    shown                    OK       324 -> 394        1236 / 100
db_startB_ste                 STE 1.62 1 MB              startB  NEVER shown (check finds B) OK     594 -> 662        1235 / 100 (first drive=1 read VBL 2357 = the first check)   unit=1 pref=0,1
db_startB_ste4m               STE 1.62 4 MB              startB  never                    OK       725 -> 793        1235 / 100
db_startB_mste4m              Mega STE 2.06 4 MB         startB  never                    OK       679 -> 746        1235 / 100
db_startB_st104               ST 1.04 1 MB               startB  never                    OK       599 -> 667        1235 / 100
db_wrongB_ste                 STE 1.62 1 MB, B = a COPY OF DISK 1, disk 2 swapped into A   wrongB  shown   OK  392 -> 461   1335 / 1 (B read once: boot sector, rejected)   0,0,0
db_none_ste_v                 STE 1.62 1 MB, B empty     none    shown, re-shown after each of 11 key presses (60 s)  no hang  -   1241 / 0 (6 boot-sector reads of A in the window)  0,0,0
db_none_nob_ste               STE 1.62 1 MB, --drive-b false  none  same                 no hang  -                 1241 / 0
```
Final default set (includes MSRCredit's `mr_credit`, `fl_driveb` default yes), build `work/fdb/build_def` (`disk_a.st` md5 `900e8299...`, disk B unchanged `0d0be455...`):
```
def_insB_ste_drive            STE 1.62 1 MB              insB    shown                    OK       292 -> 374; then 'up' held 30 s: $100e 808 (def_insB_ste_drive_drive.png)   1237 / 100   unit=1 pref=0,1
def_startB_ste_drive          STE 1.62 1 MB              startB  never                    OK       508 -> 576; up 30 s: $100e 960   1236 / 100   1,0,1
def_insB_mste4m               Mega STE 2.06 4 MB         insB    shown                    OK       321 -> 406; up 30 s: $100e 839   1237 / 100   1,0,1
def_startB_st104              ST 1.04 1 MB               startB  never                    OK       615 -> 685; up 30 s: $100e 1070  1236 / 100   1,0,1
def_none_nob_ste              STE 1.62 1 MB, --drive-b false  none  shown, no hang     -        -                  1240 / 0                 0,0,0
msrfloppy.py gate (swap route), lone copy of disk A, STE 1.62 1 MB: prompt VBL 3709, after swap + 30 s race $100e 216, MSPO, tick clock advancing, road magic RDG1 (def_msrfloppy_gate_lone_ste_1024.out)
```
Every success cell: marker `000B2700: 4d 53 50 4f` (MSPO) before and after, `$b8f00` tick clock advancing, the race screenshot `*_race.png` (HUD, "VOTE YOUR SHERIFF" road), and the 100 sector reads of the race load (first `addr=0x68000 track=0 sect=1` boot-sector check, last `addr=0x62400 track=22 sect=3`) identical to the one-drive route's 100 reads, but on `drive=1`.
The "never shown" startB result is the proof of "disk 2 from B at the first check": the prompt is the game's reaction to a failed check.
Controls in the same session: unpatched `our_none_ste` (no fl_driveb): drive B selected once at boot, no further.

**Hatari gotcha for every floppy gate (also sent to MSRFinalIntegrate):** `~/.config/hatari/hatari.cfg` has `bAutoInsertDiskB = TRUE`: Hatari inserts `xxx_b.st` into drive B whenever `xxx_a.st` is given as disk A. `msrfloppy.py gate build/floppy/disk_a.st` therefore always had disk 2 in drive B;
the original game never read it, but with `fl_driveb` the first check finds it and the prompt never appears (`gate`: "no disk-2 prompt", race running in the screenshots `build/shots/floppy_fdb_ste_1024/`, run on `build_def`, 400 s). The one-drive gate must use a lone copy of disk A
(`cp build/floppy/disk_a.st /tmp/x/disk_a.st; msrfloppy.py gate /tmp/x/disk_a.st --disk-b build/floppy/disk_b.st`: the result above), or `work/fdb/fdb.py` (scratch names `disk1.st`/`disk2.st`).

## 5. Cost of the probe, limits

Measured with the `none` cells (nothing inserted; a key press every 6 s; "VBL between two key presses" is the whole key -> check -> prompt cycle including ~6 s of harness sleeping):
```
our_none_ste (no fl_driveb)        3044 3418 3793 4168 4545 4925 5305 5683 6062 6441 6819   (about 375 VBL per cycle)
db_none_ste_v (fl_driveb, B empty) 3783 4183 4590 5007 5431 5864 6304 6754 7208 7676 8149   (400 -> 473 VBL per cycle)
db_none_nob_ste (--drive-b false)  4048 4463 4873 5294 5720 6153 6594 7043 7497 7985 8458   (415 -> 473)
```
i.e. a failed check (wrong or no disk in the preferred drive) costs +0.5 s growing to about +2 s per key press with an empty or absent drive B (the growth with the number of probes is unexplained [INFERENCE: head position bookkeeping of the empty drive / index timing]); the successful flows (swap route, B holds disk 2) are not slower
(first disk-2 read after the key about 350 VBL after the prompt in both `our_insB_ste` and `db_swapA_ste`, i.e. harness time). The FDC trace of a none cell shows the B probe: `fdc type I restore ... drive=1` right after the drive-0 restore, then `fdc change drive/side ... drive 1->-1`.
Not a hang in any cell. Real hardware: an absent drive B has no index pulses, so the driver's waits run into their forced interrupts (`$60000` / `$40000` loops each, about 1-2 s apiece at 8 MHz, three of them per probe) [INFERENCE: not measured on a real ST; the emulator's empty drive B answers faster].
Difference to MW1's probe (restore + seek + read that must move the DMA pointer by 512): the game's driver already has the bounded waits, and the compare of freshly zeroed buffer longs plays the DMA test's part (nothing can match unless the sector really arrived); the retry loop is bounded by construction: 2 reads per check, then the original prompt (no reselecting B forever).

## 6. Open points

* Real STE / MiSTer / a real second drive: not tested. [INFERENCE] MiSTer: a drive B without an image answers with RNF after ~6 ms (MW1 notes, from `fdc1772.sv`), which the driver turns into an error code and my compare ignores; a mounted B image that is not disk 2 is rejected by the compare.
* The "Insert Disk 1" direction (`d778`) and a second race (second disk-2 check, `pref[1] = B`) were not exercised in the gates; the logic is the same code path. [INFERENCE]
* Saving: the floppy release has no save path through `d6fa` as far as the dump shows; writes would go to A (pinned).
