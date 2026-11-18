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

## 3. The patch `patches/fl_driveb.s` (`media: floppy`, site `$d6fa`, 26 bytes -> `jmp $BB400.l`, blob `$BB400-$BB52F`, 308 B, variables `unit`@`$BB52E`, `pref[2]`@`$BB530`)

```
d6fa (orig 0c41 0320 6408 7000 4ef9 0000cac0 0441 0320 7004 4ef9 0000cac0)  ->  4ef9 000bb400 + 10 nops
blob: cmpi.l #$d7b2,(sp) ; beq probe   ; $d7b2 = the return address inside sub_00d798: this is a disk-check boot sector read
      bsr rd ; rts                      ; every other read: unit of the last successful check
rd:   d0 = (d3.b == 0 ? unit : 0); d1 >= $320 -> d1 -= $320, d0 += 4; jmp $cac0   ; = the original d6fa with the unit ORed into the device word; writes stay on drive A
probe: slot = (4(sp) == $d78a) ? disk 2 : disk 1    ; 4(sp) = return address into sub_00d788 / sub_00d778
       unit = pref[slot]  (A at power-on)
       2 tries: [unit == B: bpres; no answer -> count as a mismatch, do not read]
                clear the two probe longs ($68002, $6800e), read the boot sector with the game's own driver (rd),
                compare the slot's long; match -> pref[slot] = unit, return; else unit ^= 1 (flips back after the 2nd failure)
bpres: (drive B only) $43e = -1; PSG select B side 0 (cf0e); restore with h=1 (cmd $0b, no spin-up wait) via the game's cf8e;
       wait for the FDC interrupt (GPIP bit 5) <= $38000 loops (~1.2 s), else forced interrupt (cf5a) = no drive;
       status (cf78): seek error (bit 4) or no TR00 (bit 2) = no drive;  then <= $2d00 status reads (~130 us each, ~1.5 s) for an INDEX pulse (bit 1) = no disk spinning;
       deselect (cf0e, 7), $43e restored.  d0 = 0: a drive with a disk answers.
```
Behaviour:
* **one drive, swap route** (disk 2 into A at the prompt): unchanged results; the first failing check (disk 1 in A) also looks at B (`bpres`, 0.9 s if there is no drive, 2.0 s for a drive without a disk), then the prompt; after the swap A matches at once, `pref[1] = A`.
* **two drives**: first check A (disk 1: mismatch, readable) -> B (disk 2: match) -> `pref[1] = B`, `unit = B`: the race load (100 sectors) is read from B, every later disk 2 check starts on B.
  Disk 1 stays in A (`pref[0] = A`). Disk 2 already in B at power-on: the prompt never appears (the first check finds it).
* **absent / empty / wrong disk in B**: `bpres` keeps the game's own long waits (restore `$60000`, seek-0 restore `$60000`, read `$40000` loops, a forced interrupt after each, 4.4 s each in Hatari) away from a drive that does not spin a disk; the probe never trusts a status code:
  the two compared longs are zeroed before each read, so only data that really arrived in the buffer can match (the role of the DMA-pointer test in MW1; Hatari and the real FD1772 leave status "ok" after a forced interrupt).
  After both drives fail `unit` is back at the preferred drive and the caller shows its original prompt; the next key press repeats the check (cost: section 5; there is no 'no drive B' memory: a MiSTer image mounted at the prompt must be seen).
* **FDC track register**: the driver's per-unit `$cfac` table does it (first use of B: restore, since `$ffff`); `bpres` leaves B's head at track 0 while `$cfac[B]` still says unknown/where the last read left it: harmless, the check read that follows seeks to track 0 from whatever the register says (a step out at track 0 stays at 0) and stores 0.
* **Writes** (`d3.b != 0`: none exist for the floppy release) are pinned to drive A.
* The `$B2700` payload/trampoline is untouched; one site, one blob (`msrpatch.py verify` pairs it with every other patch: ALL OK; the first version's blob `$B8E00` (164 B) fitted the gap before `mg_sync`'s data `$B8F00`, with `bpres` the blob is 308 B and moved to `$BB400`, free between `hd_stage` and `hd_init`; payload 55,348 B = 109 sectors of the 129 free ones).
* Merge note for MSRCredit's `tools/msrpatch.py` change: `fl_driveb.s` uses only existing headers (`name default media site orig doc note`, no `phase`), nothing in `tools/` was edited; `work/fdb/msrpatch_priv.py` = the current `tools/msrpatch.py` (with `phase: stage1`) with its `ROOT` fixed; `verify` ALL OK in both.

