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
 text    original (286352 B)                    data         front (58 B, pos.-independent) + payload image
 data    front + payload image                  front: copy image -> $B8000; uinit (USER mode); Super(0) (original insn);
 reloc   $00000002 $00                                 init (supervisor); jump to text+8 = the rest of the original program
SPRITE40.DAT (stage 2, same size): the 32-byte stack routine ends in `jmp hook2` instead of `rts`   (file $124..$153)
WAR.PRG stack routine (text $1e4): `jmp hook1` ONLY if a patch has `; stage: 1` (the HD build)
```
* **Carrier = the appended data segment of WAR.PRG** (as Midwinter did): TOS loads text+data with its own file API, the disk layout of every other file is unchanged, and the same WAR.PRG works from a floppy and from a GEMDOS folder. The depacker output reaches beyond the carrier's text end, so `front` moves the payload to `$B8000` before anything runs.
* **Why the payload cannot sit in WAR.PRG's text**: there is no slack; and the stub overwrites everything from `$514` to `$58010` with the game.
* **hook2** (`patches/core.s`, called with the exact registers/SR of the original `rts`): preset `MARKER = 'PMPF'` (a refused stage keeps it), pass 1 compares the ORIGINAL bytes of every stage 2 site, pass 2 writes them, `MARKER = 'PMPO'`, `jmp $10a6`. hook1 is the same for stage 1 (marker `'PMP1'` = stage 1 applied, stage 2 pending; a stage 1 refusal makes hook2 apply nothing).
* **Site table** `$B8200..$B878F` (1424 B): `{addr.l len.w stage-1.w orig[len] new[len]}`, `addr = 0` ends (8+2*len per site; about 70 six-byte hooks). Overflow is a build error. `UINITTBL $B8790`, `INITTBL $B87C0` (11 routines each), `FLAGS $B87F0`, `MARKER $B87F8`.
* **STE probe** (`init`, `FLAGS`): temporarily points the bus error vector at a handler, reads `$ff8901`, and checks that `$ff8905` reads back what is written. bit0 = STE-class DMA sound, bit1 = probe ran, bit2 = bus error seen. [obs] STE: `3`, ST: `6`.
* **Blob ranges** (`pmpatch.py PREFIX_RANGES`, shared contract): `tick_`/`p3b_` `$B8800-$BAFFF`, `test_` `$BAC00-$BAFFF`, `hd_` `$BB000-$BCFFF`, `p4_` `$BD000-$CFFFF`, `snd_` / sample bank `$D0000-$EFFFF`. Blob segments and `; data:` reservations outside the range of their prefix are build errors; overlaps too. Patch headers: `; name:` `; default: no` `; stage: 1|2` (default 2) `; site: $addr` `; orig: hex` `; data: $addr len` `; init: $addr` `; uinit: $addr`.
* `build` verifies first (`verify`: derived origs vs the patch's declared `; orig:`, resident images vs the RAM dumps). `build/<kind>.json` lists the sites and used spans. `live` writes `<prefix>.img` (at `$B8000`, FLAGS 3 or 6, MARKER 'PMPO') and `<prefix>.json` (`img_base`, `sites`) for `capture_frames(live=)`; stage 2 patches only.

## 4. The floppy build
`pmpatch.py build --floppy` -> `build/floppy/powermonger.st`: `protected.st` with `AUTO\WAR.PRG` replaced (its FAT chain extended into free clusters: 282 clusters instead of 280 for the empty payload) and `DATA\SPRITE40.DAT` patched in place (30 bytes differ). Nothing else on the disk changes, so the protection (the manual question) and the loader behave as before. Free space on the disk: **54272 B after the empty payload, so the floppy payload is limited to about 53 KB** (core 2 KB + patches; no sample bank). Options if that is not enough, user decision: (a) the disk has 80 tracks; the game's FAT reader takes sectors per track and root entries from the BPB, extra tracks would need the BPB changed [INFERENCE]; (b) `DATA\SPRITE40.DAT` cannot be dropped (it is the game).

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
| `hd_core` | blob `$BB000..` + data `$BC000..$BCFFF` | `uinit` (USER mode, before Super: Dgetdrv + Dgetpath -> `HDBASE` = "C:\" or "C:\dir\", so the folder the program was started from is the data folder), `init` (supervisor: snapshot of TOS's vector table `$8..$3ff`), `tos_in`/`tos_out` (SR `$2700`, private stack, TOS vectors installed / game's restored), `hd_load`, `hd_sector` |

* Names are upper-cased (the game passes `data\sprite40.dat` in stage 1) and prefixed with `HDBASE`. A missing file makes `$d4d2` show the "insert the Powermonger disk" prompt and retry forever (as the original with a missing file).
* `SAVEDISK.DAT`: reads of a missing disk fail (the game then says "PLEASE INSERT SAVE GAME DISK"); a write creates it (Fcreate) and seeks (sparse); the shipped file is a formatted disk so Load/Save work at once. [obs] `build --hd --only test_hdsav` + `boot --hd ... --call $ce000` (the routine is run from the main loop through the debugger, so it executes after the game has trashed TOS's RAM): `{'write': 0, 'read': 0, 'compare': 0, 'sector0': 0, 'format': 0}` and the host copy of `SAVEDISK.DAT` is still 409600 B, sector 0 = "POWE..", sectors 5-6 = the pattern. The game's own Load/Save menu was not driven through the UI.
* **Limits [INFERENCE, not tested on real hardware]**: the game overwrites the whole TPA and the low RAM TOS keeps its state in (on TOS 1.62 the GEMDOS current-basepage variable is at `$5662`, inside the first file's destination: [obs] Hatari prints "program ... accessing another program" for it). Hatari's GEMDOS emulation only reads the stacked arguments, so it works; real TOS GEMDOS + a resident ACSI/IDE driver would need TOS's low RAM state swapped as well (the vectors are, nothing else is). The HD build is therefore specified for Hatari `--harddrive` (GEMDOS emulation). **ACSI + HDDRIVER** (`boot --hd build/hd --acsi`, TOS 1.62 + `gamebench/hd` driver via `hunter.build_hd`): started, but it had not reached the name prompt after more than 5 minutes when this was written; no result. [INFERENCE] it fails for the reason given above (the game overwrites TOS's low RAM and the driver). Not supported/verified.

## 8. Gotchas
* **Keyboard deadlock when a key arrives right after the game starts** [obs, `--trace acia`]: the game resets the ACIA at pc `$10e6` (a few frames after the `$10a6` hand-over) and only later enables the keyboard interrupt; the MFP reacts to the falling edge of the ACIA IRQ line only, so a key byte received in between leaves the IRQ asserted for good and the game never sees a key (`$fffc00 = $83`, `$18be` never runs). The harness presses `space` every 4 s during the intro; with the slow floppy loads that never collided, with the fast HD loads it did every time (name prompt without text). `pmpatch.py make_pm` therefore suppresses `key('space')` once `$10a6` holds `$41f9`. Not a patch problem (a real user who types in that window on the original game has the same risk).
* The nested PRG at `$576` reuses its intro code regions as buffers: only the stage 1 hand-over image is a valid reference for stage 1 sites, never an idle dump.
* `pc = $576` / `pc = $10a6` are also executed once earlier by the decoder (its own code is there). The first Hatari breakpoint hit is the decoder entry; test the first word (`($576).w = $4eb9`, `($10a6).w = $41f9`) to catch the hand-over.
* Hatari `--trace fdc --trace-file` is block-buffered and very slow (60 s wall for 28 s emulated): use it only for the FAT/boot phase.
* The fake basepage at `$53a` and the 12 bytes at `$500..$513` are the stub's; the game keeps them, patches must not use `$500..$575`.
* The floppy image's second FAT differs from the first (FAT2 untouched by the build, as in the original; the game reads only FAT1).
* `mtools` need `MTOOLS_SKIP_CHECK=1` (README.md): `mdir -/ -i build/floppy/powermonger.st ::` lists the patched disk.
