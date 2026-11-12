# Populous 2 ST: which release has a working in-game SAVE/LOAD, and how its disk layer relates to PP's HAGA build

2026-11-12. Six user disks (`alt/ST/`, git-ignored, never modified: every test ran on a copy in
`work/scratch/disks/run/`). Hatari 2.6.1, STE TOS 1.62 unless stated. Method: `work/scratch/disks/matrix.py`
(cold boot → main menu → CONQUEST → first battle → requester → SAVE GAME → play → LOAD GAME) and interactive
runs in the same folder; screenshots in `work/scratch/disks/shots/`, raw logs `chain*.log`.

## 1. Catalogue

| image | size | boot sector sum | boot code | files |
|---|---|---|---|---|
| `[cr ICS][512 kB]` (1991) | 737280 | `$fb35` | none (filler; TOS boots the disk and runs `AUTO\ICS.PRG`) | 33, `AUTO\ICS.PRG` 6752 (ICS cracktro), `AUTO\LOADER.PRG` 157 |
| `[cr ICS][a][512 kB]` (1992) | 737280 | `$1234` | The Medway Boys Protector IV (F1/F2 prompt) | 33, same md5s as ICS 1991 |
| `[cr Illegal]` (1992) | 737280 | `$fb35` | none | 33, same md5s as ICS 1991 |
| `[cr Vmax]` (1992) | 737280 | `$fb35` | none | 33, `AUTO\POPUL2.PRG` 2016 |
| `[cr Elite]` (1992) | 737280 | `$fb35` | none | 31, no AUTO folder: `LOADER.PRG` 548 (cracktro) in the root |
| `[cr Superior][1 MB]` | 755712 | `$1234` | Sagrotan 4.14 boot-virus protector | 32, `BOOT.PRG` 1988; 82-track, 3-sector FAT, non-MSDOS BPB (`mdir` refuses it) |

Booting: TOS 1.62 boots from all six (TOS uses the floppy's BPB and runs `AUTO\*.PRG`; the boot code itself runs
only when the sum is `$1234`). Elite and Superior boot to the desktop and are started with File→Open on
`LOADER.PRG` / `BOOT.PRG`.

Main program, per image (`md5`, from `mcopy`/FAT12 extraction):

| file | ICS 1991 | ICS[a] | Illegal | Vmax | Elite | Superior |
|---|---|---|---|---|---|---|
| POP2.TOS | `b137f2` 94660 | `b137f2` | `b137f2` | `b8fc76` 94660 | `e0f20f` 158260 | — |
| POPULOII.SPR | — | — | — | — | — | `a43fde` 150374 |
| data (`BLOCK0-3.PAK` …) | one set | same | same | same | repacked (PIF, `FX.DAT` 110624) | repacked (`FX.DAT` 100596) |

`ICS 1991` vs `Illegal`: **5 bytes differ in the whole 737280-byte image** (`cmp -l`: bytes 9,10,11 = the boot
jump field, 511,512 = the boot checksum); all 33 files are md5-identical.
`Vmax` vs `ICS 1991`: `POP2.TOS` differs in **1 byte**, text offset `$70`: `4ef8 0140` → `4ef8 0180`
(`jmp $140.w` → `jmp $180.w`, a different address for the same installed stub), i.e. the same crack family.

### The ICS family is the same build as PP's game, byte for byte

```
ICS91 dump at pc=$140 (breakpoint, before the installed stub runs) vs FILES/P2M.FIC unpacked
(lz_unpack, 0x79c10 bytes at $1770):   0 differing bytes / 498704
```
Every one of the 28 data files on the ICS disk is present in PP's `FILES/P2D`, byte-identical, and their
total size equals P2D exactly:

```
AWARDS.PAK 5696 -> P2D @ 0x257e0   FACES.PAK 6644 -> 0x1afcc   ...  (28 files, all "-> P2D @ ...")
sum of the 28 = 418679 = P2D length
```
So **PP's game is this crack's game**: same 1992 floppy build, same data files. Elite and Superior are
*different builds* (different main program and repacked data; the Elite main program is RNC1-packed,
unpacked size 303749 = header `52 4e 43 01 00 04 a2 85 00 02 67 dd`).