Headers as written:
```
; name: fl_driveb
; default: yes
; media: floppy
; site: $d6fa
; orig: 0c410320640870004ef90000cac00441032070044ef90000cac0
```

## 4. Gates of the FIRST version (V1, no `bpres`; build `work/fdb/build_db`: all default patches + `fl_driveb`; Hatari 2.6.1, `--fastfdc no`; each success cell = prompt gone, `$100e` advancing, marker `MSPO` at `$b2700`, FDC `drive=1` reads; the final version is re-gated in 4b)

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

### 4b. Re-gate of the FINAL version (`bpres`; build `work/fdb/build_def2`, `disk_a.st` md5 `31e29c6a...`, 109 sectors; all Hatari 2.6.1, real FDC timing; raw `work/fdb/out/f_*.log|.out`)
```
cell                    machine                    mode     prompt             result  $100e advancing  fdc reads (whole run)  vars (unit; pref0,pref1)
f_msrfloppy_gate_lone   STE 1.62 1 MB, lone disk A msrfloppy.py gate (swap)  shown, VBL 2407  OK   after swap+30 s $100e 218, MSPO, RDG1
f_swapA_ste             STE 1.62 1 MB              swapA    shown              OK      283 -> 348       1338 / 0               0; 0,0
f_swapA_nob_ste         STE 1.62 1 MB, ONE drive   swapA    shown              OK      290 -> 360       1337 / 0               0; 0,0
f_swapA_mste4m          Mega STE 2.06 4 MB         swapA    shown              OK      278 -> 344       1338 / 0               0; 0,0
f_swapA_st104           ST 1.04 1 MB               swapA    shown              OK      287 -> 357       1338 / 0               0; 0,0
f_insB_ste_drive        STE 1.62 1 MB              insB     shown              OK      305 -> 371; 'up' held 30 s: $100e 742  1238 / 100   1; 0,1
f_insB_ste4m            STE 1.62 4 MB              insB     shown              OK      294 -> 369       1239 / 100             1; 0,1
f_insB_mste4m           Mega STE 2.06 4 MB         insB     shown              OK      302 -> 374       1238 / 100             1; 0,1
f_insB_st104            ST 1.04 1 MB               insB     shown              OK      290 -> 361       1239 / 100             1; 0,1
f_startB_ste_drive      STE 1.62 1 MB              startB   never              OK      495 -> 563; 'up' held 30 s: $100e 944  1237 / 100   1; 0,1
f_startB_mste4m         Mega STE 2.06 4 MB         startB   never              OK      494 -> 562       1237 / 100             1; 0,1
f_startB_st104          ST 1.04 1 MB               startB   never              OK      497 -> 565       1237 / 100             1; 0,1
f_wrongB_ste            STE 1.62 1 MB, B = disk 1 copy, disk 2 swapped into A  wrongB  shown  OK  307 -> 375  1337 / 1 (B rejected)  0; 0,0
```
Plus the unrelated-disk / empty / absent cells of section 5 (`v2_*`, all with the race reached after the swap, `$100e` advancing, vars `0; 0,0`). MSPO intact in every cell.

**Hatari gotcha for every floppy gate (also sent to MSRFinalIntegrate):** `~/.config/hatari/hatari.cfg` has `bAutoInsertDiskB = TRUE`: Hatari inserts `xxx_b.st` into drive B whenever `xxx_a.st` is given as disk A. `msrfloppy.py gate build/floppy/disk_a.st` therefore always had disk 2 in drive B;
the original game never read it, but with `fl_driveb` the first check finds it and the prompt never appears (`gate`: "no disk-2 prompt", race running in the screenshots `build/shots/floppy_fdb_ste_1024/`, run on `build_def`, 400 s). The one-drive gate must use a lone copy of disk A
(`cp build/floppy/disk_a.st /tmp/x/disk_a.st; msrfloppy.py gate /tmp/x/disk_a.st --disk-b build/floppy/disk_b.st`: the result above), or `work/fdb/fdb.py` (scratch names `disk1.st`/`disk2.st`).

