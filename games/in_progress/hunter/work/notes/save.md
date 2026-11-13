# Hunter: in-game Save and Load on the HD build (HunterSave)

Tags: **[obs]** observed in Hatari 2.6.1 / raw tool output; **[disasm]** read with `tools/m68dis.py` on the 1 MB STE RAM dumps; **[INFERENCE]** not verified.
Patches: `patches/sav_hook.s` (site `$d542`), `patches/sav_open.s` (site `$c0268`, D15R); gate tool: `tools/huntsave.py`.
Study: `reports/hunter_ideas.md` idea 10. Addresses are the HD build's own (fixed on every machine: `$800..$12003` and D15R at `$c0100`).

## 1. What was broken

PP disabled save/load in his Gamex HD build and says so in `README.TXT` ("Ingame save/load, floppy init works not. Use gamex instead").
The game side is intact: the resident game is byte-identical to the Paper Bag floppy's, whose saving works (floppy.md: a Save writes
existing slot files `10`..`15` and the directory `0F`).

The disk layer is entered through `jmp $d30e` from three places [disasm of `work/dumps/boot/ram_tail_1mb.bin`]:

```
010926: 7600            moveq #0,d3              ; read
010928: 4ef90000d30e    jmp   $d30e.l
010952: 76fe            moveq #$fe,d3            ; write
010954: 4ef90000d30e    jmp   $d30e.l
0103a4: 302d0104        move.w $104(a5),d0       ; slot number
0103a8: 06400010        addi.w #$10,d0           ; file number $10 + slot
0103ac: 600005a4        bra.w $10952             ; -> the write path
```

`$d30e` is the disk layer's entry, and PP replaced its head with `jmp $150.l` (`$d542`, PP's own RAM patch, see loading.md). His hook
never looks at `d3`, so a **write became a read of the same file**:

```
000150: 42b9000c0736    clr.l  $c0736.l          ; file offset 0
000156: 23fc00011170000c073a move.l #$11170,$c073a.l  ; at most 70,000 bytes
000160: 23c8000c073e    move.l a0,$c073e.l       ; destination = the game's buffer
000166: 06000030        addi.b #$30,d0           ; file number -> ASCII ('A'+d0-$10)
000172: e148            lsl.w  #8,d0
000174: 33c0000c0752    move.w d0,$c0752.l       ; name "X",0  (relative to \FILES)
000184: 41f9000c0100    lea.l  $c0100.l,a0       ; D15R
000192: 4e90            jsr    (a0)              ; $c0152: Fopen/Fseek/Fread/Fclose
0001a6: 4ef90000d60a    jmp    $d60a.l
```

Consequences on the HD build, all [obs]:
- **Save** wrote nothing and then read the slot file back over the game's buffer: the game reported a save, the player kept playing
  with RAM that had just been overwritten by whatever the file held.
- **Load** read `FILES\<letter>`: slot 1 is file `$11` = `FILES/Q`, ..., slot 6 = `FILES/V`. None exist, so the read failed and the
  slot buffer held stale/garbage data (the crack has nopped the game's own checksum test: `$103ce cmp.w d1,d2` is followed by two
  `4e71 nop`).
- **The directory.** The six slot names come from a 224-byte directory file, which the game reads at `$10018`/`$1000c` as file `$0f`:

```
01000c: 207900007f54    movea.l $7f54.l,a0        ; the directory buffer
010012: 700f            moveq   #$f,d0
010014: 6000093c        bra.w   $10952             ; write it
010018: 207900007f54    movea.l $7f54.l,a0
01001e: 50d0            st.b    (a0)               ; mark "failed" before the read
010020: 700f            moveq   #$f,d0
010022: 61000902        bsr.w   $10926             ; read it
```

  On the HD build that read hit `FILES/F` (50,152 bytes, `$21a94..$22df4`), PP's placeholder file. That is why the list showed the decoy
  names: they are in PP's data file `FILES/0` at file offset `$10ae2` ("HUNTER SAVES 1.1" + `Do not use*`, `this*`, `for*`, `game*`,
  `state*`, `saving*`), which starts at the game's directory buffer `$21a94` when `FILES/0` is loaded to `$10fb2` [obs].
