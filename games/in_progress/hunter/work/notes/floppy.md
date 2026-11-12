# Hunter floppy build (HunterFloppy)

Tools: `tools/huntpatch.py verify|taildump|build --floppy [--samples F] [--two-disk] [--geometry TxS] [--zip]`, `tools/huntfloppy.py` (Hatari cold-boot cells), `tools/fire_depack.py`, `patches/core_floppy.s`, `patches/FLOPPY.TXT` (README of the zip).
Tags: **[obs]** observed (Hatari 2.6.1 output quoted), **[disasm]** read from disassembly (capstone on the file / RAM dump), **[INFERENCE]**.
Everything is derived from the user's images in `alt/floppy/` (git-ignored, never modified; builds go to `build/floppy`, `dist/`).

## 1. The two images

| | Paper Bag `.st` | Replicants `[t]` `.st` |
|---|---|---|
| size / geometry | 829440 B, 81 trk x 10 spt x 2 (BPB: spc 2, 112 root entries) | 737280 B, 80 x 9 x 2 |
| boot sector | not executable (sum `$558a`, not `$1234`) | not executable (`$3ee8`) |
| autostart | `DESKTOP.INF` `#Z 00 A:\HUNTER.TOS` (the TOS desktop runs it) | **none**: `HUNTER.PRG` only (we would have to add a DESKTOP.INF) |
| loader | `HUNTER.TOS` 2206 B, plain GEMDOS program | `HUNTER.PRG` 79812 B, one packed program |
| free | 43008 B | 261120 B |

### 1.1 Paper Bag boot flow [disasm of HUNTER.TOS, file offsets]
1. Desktop autorun -> `HUNTER.TOS`: Super, `sp=$7fff8`, Setscreen `$78000` low res, prints "PAPER BAG PRESENTS ... SAVE YOUR GAMES TO THIS DISK", **waits for a key** (Crawcin). `T`/`t` only patches `$22a` with a `nop` that changes nothing (both paths reach `jmp $800.w`): the "trainer" is vestigial, there is none.
2. Blanks the palette, GEMDOS `Fopen "800"`, `Fread $1ea00` to `$20200`, `Fclose`, **depacks** (`$5a6`, Pack-Ice style "FIRE" format, backward bit stream) to `$20800`.
3. Disables interrupts (`sr=$2700`, MFP off), copies the unpacked game (`$4c01` longs) to **`$800`** (resident code `$800..$12003`, 71684 B), copies its own file loader (`$232..$722`, `$4f1` B) to `$d30e`, applies 22 `move.[bwl] #imm,abs` patches (copy protection/loader hooks), copies a helper to `$80040`, `jmp $800.w` (RAM `$6a124`, the code runs from a copy at `$6a000`).
4. **Files are read by the cracker's own FAT12 + FDC code** (`$d30e`.., `$ff8604/6` direct, no GEMDOS/BIOS): name search in the root directory, FAT chain, one sector per read. Geometry comes from the BPB: spt `$18(a0)`, sides `$1a(a0)`, FATs/spf/root entries `$10/$16/$11`; the only hard-coded number is **2 sectors per cluster** (`$d3dc: subq #2,d0 / add d0,d0`). So other track/sector counts work, 1-sector clusters do not. Loaded files that start with `FIRE` are unpacked in place (`$d62a`).
5. Saving: the loader has a write path (`$80` flag = `$ffff`, FDC write commands `$a0`) that writes into the **existing** clusters of the save slot files (`0F` "HUNTER SAVES", `10..15`); it never allocates, so adding files cannot disturb it.