## 2. Test matrix (all runs cold-booted, STE TOS 1.62, blank 720K in B:)

| image | RAM | boots | plays | SAVE completes | LOAD restores | notes |
|---|---|---|---|---|---|---|
| ICS 1991 | 512 KB | yes | yes | yes, A: `T1.GAM` 56690 | yes: turn 238 at SAVE, 445 before LOAD, **299 after** | interactive, full |
| ICS 1991 | 1 MB | yes | yes | yes | yes: 238 → 441 → **299** | `chain.log` |
| ICS 1991 | 2 MB | yes | yes | yes | yes: 242 → 420 → **301** | `chain.log` |
| ICS[a] | 1 MB | yes | yes | yes | yes: 240 → 448 → **300** | Medway protector prompt first |
| Illegal | 512 KB | yes | yes | yes | yes: 240 → 427 → **299** | |
| Illegal | 1 MB | yes | yes | yes | yes: 238 → 447 → **299** | |
| Vmax | 512 KB | yes | yes | yes | yes: 284 → 479 → **305** | interactive |
| Vmax | 1 MB | yes | yes | yes | yes: 239 → 450 → **298** | |
| Vmax | 2 MB | yes | yes | yes | yes: 238 → 445 → **299** | |
| Elite | 512 KB | cracktro | **no** | — | — | after the Bullfrog logo returns to the desktop (TOS at `$e0b94c`): not enough RAM |
| Elite | 1 MB | yes | yes | yes, **B:** `T1.GAM`/`E1.GAM` 56690 | yes: 433 → **289** interactive, and 208 → 311 → **238** by script (`chainD.log`; `$8b41a`) | A: has only 32 KB free (the save to A: fails: "DISK…") |
| Elite (HD folder, `autorun C:\LOADER.PRG`) | 1 MB | yes | yes | yes, `C:\HD1.GAM` | yes: 433 → 289 | **GEMDOS file layer** |
| Superior | 512 KB | yes | **no** | — | — | "THIS VERSION NEEDS 1 MEG" (`s512_b.png`) |
| Superior | 1 MB | yes | yes | yes, **A:** `S1.GAM` 56690 (re-uses the erased `AUTO` entry) | yes: 2680 → 3060 → **2737** | interactive, `$9971c` |
| Superior | 2 MB | yes | yes | yes | yes: 2314 → 2490 → **2319** | `chainB.log` |
| ICS 1991 | Mega STE 4 MB TOS 2.06 (60 Hz) | yes | **no** | — | — | "SORRY PAL MACHINES ONLY" (`ics91_mste_afterproceed.png`) |
| ICS 1991 | TT 4 MB TOS 3.06 (60 Hz) | yes | **no** | — | — | same PAL message (`ics91_tt_menu.png`) |
| ICS 1991 | Falcon 4 MB TOS 4.04 | cracktro yes | **no** | — | — | cracktro drawn, keys ignored, PC parked in TOS `$e00d60`; unresolved |

Save/load works in **all five ICS-family disks at 512 KB**, Elite at 1 MB (B:), Superior at 1 MB.
The manual question is present but the crack family nops the compare: ICS image at `$14a86` is
`30 3c 10 bc 00 30 b4 41 4e 71 4e 71` (`cmp.w d1,d2` + **`nop`/`nop`** where PP has `bne.w`), so any answer
passes (`0000` + OK). Elite and Superior do not ask it at all (different builds).
Crack intros: ICS/Vmax/Illegal "INTERNATIONAL CRACKING SERVICE presents POPULOUS II cracked by ILLEGAL THE
IMMORTAL" + starfield, Superior "1 Meg Version, cracks and pack by Wanderer", Elite "A NO-LIMITS CRACK".

## 3. The save/load code of the ICS family, and where PP changed it

### 3.1 The two layers