## 5. Cost of the probe (user question: one-drive users are the majority)

**Correction.** The first version's cost line here ("+0.5 s growing to +2 s per key press", from the `none` cells' VBL between key presses) was WRONG: in those cells the harness pressed a key every 6 s while a failed check took 13 s, so most key presses fell into the busy check and the measured cycle was the harness' (see `work/fdb/ana.py`).
Per-press timing now comes from the FDC trace itself: `work/fdb/fdb.py ... swapA --presses 3` presses a key at the prompt 3 times (15 s apart, each a failed check because disk 1 is still in A), then swaps disk 2 into A and presses once more;
`work/fdb/ana.py NAME` prints per press: key -> first FDC event (game latency), check duration (first -> last FDC event), reads per drive, type I commands on B, forced interrupts. VBL = emulated time at 50 Hz. Raw: `work/fdb/out/NAME_events.txt`, `NAME.log`.
Variants: V0 = default set WITHOUT fl_driveb (`work/fdb/build_v0`), V1 = first version (no `bpres`, `build_v1`; it was `default: yes` in `patches/` for a few hours), V2 = final (`bpres`, `build_v2` = `build_def2`).

```
check duration of a FAILED check at the prompt (disk 1 in A), seconds, 3 presses each (a/b/c); STE TOS 1.62 1 MB unless noted
B situation               V0 (no fl_driveb)      V1 (first version)       V2 (final)
drive B disabled (--drive-b false) / no drive     -                       14.1 14.0 14.1 (v1_nob_ste)  0.86 0.90 0.92 (v2_nob_ste); ST 1.04 0.86 0.86 0.90 (v2_nob_st)
drive B enabled, no disk  0.20 0.04 0.18 (v0_empty_ste)   13.3 13.3 13.4 (t_v1_empty_ste); ST 1.04 13.3 13.3 13.4 (v1_empty_st)   1.96 1.92 2.10 (v2_empty_ste); ST 1.04 2.10 2.04 1.98 (v2_empty_st)
B = blank DOS-formatted disk  -                  -                        0.28 0.28 0.46 (v2_blank_ste); ST 0.16 0.44 0.42 (v2_blank_st)
B = random-bytes disk         -                  0.16 0.36 0.12 (v1_junk_ste)  0.20 0.36 0.48 (v2_junk_ste); ST 0.22 0.22 0.28 (v2_junk_st)
B = copy of disk 1            -                  -                        0.44 0.42 0.44 (v2_disk1_ste); ST 0.32 0.28 0.26 (v2_disk1_st)
ST 1.04, no disk in B      0.12 0.04 0.14 (v0_empty_st)
```
Key press that SUCCEEDS (disk 2 now in A) up to the end of the race load (key -> first FDC activity = game latency 3.5 s; then check + 100 sectors): V0 6.82 s, V1 6.78-6.98 s, V2 6.74-7.12 s on every B situation and both machines (e.g. v2_blank_ste 7.08, v2_junk_ste 6.74, v2_empty_st 6.92):
**the one-time cost for a user who presses a key once at the prompt, after the swap, is zero**; before the swap each key press (a failed check) costs the V2 figures above minus V0's 0.04-0.2 s: about 0.7 s with no drive B, 1.8 s with an empty drive B, 0.1-0.4 s with an unrelated disk in B.