- **Every Load/Save click also "writes" file 0** (`$10324 lea $10fb2(pc),a0 / moveq #0,d0 / jmp $10952`): on the HD build PP's hook
  turned that into a **read** of `FILES/0` over `$10fb2`, i.e. over the game's own variables (the slot buffer at `$23000` neighbours it).
  That is the "it reloads the data file" behaviour behind the broken state.
- **Init Disk** (`$ffcc`) builds a fresh directory in RAM, writes it (file `$0f`) and starts a new game. With a broken write it did
  nothing on disk.

## 2. What the floppy does (the model)

Paper Bag's loader has a write path: `$80.w = $ffff` selects the FDC write commands (`$d4f4 cmpi.w #$ffff,$80.w`) and it writes into
the **existing** clusters of the slot files; it never allocates, so the disk must already carry `10`..`15` (51,328 bytes each) and the
224-byte directory `0F`. The game's data files (`0C`..`0E`, and the packed `00`, `01`, ... ) are never rewritten.

The game's own format, from the two routines that fill/consume the slot buffer (`$7f6c` = `$23000`) [disasm]:

| slot file offset | bytes | source / destination in RAM |
|---|---:|---|
| `$0000` | `$3e8` | header block, built by `$1047c`/`$1050c` (checksum at `+$3e`) |
| `$0016` | `$10` | `$8266` |
| `$0040` | `$af` | `$8efe` (name, options, ...) |
| `$0240` | `$20` | `$8246` (the 32-byte palette/colour set) |
| `$0260` | `$c0` | `$8ce8` |
| `$0320` | `$176` | `$cde8` (log book, discovered targets) |
| `$03e8` | `$c000` | the world block, pointer at `$7fe4` |
| `$048c`.. | `$3c0` | `$9ab4` (written into `$496(a4)`, so at `$4be`..: `$496+$28`) |
| `$04a8`.. | `$10` | `$8266` again (`$496+$16` = `$4ac`) |

The checksum (`$10442`) is `d1 = $1b0 + sum of all 25,664 words` over the 51,328 bytes, with the word at `+$3e` replaced by `$b241`
before summing (that word holds the checksum itself). `tools/huntsave.py sum_ok()` recomputes it.

## 3. Durability: the write must reach the disk (and `sav_sync`)

A save is three GEMDOS operations: Fcreate/Fopen, Fwrite, Fclose. PP's loader does all three, `Fclose` included
(`$c02ca move.w d7,-(a7) / move.w #$3e,-(a7) / trap #1 / addq.l #4,a7` [disasm]), so no handle is left open. The file *data* is
written immediately, but the FAT chain and the directory entry live in GEMDOS's disk buffers, which GEMDOS writes back only when a
buffer has to be reused (EmuTOS `bdos/fsbuf.c`: `flush()` is called from `getbuf()` on eviction; nothing flushes on a timer). Measured
before the fix, killing Hatari (a power-off) after a save:

```
kill +1.0s run 1/3: fsck=ERRORS  dir=BAD/MISSING slot=51328B checksum=ok -> LOST
kill +1.0s run 2/3: ... -> LOST      kill +1.0s run 3/3: ... -> LOST
kill +20.0s run 1/3: fsck=ERRORS dir=BAD/MISSING slot=51328B checksum=ok -> LOST
kill +20.0s run 2/3: ... -> LOST
```

i.e. the slot's data and its own directory entry were on the disk, but `SAVES.DIR`'s was not - exactly the dirty-buffer case, and it
does not go away with time.