### 1.2 What the loader keeps in RAM: a file cache over `$80200..$FFFFF` [obs + disasm]
`HUNTER.TOS` copies a helper (`$722..$8da`) to `$80040` that stores every FIRE file it loads, packed, in a RAM cache starting at **`$80200`** (two `lea $80200.l,a0` at file `$72c`/`$7a0`) with `$7fe00` bytes left (long at `$7fc`), i.e. it runs to the end of 1 MB. That is exactly where our payload (`$8BA00..$AEFFF`) lives. First build: patches present -> the game started, then reset itself; Hatari PC samples showed `$800ae` (inside the cache copy loop) and the build without payload (empty patch set, 1.5 KB payload) was fine [obs]. Fix (in `build_hunter_tos`): the three constants become `$AF000` / `$100000-$AF000` (cache `$AF000..$FFFFF` = 331776 B), and the loader stage clears the first 8 bytes there (RAM is not zeroed on warm boots). The cache is a speed feature of the crack: it stays, only smaller.

### 1.3 Replicants [disasm of the unpacked program]
`HUNTER.PRG` is one program packed with the same routine (stream header `FIRE` at `$230`, packed `$13590`, unpacked `$1c72a`; `tools/fire_depack.py --prg` reproduces it, 116522 B = text `$1c53e` + bss `$1800`). It starts with 4 unconditional RAM patches (`$f94c`, `$a968`, `$f8a4`, `$f31a`: **trainer always on**, no key to switch it off), then copies a `$1ba00` byte image to `$800`. That game image is **not** the PP/Paper Bag one: searching Paper Bag's patch sites in it: `p4_edge` site found at `$7442` (Paper Bag `$7450`), `p4_poly` `$7546` (`$7554`), `p4_ikbd` (`$c5fa`) **not found**, `$c628` ambiguous; 1169 of 1719 32-byte chunks match, at shifted offsets (-10, -24, -26, -2208 ...). Every patch blob that touches game variables would have to be re-derived and re-proven pixel-identical.
**Choice: Paper Bag.** Its resident game is the same as PP's HD build (below), no trainer, autostarts. Replicants' only advantage is 261 KB free; the extended disk geometry (section 3) gives Paper Bag more room than that.

