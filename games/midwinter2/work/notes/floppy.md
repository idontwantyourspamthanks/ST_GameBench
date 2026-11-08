# Midwinter 2 floppy build: boot path, injection, tests (2026-11-08)

Tools: `tools/m68dis.py`, `tools/mw2patch.py build --floppy`, `tools/mw2harness.py` (Hatari 2.6.1), runner
`work/floppy_tests/run_cell.py`. Raw test outputs: `work/floppy_tests/*.out`. All claims below are from
disassembly of the FFA images or from those outputs; anything unproven is marked [INFERENCE].

## 1. Floppy boot path (FILES/FFA is a working floppy image)

- Boot sector (`xxd FILES/FFA`, word sum `$1234`): at `$3A` `move.l #$4d9a6,d0` sets the DMA address, then
  FDC DMA count 12, command `$84` (read sector, sector register = 2, side 0), wait for GPIP bit 5, `jmp $4d9a6.l`
  at `$B4`. It loads sectors 2-9 of track 0 side 0 = FFA image offset `$200`, 4096 bytes = **file 1, the boot stub**
  (`$4D9A6-$4E9A5`).
- The stub (disassembled to `/tmp/fl/stub.asm`; offsets below are RAM addresses):
  - `$4D9A6`: `move #$2700,sr`, stack `$783E8`, installs vectors (`$8..` -> rte at `$4DECA`, VBL `$70` -> `$4DECC`,
    ACIA `$118`), `$4DB26` reads the FFA directory (one sector, track-side 1) to `$4EA00`.
  - Loads files 2-5 (`$50000/$58000/$60000/$68000`, title pictures, depacked by `sub_04DF52`), file 8 to `$806`
    (`$4DA3A-$4DA4A`), runs a title animation/wait loop, then file 9 to `$3104`
    (`$4DA8C: move.l #$3104,$4e9ac`; `$4DA96: move.w #9,$16(a6)`; `$4DA9C: bsr $4db52`) and ends
    **`$4DAA0: 4ef8 3104  jmp $3104.w`**. This is the game entry on floppy.
  - The loader `sub_04DB52` / `sub_04DB60` takes the file number at `$16(a6)` (a6 = `$4E9D8`), the destination
    at `[$4E9AC]`, looks the entry up at `$4EA08 + 8*file` (`[cksum.w][offset.w][track-side.b][len.u24]`), reads
    9-sector track-sides straight into the destination (the final partial one through `$4EC00`), then XORs
    the BE words (`sub_04DC90`) and **retries forever** on a checksum mismatch (`$4DB52: bne.b`).
- PP's RUNME, his patcher (`$4BC-$59C`) and the HAGA service are **not** involved: nothing in this path references
  `$4BC`, `$200-$5E7` or `$F8000`. Unpatched floppy boot, in-game RAM dump (1 MB STE, `/tmp/fl/flop_ingame_1mb.bin`,
  taken at the Lobos 3D view): every PP patch address that lies in file 9 and is not overlaid later reads the
  original FFA bytes (`$27AC4 2e2e010a`, `$27CFC 7e00`, `$27A38/$27A4E/$27A86 33fc`, `$27CAA/$27C4A 6100`,
  `$27B12 2e2e010a`, `$2798A 4df8770e`, `$2C542 1039`, `$26A24 0240007f`); `$200-$22F` is zero (no `$200` stub);
  `$5E4-$805` is zero. (`$1F5EA/$1ACC8/$1AA14/$1F636` lie in the `$18D96-$210B2` overlay from FFB and hold
  overlay bytes; `$2C574` read `6002` only because the test wrote it.)
