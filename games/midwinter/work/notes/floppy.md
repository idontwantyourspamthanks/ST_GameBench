# Midwinter 1 floppy build: boot path, injection, tests (2026-11-08)

Tools: `tools/m68dis.py`, `games/midwinter/tools/mw1patch.py build --floppy`, `tools/mw1floppy.py` (Hatari 2.6.1). Everything below comes
from disassembly of `FILES/MWA` or from the quoted test outputs; [INFERENCE] marks the rest. Companion: `loading.md` (HD path, file system).

## 1. MWA is a bootable floppy image

`FILES/MWA` (409600 B = 10 sectors x 80 tracks x 1 side): boot sector word sum **`$1234`** (checked: `bootsum 1234`; MWB `1235`, MWC `e640` are not bootable).
Boot sector (`m68dis` of image bytes `$0-$1FF` placed at `$2000`):
```
00203a  move.l #$cfe4,d0 -> DMA address $ff8609/0b/0d     (DMA target $CFE4)
002058  move.w #$90 / #$190 / #$90,$ff8606                  (sector-count register toggle)
002072  move.w #$c,$ff8604                                  (12 sectors)
00207c  move.w #$84,$ff8606 ; 002086 move.w #2,$ff8604       (FDC sector register = 2)
002090  move.w #$80,$ff8606 ; 00209a move.w #$90,$ff8604    (command $90: read sector, multiple)
0020a4  btst.b #5,$fffa01 ; bne                              (wait for the FDC)
0020b4  jmp $d000.l
```
(The string `midwint.blk` sits at sector offset `$2F-$39`, just before the code at `$3A`.) So MWA sectors 2-13 land at `$CFE4`: a TOS-header-prefixed
program (`601a` header, 28 bytes) whose code starts at **`$D000`**. Its first lines (`m68dis` of `FILES/MWA +$200` at `$CFE4`):
```
00d000  lea.l $d618.l,a7 ; lea $d458(pc),a6                 (a6 = parameter block)
00d01c..  vectors $68/$70 -> $d064, $118 -> $d06e, $114 -> $d082
00d052  move.l #$3df28,$16(a6)                              (destination)
00d05a  bsr $d092 ; 00d05e jmp $3df44.l                      (load file 0 of the stub table, run it)
```
The stub's own FDC driver (`sub_00d0b8` / `sub_00d20c`, DMA + `$ff8604`) reads entry 0 of its table (`$D47E` = MWA file offset `$69A`):
`{start 558, nsect 148, length $1272E}` = the **stage-2 program** (75566 B, TOS header + code at `$3DF44`) to `$3DF28`.
Stage-2 (`sub_03ec9e` -> `sub_03ecce`, same driver again) loads from its table at `$48632` the title picture (file 0 -> `$486B2`), then the whole
resident game (file 1, sector 195, 185678 B -> `$7E4`), the second picture (file 2), writes `$31415926` to `$426` and `$800` to `$42A` and ends in
**`$3E1AA: 4ef9 0000 0800  jmp $800.l`** (game entry). Neither the stub nor stage-2 verifies a checksum (the 4th entry word is not used by them).

PP's RUNME, his patcher (`$3B0-$482` of RUNME text) and the HAGA service never run on floppy. His 12 RAM patches (loading.md section 4) are therefore
absent: the game uses its original FDC code (`$1011E`... still `4eb9`, `$10E5C` still `30280002`) and **its original security check**.

Evidence — unpatched `FILES/MWA` cold boot, STE TOS 1.62 1 MB (`tools/mw1floppy.py fl_orig ... --shots`, shots every 4 s):
intro picture and credits, then `Insert graphics disk / Press any key when ready` (at 48 s, `work/ref/insert_graphics.png`); after swapping drive A to MWB
and a keypress: the **"FVPF SECURITY CHECK — Identify these two people by clicking on their names"** page stays up (s057-s071 in `/tmp/mw1fl_fl_orig/`,
contact sheet viewed; the page is not left without clicks). The same on Mega STE TOS 2.06 4 MB (`fl_orig_mste4mb`: `FVPF Security Check` in the last shots).
The HD game passes it silently (`$12050 <- rts`, loading.md section 4).

## 2. Free space on MWA, directory