**What the time is (V1 trace, `t_v1_empty_ste -v`)**: A: restore, boot sector read (0.04-0.2 s); then `type I restore drive=1 spinup=on` and nothing completes: three forced interrupts at +4.4 s, +8.8 s, +13.3 s (219.7 VBL each) = the three bounded waits of the game's driver in sequence:
restore in `sub_00ce64` (`$60000` loops), restore to track 0 in `sub_00ce32/ce4e` (`$60000`), the sector read `$cc48` (`$40000`); then B is deselected. So the cost is the bounded FDC waits times the three commands, not motor spin-up, head load or the second read.
Hatari's 4.4 s per wait: the loop `btst.b #5,$fa01.w / beq / subq.l #1,d0 / bne` is 16+8+8+10 = 42 cycles by instruction count = 2.06 s for `$60000`; the read loop with its three `move.b $860x.w,d16(a6)` and `cmpa.l` is about 112 cycles = 3.7 s for `$40000`
(sum 7.8 s); Hatari measures 4.4 s for each of the three (MFP / DMA-chip wait states, 35 M cycles each), 13.3 s. **Real STE worst case from the loop counts: 7.8 s (instruction count) to 13 s (Hatari-like bus timing) per failed check** with no drive B - far above 2 s - IF the FDC never raises its interrupt.
Why `bpres` is bounded below that: a restore with h=1 on a drive that is not there ends by itself after 255 steps at 3 ms = 0.77 s with seek error (bit 4) and no TR00 (Hatari with `--drive-b false` shows exactly that: 0.86 s per check); if no interrupt comes at all `bpres` waits its own `$38000` loops (42 cycles = 1.2 s at 8 MHz; Hatari-like bus timing about 2x) and forces one.
A drive that is there but holds no disk reaches TR00 but never shows an index pulse: 1.5 s of status polling (`$2d00` iterations at ~1100 cycles with the game's register delays = 1.5 s) -> 2.0 s per check with the restore in Hatari. [INFERENCE: real ST: no drive B = TR00 never asserted (input pulled inactive) so restore ends by seek error after 255 steps; an ST drive spins while selected so an index pulse appears within spin-up + 0.2 s; neither measured on hardware.]
A drive with a disk: restore from the last head position (22 steps at most 66 ms) + index within 0.2 s (Hatari: immediately), the rest is the game's read (0.1-0.4 s per check with an unrelated disk).
MiSTer (read from the core, MW1 notes): a drive B without an image reports RNF (status bit 4) after 6 ms for a restore: `bpres` says "no drive" at once; with an image: TR00, index while selected.

No 'no drive B' flag: it would defeat a MiSTer image mounted into B at the prompt, and the cost per failed check is now ~0.9 s (no drive) / 2 s (empty drive) instead of 13 s.
Not a hang in any cell. Difference to MW1's probe (restore + seek + read that must move the DMA pointer by 512): the compare of freshly zeroed buffer longs plays the DMA test's part (nothing can match unless the sector really arrived); the retry loop is bounded by construction: 2 reads per check, then the original prompt (no reselecting B forever).

### How a one-drive user turns it off / what to expect
* Expect: after a wrong disk in A at the "Insert Disk 2" prompt (the key press before the swap) the prompt takes about one second longer to come back (2 s if a second drive is connected but empty). With the right disk in A nothing differs from the original. Disk 2 in drive B (if there is one) is used automatically.
* Switch off: `python3 tools/msrpatch.py build --floppy --only $(python3 tools/msrpatch.py list | awk '$2 ~ /^yes/ && $1 !~ /^pp_/ && $1 != "fl_driveb" {print $1}')` (the same list `tools/play.sh` builds for its `--no-*` switches); a `--no-driveb) DROP+=(fl_driveb) ;;` line in `tools/play.sh` next to `--no-blit` does it there (not added: play.sh belongs to MSRFinalIntegrate).

## 6. Open points

* Real STE / MiSTer / a real second drive: not tested. [INFERENCE] MiSTer: a drive B without an image answers with RNF after ~6 ms (MW1 notes, from `fdc1772.sv`), which the driver turns into an error code and my compare ignores; a mounted B image that is not disk 2 is rejected by the compare.
* The "Insert Disk 1" direction (`d778`) and a second race (second disk-2 check, `pref[1] = B`) were not exercised in the gates; the logic is the same code path. [INFERENCE]
* Saving: the floppy release has no save path through `d6fa` as far as the dump shows; writes would go to A (pinned).