- The game therefore runs its **original FDC driver** (`sub_27AC4` etc. unpatched) and its **original security
  check**: after the M/J/K key the game shows "SECURITY CHECK - Identify this member of the Secret Police"
  (Hatari screenshot, `/tmp/fl/s6.png`). PP's HD patcher removes it with `$2C574 <- 6002` (bra.s over
  `bsr.w sub_02D65A`; the HD trampoline replays that patch as its first instruction because it displaced it
  from `$594`). Writing `$60 $02` to `$2C574` from the debugger at the M/J/K screen skips it (the 3D view is then
  reached); that is what the test runner does. **The floppy build does not include it**: `core.s` is assembled with
  `FLOPPY equ 1`, which drops the replay.
- `$2C542`: `move.b $ff8001,d0 / cmp.b #5,d0 / bcs $2c560` reads the MMU memory configuration. On a 1 MB machine
  (config 5) it executes `move.w #$ffff,$e550` / `move.l #$e566,$e554`. PP's `$2C542 <- bra.s` makes the HD build
  take the small path always. On floppy the 1 MB path is live: `$e550 = ffff`, `$e554 = $e566` (RAM dump). The
  descriptor list at `$e566` is `[0050][00080000][ffff]` = 80 track-sides read to `$80000` (368640 B, to `$DA000`);
  the default list at `$e558` is `[0013][0004A5D2][0015][00068000][ffff]` (19 + 21 track-sides). `sub_01AF12`
  (read pass) and `sub_01AF62` (write pass) walk the list at `$e554` (`disassembly: $1AF28..$1AF8C`). Start New
  Campaign / Create Back-up copy a disk through it, which would overwrite the payload at `$B3000`:
  patch `floppy_copybuf` shrinks the count to 40 (`$80000-$AD000`).

## 2. Site originals on floppy