* `$36efc` — the game's whole disk interface, a command dispatcher (`movem.l d1-d7/a0-a6,-(a7)`;
  `d0` = command, `a0` = name, `a1` = buffer, `d1` = length, `a2` = FAT scratch):
  ```
  036efc: 48e77ffe  movem.l d1-d7/a0-a6,-(a7)
  036f00: 2c00      move.l  d0,d6
  036f12: bc3c0004  cmp.b   #$4,d6   -> $3721c  (format)
  036f20: 4a06      tst.b   d6       -> $36fd8  (0 = read)
  036f2c: bc3c0001  cmp.b   #$1,d6   -> $37048  (1 = write)
  036f38: bc3c0002  cmp.b   #$2,d6   -> $3715c  (2 = delete)
  036f44: bc3c0003  cmp.b   #$3,d6   -> $3719a  (3 = directory)
  036f52: bc3c0005  cmp.b   #$5,d6   -> $375ae  (5 = raw sector read)
  ```
  Only four call sites exist in the whole image (the four `jsr $36efc.l` operands):
  `$2cb0e` (cr 3, directory), `$2cbe4` (cr 1, write), `$2cc58` (cr 0, read), `$2cd1a` (cr 0, the loader's
  file-by-number read, reached through `$2cc98`). Commands 2, 4 and 5 are dead library code in this build.
* `$36fd8`/…/`$375ae` — a complete FAT12 driver (BPB parsed from the boot sector at `$36f8e`; FAT12 get/set at
  `$37462`/`$374e6`; cluster chains at `$37448`) on top of `$375e0`, a **raw ST FDC driver**: direct WD1772
  register writes (`move.w #$90,$8606.w` …), MFP GPIP polling (`btst.b #$5,$fa01.w`), YM port A drive select
  (`$37a0c`: `move.b #$e,$8800.w` …), DMA address pokes (`$8609/$860b/$860d`). No GEMDOS, no BIOS.
  Drive letters come from the name: `036f6e: 0c2c003a0001 cmpi.b #$3a,$1(a4)` (`A:`/`B:`).
* No file system on the hard disk is involved anywhere: the game only ever talks to drive A or B
  (`addq.w #$1,a4 / cmpi.b #$5c,(a4)` skips `\` after the letter).

### 3.2 The save file format

Breakpoint at `$36efc` during SAVE GAME (ICS 1991, 1 MB):

```
1. call:  D0=00000003 D1=00000010 D2=000000C8  A0=00015C34  A1=00007000  A2=00002300
   A0 -> 00 00 ...                          (directory; empty drawer string = current drive)
2. call:  D0=00000001 D1=0000DD72 D2=00000022  A0=00015BB4  A1=00039630  A2=00002300
   A0 -> "TST.GAM"
```
* **SAVE** = command 1: write `d1` = `$dd72` = **56690 bytes** from `$39630` to the file named in `a0`.
* **LOAD** = command 0: `D0=00000000 D1=0000DD72`, `A1=$39630`; the raw-sector trace shows it as **one**
  read: `$375ae` with `D1=$44a` (sector 1098) `D2=$6e` (110 sectors) — the file is read whole into `$39630`,
  no seeks, and the destination address is a constant (`move.l #$8b2ae` is the same constant in the Elite
  build). There is **no header, no checksum, no sector layout**: the file *is* a 56,690-byte RAM dump.
* Verified: the file the game wrote is byte-identical to RAM at the moment of the write
  ```
  mcopy ::TST.GAM -> 56690 bytes;  ram_at_save.bin (savebin $39630 0xdd72) -> 56690 bytes;  equal = True
  ```
  The turn counter is at `$3979c`, i.e. offset `$16c` of the file (`00 ed` in both).
* Directory = command 3: fills `$20`-byte records (type `$fd`, length, 11-char name) from `a1`, `d1` = 16
  entries; the caller filters names ending `GAM` (backward compare of `4d 41 47 00` = "MAG\0" at `$2cba2`).
  The name buffer gets `.GAM` appended and the drawer string is prepended; the file stamped 1991-12-04 16:23
  in the directory is a hard-coded timestamp.

### 3.3 Exactly what PP replaced

PP's RAM patches (verified by comparing a dump at pc=$140 against the pristine image):