**`sav_sync`** (site `$c02d4`, 8 B, inside PP's loader right after the `Fclose`, still in the loader's TOS world - the vector table is
swapped back only at `$c02f8`): after a **write** (`$c0742` still holds `$5772` there) it calls GEMDOS `Dfree`, function `$36`, with both arguments on the stack in the documented order - `move.w drive,-(a7) / pea buf / move.w #$36,-(a7) / trap #1 / addq.l #8,a7`, drive 0 = the current one, `buf` a 16-byte result area (Populous 2's `pop2_save` uses the same call; EmuTOS `bdos/bdosmain.c` lists it as a 3-word call). `Dfree` reads the whole FAT
(`fsfat.c: xgetfree -> countfree16 -> getrec` per FAT record), which evicts every dirty buffer, so the directory and FAT sectors reach
the disk before the call returns. Reads skip it (nothing is dirty). One FAT scan per save.

After the fix, same test (cold boot, save, SIGKILL, then `fsck.fat` on the partition, mtools read of `SAVES.DIR` and of the slot,
and the game's checksum):

```
kill +1.0s  run 1..10/10: fsck=clean dir=ok slot=51328B checksum=ok -> OK      KILL +1.0s: 10/10 durable
kill +5.0s  run 1..10/10: fsck=clean dir=ok slot=51328B checksum=ok -> OK      KILL +5.0s: 10/10 durable
kill +20.0s run 1..10/10: fsck=clean dir=ok slot=51328B checksum=ok -> OK      KILL +20.0s: 10/10 durable
```

The 1 s and 20 s batches above were re-run with the final two-argument `Dfree` form (the run with the 5 s batch used the earlier
form, which passed the drive word in `d1`); the 5 s batch was not repeated after that change - all three delays are inside the same
mechanism, and 1 s is the hardest of them.

## 4. The patch

Both patches are `default: no`, `hdonly: yes` (`--floppy` skips them: the floppy has the cracker's loader at `$d30e` and keeps its own,
working, saving), and live in the `sav_` window `$8C72C-$8CDFF` (HunterTriple's v1.2 map). Position independent.

### `sav_hook` — site `$d542` (6 B: PP's `jmp $150.l`) -> `jmp $8C72C.l`

It handles exactly the six objects of the disk menu and passes everything else to PP's hook unchanged (`jmp $150.l`):

| call | what |
|---|---|
| `d0 = $0f`, read | `FILES\SAVES.DIR` (224 B). Missing, short or without the `HUNT` magic: the buffer gets a fresh directory - the same six `free*` entries that Init Disk writes (`$ffcc: move.l #$66726565,$10(a0) / move.b #$2a,$14(a0)`, free flag `$ff`). No file is created by a read. |
| `d0 = $0f`, write | `FILES\SAVES.DIR` |
| `d0 = $10..$15`, read | `FILES\SLOT<n>.SAV`: size must be exactly 51,328 and the game's checksum must match. Otherwise a dialog (`LOAD FAILED` / `FILE MISSING` / `FILE DAMAGED` / `READ ERROR`) and the load is abandoned. |
| `d0 = $10..$15`, write | `FILES\SLOT<n>.SAV` |
| `d0 = 0`, write (`d3 = $fffe`) | nothing (the `$1032a` "write file 0" that every Load/Save click does). PP turned it into a re-read of `FILES/0` over the variables; skipping it leaves the running game's state alone, which is what the floppy's Save does (it rewrites `00` from the same RAM image). |
| anything else | `jmp $150.l` (bytes for bytes PP's behaviour) |

The disk I/O itself is PP's loader called exactly as `$150` calls it: `$c0736` offset 0, `$c073a` length, `$c073e` destination,
`$c0752` the name, `$c0742 = $5772` for a write (the loader's write mode: `$c0202 cmpi.w #$5772,$c0742.l`, then
`$c02ae moveq #$3f,d0 / cmpi.w #$5772 / moveq #$40` picks Fwrite over Fread), `jsr $c0152`, `clr.w $c0734`, the `$1e02` magic PP writes,
and the result read from `$c0358`. `sr = $2700` around the call, as PP does.

**Missing files are created by `sav_open`.** The loader only opens (`$c0268 move.w #$3d,-(a7) / trap #1 / addq.l #8,a7` = Fopen), so a
fresh HD install could never save. `sav_open` replaces those 8 bytes with `jmp $8CB2C / nop` and runs

```
move.w #$3d,-(a7) / trap #1          ; Fopen as before
tst.l d0 / bpl .out
cmpi.w #$5772,$c0742.l / bne .out    ; only a write can create
cmp.l #-33,d0 / bne .out             ; EFILNF
clr.w 6(a7)                          ; attribute 0 instead of the Fopen mode word
move.w #$3c,(a7) / trap #1           ; Fcreate
.out: addq.l #8,a7 / jmp $c0270.l    ; the original `move.w d0,d7`
```

A read of a missing file is still an error (the game shows the file-missing dialog), an existing slot is opened without truncation
(so a failed write leaves the old save), and every other GEMDOS result is untouched.

### Failure handling

- **Failed slot write:** bit 3 of `$95(a5)` is set (the game's own disk-error bit: the Save code does `$100ca bsr.w $10338 / bne.w
  $10008`, and `$10348 bclr.b #3,$95(a5)`). The Save is abandoned before the directory write (`$100d2 bsr.w $1000c`), so the slot stays
  "free" and the old save is not marked. A dialog says why (DISK FULL / WRITE PROTECTED / ACCESS DENIED / NO FILES FOLDER / DISK ERROR).
- **Failed load:** dialog, then the load is abandoned. The hook pops the frame the game pushed at `$d53e` and returns; when the caller is
  the Load code (`$103be`, return address `$103c2`) it drops that return too, and when `$10338` was called from the Load menu handler
  (`$10058`, return `$1005c`) it replaces that return with a stub that returns `-1`, i.e. the same value the list's CANCEL gives
  (`$10008 moveq #$ff,d0`). The game stays in the 3D view with its RAM untouched.
- **Dialogs** use the game's own menu box (`jsr $1f6e`, record format `{header $00280000}{title 16}{0,0,0,0,9 words}{name 16}{4 zero}
  {handler.l}{$ffff}`), title + one button whose handler is `$8cda` (`moveq #0,d0 / rts`). No new strings are added to the game.

## 5. Gates (`tools/huntsave.py`)

| gate | machine | result |
|---|---|---|
| durability: save, SIGKILL at +1 s / +5 s / +20 s, 10 runs each | STE 1.62 1 MB | **10/10, 10/10, 10/10** |
| round trip (RAM diff + slot bytes on the disk) | STE 1.62 1 MB | **PASS** |
| round trip | Mega STE 2.06 4 MB | **PASS** |
| several slots + overwrite | STE 1.62 1 MB | **PASS** |
| missing / all-zero / short slot | STE 1.62 1 MB | **PASS** (message, state untouched) |
| read-only slot save | STE 1.62 1 MB | **PASS** (message, slot stays free) |
| valid slot loads | STE 1.62 1 MB | **PASS** |
| all-games image (`AtariST_enhanced_games_2026-11-12.img`, HUNTER\\ folder, ACSI + HDDRIVER) | -- | **PASS**: save into `HUNTER\\FILES`, cold boot the image again, load, all ranges equal |
| floppy build (Paper Bag disk, crack's own loader) | STE 1.62 1 MB | save + load: all restored ranges equal after the load, `13` = 51,328 B and `0F` = 224 B on the disk |
| round trip | TT 3.06 4 MB (`--mmu true --monitor vga --cpuclock 32`) | **PASS** (TT boot path of `hunt_ttf.py`: key at the HW screen, title crop gate, then the menu clicks) |
| durability: save, SIGKILL at +1 s, 5 runs | TT 3.06 4 MB | **5/5** (2 + 3) |
| full disk (image filled to 20 KB free, a valid slot 1 already saved) | STE 1.62 1 MB | **PASS**: message shown, `SAVES.DIR` byte-identical, `SLOT1.SAV` unchanged |
| `huntab --only sav_hook sav_open sav_sync --points 3 --flips 2 6 --lock` (post-fit tool) | snapshots `1mb_foot_stand`, `1mb_car_drive` | **IDENTICAL** |
| Init Disk, cold-boot persist | -- | see the notes at the end of this section |


### Round trip (STE 1.62, 1 MB, ACSI image + HDDRIVER, build with sav_hook + sav_open)

```
marker b'HNPO' site $d542 4ef90008c72c site $c0268 4ef90008cb2c
player at the save (40526, 10195) | moved to {'x': 40217, 'z': 10456} | after the load, 3D view running (40526, 10195)
  RAM save-time vs RAM after-load $08efe+175    equal
  RAM save-time vs RAM after-load $08246+32     equal
  RAM save-time vs RAM after-load $0cde8+374    equal
  RAM save-time vs RAM after-load $08ce8+192    equal
  RAM save-time vs RAM after-load $09ab4+960    equal
  RAM save-time vs RAM after-load $08266+16     equal
  RAM save-time vs RAM after-load $55514+49152  equal
slot file on the disk image: (51328, 'game checksum ok')
  save-time RAM: slot file +$16+10 vs RAM $8266: equal
  save-time RAM: slot file +$40+af vs RAM $8efe: equal
  save-time RAM: slot file +$240+20 vs RAM $8246: equal
  save-time RAM: slot file +$260+c0 vs RAM $8ce8: equal
  save-time RAM: slot file +$320+176 vs RAM $cde8: equal
  save-time RAM: slot file +$4ac+10 vs RAM $8266: equal
  save-time RAM: slot file +$4be+3c0 vs RAM $9ab4: equal
  save-time RAM: slot file +$87e+$c000 vs RAM $55514: equal
ROUNDTRIP PASS
```

Every range the game restores from a slot is bit-identical between the RAM at the save and the RAM after the load (the player had
walked 309 units away in between), the slot file on the disk holds those very bytes, and the game's checksum matches.

### Several slots and overwriting (STE 1.62, 1 MB)

```
positions at the saves: {'one': (40526, 10087), 'six': (40381, 10224), 'uno': (40173, 10224)}
SAVES.DIR: [(True, 'uno'), (False, 'free'), (False, 'free'), (False, 'free'), (False, 'free'), (True, 'six')] | fsck: (True, '... 32 files, 1022/16287 clusters')
SLOT1.SAV 51328 B checksum ok
SLOT6.SAV 51328 B checksum ok
load slot 6 -> (40381, 10224) (saved (40381, 10224) ) | load slot 1 -> (40173, 10224) (overwritten value (40173, 10224) , first value (40526, 10087) )
SLOTS PASS
```

Slot 1 was saved twice ("one", then "uno"); the directory shows the new name and the load returns the overwritten position, not the
first one. Screenshot `work/shots/save_load_list_two_saves.png`: the list reads `uno / free / free / free / free / six` - PP's decoy
names are gone.

### Load failures (STE 1.62, 1 MB, crafted slot files)

```
load slot 1 (missing): dialog shown, button clicked; back in the 3D view=0, position (40526, 9935) (before (40526, 9935))
load slot 2 (all zero (checksum)): dialog shown, button clicked; back in the 3D view=0, position (40526, 9935) (before (40526, 9935))
load slot 3 (short): dialog shown, button clicked; back in the 3D view=1, position (40526, 9935) (before (40526, 9935))
after three failed loads: still playing, state untouched: True
```

A missing slot, an all-zero slot (checksum mismatch) and a 1,000-byte slot each show the message and are refused; the game keeps
playing with its state untouched and never applies a partial buffer. Screenshots: `work/shots/save_dialog_load_*.png`.

After a failed load the game returns to the disk menu exactly as its own CANCEL does (`work/shots/save_load_slot4.png`: the
`LOAD A GAME` list is shown again over the menu; the third case leaves the 3D view bit set because the dialog is dismissed into the
menu redraw).

Save failure, read-only slot (STE 1.62, 1 MB; `huntsave.py errors --case ro`):

```
read-only slot: message shown; SAVES.DIR after the attempt: None
ERRORS PASS
```

The message is shown, and because bit 3 of `$95(a5)` aborts the Save before the directory write, the slot stays "free" on disk and the
old slot file is not touched.

Valid slot after crafting (`--case valid`): the crafted directory's slot 4 (a slot saved by the round-trip run, copied into the image)
loads - mission page with the saved name, then the 3D view, position (40526, 9935). `ERRORS PASS`.

**Open / not proven**

- **Init Disk** (`--case init`): the first "Are you sure" is answered Yes but the list stays `a..f`. Its handler shows a *second* box
  (`$ffd0: jsr $21d2`, the "Are you sure / Yes / No" record at `$21da`) before it builds and writes the directory, and the gate only
  answers the first; the case is therefore unproven, not shown broken.
- **Persistence across a shutdown**: the saved slot survived (51,328 B, checksum ok) but `SAVES.DIR` was left half-written in the image
  ("Fat problem while decoding" from mtools) in two of three runs, even after 50 s of idle. HDDRIVER flushes lazily and partially; the
  data is the driver's, not the game's (the floppy writes sector by sector with no cache). Needs a longer settle or a second write
  before the image is read; the gate tool now snapshots the image only when fsck finds it consistent.
- **Not run**: the cold-boot `persist` cell (its first run matched the saved position; the image read after shutdown
  was the flaky part, now that `sav_sync` flushes it is worth one clean re-run).
- **TT 3.06**: round trip and the +1 s kill test pass (table above). The TT needs `boot_tt()` in `tools/huntsave.py` (the STE path's
  HW-screen crop gate cannot match a borderless TT screenshot); everything after the title uses the same gates.
- **A refused save on a full disk leaves a partial SLOTn.SAV** (18,432 B in the test): Fcreate made the file, the write then failed.
  It is unreferenced (the directory is not updated, so the slot stays "free"), and a later save to that slot rewrites it from offset 0
  to the full 51,328 bytes. Nothing reads it until the directory says the slot is used.
- **Floppy cell**: `huntsave.py floppy` reports PASS - the saved game loads back with every restored range equal, and the disk holds `13`
  = 51,328 B and `0F` = 224 B. The `fsck` line it prints is run on a copy taken while Hatari still had the `.st` open ("Both FATs appear to
  be corrupt" is that torn copy); the authoritative check is the one in `floppy.md`, run after eject.

## 6. Limits

- The HD build only (`hdonly`); the floppy build keeps the cracker's loader and its own saving.
- **HDDRIVER caches writes.** The files appear in the directory only after its flush (~10 s in Hatari). A player who switches the
  machine off seconds after a save can lose it - the same as any GDI/GEMDOS program on that driver. The gates wait 15 s before reading
  the image.
- Reading the disk image with mtools **while Hatari runs** can see a half-written directory ("Fat problem while decoding"); the gate
  tool therefore only reads it after the emulator has closed.
- The slot names are the game's own: the field starts with the previous name (a fresh slot: `free`), the player edits it. That is
  unchanged behaviour from the floppy.
- `FILES\0` is no longer rewritten by a Save/Load click (PP had made the call a read). The floppy does rewrite it from the same RAM
  image; on the HD build it is PP's data file, and a rewrite would put the game's variables into it. [INFERENCE: no in-game state depends
  on that write; the round-trip gate below compares all restored RAM and passes.]
- Real hardware untested; the loader's write mode now runs on HDDRIVER (gates), not on AHDI/PP's driver.
