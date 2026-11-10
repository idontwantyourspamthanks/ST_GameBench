# Powermonger: boot chain, loading, patch delivery, free RAM (PMLoader)

Tags: **[obs]** observed in Hatari 2.6.1 (raw output quoted or reproducible with the command given); **[disasm]** read from the RAM dumps with `tools/m68dis.py` / capstone (addresses given); **[INFERENCE]** not verified.
Tool: `tools/pmpatch.py` (verify, list, build, live, boot). Delivery core: `patches/core.s`. HD code: `patches/hd_*.s`.
Addresses are from the 1 MB STE / TOS 1.62 reference run unless stated. The game itself is position dependent and uses fixed addresses; they do not change with machine, TOS or RAM size. Only TOS-owned addresses (the TPA the program is loaded to) vary.

## 1. The boot chain: two self-decoding PRGs in series

```
TOS -> boot sector ("Boot 60hz III", harmless) -> \AUTO\WAR.PRG (Pexec, loaded by TOS)
  stage 0  WAR.PRG plaintext stub: Super(0), blank palette, vectors -> rte stub, copy to $500, jmp $508
  stage 1  depacks (in place) the nested PRG -> text $576..$579AD: the INTRO (title pictures, credits), and a FAT12 loader
           at the end of the intro: loads DATA\SPRITE40.DAT to $13BA and jumps into its own copy of the same stub
  stage 2  DATA\SPRITE40.DAT is NOT sprites: it is a second self-decoding PRG with the same stub.  It depacks the GAME
           PROPER -> text+data $10A6..$1C48D (111592 B), bss to ~$6F2BC.  All game code ($127e6, $13020 ...) is here.
  then     the game loads DATA\*.DAT by name with the same FAT12 loader (resource table at $e0c4) as it needs them.
```
[obs] stage 2 = `DATA\SPRITE40.DAT` because the string "data\sprite40.dat" (lower case, so a case-sensitive grep for SPRITE40 misses it) is at `$13BA` of the stage 1 image, passed to the loader at `$1356: jsr $57032` [disasm of `work/dumps/entry576.bin`], and the file starts with `601a 0001 8ccc ...` and the same 48-byte decoder as WAR.PRG [obs: `xxd DATA/SPRITE40.DAT`]. The file is dated 1987 in the directory, which is why it looks like a leftover. The Empire trainer disk changes 3288 bytes inside it (README.md), consistent with it being code.

### 1.1 WAR.PRG layout (286384 B)
`601a`, text `$45E90`, data 0, bss 0, no symbols, relocation table = one zero long (no relocations: the program is position dependent and pc-relative at the start). Text offsets (`$0` = file `$1c`):

| text offset | content |
|---|---|
| `$0..$7` | `clr.l -(a7); move.w #$20,-(a7); trap #1` = Super(0). Never returns to user mode. |
| `$8..$4f` | `lea $8240.w,a0` clear the palette, `lea $500.w,a2`, `movem.l $70(pc),d0-d1; movem.l d0-d1,(a2)` (writes `bclr #6,$fa11.w` + `rte` at `$500..$507`), vectors `$64..$7c` and `$100..$1fc` all set to `$506` (rte), except `$118` -> `$500` (acknowledges the keyboard), `lea $500.w,a7` |
| `$4e..$65` | copies 12 bytes of code (text `$66..$71`) to `$508`, `jmp $508.w` |
| `$66..$71` (runs at `$508`) | `move.l #$45e16,d0 / move.b (a2)+,(a1)+ / subq.l #1,d0 / bne` with `a2 = text+$7a`, `a1 = $514`: the loop moves text `$7a..` down to `$514` (the 12 bytes of the copy loop at `$508` are what is moved there first; the loop is not overwritten before it ends). **RAM address of text offset t ($7a <= t) = t + $49a.** |
| `$7a..$bf` (RAM `$514`) | `move.l #$78000,d0; lsr.w #8,d0; move.l d0,$8200.w` (video base `$78000`); builds a fake basepage at `$53a` (text `$a0`, 28 bytes, sizes copied from `$c2/$c6/$ca`), `move.l a0,-(a7); bsr.b $c0` |
| `$c0..$db` (RAM `$55a`) | nested PRG header `601a 0004 5db3 ..` whose code starts at `$dc` (RAM `$576`) |
| `$dc..$214` (RAM `$576`) | the decoder (below); at the end it builds a 32-byte routine on the stack with eight `move.l #imm,-(a7)` at text `$1e4..$212` (6 bytes each) and `jmp (a7)` at `$214` |
| `$216..` | packed block: word at `+2` = offset of the packed stream, Huffman tree table at `+4`, stream header (packed size, unpacked size) |