Sector classes of the image (1-based, computed by `all sectors zero / one repeated byte / data`):
```
1-5 data, 6-7 zero, 8-388 data, 389-392 zero, 393-474 data, 475 zero, 476-541 data, 542 zero, 543 data, 544-557 zero,
558-578 data, 579-584 zero, 585-610 data, 611-640 zero, 641 data, 642-704 zero, 705 data, 706-800 = $E5 filler (95 sectors)
```
Game files (MWA directory table `$258A6`, `python3 tools/mw1patch.py files`): 11-63, 64, 65, 66-72, 73-76, 77, 78-176, 177-194, 195-557 (resident game),
558-705 (stage-2). Sectors **706-800 (95, 48640 B)** are the `$E5` format filler: the payload needs 64 sectors (706-769). The stub's table has one entry, stage-2's
table (`$48632`) is followed by its parameter block (`$48650`), so the injection cannot add a table entry; see section 3.

## 3. Injection (`floppy_mwa` in `mw1patch.py`)

* Payload = the same `$8000` image as on HD (core + site table + blobs), stored at MWA sectors **706-769** (file offset `$58200`), padded sectors keep `$E5`.
* **Stage 1** (44 bytes, assembled in the tool) is written over two dead FDC helper routines of the stage-2 program at `$3EE3C-$3EE73` (56 B; both end in `rts`,
  disassembly `3ee3c: move.w #$84,$ff8606 ... rts` and `3ee5a: move.w #$82,$ff8606 ... rts`). Nothing references them: `m68dis --xref/--callers` for
  `3ee3c 3ee5a 3ee92 3ed80` print nothing; a raw scan of the 75566 bytes for 32-bit values and for `bsr/bra/jsr/lea d16(pc)` operands into `$3EE3C-$3EE73` finds only
  one misaligned hit (`$3E213`, inside a `bsr.w`). [INFERENCE: leftover of an earlier loader version, as in MW2's floppy stub; the boot tests run through the whole chain without them.]
```
3ee3c  move.l #$02c20040,$48646.l     ; stage-2 table entry 2 ($48632+20): start sector 706 ($2C2), 64 sectors   (entry 2 = the second title picture, already shown)
3ee46  move.l #$8000,$4864a.l         ; length
3ee50  move.w #2,$14(a6)              ; file number                 (a6 = $48650, unchanged since stage-2's start)
3ee56  move.l #$b3000,$1a(a6)         ; destination
3ee5e  bsr.w $3ec9e                    ; stage-2's own loader: drive select, read, retry until the FDC reports OK
3ee62  jmp $b3000.l                    ; the trampoline (core.s), which ends in `jmp $800.w`
```
  Bytes: `23fc 02c20040 00048646 23fc 00008000 0004864a 3d7c 0002 0014 2d7c 000b3000 001a 6100 fe3e 4ef9 000b3000`.
* Stage-2's final `jmp $800.l` (`$3E1AA`, file offset `(558-1)*512 + $3E1AA-$3DF28`) becomes `jmp $3EE3C.l` (`4ef9 0003ee3c`).
* The tool asserts: boot-sector sum still `$1234`; the original bytes at both stage-2 sites; sectors 706-800 all `$E5`; the payload reads back through `sector_file`.
* Why entry 2 and not a free entry: the loader computes `a0 = $48632 + idx·10` and reads `{start,nsect,len}`; entry 3 would be stage-2's own `a6` block,
  which the loader overwrites (`move.l $1a(a6),$0(a6)` before it reads the entry). Entry 2 is dead by then (stage-2 never reloads file 2; the game's directory has its own copy).
* The floppy trampoline is the HD one (core.s unchanged, two-pass verify then apply, `MWPO`/`MWPF` at `$B2FF8`).
  Sites: the original bytes on floppy are the raw image bytes. `floppy_conflicts` aborts the build if a normal site overlaps one of PP's 12 patch addresses;
  `media: floppy` sites (e.g. `floppy_secbypass`, `$12050`: `33fc` -> `4e75`) take their `orig` from the image instead of from image + PP patches.
* The game's loader hook (`$10D6C`) is game code and exists unchanged on floppy; the same `jmp $B3070` splice is applied (deferred patches work, below).
* HAGA file patches (`pp_nofade`, `pp_bigram_cache`) are skipped on `build --floppy` (no HAGA, no fade, no cache).
* `floppy_secbypass` (`default: no`) reproduces PP's `rts` at `$12050` so a floppy boot also skips the manual check. Whether to ship it is a decision for the maintainer
  (Midwinter 2's floppy set skips its check as well); the tests below use it.

## 4. Tests (raw)

`python3 tools/mw1patch.py build --floppy --only floppy_secbypass --out build/fl_t1` (+ `live --floppy ... --out build/live/fl_t1`), and
`... --only floppy_secbypass test_boot_text test_load_cursor --out build/fl_t2`. Cell: `python3 tools/mw1floppy.py NAME MACHINE TOS MEM_KB DISKDIR --live PREFIX --team`.
The runner boots drive A = MWA, waits for `insert_graphics.png`, swaps drive A to MWB (`hatari-option --disk-a`), presses space until the Options screen, then clicks PLAY.
(Gotcha: name the files `mwboot.st` / `mwgfx.st`, not `A.st` / `B.st`: Hatari's `bAutoInsertDiskB` puts `B.st` into drive B whenever `A.st` is in drive A, and a later
swap of drive A to `B.st` fails with "Cannot insert same floppy to multiple drives!" and a blocking dialog.)

```
cell fl_t2 ste TOS 1.62 1024 KB floppy build/fl_t2                    (floppy_secbypass + test_boot_text + test_load_cursor)
'Insert graphics disk' prompt after 52 s: drive A -> MWB.st
Game Options screen reached: True after 67 s
[options] marker: 000B2FF8: 4d 57 50 4f                                      MWPO
[options] payload $B3000..+$8000 vs built image: 0 bytes differ
[options] site $012050 [floppy_secbypass] RAM 4e75 new 4e75 orig 33fc -> PATCHED
[options] site $0250ea [test_boot_text] RAM 5041544348 new 5041544348 orig 4d4f555345 -> PATCHED
[options] site $053c30 [test_load_cursor] RAM ffffffffffffffff new ffffffffffffffff orig a89faca291ae005a -> PATCHED     <- deferred, via the $10D6C hook on floppy
THE TEAM screen reached: True ; [team] same marker/payload/site lines

cell fl_t1_st104 st TOS 1.04 1024 KB floppy build/fl_t1               (floppy_secbypass only)
'Insert graphics disk' prompt after 51 s ... Game Options screen reached: True after 65 s
[options] marker MWPO   payload 0 bytes differ   site $012050 [floppy_secbypass] RAM 4e75 -> PATCHED     THE TEAM screen reached: True (same lines)

cell fl_t1_mste1mb megaste TOS 2.06 1024 KB floppy build/fl_t1  -> Options True after 67 s, MWPO, payload 0 differ, site PATCHED, THE TEAM True
cell fl_t1_mste4mb megaste TOS 2.06 4096 KB floppy build/fl_t1  -> Options True after 67 s, MWPO, payload 0 differ, site PATCHED, THE TEAM True
```
Without `floppy_secbypass` the patched floppy reaches the security page with `MWPO` set (marker is written before the game starts); the patched floppy is otherwise the original
boot. One earlier run of `fl_t1_mste4mb` (started 5 s before a second Hatari instance) never left the TOS 2.06 boot logo in 300 s (`RS:90 00:00:0B:0` in the status bar); the rerun above
passed and the unpatched floppy at the same machine reached the security page, so I treat it as an emulator start-up flake [INFERENCE, not reproduced].

`python3 tools/mw1patch.py build --floppy --out build/fl_zip --zip build/fl_zip/test.zip` writes `MWA.st MWB.st MWC.st README.TXT` (from `patches/FLOPPY.TXT`);
md5 of the zero-patch set: `a7155514eafcc37af381ec8e6c857a9d MWA.st`, `ae1dbe50dcef64e3ed19503892afebdb MWB.st` (= FILES/MWB), `22e592651ab1564fafed23a13c22d171 MWC.st` (= FILES/MWC).
`cmp -l build/fl_t2/MWA.st FILES/MWA | wc -l` = 32809 differing bytes (payload sectors, 44 B stage 1, 6 B jump).

## 5. Not done / open

* The game's disk-copy / save paths on floppy (MWC save disk writes) were not exercised: no in-game save was made, so nothing proves `$B3000-$BAFFF` survives them. The HD build
  saves through PP's service (`$32E`/`$328` stubs) into the MWC image; the floppy driver writes with the stub-less original code (`$10F86`...).
* The floppy tests stop at THE TEAM; the HD builds were also run into the 3D view (loading.md section 5). `tools/mw1.py` `boot_to_game` autoruns RUNME, so a floppy variant of that navigation was not written.
* MWC (the data disk) has a 9-sector directory variant (`$100FE` sets `[$107D8] = 9`): HD builds map disk C through PP's stub with 10 sectors/track (`mulu #$1400`);
  [INFERENCE] a 10-sector MWC image (README.TXT) is what that stub expects. Not tested.