All 24 default sites plus the load-hook site (`$2789A`) were read from the RAM of an unpatched floppy boot at the
3D view and compared with the tool's `orig` bytes: 25/25 identical, including the three deferred sites
(`$1D768`, `$1B996`, `$200CE`, overlay FFB file 1, loaded by the game's own `sub_2783E` path). None of them
overlaps a `PP_PATCHES` address, so the HD-derived `orig` values are valid on floppy; `build --floppy` aborts if
that ever stops being true (`floppy_conflicts`).

## 3. Injection

See patches/README.md "Floppy build". Facts behind the design:
- The stub has 18 free bytes only (4078 of 4096 used) and its tail bytes are palette data, so stage 1 lives in
  dead code: `$4DDAA-$4DDE9` (64 B, `rts` at `$4DDE8`) is a DMA-wait routine (`dbra` delay, `btst #5,$fffa01`,
  read back `$ff8609/0b/0d`). No branch, `bsr`, `jsr`, `jmp` or 32-bit constant in the stub targets it: `grep` of the
  disassembly for `4ddaa/4ddb2/4dde4` finds only the routine's own lines, and a raw scan for the 32-bit values
  `$0004DDAA-$0004DDE8` in the 4096 stub bytes finds nothing. [INFERENCE] it is a leftover of an earlier loader
  version; the boot tests below run through the whole stub without it.
- FFA directory: 512 B at track-side 1 = 63 entries; entries 0-9 are used, 10-62 are zero. (Entries from 63 on
  are file 2's data: the game's 3-sector directory read sees it, nothing uses it.) FFA's files end at track-side
  71 (file 9: track-side 19 + `$18C` + 240140 B); track-sides 72-79 are filled with `$F6`. File 10 = the
  `$1F00`-byte payload at track-side 72 (4608 B) + 73. Directory checksum = XOR of BE words, as `sub_04DC90`.
  FFA boot-sector sum stays `$1234` (asserted by the build).
- Free RAM: in-game RAM dump of the unpatched floppy boot: `$B0000-$FFFFF` is **all zero** (1 MB). Nothing
  (stub, files 8/9, title pictures at `$50000-$6FFFF`, stack `$783E8`) touches `$B3000` before the trampoline runs.
  The one transient user of `$80000-$DA000` is the disk-copy buffer above (handled by `floppy_copybuf`).

## 4. Test log

All runs: Hatari 2.6.1, 1 MB, `work/floppy_tests/run_cell.py` (cold boot from `A.st` = FFA, swap drive A to FFB at the
"Insert Graphics Disk" prompt, campaign disk `work/disk_overlay/FILES/FFD` in drive B, M, HQ hall -> personnel ->
control -> map -> Lobos -> boss -> thumbs up; the security check is skipped by `w $2c574 $60 $02` at the M/J/K
screen). Raw output: `work/floppy_tests/<cell>.out`, in-game RAM dumps `<cell>_ram.bin.gz`, screenshots `<cell>_*.png`.

### T1 unpatched floppies (FILES/FFA, FFB, FFC copied unchanged)
```
t1_ste162_unpatched (STE TOS 1.62):   6220=d 700a=2   MWPO 00 00 00 00
    world_rate 8MHz {'flips': 43, 'fps': 4.3, 'units_per_sec': 19.28}   heading 0x300 x9 (no turn at dx -150: unpatched yoke)
t1_megast104_unpatched (Mega ST TOS 1.04): 6220=d 700a=2   MWPO 00 00 00 00
    world_rate 8MHz {'flips': 43, 'fps': 4.3, 'units_per_sec': 17.88}   heading 0x300 x9
```
(HD build control: 18.4/s, work/regression.md A0.) RAM dumps: all 25 floppy sites (24 patches + load hook) still hold
the tool's `orig` bytes; `$B0000-$FFFFF` is all zero (0 non-zero bytes) in both.

### T2 patched floppies (`build --floppy`, FFA md5 4c5e20ad9415a25791991f3c135664e3)
```
t2_ste162_patched:     MWPO at the M/J/K screen: 4d 57 50 4f   6220=d 700a=2   MWPO 4d 57 50 4f
    world_rate 8MHz {'flips': 46, 'fps': 4.6, 'units_per_sec': 27.29}
    heading series ['0x0','0x0','0x0','0x390','0x390','0x390','0x390','0x390','0x390']   (turns -0x70, then stops)
t2_megast104_patched:  MWPO 4d 57 50 4f   6220=d 700a=2
    world_rate 8MHz {'flips': 46, 'units_per_sec': 28.51}
    heading series ['0x0','0x0','0x390','0x390','0x390','0x390','0x390','0x390','0x390']
t3_ste162_patched_pre16: MWPO 4d 57 50 4f   6220=d 700a=2   heading ['0x300','0x2c4','0x2c4' ...] (turn, stop)
```
HD build reference (work/regression.md): STE 27.5/s, ST 28.0/s, turn 0x300 -> 0x2c6.
RAM dumps (`check_dump`): for t2_ste162, t2_megast104 and t3_ste162: 25/25 sites hold the patch's `new` bytes, including
the three deferred sites (`$1D768`, `$1B996`, `$200CE`), i.e. the hook at `$2789A` fired on the floppy loader's
`sub_2783E`; marker `MWPO`; payload bytes differing from the built image: `$B3402,$B3403` (tick_vbl clock) and `$B46C1`
(p5 data), nothing else; non-zero bytes above `$B4F00`: 0. Common patch sites: the 24 HD patches have identical
`addr/orig/new` in the HD and floppy site lists (`floppy_copybuf` is the only extra).

### T3 world rate, 8 vs 16 MHz (patched floppies)
```
STE 1.62, 8 MHz ............................ 27.29 units/s  (4.6 fps)   t2_ste162_patched
STE 1.62, 16 MHz set BEFORE the walk ....... 27.52 units/s  (10.1 fps)  t3_ste162_patched_pre16   (+0.8 %)
Mega ST 1.04, 8 MHz then 16 MHz same walk .. 28.51 -> 28.77 units/s (4.6 -> 13.4 fps)              (+0.9 %)
STE 1.62, 8 MHz then 16 MHz same walk ...... 27.29 -> 29.38 units/s (4.6 -> 13.4 fps)              (+7.7 %)
```
The last row is outside 5 %. In that session the 16 MHz window is a later stretch of the same walk, and the starting
heading differs between the STE and Mega ST runs (`0x300` vs `0x0`); the same-timeline 16 MHz cell above is +0.8 %.
[INFERENCE] the 7.7 % is terrain (HUD distance `$6888` is a distance to the objective, not a speed), not a clock
dependence; not separately proven. (An earlier run of this same-walk order also ended with a `$6888` reading of ~5000
units/s after the turn test; not investigated, the turn test had run first there.)

### Campaign creation on floppy (patched build, STE 1.62, 1 MB)
Start New Campaign (name `test`) -> CREATE CAMPAIGN DISK, single drive A swapped MISSIONS/CAMPAIGN disk
(`hatari-option --disk-a`), 8 clicks of the copy icon:
- `$e552 = 0x0028` (40 track-sides per pass), progress rings advance one step per pass, four read passes and the
  write passes complete; after each of the first passes and after the full sequence the payload at `$B3000-$B4EFF`
  equals the built image except `$B3402,$B3403,$B46C1` and `$B2FF8` still reads `MWPO`.
- **Without `floppy_copybuf`** (`build --floppy --only <all defaults but floppy_copybuf>`): the first read pass crashes the
  emulated machine: Hatari log `Address Error reading at address $b416f, PC=$b40f6` (`$B40F2` is `tick_vbl`'s blob, inside the
  payload). [INFERENCE] the 80-track-side buffer (`$80000-$DA000`) overwrote it: the machine ran fine until the pass
  started, but my payload comparison in that run used the wrong site table and is not valid, and the debugger no
  longer answered after the exception.
- Hatari limitation: after the first write pass Hatari logs `Writing not possible, discarded the contents of floppy
  image '<campaign>'` on every later eject (same with an .msa image), and the last write pass shows `Disk Error`
  (`$e570 = 0x4e`, `$9e30 = 0xffff`). The first pass did write: the campaign image then has `camp` at offset 0 and
  track-sides 1-39 equal to FFC's. [INFERENCE] Hatari refuses to save images whose boot sector the game has overwritten;
  the `Disk Error` is then the game's final verification reading the discarded data. Not proven; I did not complete
  a creation in Hatari.
- Two-drive variants were tried (A = FFC / B = blank, and A = blank / B = FFC): after the first write pass the MISSIONS disk
  icon shows `WRONG DISK` in both. [INFERENCE] the copy code reads and writes drive A; not proven.

### T4 zip
`python3 tools/mw2patch.py build --floppy --out build/floppy --zip` -> `dist/Midwinter2_patched_floppies_2026-11-08.zip`
(FFA_boot.st, FFB_graphics.st, FFC_missions.st, FFD_campaign_blank.st, README.TXT). Unzipped and compared with `cmp`/`md5sum`:
```
4c5e20ad9415a25791991f3c135664e3  FFA_boot.st            == build/floppy == A.st copies of t2_ste162, t2_megast104, t3_ste162
9d4ea2ddfcfe5fa7fdf7b54f26168ed3  FFB_graphics.st        == FILES/FFB == B.st copies of the same runs
252d0ad0674db02ba5d104891db12e29  FFC_missions.st        == FILES/FFC
5e034299f50432eb6fe5e7048a5d2ccc  FFD_campaign_blank.st  == FILES/FFD
```
FFA differs from FILES/FFA in 7972 bytes: `$2FA-$2FD` (stub `bra.w`), `$604-$623` (stage 1), `$2458-$245E` (directory entry 10),
`$A2000-$A31FF` and `$A4400-$A50FF` (payload on track-sides 72, 73). The HD build is unchanged: `build` writes a
byte-identical RUNME.TOS and HAGA (md5 `cf6ed481...`, `8aa73e63...`) before and after these changes.