### 1.2 The decoder (text `$dc..$140`) and the stack routine [disasm, reproduced bit-exactly in Python]
`pmpatch.py pm_depack()` is a transcription. Facts: the bitstream is read backwards from the end of the packed data (`move.b -(a0),d1`, 8 bits per byte, MSB first), each bit picks the child of a Huffman node in a table of words at `a3` (`bmi` = leaf, leaf word `$f0xx` = byte `xx`, `$f100` = escape: the next leaf is a run count c and the LAST WRITTEN byte is repeated c times), the output is written backwards (`move.b d4,-(a2)`) from `a2 = a0 + unpacked + $100` down. The image therefore ends up at `packed_start + $100` (text `$722` for WAR.PRG).
Then: relocation of the nested PRG by `d2 = $576` (a `601a` header at `a4`, relocation table after text+data+symbols, standard TOS delta table), the fake basepage fields are filled (text start/size etc.), and the routine pushed on the stack runs:
```
12d8 5380 66fa   move.b (a0)+,(a1)+ ; subq.l #1,d0 ; bne     copy text+data ($57438 B) from the depacked image ($bd8) to $576
4219 5381 66fa   clr.b (a1)+ ; subq.l #1,d1 ; bne             clear d1 ($8a2) bytes after it
4cef 7fff 0020   movem.l $20(a7),d0-d7/a0-a6                  the registers the stub was entered with
4fef 005c        lea $5c(a7),a7                               (a7 now points at the slot that 2549 005c wrote: move.l a1,$5c(a2))
4e75             rts                                          -> a1 = $576
```
[obs] the stack routine sits at `$498..$4b7` in stage 1 (a7 = `$498` when `jmp (a7)` runs) and after the copy `pc = $576`, `a7 = $4f8`, `SR = $2304`, `d0 = $70080 d1 = $fa114e73` (leftovers of TOS), `a1 = $4632a` (Hatari breakpoint `pc = $576 && ($576).w = $4eb9`, `r` output in the session log; same for stage 2: `pc = $10a6 && ($10a6).w = $41f9`: `a7 = $ff8`, `SR = $2404`, `a0 = $106a a1 = $25a40`).

### 1.3 The first moment all resident code is in place
* **Stage 1** hands over at `$576` (`jsr $1594; jmp $660`): the intro code, loader and pictures are resident. Nothing of the game proper exists yet.
* **Stage 2 hands over at `$10A6`** (`lea $2de6a,a0`): this is the moment the game proper is complete and has not executed an instruction: **the place for the trampoline**. [obs] The relocated depacked SPRITE40.DAT equals RAM at that moment in all 111592 bytes (`pmpatch.py verify`: "0 differing bytes", dump `work/dumps/entry10a6.bin`); the stage 1 image equals RAM at `$576` in all 357432 bytes (`entry576.bin`). So site `orig` bytes are DERIVED from the shipped disk image (depack + relocate), not from a dump.
* Why it is the right place: the game keeps running its own code (self-relocating intro regions are reused as buffers: 99% of the stage 1 area differs in `map_idle.bin` already) and the only later loads are `DATA\*.DAT` data files. [obs] `map_idle.bin` vs the stage 2 image: 98.7% identical bytes (the rest are variables).

## 2. How the game reads the disk (all raw, no GEMDOS/BIOS after Super)