```
$1cf8  bclr.b #7,d0            -> 4ef8 02ac  (jmp $2ac, keyboard handler hook; not save related)
$14a88 6600fec0 bne.w          -> 6002      (manual question always passes)
$2cc98 48e77ffe movem.l …      -> 4ef8 0206  (jmp $206: store the file number at $148, then jump to the
                                              displaced instruction at $2cc9c)
$36efc 48e77ffe movem.l …      -> 4ef8 0140  (jmp $140: PP's stub)
```
**Nothing else in the 498,704 bytes differs.** The original FAT12 + FDC layer is still in RAM in PP's build;
only its entry point is redirected. `$140` (PP's stub, 700 bytes copied from RUNME text `$3f8`) ignores `d0`
and only knows "copy file number N out of the P2D image in RAM" (offset table at `$148`+`$46`,
`move.l $18e(pc,d0.w)`), which is why save/load dies: the requester's directory call (cr 3) and the save
(cr 1) get answers built for a numbered data file.

PP's own `$206` hook (`lea $148(pc),a0 / move.w d0,(a0) / jmp $2cc9c.l`) marks *which* call is a data load.
So the information needed to separate "data file" from "save file" is already there, at `$148`.

## 4. Elite's build: the same game with a GEMDOS disk layer (the template we want)

The Elite release is a different build *and* it has been converted to file I/O: its four save/load entry points
call GEMDOS directly (disassembled from RAM, `elite_req.bin`):

```
$2db64  Fopen(name) -> if >0 Fclose               ; "does the file exist?" (overwrite prompt)
$2dbe0  Fopen -> Fclose (existing) ; Fcreate -> Fwrite(handle,$dd72,$8b2ae) -> Fclose ; return d0 = (written==$dd72)
$2dc5e  Fopen -> Fread(handle,$dd72,$8b2ae) -> Fclose ; jump $2e332 (post-load)
$2dcfc  multiply d0 by $30 into a per-slot table at $2de52, Fopen, Fread(size,name), Fclose
$2da00  build "<drawer>/*.GAM" (':' -> '/', '\' accepted), Fsfirst/Fsnext, return count
```
and each routine is wrapped in the game's own "keyboard off" flag swap, which in the ICS build exists too:

```
Elite:  33f9 0008a892 00089d04  move.w $8a892,$89d04 ; 33fc 0100 00089d04 move.w #$100,$89d04  ... restore
ICS:    33f9 00011d50 00039614  move.w $11d50,$39614 ; 33fc 0100 00011d50 move.w #$100,$11d50  ... restore
```
i.e. the Elite conversion *is* option (b) below, already done by someone else, for a slightly older build
(the ICS wrappers at `$2cae0/$2cba6/$2cc1a/$2cc98` have the identical prologue and differ only in calling
`jsr $36efc` instead of GEMDOS). Working proof of the technique in this exact game family: Elite at 1 MB
played, saved `C:\HD1.GAM` on a GEMDOS hard-disk folder and loaded it back (turn 433 → 289), and the file is
56690 bytes like the floppy one.

HAGA itself can create and write files (its own statesave does):
```
Fcreate: [0x1e46]   Fwrite: [0x2a58]   (patterns 3f3c 003c 004e 41 / 3f3c 0040 004e 41 in originals/POPUL2/HAGA)
```
but the service PP's stub calls for data (`movea.l $328(pc),a1 / move.w $8(a1),d1 / jsr (a1,d1.w)` with the
parameter block at `$32c`) is a *read-at-offset* entry; whether it has a write entry was not established
[INFERENCE: it does not, PP's stub only reads].

## 5. Recommendation

**Bring the save into our build with option (b) — map the game's own three live commands to GEMDOS — using the
Elite build's routines as the template, and keep PP's numbered-copy stub for the data loads.**

Why this and not the others:

* (a) *restore the original disk layer* (`$36efc` back to `48e77ffe`): the layer is intact in RAM, so this is one
  4-byte patch — but it restores a raw FDC driver, which on a GEMDOS hard disk will read/write garbage sectors
  on the physical drive. It only helps the floppy build, where the driver already works (see (c)). Prototype
  `pop2_save_a/b` took this route and never completed a save in Hatari.
* (b) *GEMDOS at the three call sites* (`$2cb0e` cr 3, `$2cc58` cr 0, `$2cbe4` cr 1): the format is a flat
  56,690-byte block, so Fcreate/Fwrite/Fclose and Fopen/Fread/Fclose are the whole job, plus Fsfirst/Fsnext
  for the requester. Needed pieces, all evidenced: buffer and length (`$39630`, `$dd72`), the flag swap
  (`$11d50`/`$39614`, already in the ICS wrappers), the "keyboard off" window, and the Elite implementation
  of each of the four routines. The `$148` marker already distinguishes data loads from game loads, and the
  three commands to convert are exactly those that are *not* marked. Estimated as a patch in `pop2patch.py`
  (payload blob + three sites) rather than a re-implementation; the four `jsr $36efc` sites are absolute, so it
  is also TOS-relocation safe.
* (c) *base the FLOOPY build on the ICS crack*: attractive and recommended as a **second, separate** step, not
  as the HD fix. Evidence in favour: the game image is byte-identical to P2M.FIC, it **runs in 512 KB** (our
  RUNME/HAGA floppy build needs 2 MB), and save/load works out of the box, with ~117–175 KB free on the game
  disk (three saves). What it needs: the crack's own packed loader (`POP2.TOS` text `$52` ends
  `4ef8 0140  jmp $140.w`, i.e. the stub is installed by `AUTO\ICS.PRG`, not by the game image) has to be
  replaced by our payload stage (the same trick as RUNME: copy the payload before the unpack, then hook the
  final `jmp`), and `AUTO\ICS.PRG` (the cracktro) is dropped. Risks: the crack's raw FDC driver is ST/STE
  hardware only — on a Falcon the cracktro loads but the game never starts (PC parked in TOS `$e00d60`), and
  on TT / Mega STE at 60 Hz it stops at the game's own "SORRY PAL MACHINES ONLY" (`$1836`/`$1840`), so the
  crack is **not** a fix for 60 Hz and does not replace our HD build for TT/Falcon.