## 2. Same resident code as PP's HD build [obs]
`huntpatch.py taildump --floppy` boots the unmodified Paper Bag image, breakpoint `pc=$6a124`, dumps RAM (`work/dumps/boot/ram_tail_floppy_1mb.bin`). `fl_tail()` rebuilds `$800..$12003` from the disk (unpack file 800 with our `fire_depack`, apply the cracker's patches decoded from `HUNTER.TOS`) and `verify --floppy` compares:
```
tail image $00800..$12004 (71684 B, 71684 compared) vs ram_tail_floppy_1mb.bin: IDENTICAL
p4_edge   site $07450  original 426d16043018 (match)      p4_ikbd  site $0c5fa  original 70166100e9c0 (match)
p4_poly   site $07554  original 3c00dc463f06 (match)      snd_core site $0c628  original 082d00070093 (match)
verify: ALL OK
```
Against PP's HD dump (`ram_tail_1mb.bin`): 13 differing bytes in `$800..$12003`: PP's two hooks (`$aff0` kbd, `$d542` file hook) and `$a8a4` (`'DBUG'` immediate of a debug exception handler: Paper Bag has it, PP zeroed it). The depacker is checked the same way: it reproduces HD `FILES/1,3,6,C` byte for byte from Paper Bag `01,03,06,0C`, and file 800 equals the RAM at `$800`. Hence the patch sources are shared unchanged (`p4_*`, `snd_core`, `core.s` entry); the floppy build uses the same `build_image()`. `huntab.py` (identical picture gate) was **not rerun**: the patched code and all bytes it reads are the HD ones (the three differences above are outside it); the pixel-identity proof of `p4_*` stands on the HD runs [INFERENCE].

## 3. One disk (the user's choice): 82 tracks x 11 sectors, full bank
Paper Bag has 43 KB free; we need the bank (HNSOUND.BIN 124126 B) + payload + the longer `HUNTER.TOS`. mkfs.fat -A (Atari variant), spc 2, 112 root entries, 2 FATs, copy every file by name [obs, `mcopy`]:

| geometry | bytes | free with Paper Bag files only |
|---|---|---|
| 81 x 10 x 2 (original) | 829440 | 43008 |
| 80 x 11 x 2 | 901120 | 116736 |
| 81 x 11 x 2 | 912384 | 128000 |
| **82 x 11 x 2** | **923648** | **139264** |
| 83 x 11 x 2 | 934912 | 150528 |

Needed with 1 KB clusters: bank 122 clusters (124928 B) + payload file 5 (4596 B) + `HUNTER.TOS` same 3 clusters (2512 B) = ~130 KB. **Chosen: 82 x 11, full-quality bank, 9216 B free** [obs: `build --floppy --samples ...`]. 80 x 11 (116736) would need a bank of about 105 KB or less; dropping the half-scale copies of the loop samples (`$A4DF4..` = 38634 B, bank -> 85.5 KB) would give 80 x 11 a 20 KB margin, but costs 6,866 -> 8,801 cycles/VBL for a voice at volume 15 (4.3 % -> 5.5 % of a frame, +1.2 points while the engine plays at full volume; `snd.md` table) [from snd.md, not remeasured]: not done, the full bank fits.
The payload file is stored as records `{dest.l len.w bytes}` of its non-zero runs (17408 B image -> 4596 B; the stage clears `$8BA00..$8FFFF` first), `pack_payload`/`unpack_payload` round-trip asserted at build time.
Real hardware: 11-sector, 82-track disks need a drive that seeks to track 81 and a disk written in the 11-sector format (Fastcopy/MSA-style tools, Gotek); the `.st` has no interleave/skew, so write it with a skew or reading is slow (see section 9: with real FDC timing the load takes about as long as the original's). Standard-format alternative: `build --floppy --samples F --two-disk` (section 5).

## 4. Loader stage (`core_floppy.s`, appended to HUNTER.TOS) and the splices
`build_hunter_tos` (all asserted against the original bytes): `$68` T-key `lea/move.w` -> 4 nops; `$b8` `move.w #$4e73,$90.w` -> `bsr.w stage1` + nop; `$22a` `bra.b $22e/nop` -> `bsr.w stage2` (then the original `jmp $800.w`); the three cache constants; stage appended to the text (+306 B, no new relocations; it must lie within the 16388 B HUNTER.TOS copies to `$6a000`).
- **stage1** (right after file 800 is unpacked: TOS alive, interrupts on): needs phystop >= 1 MB (else untouched game); clears cache head and `$8BA00..$8FFFF`; GEMDOS-reads `HNPATCH.BIN` to `$B8400`, unpacks the records (destinations range-checked), checks `'HNPA'`, calls the payload's own STE `probe` (address exported from `core.s` via the vasm listing, no second copy); on STE-class hardware reads `HNSOUND.BIN` to `$90000` (checks `'HSND'`, else clears the magic: the payload plays the YM). Plain ST never reads the 124 KB.
- **stage2** (the copy at `$6a000`, SR `$2700`): `jsr $8BA04` = `hnentry` of `core.s`: verify ALL boot sites, apply all or none, `'HNPO'`/`'HNPF'` at `$8BFF8`, FLAGS `$8BFF0` (unchanged HD core).
- Deferred (`; load:`) and `; image:` patches are HD loader features and are refused by `--floppy` (the default set has none).

## 5. Two-disk set (alternative, `--two-disk`)
Disk 1 = original geometry, no bank; disk 2 = 720 KB FAT12 with `HNSOUND.BIN` (contiguous, serial `$485344`). On STE-class hardware the stage shows a prompt (navy page, VT52): RETURN or joystick FIRE = load, SPACE/ESC/joystick UP = skip. It tries drive A (serial check by raw `Floprd` of the boot sector), then drive B if `_nflops >= 2`, so disk 2 in B needs no swap; from A it asks for the game disk and loops until drive A's boot sector serial equals the one read at start (the game reads disk 1 later with its own FDC code). Joystick via `Kbdvbase` `joyvec`.
[obs, **before** the cache fix, so the game crashed afterwards] prompt page, "Loading ....", game-disk prompt and refusal rendered correctly on STE 1.62 (`work` shots in `/tmp`, not kept). **After the cache fix the two-disk path was not rerun**, nor the B-drive and skip paths; treat it as untested. It remains in the tree because the user asked for the standard-format alternative to be documented.

## 6. Cold-boot results (Hatari 2.6.1, `tools/huntfloppy.py`, single 82x11 disk, full patch set + bank) [obs]
```
BOOT OK cell=ste162  machine=ste    tos=1.62 mem=1024K  in_game=True MARKER=b'HNPO' FLAGS=00000003 fps=4.80   $90000=48534e44 ('HSND')
BOOT OK cell=st104   machine=st     tos=1.04 mem=1024K  in_game=True MARKER=b'HNPO' FLAGS=00000006 fps=5.60   $90000=00000000 (bank not read)
BOOT OK cell=mste206 machine=megaste tos=2.06 mem=4096K in_game=True MARKER=b'HNPO' FLAGS=00000003 fps=4.80   $90000=48534e44
```
(in_game = 3D loop running + screen flips; ST 1.04 uses fixed waits because the reference crops are STE pictures.) STE sound: `--wav 6` (Hatari WAV capture, injected explosion, as `snd_test coldboot`): `payload mode=2 (DMA sound)`, `build/wav/ste_pre.wav` 6.0 s, rms 885, peak 5609 (git-ignored). **TT 3.06** (4 MB): loader and patches ran (`HNPO`, FLAGS 3, bank loaded) and the HUNTER title is displayed at 32 MHz; the harness could not navigate on to the 3D view (the `title2` crop gate fails on the TT, the blind run did not leave the title), so TT 3D view is **not proven**. **Falcon 4.04: not run.** Lean set (no samples, 81x10, YM only) and STE with 1 drive/2 drives are the same code path as above minus the bank read; the lean build was not cold-booted after the cache fix.
A 3D view is only reached after SPACE is pressed repeatedly: the title ignores keys while the game loads from the floppy (`leave_title`).

## 7. Free RAM and saving
Poison test (`huntfloppy.py poison` / `--bp-load` / `poison-check`): at the loader's jump to the game the RAM `$8BA00..$AEFFF` is saved, every byte that is neither payload, payload state nor bank is replaced by a non-zero pattern, the game boots to the 3D view and drives 25 s (Up+Left), RAM is dumped [obs]:
```
pattern /tmp/hf/pat.bin: 14059 free bytes of 144896 poisoned
BOOT OK cell=ste_poison ... in_game=True MARKER=b'HNPO'
poison check ste_dump_poison.bin: 14059 pattern bytes in $8BA00..$AEFFF, 0 changed
bank bytes differing in RAM after boot+25 s drive: 0 of 124126 ; payload code/table bytes changed: 0
```
(STE 1 MB, TOS 1.62; the cache lives at `$AF000+`.) Not repeated at 2/4 MB or on plain ST.
Saving: ESC -> Disk Operation -> Save Game -> slot -> name works in the patched game on the extended disk (game returned to the 3D view, `HNPO`); see the result line at the end of this section for what changed on the disk. The write path touches only the existing slot files, our files are ordinary directory entries.

Save result [obs, STE 1.62, 82x11 disk]: ESC -> Disk Operation -> Save Game -> slot "free" -> name `tst` -> Return, then eject (Hatari writes the image back on eject): files whose content changed: `00`, `0F`, `13` (the game's own save writes: the slot file `13`, the directory file `0F` and `00`, which the game also writes [INFERENCE: not compared with an unpatched run]); directory entries identical, free bytes 9216 -> 9216, `HUNTER.TOS`, `HNPATCH.BIN`, `HNSOUND.BIN`, `DESKTOP.INF` byte-identical, `fsck.fat -n`: `30 files, 886/895 clusters`, no errors; the game was back in the 3D view with `MARKER='HNPO'`. Loading the saved game again was not tried.

## 8. Not done / open
- Falcon 4.04, TT 3D view, 2 MB, 512 KB (stage skips everything below 1 MB; not run), plain-ST/STE lean single-disk cold boot after the cache fix, two-disk paths (swap, B drive, skip, joystick FIRE) after the cache fix, `huntab.py`.
- Real 11-sector hardware (skew, drive tolerance) is untested; the file cache now holds 331 KB instead of ~523 KB, so the title/level loads may reload files that the original cache would have kept (not measured).
- `build --floppy --zip` writes `dist/Hunter_patched_floppy_<date>.zip`: `HUNTER_disk1.st` + `README.TXT` (`patches/FLOPPY.TXT`, rewritten for the one-disk set).

## 9. Load times with real FDC timing (`--fastfdc no`, Hatari 2.6.1, STE 1.62) [obs]
Correction: an earlier remark that the title load "takes minutes without --fastfdc" was wrong; the title ignores keys while loading and my first test pressed SPACE only once. `tools/huntfloppy.py` now defaults to `--fastfdc no`. Measured with `meas`-style polling (key at the "Paper Bag" screen -> MAIN OPTIONS visible, emulated seconds from the VBL counter, space pressed every 8 s so each figure is +-8 s):

| disk | stage done (marker HNPO) | key -> MAIN OPTIONS |
|---|---|---|
| (a) original Paper Bag, 81x10 | - | **39 s** |
| lean build (81x10, no bank, our stage) | 15 s | 42 s |
| (b) ours 82x11, bank read with GEMDOS Fread | 24 s | 51 s |
| ours 82x11, bank read by raw track reads (`Floprd`, shipped) | 20 s | 51 s |

Cause analysis: the crack's loader does read ONE sector per FDC command (`$d474`: DMA sector count 1, command `$80`, one call per sector, [disasm]); but the original, 81x10, loads in 39 s, i.e. ~22 sectors/s, so Hatari's .st track layout does not make it lose a rotation per sector, and 11 sectors per track costs nothing: the game phase is 27 s on both 81x10 (lean: 42-15) and 82x11 (51-24). The extra time of our disk is our stage (+3 s lean) and the 124 KB bank (+9 s with Fread, ~+5 s with raw track reads; Floprd reads whole tracks per command). So no loader rewrite was done. What a .st cannot express: sector interleave/skew (and gaps); Hatari does not model it for .st, so this test cannot show whether a real drive loses rotations with one-sector-per-command reads. On real hardware/Gotek the disk should be written with a skew (FlashFloppy `image.cfg` interleave/cskew) if loading is slow; an .msa is only a compressed .st (no layout information), .stx/.hfe could carry it but are not produced. Nothing about real timing is proven.
Shipped bank read: `loadbank` (XBIOS Floprd, track at a time, LSN from the disk built in a second pass, contiguity asserted).

Cold boots with real FDC timing after the cache fix [obs]:
```
BOOT OK ste162_slow  STE 1.62 1 MB   HNPO FLAGS 3 fps 4.80 bank 'HSND' (shipping 82x11 disk, in_game after 89 s)
BOOT OK mste206_slow Mega STE 2.06 4 MB HNPO FLAGS 3 fps 4.80 bank 'HSND' (226 s incl. the TOS 2.06 memory test)
BOOT OK lean_ste     STE 1.62, lean 81x10 build (no bank): HNPO FLAGS 3 fps 5.00, $90000 = 0 (YM sound)
BOOT OK two_swap     STE 1.62, --two-disk, swap path: prompt 1 after 22 s, refusal without the disk, prompt 2 after 37 s, 3D view after 103 s, HNPO, bank 'HSND'
plain ST 1.04 (82x11, blind harness): HNPO FLAGS 6 reached MAIN OPTIONS; the blind menu clicks of the harness missed (twice), so the 3D view was NOT reached in this timing; the fast-FDC run earlier reached it (fps 5.60).
```
Not rerun with real timing: two-disk B-drive and skip paths, TT/Falcon.