### 2.1 Driver stack [disasm; stage 2 addresses, stage 1 has the same code at +`$49abe`: `$574ba` = `$d9fc`, `$57032` = `$d574`]
* `$d9fc` sector driver (`d1` = first logical sector, `d2` = count, `d3.b` = 0 read / 1 write / 2 format, `d3` bit 15 = slow, `a0` = buffer, `d0` low bit = side, `d0` high word = sectors per track (9..11, default 10); returns `d0 = 0` and Z set on success, else an error code). It programs the WD1772 and the DMA directly (`$ff8604/$ff8606/$ff8609..$ff860d`), drives the motor through YM port A, and saves/restores `$43e` (floppy lock). **Callers: 6 in the FAT reader (`$d638 $d68c $d732 $d760 $d790 $d7b0`) and 6 in the save-game disk code (`$1baaa $1bac6 $1bd5e $1bdd2 $1be70 $1bea0`). The FAT reader only ever passes `d3 = 0` (read).**
* `$d574` by-name loader (`a0` = "DATA\X.DAT", `a1` = destination): parses an optional "A:", reads sector 0 (BPB: root entries `$11(a0)`, sectors per FAT `$16`, sectors per track `$18`), walks the directory path component by component (11-byte 8.3 compare, subdirectories), follows the FAT12 chain (`$d770`) and reads contiguous runs with one `$d9fc` call, the last partial sector into the buffer at `$d7fc` and a byte copy. `d0 = 0 / Z` = loaded, `$df` = not found. [obs] stage 2 callers: `$d528` (inside `$d4d2`), `$1bd28`, `$1bd46`; stage 1: only `$1356`.
* `$d4d2` resource loader (word argument = resource number) retries `$d574` forever with a "PLEASE INSERT THE POWERMONGER DISK INTO DRIVE A:" screen (`$1bec8`) when it fails. `$df52` (the game's file API, 16 callers) copies a preloaded buffer if the pointer in `$e040[n]` is set, else loads via `$def0`/`$d4d2`, and unpacks with `$e2b8` if the loaded size (`$df12[n]`) differs from the expected size (`$e084[n]`): the DATA files are compressed.

### 2.2 The files (resource table `$e0c4`, 12-byte entries {name ptr, destination, size}; destinations at the stage 2 hand-over)
Call sites of `$df52` carry `move.w #n,-(a7)` just before the `jsr`:

| n | file | file size / unpacked | dest at hand-over | called from (stage 2) |
|---|---|---|---|---|
| 0 | TEXTURES.DAT | 8104 / $3280 | set at run time (`$2e000`) | `$12f70` |
| 1 | QAZ.DAT | 15388 / $7d00 | run time (`$78000`) | `$13d0a $187e8` |
| 2 | SPRITE16.DAT | 3932 / $1d60 | `$312a0` | `$12f7c` |
| 3 | SPRITE8.DAT | 8724 / $4c7c | `$33000` | `$12f88` |
| 4 | SPRITE24.DAT | 5532 / $32a0 | `$37c7c` | `$12f94` |
| 5 | SPRITE32.DAT | 8620 / $4380 | `$3af1c` | `$12fa0` |
| 6 | (CAP_SPR.DAT, not on disk) | | `$3f29c` | |
| 7 | (BITMAP.DAT, not on disk) | | `$3f29e` | `$13c0e` |
| 8 | CAPGRAPH.DAT | 11164 / $7d00 | run time (`$24400`) | `$18804` |
| 9 | FX.DAT | 75544 / $16b6a | `$5879a` | `$11c0` |
| 10 | MAP.DAT | 85200 / $17c00 | `$3f364` | `$11224` |
| 11 | MAPDATA.DAT | 17388 / $fef4 | `$3f364` | `$113d0` |
| 12 | END_PIC1.DAT | 16960 / $7d00 | run time | `$1a654` |
| 13 | END.DAT | 60936 / $11e5e | `$3f768` | `$1a66e` |
| 14 | LOSE.DAT | 28420 / $7d00 | run time | `$1a5e2` |
| 15 | WIN.DAT | 10364 / $7d00 | run time | `$1a524` |
| - | SPRITE8.DAT again (`$1bafc`) | | screen buffer `$2df7c` | `$1bd0e $1bd38` |

(`$e0c4`/`$e084` read from `work/dumps/entry10a6.bin`; this is the game's own list, there is no other data on the disk.)

### 2.3 Where the data is on the floppy (`protected.st`: 800 sectors per side... 1600 sectors, 10 per track, side-interleaved: sector number = track*20 + side*10 + (sector-1))
BPB: boot sector 0, FAT1 sectors 1..5, FAT2 6..10, root directory 11..17, data from sector 18 (cluster 2), 2 sectors per cluster. [obs: `pmpatch.py`'s own FAT12 parser, cross-checked with `mdir -/`]

| file | bytes | sectors (track/side) |
|---|---|---|
| `AUTO\WAR.PRG` | 286384 | 22-569 (t1 s0 sec3 .. t28 s0 sec10), 770-773 (t38 s1 sec1-4), 1482-1489 (t74 s0 sec3-10) |
| `DATA\SPRITE40.DAT` (stage 2) | 101608 | 570-769 (t28 s1 .. t38 s0) |
| MAP.DAT | 85200 | 774-941 |
| TEXTURES / QAZ / SPRITE16 / SPRITE8 / SPRITE24 / SPRITE32 / CAPGRAPH | 8104 15388 3932 8724 5532 8620 11164 | 942-957 958-989 990-997 998-1015 1016-1027 1028-1045 1046-1067 |
| FX.DAT | 75544 | 1068-1215 |
| MAPDATA / WIN / LOSE / END_PIC1 / END | 17388 10364 28420 16960 60936 | 1216-1249 1250-1271 1272-1327 1328-1361 1362-1481 |
| free | | clusters 738-792 = sectors 1490-1599 = **55 clusters = 56320 B** |

[obs] A cold boot with `--trace fdc` logged TOS reading WAR.PRG in exactly these runs (track 1..28 side 0/1 sector by sector, `addr` = TPA, then t38 s1 sec1-4 and t74 s0 sec3-10; the FAT sectors 7, 8, 9 of track 0 `$56d0..$5ed0` before it). After `pc = $5b6`... the game's own driver takes over.

### 2.4 Copy protection and saves
* **Protection** = the manual question at the first map entry, answered from RAM (boot.md): not a disk check. [obs] No code path of the loader checks anything but the FAT12 contents; the loader never writes to the game disk (the FAT reader passes `d3 = 0` only, section 2.1).
* **Saves**: a separate SAVE GAME DISK in A:, prepared by the game itself ("FORMAT THE POWERMONGER DISK?", strings at `$1c06d..`). [disasm `$1ba72..$1bf2e`] Sector 0 of that disk is the 512-byte block at `$1bb0e` ("POWERMONGER ST SAVED GAME DISC ..."; the game checks `'POWE'`, `$1bd52`), slot k (letter `A`+k in `$e296`) is `$c6` = 198 sectors at sector `1 + k*198` (the game state `$3f768..`, read with `d3 = $8000`, written with `$8001`), the used-slot flags are bytes `$1bbfa+k` of sector 0. Format = `d1=0 d2=$320 d3=2` (800 sectors) and the boot block is written back with `d3 = 1`. So **the game writes only to a second floppy** (the data disk), never to `protected.st`. The floppy build keeps all of that untouched.

## 3. Patch delivery (floppy and HD share the carrier)
```
WAR.PRG (rewritten)                                          RAM
 header: data segment = N                       text $0..$7  jmp front.l ; nop   (relocation entry at text+2)
 text    original (286352 B)                    data         front (pos.-independent) + payload records
 data    front + payload image                  front: copy the records to RAM; uinit (USER mode); Super(0) (original insn);
 reloc   $00000002 $00                                 init (supervisor); jump to text+8 = the rest of the original program
SPRITE40.DAT (stage 2, same size): the 32-byte stack routine ends in `jmp hook2` instead of `rts`   (file $124..$153)
WAR.PRG stack routine (text $1e4): `jmp hook1` ONLY if a patch has `; stage: 1` (the HD build)
```
* **Carrier = the appended data segment of WAR.PRG** (as Midwinter did): TOS loads text+data with its own file API, the disk layout of every other file is unchanged, and the same WAR.PRG works from a floppy and from a GEMDOS folder. The depacker output reaches beyond the carrier's text end, so `front` moves the payload to `$B8000` before anything runs.
* **Why the payload cannot sit in WAR.PRG's text**: there is no slack; and the stub overwrites everything from `$514` to `$58010` with the game.
* **Sparse payload.** The flat image ($B8000..highest used byte) is stored as records `{dest.l, len.l, bytes}` (non-zero runs, long aligned, runs closer than 12 bytes merged), a zero-fill record `{dest.l, len.l | $80000000}` per `; data:` reservation plus one for `$B8790..$B87FF` (init tables, FLAGS, MARKER), and a long 0 at the end. `front` executes them in that order (zero fills first, so runs overwrite where they overlap). **`; data:` spans are zeroed at boot** (free RAM is proven free but not zero); empty space between blobs costs nothing on disk. [obs] empty set: 392 B of records; blobs at `$BD400`, `$CD000`, `$D0000` plus data at `$BD000` and `$E0000` (flat image `$B8000..$E0FFF`): 456 B; `build --floppy` free space stays 55296 B. `live` still writes the flat `.img`/`.json`.
* **hook2** (`patches/core.s`, called with the exact registers/SR of the original `rts`): preset `MARKER = 'PMPF'` (a refused stage keeps it), pass 1 compares the ORIGINAL bytes of every stage 2 site, pass 2 writes them, `MARKER = 'PMPO'`, `jmp $10a6`. hook1 is the same for stage 1 (marker `'PMP1'` = stage 1 applied, stage 2 pending; a stage 1 refusal makes hook2 apply nothing).
* **Site table** `$B8200..$B878F` (1424 B): `{addr.l len.w stage-1.w orig[len] new[len]}`, `addr = 0` ends (8+2*len per site; about 70 six-byte hooks). Overflow is a build error. `UINITTBL $B8790`, `INITTBL $B87C0` (11 routines each), `FLAGS $B87F0`, `MARKER $B87F8`.
* **STE probe** (`init`, `FLAGS`): temporarily points the bus error vector at a handler, reads `$ff8901`, and checks that `$ff8905` reads back what is written. bit0 = STE-class DMA sound, bit1 = probe ran, bit2 = bus error seen. [obs] STE: `3`, ST: `6`.
* **Blob ranges** (`pmpatch.py PREFIX_RANGES`, shared contract): `tick_`/`p3b_` `$B8800-$BAFFF`, `test_` `$CE000-$CFFFF`, `hd_` `$BB000-$BCFFF`, `p4_` `$BD000-$CDFFF`, `snd_` `$D0000-$DCFFF` (no sample bank). `$DD000-$EFFFF` is reserved for the HD build's TOS swap buffer (every build refuses payload there; the buffer may spill to `$F5FFF`, section 7.1). In the HD build `$BD000-$DCFFF` (the "overlay window") is overwritten by stage 1's SPRITE40.DAT load and restored from `PMLATE.DAT` in the same call, including `; data:` zero-fills (section 7.1), so patches in the window need nothing special. Blob segments and `; data:` reservations outside the range of their prefix are build errors; overlaps too. Patch headers: `; name:` `; default: no` `; stage: 1|2` (default 2) `; site: $addr` `; orig: hex` `; data: $addr len` `; init: $addr` `; uinit: $addr`.
* `build` verifies first (`verify`: derived origs vs the patch's declared `; orig:`, resident images vs the RAM dumps). `build/<kind>.json` lists the sites and used spans. `live` writes `<prefix>.img` (at `$B8000`, FLAGS 3 or 6, MARKER 'PMPO') and `<prefix>.json` (`img_base`, `sites`) for `capture_frames(live=)`; stage 2 patches only.

## 4. The floppy build
`pmpatch.py build --floppy` -> `build/floppy/powermonger.st`: `protected.st` with `AUTO\WAR.PRG` replaced (its FAT chain extended into free clusters: 281 clusters instead of 280 for the empty payload) and `DATA\SPRITE40.DAT` patched in place (30 bytes differ). Nothing else on the disk changes, so the protection and the loader behave as before. The disk has **55296 B free after the empty payload**; since the payload is stored sparsely, that limit applies to the packed records (code, tables, sample data), not to the address ranges. `DATA\SPRITE40.DAT` cannot be dropped (it is the game).

## 5. Free RAM (pattern method, hunter loading.md section 5)
`pmpatch.py boot --fill build/<kind>.json --scenario`: at the stage 1 hand-over (Hatari breakpoint `pc = $576 && ($576).w = $4eb9`, `loadbin`) every byte of `$B8800..$EFFFF` that the payload does not use gets `fill_byte(a)` (non-zero, position dependent). Then the full cold boot (intro, name, options, chart, protection answer, map view), `get_men`, wait for the battle (iteration 340), and after each stage all 227328 bytes are compared:

| build / machine | pattern bytes in `$B8800..$EFFFF` | changed after map view / get_men (17 moving) / battle (iteration 353) | `$F0000..$F7FC7` non-zero |
|---|---|---|---|
| floppy, STE TOS 1.62, 1 MB | 227328 | **0 / 0 / 0** | 5 bytes (TOS stack) |
| floppy, STE TOS 1.62, 4 MB | 227328 | **0 / 0 / 0** | 0 |
| HD folder, STE TOS 1.62, 1 MB | 222632 (payload data `$BB000..$BCFFF` excluded) | **0 / 0 / 0** | 37 bytes at `$F7F46..` (stack of the GEMDOS emulation) |

[obs] (first two rows were run with the first core revision, which differs from the final only in the size of `hook1/hook2/apply` inside `$B8000..$B87FF`; the third with the final one.) So **`$B8800..$EFFFF` (227328 B) is free through boot, loading, menus, map, get men and battle at 1 MB and 4 MB; `$F0000..$F7FFF` is not.** Plain ST 1 MB was not poisoned (same layout [INFERENCE])."


## 6. Cold boots (empty patch set = the build with no patch, only the carrier + hooks)
| build | machine | TOS | RAM | result [obs, `pmpatch.py boot`] |
|---|---|---|---|---|
| floppy | STE | 1.62 | 1 MB | map view (in_game True), `MARKER='PMPO'`, `FLAGS=3` |
| floppy | ST | 1.04 | 1 MB | map view, `PMPO`, `FLAGS=6` (probe ran, bus error, no DMA sound) |
| HD folder (Hatari `--harddrive`) | STE | 1.62 | 1 MB | map view, `PMPO`, `FLAGS=3`, `HDBASE`="C:\\" |
| HD folder | ST | 1.04 | 1 MB | map view, `PMPO`, `FLAGS=6` |
| floppy | STE | 1.62 | 4 MB | map view (in_game True), `PMPO`, `FLAGS=3` (final build; also the first-core fill run) |
| HD folder | STE | 1.62 | 4 MB | NOT run |

**Wrong original byte** (`build --only test_poke1 test_poke2 --corrupt`: first optional site's orig byte flipped in the payload; test patches change 4 harmless bytes at `$56ff0` (stage 1 padding) and `$1bb2c` (save-disk text), `patches/test_poke*.s`):
* floppy, stage 1 site corrupted: `MARKER='PMPF'`, map view reached (in_game True), `$1bb2c = 20285745` (" (WE", the stage 2 site was NOT written either).
* floppy, `--only test_poke2 --corrupt` (stage 2 site): `PMPF`, map view, `$1bb2c = 20285745`.
* HD folder, same stage 2 corruption: `PMPF`, map view, `$1bb2c = 20285745`: the mandatory `hd_*` sites are their own group, applied first, so the game still loads from the folder.
**Positive**: floppy `--only test_poke1 test_poke2`: `PMPO`, `$1bb2c = 504d5032` ("PMP2"). The stage 1 half (`$56ff0` at pc `$1360`) was not captured (the `--peek1` log parser read the wrong log lines in that run; fixed afterwards, not re-run). The stage 1 hook itself is exercised in every HD boot (the `hd_s1` site must be applied or SPRITE40.DAT is never loaded) and in the floppy "stage 1 corrupted" run (it refused).


## 7. The HD build
`pmpatch.py build --hd` -> `build/hd/`: `AUTO\WAR.PRG` (the same carrier; `hook1` installed), `DATA\*.DAT` (15 files extracted from the disk image, SPRITE40.DAT patched), `SAVEDISK.DAT` (409600 B = the save game disk image with the game's own sector 0), plus the `hd_*` patches (`patches/hd_*.s`) that replace the floppy code by GEMDOS calls:

| patch | site | what |
|---|---|---|
| `hd_s1` | stage 1 `$1356` `jsr $57032` | `jsr hd_load` (loads DATA\SPRITE40.DAT) |
| `hd_load` | stage 2 `$d574` (6 B) | `jmp hd_load`: by-name loader -> Fopen / Fseek(0,2) / Fseek(0,0) / Fread(size) / Fclose; `d0 = 0` and Z on success |
| `hd_sector` | stage 2 `$d9fc` (6 B) | `jmp hd_sector`: the sector driver (used only by the save-game code once `$d574` is replaced) -> `SAVEDISK.DAT`, byte offset = sector * 512; format = no-op (the game rewrites sector 0 with the slot flags) |
| `hd_core` | blob `$BB000..` + data `$BC000..$BCFFF` | `uinit` (USER mode, before Super: Dgetdrv + Dgetpath -> `HDBASE` = "C:\" or "C:\dir\", so the folder the program was started from is the data folder), `init` (supervisor: copy of TOS's low-RAM region R to the swap buffer S), `tos_in`/`tos_out` (exchange R and S, MFP / SR / stack switch, keyboard FIFO), `hd_load`, `hd_sector` (section 7.1) |
| `hd_kbd` | stage 2 `$18e4` (10 B, unchanged) | verification-only site: the game's keyboard byte processor that `hd_core` feeds the bytes queued during a call to |

* Names are upper-cased (the game passes `data\sprite40.dat` in stage 1) and prefixed with `HDBASE`. A missing file makes `$d4d2` show the "insert the Powermonger disk" prompt and retry forever (as the original with a missing file).
* `SAVEDISK.DAT`: reads of a missing disk fail (the game then says "PLEASE INSERT SAVE GAME DISK"); a write creates it (Fcreate) and seeks (sparse); the shipped file is a formatted disk so Load/Save work at once. [obs] `build --hd --only test_hdsav` + `boot --hd ... --call $ce000` (the routine is run from the main loop through the debugger, so it executes after the game has trashed TOS's RAM): `{'write': 0, 'read': 0, 'compare': 0, 'sector0': 0, 'format': 0}` and the host copy of `SAVEDISK.DAT` is still 409600 B, sector 0 = "POWE..", sectors 5-6 = the pattern. The game's own Load/Save menu is driven by `pmpatch.py boot --saveload` (7.1).
* **Works on a real driver now (ACSI + HDDRIVER, `boot --hd build/hd --acsi`), and on Hatari's GEMDOS emulation, with the same code**: section 7.1. Not run on real hardware.

### 7.1 Real hard-disk driver (ACSI + HDDRIVER): the TOS-region swap (PMRealHD)
**Why it failed before** [obs]: at `uinit` (`pc = $b8008`, `--acsi`, TOS 1.62 STE 1 MB) `_membot = $a892`, `_memtop = $f8000`, `_sysbase = $940` (OS header in RAM, `p_run` field `$28(_sysbase)` -> variable `$5662` -> BP), BP = `$1323a` (`hitpa $f8000`, text `$1333a`, parent PD `$13136`, env `$13236`), `hdv_rw = $ea7c` (HDDRIVER code in `$a800..$12400`). Non-zero RAM per 4 KB page: `$0..$6fff` (OS variables, GEMDOS pool, `p_run`), `$7000..$9fff` zeros (TOS bss, unused pool slots: still TOS's), `$a000..$12fff` the driver, `$13000..` the program. Everything TOS and the driver own is in R = `[$8, (BP+$100) & -4)` and all of it is overwritten by the game; the first real `trap #1` (stage 1's `hd_load`) therefore crashed (Address Error at `$69`, `PC=$e09598`: TOS's bomb handler on trashed state). **Mega STE 4 MB, TOS 2.06**: `_membot = $ccb2`, BP = `$155da`, `hdv_rw = $10e9c`, `p_run` variable `$5cd4`. So R is **78640 B (`$8..$13337`) on STE/1.62 and 87760 B (`$8..$156d7`) on Mega STE/2.06**: it differs per machine and it does NOT fit `$DD000..$EFFFF` (77824 B). `init` reads BP at run time and sizes R; the swap buffer S starts at `$DD000` and may extend to `$F5FFF` (`SMAX = $19000`; `READY` stays 0 and every load fails if R is bigger). `$F0000..$F7F45` is never written by the game or TOS ([obs] section 5 for the floppy; HD with `--fill`: Mega STE 2.06 `$f0000..$f7fc7` has 0 non-zero bytes outside S, STE 1.62 has 63 at `$F7F21..` = TOS's stack as before). `pmpatch.py`: `HD_SWAP_BASE/HD_SWAP_END`; every build refuses payload in `$DD000..$EFFFF`; `snd_` is limited to `$D0000..$DCFFF`; `hd_equs()` checks `hd_core.s` equates against them.

**Mechanism** (`patches/hd_core.s`, all of it in USER/supervisor code of our blob at `$BB000`, variables and a 3.5 KB private stack in `$BC000..$BCFFF`):
1. `init` (supervisor, before WAR.PRG ran an instruction of its own) copies R to S. `hd_load` / `hd_sector` run with SR `$2700`, then `tos_in`: EXCHANGE R and S long by long (S then holds the game's bytes; ~0.1 s at 8 MHz for 78 KB, [INFERENCE] not timed), SR `$2500` (MFP only), IMRA = 0, IMRB = timer C (+ keyboard ACIA, below), `IPRB`/`ISRB` bits of timer C cleared (the game's `rte` stubs never clear `ISRB`), private stack, TOS's vectors (they are in R); the GEMDOS calls; `tos_out`: exchange back, MFP and SR restored. TOS's world persists across calls (S keeps its latest state, so `_hz_200`, the driver's state and the GEMDOS pool stay consistent; its clock only runs while a call runs).
2. [obs] MFP at the calls: stage 1 `IERA=$1e IERB=$64 IMRA=$1e IMRB=$64 TCDCR=$57`, map view `IERA=$3e IERB=$64 IMRA=$3e IMRB=$64 VR=$40 TCDCR=$51`: timer C is already /64 (TOS's 200 Hz), so the code only reprograms it (TCDR = 192) if it is not; that branch is not exercised.
3. **Keyboard bytes** [obs, the bug this took the longest to find]: with the ACIA masked during a call (and during the 0.1 s exchanges), the one-byte ACIA overruns, bytes of the IKBD's 6-byte absolute-mouse packets (`$f7`, buttons, x, y: state machine `$18e8`, state in `$1c48e`) are lost, the next packets are mis-assembled, `$2df92/$2df94` get a wild position and the pointer draw (`$147e`/`$14a8`, `move.w (a4),(a6)+`, `a4 = $9d3ed8`) takes a bus error: the game died right after pressing SAVE (3 runs, Hatari `Bus Error reading at address $9d3ed8, PC=$147e`; `$1c492` changed `$ab -> $f7` = a packet header stored as x; a breakpoint at `hd_sector`'s return showed the game's own `$18be` running immediately after the restore). Fix: vector `$118` is `hd_acia` in BOTH worlds during the exchange (the game's slot in R and TOS's slot in S are patched before the exchange and restored after), the ACIA is the only interrupt open while R is being exchanged, `hd_acia`/`drain` queue every byte in a 128 B FIFO, and after `tos_out` `replay` feeds them, in order, to the game's own processor `$18e8` (`d0` = byte; the site `hd_kbd.s` verifies the bytes at `$18e4` in the mandatory group). Stage 1's single call (the overlay case) drops them: the intro has no mouse.
4. **Stage 1's SPRITE40.DAT** (`$13ba`, 101608 B, inside R) is read into the overlay window `OVL = $BD000..$DCFFF` while TOS's world is in, copied to `$13ba` by a plain copy after `tos_out`, and then **every payload byte that lives in the window is read back from `PMLATE.DAT`** (next to `DATA\`, written by `build --hd`; records `{dest.l, len.l [bit 31 = zero fill], bytes}`, `{0,0}` ends; read record by record straight to the destination, no staging buffer). The window holds blobs and zero-initialised `; data:` spans (`p4_spr`: 62464 B of sprite cache at `$BDC00`, `snd_`: `$D1000` 16 KB, ...): `front` has delivered them before stage 1, the overlay destroys them, the same call restores them, so the p4_/snd_ code and caches are intact before stage 2 exists and before any hook runs; interrupts stay masked during the whole call. **Deviation from the lead's spec**: the file is read when stage 1 asks, not preloaded in `uinit`, because a `uinit` preload would destroy the p4_/snd_/test_ blobs `front` has just copied before their own `uinit`/`init` routines and the whole of stage 1 could use them. Build assertions (`late_records()`): the records are applied to a window full of `$EE` and compared with the payload byte for byte (used spans, zero spans), a span that is only partly a zero-fill span is refused, SPRITE40.DAT must fit the window, `PMLATE.DAT` is regenerated by every `build --hd`; a refused `PMLATE.DAT` read fails the load. [obs] with the default set: PMLATE.DAT 2190 B, records `$bd000 210 / $bd100 202 / $bd200 zero 288 / $bd500 342 / $bd700 580 / $bdc00 zero 62464 / $d0000 776 / $d0e00 zero 64 / $d1000 zero 16384`.


**Results** [obs, `pmpatch.py boot ...`, default patch set (snd_, tick_, p4_ptr/spr, hd_*), HDDRIVER V10.15 from `gamebench/hd`]:
| gate | result |
|---|---|
| `boot --hd build/hd --acsi`, STE 1 MB TOS 1.62 | map view, `in_game=True`, `MARKER='PMPO'`, `FLAGS=0x3` (5 runs) |
| `boot --hd build/hd --acsi --machine megaste --tos 2.06 --mem 4096` | map view, `PMPO`, `READY='HDSW'`, R = `[$8,$156d8)` = 87760 B, S `$dd000..$f26cf` |
| `--saveload` (both machines, several runs) | game's own menu (Option symbol -> FILE -> SAVE (the "THIS SAVE GAME ALREADY EXISTS OVERWRITE?" requester is answered OK) / LOAD, slot A): state `$3f768`, `$c6` sectors, captured by the debugger at `hd_sector`'s entry (write) and at the load call's return `$1bdd8`: **saved vs loaded 0 bytes differ**, saved vs the state 5 s later 208..586 differ (so the load restored something), `SAVEDISK.DAT` slot A in the ACSI image (`mcopy ...@@1024`) == the saved bytes, sector 0 flag `$ff`, the game keeps iterating. Not done: quitting and loading the file in a fresh boot. |
| `--fill build/hd.json --scenario` (map view, get_men with 13-16 people moving, battle iteration 358/370), STE 1.62 and Mega STE 2.06 4 MB | **0 changed** of 62388 pattern bytes in `$b8800..$effff` after each stage (S and the late-restored spans are `used`); the pattern is loaded at the stage 2 hand-over for HD (stage 1's overlay legitimately writes the file into the free gaps of the window; stage 1 itself is proven by the floppy run) |
| Hatari GEMDOS emulation (`boot --hd build/hd`, no `--acsi`), STE 1.62 | map view `PMPO`; `--saveload`: identical result (0 differ, host `C/SAVEDISK.DAT` slot A == saved). The exchange runs there too (harmless). Plain ST / TOS 1.04 with the new core: NOT re-run. |
| floppy build (`build --floppy`, same default set), STE 1.62 | map view `PMPO`, get_men, battle; screenshot with `p4_spr` matches the HD one (houses, people, trees drawn the same way; positions differ because the land is seeded per run) |
**Swap spill proof ($F0000..$F5FFF)** [obs, `boot --hd build/hd --acsi --saveload --fill build/hd.json --scenario`]: `$F0000-$F5FFF` is NOT part of the section 5 proof, so the HD run proves it itself. After `init` has run the harness reads `RLEN`, and at the stage 2 hand-over loads the position-dependent pattern into every free byte of `$B8800..$EFFFF` AND into `[S end, $F6000)`; it then compares after boot, a save and a load through the menu, the map view, get_men and the battle. Mega STE 4 MB / TOS 2.06 (R 87760 B, S `$dd000..$f26cf`, 76866 pattern bytes, incl. `$f26d0..$f5fff`): **0 changed** at the map view, get_men (15 moving) and battle (iteration 563), 0 non-zero bytes elsewhere in `$f0000..$f7fc7`. STE 1 MB / TOS 1.62 (R 78640 B, S `$dd000..$f032f`, 85986 pattern bytes): **0 changed** at the map view, get_men (14 moving) and battle (iteration 476), 63 non-zero bytes at `$f7f21..` (TOS stack, above the proven span, unchanged from section 5). The swap buffer's own contents are proven by function (every load, save and the stage 1 overlay go through it). The cap is `SMAX = $19000` (`S` ends at most at `$F6000`, exactly the span proven). **Refusal**: if the basepage cannot be found or R > `SMAX`, `init` leaves `READY = 0`, prints a message through GEMDOS `Cconws` (TOS is still intact: 4 lines, 40 columns, "Press a key", then `Cconin`) and every `hd_load` / `hd_sector` fails; [obs] a build with `SMAX = $10000` (R does not fit; `pmpatch.py` patched in a throwaway copy) on STE/1.62: HDDRIVER's screen followed by the message, `READY = 0`, after the key the game stays on a black screen in stage 1 (`MARKER = 'PMP1'`), no crash loop. The 40-column wording was fixed after the first run showed the first draft wrapped; the final text was assembled but not re-shown on screen.
Limits: not run on real hardware; the ST-class machines (TOS 1.04), TT/Falcon, and a 4 MB STE with TOS 1.62 were not run with this core; a TOS/driver combination with R above `SMAX` is refused as above, not supported; times per call were not measured.

## 8. Gotchas
* **Keyboard deadlock when a key arrives right after the game starts** [obs, `--trace acia`]: the game resets the ACIA at pc `$10e6` (a few frames after the `$10a6` hand-over) and only later enables the keyboard interrupt; the MFP reacts to the falling edge of the ACIA IRQ line only, so a key byte received in between leaves the IRQ asserted for good and the game never sees a key (`$fffc00 = $83`, `$18be` never runs). The harness presses `space` every 4 s during the intro; with the slow floppy loads that never collided, with the fast HD loads it did every time (name prompt without text). `pmpatch.py make_pm` therefore suppresses `key('space')` once `$10a6` holds `$41f9`. Not a patch problem (a real user who types in that window on the original game has the same risk).
* The nested PRG at `$576` reuses its intro code regions as buffers: only the stage 1 hand-over image is a valid reference for stage 1 sites, never an idle dump.
* `pc = $576` / `pc = $10a6` are also executed once earlier by the decoder (its own code is there). The first Hatari breakpoint hit is the decoder entry; test the first word (`($576).w = $4eb9`, `($10a6).w = $41f9`) to catch the hand-over.
* Hatari `--trace fdc --trace-file` is block-buffered and very slow (60 s wall for 28 s emulated): use it only for the FAT/boot phase.
* The fake basepage at `$53a` and the 12 bytes at `$500..$513` are the stub's; the game keeps them, patches must not use `$500..$575`.
* The floppy image's second FAT differs from the first (FAT2 untouched by the build, as in the original; the game reads only FAT1).
* `mtools` need `MTOOLS_SKIP_CHECK=1` (README.md): `mdir -/ -i build/floppy/powermonger.st ::` lists the patched disk.

## 9. 68020/030 caches (TT, Falcon) and the Falcon YM mirror (PMPack, 2026-11-10)
Tags: **[obs]** Hatari 2.6.1 (TT TOS 3.06, Falcon TOS 4.04, 4 MB, `tools/pmdiag.py`, `--trace cpu_exception`); **[INFERENCE]** not run.
* **The original does not run on TT/Falcon.** [obs] TOS 3.06 sets CACR = `$3111` (instruction + data cache on). The two in-place depackers `rts` into addresses the decoder has just overwritten with data writes (stage 0 -> stage 1 at `$576`, stage 1 -> stage 2 at `$10A6`), so the instruction cache executes stale decoder lines: Line-F exception (vector `$2c`) at pc `$672`, TOS resets, and its start-up logo loop (`vsync`, `$e00d7a`) hangs forever because the game left the VBL vector `$70` at its `rte` stub (`$466` frozen). Black screen, pc = `$e00d8c`. The same Line-F at `$672` on the Falcon (then a TOS bomb and the "double bus error" dialog). Proof: breakpoint `pc = $508` (the stage-0 stub) + `r cacr=$0` lets the unpatched original run into stage 2 on a TT, and our patched floppy cold-boots to the map view.
* **Fix (`core.s` `cacroff`, called by `init`, supervisor, before the game's first instruction).** On a 68020+ (found by executing `movec cacr,d0` under temporary illegal / line-F handlers; `cpusha bc` separates 040/060 from 020/030) every cache is switched off: 020/030 CACR = `$0808` (clear I and D, EI = ED = 0), 040/060 `cpusha bc` then CACR = 0. 68000/68010 are untouched. **The data cache stays off for the whole run** (decision as in Hunter: a 030 does not snoop the game's raw FDC DMA, and HD loads go through GEMDOS). The instruction cache stays off too by default; `ICMODE` (`$B87BC`, default 0) set to non-zero makes `hook2` switch it back on (`ICVAL` `$B87EC`: `$19` on a 020/030, `$8000` on a 040/060; 0 if TOS had it off) right before `jmp $10a6`: experiment only. The Falcon's FDC wait loops (`move.l #$40000/#$60000,d0 ; btst #5,$fa01.w`, stage 1 `$57644 $576ea $5793c`, stage 2 `$db86 $dc2c $de7e`) are CPU-speed dependent as in Hunter's ttfalcon.md, but with the caches off the floppy boots on TT and Falcon in Hatari without touching them.
* **Falcon: YM mirror writes.** [obs] The title/intro sound interrupt (stage 1, `$b5ee..$b624`) writes `movep.l d6,0(a1)` = `$ff8800/02/04/06`; Hatari's Falcon bus-errors on `$ff8804` ("Bus Error writing at address $ffff8804, PC=$b60c"). `patches/fal_ym.s` (stage 1, `$b60c`, 8 B -> `jsr $dc000.l`, `; falcon: yes`) does the same register writes through `$ff8800/$ff8802` (two `movep.w`). It is applied **only on a Falcon**: `init` reads the `_MCH` cookie (high word 3) into `FALCON` (`$B87BD`), `hook1` applies the class-4 sites only then (`core.s`, `pmpatch.py` `; falcon: yes`; to make room HOOK1 = `$B8140`, HOOK2 = `$B8190`, APPLY = `$B81F0`, TABLE = `$B8250`, `ICMODE` is now the byte `$B87BF`). A first version applied it on every machine: WAV A/B of the intro music (ST 1.04) gave rho 0.95 and a different spectrum (centroid 4137 vs 3436 Hz), so it was gated; the stage 2 sample IRQ `$1af58` has the same `movep.l` but is never reached when DMA sound is present (the timer-A set-up IRQ ends at the zero byte before it).
* **I-cache back on: failed.** With `ICMODE` = 1 (instruction cache re-enabled by `hook2`) the TT never reaches the name prompt (`name prompt not reached`, cold boot, TT 3.06, 4 MB). The cache therefore stays off (default), and the cause was not investigated.
* **fal_ym A/B (ST and STE, intro music, `tools/pmym.py`):** whole cold boot recorded from the first instruction, 82 s, no keys. `build/rc2` (fal_ym present but not applied: not a Falcon) against `build/nofal2` (same set without fal_ym, plus a harmless stage-1 poke so hook1 runs in both): ST 1.04 onset 53.642 vs 53.503 s, rho +0.959 at +0.3 ms lag, 200 ms windows mean 0.951, spectral centroid 3438 vs 3437 Hz; STE 1.62 onset 53.421 vs 53.407 s, rho +0.930 at -14 ms, centroid 3995 vs 3981 Hz. The residual (rho 0.93-0.96) is run-to-run load timing between two differently sized WAR.PRG files (also seen between two unrelated builds), not content: the intro code is byte-identical when fal_ym is not applied.