Risks of (b): (i) GEMDOS from the game's context — Elite proves it works with the same flag swap, but its
wrapper also sits behind a `$8a508`-style flag we did not identify; (ii) the requester's directory list must
be produced in the game's `$20`-byte record shape (`$fd`, length, 11-char name) and only `GAM` names pass the
caller's filter — Elite's `$2da00` shows the exact shape; (iii) do not disturb `$375be-$375e0` (the FDC
driver's own state) or TOS's floppy bookkeeping that `pop2_floppy_head` corrects — a GEMDOS path bypasses both,
which is one more point in its favour; (iv) saves must stay ≤ 56,690 bytes (the size is hard-coded in the
loader's `cmpi.l #$dd72` and in the read length), so no room for extra state.

Also worth noting for the README: PP's own `README.TXT` says "or play simple hard disk install version where
can use game's save/load options" — the Elite disk contains exactly that: `INSTALL.TOS` prints
"POPULOUS II — Hard disc install ... enter directory (default = C:\POPII)" and copies the files. That is the
third-party proof that the GEMDOS conversion is the intended HD answer.

## 6. Reproduce

```
cd work/scratch/disks
python3 matrix.py ICS91.st ics91_512 512 ics      # and Vmax.st / Illegal.st / "ICS[a].st" ...
python3 matrix.py Elite.st  elite_1m 1024 elite   # saves to B:, blank 720K made with mformat
python3 mtt.py ICS91.st ics91_tt 4096 ics tt 3.06 # TT / Falcon / Mega STE: PAL check
cat ICS91/POP2.TOS | python3 ../../../../../tools/m68dis.py <dump> 36efc   # the disk layer
```
Raw outputs quoted above are from `chain.log`, `chainA.log`, `chainB.log`, `chainC.log` in that folder and
from the interactive sessions (`shots/*.png`, `run/ics_at140.bin`, `run/ram_at_save.bin`, `run/TST.GAM`,
`run/E1.GAM`, `run/elite_req.bin`).
