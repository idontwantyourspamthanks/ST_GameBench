# Moonshine Racers: floppy release (original disks, protection, build)

Companion to `work/notes/delivery.md` (the HD delivery). Everything below cites raw output in `build/logs/`, `work/floppy/` or the
disassembly of the disk/RAM dumps. Hatari 2.6.1, STE TOS 1.62, 1 MB unless stated.

## 1. The disks

`originals/moonshine_racers_millennium.zip` (the user's addition; never modified) holds two Pasti STX images, extracted to
`originals/floppy/` (git-ignored):

| file | bytes | md5 |
|---|---:|---|
| `moonshine_racers_millennium_a.stx` | 1,866,960 | `19d5b545b60cad6a090c5037f82bcf54` |
| `moonshine_racers_millennium_b.stx` | 1,875,082 | `83b66b2d7276fe94099faac2e4e80ecb` |

Reader: **`tools/stx2st.py`** (format taken from the emulator's own reader — `hattari/src/floppies/stx.c` + `includes/floppies/stx.h`,
Pasti v3, little-endian fields; no capsimg needed). Both images: version 3, imaging tool 1, revision 2, 164 track blocks
(82 tracks x 2 sides), **10 sectors of 512 B per track**, tracks 80-81 unformatted.

```
$ python3 tools/stx2st.py info originals/floppy/*.stx
moonshine_racers_millennium_a.stx: 1866960 B, version 3, tool 1, revision 2, 164 track blocks, trailing 0 B
  side 0: 82 tracks, sectors per track [0, 10], ... tracks 0-81
  side 1: 82 tracks, sectors per track [0, 10], ... tracks 0-81
  anomalies: 5
    summary: crc=0, fuzzy=0, del=0, var=0, rnf=0, odd=0, idfield=0, empty=4, dup=0, track images=163/164, MFMSize range 6160-6368
    t80.0: no sectors (track image only)  ... (t80.1, t81.0, t81.1)
```
(identical summary for disk B, 164/164 track images). **No CRC errors, no fuzzy bits, no deleted data, no variable timing, no odd
sector sizes, no foreign ID fields, no duplicated sectors** — the only "anomalies" are the four unformatted track-sides at
tracks 80-81, which a standard 80-track drive cannot even address.

`stx2st.py st IMAGE OUT.st --geom 80,2,10` writes a plain .ST image: **1600 of 1600 sectors, 0 missing, 0 duplicated, 0 outside the
geometry** for both disks (`work/floppy/disk_a.st`, `disk_b.st`, 819,200 B each).

**Verdict: the STX media are standard 800 KB 10-sector disks; a plain .ST conversion is lossless for every sector.** The copy
protection is *not* in the media (no odd tracks, no timing, no fuzzy), it is a **manual look-up question in the loader** (section 3).

## 2. The loader chain (disk A is bootable, custom loader, no FAT)

The boot sector starts with `60 04` (BRA) and OEM "MOON", and its 256 words sum to `$1234` (checked: `sum = 0x1234`), so TOS boots it.
It is *not* a DOS filesystem (the BPB fields are garbage). **TOS runs it at its own disk buffer, not at `$7800`**: the FDC trace of the boot
read is `fdc read sector addr=0x185c drive=0 track=0 sect=1 side=0 VBL=70 ... pc=e01124` (STE TOS 1.62, `build/logs/floppy_flow.log` line 154).
The code is position independent (`lea $7832(pc),a5`), so below the sector is disassembled *as if* at `$7800` (offsets only; an earlier version of
this note and of the tool wrongly assumed the run address was `$7800`, which is why the first stage-0 loader jumped into the weeds):

```
007800: 6004                 bra.b   $7806
007802: 4d4f 4f4e            "MOON"                   ; the GAME tests this long (offset 2) to recognise disk 1: $d77a cmpi.l #'MOON',$68002
007806: 6010                 bra.b   $7818
007808: 2020 2020 "MOONSHINE   "
007818: 4df90007f830         lea.l   $7f830.l,a6
00781e: 4bfa0012             lea.l   $7832(pc),a5
007822: 3e3c007f             move.w  #$7f,d7
007826: 2cdd                 move.l  (a5)+,(a6)+
007828: 51cffffc             dbra    d7,$7826
00782c: 4ef90007f830         jmp     $7f830.l        ; relocate 512 B of itself to $7F830 and run there
   (the relocated code, offsets $32.. of the sector:)
007832: lea $80000.l,a7 ; clear the palette ; moveq #5,d7 ; lea $78c4(pc),a0
00784c: movem.l d7/a0,-(a7) ; move.l #$a,-(a7) ; move.w (a0),-(a7) ; move.l #1,-(a7) ; clr.l -(a7) ; move.l 2(a0),-(a7) ; move.w #8,-(a7) ; trap #$e
        ; = XBIOS Floprd(buf=(2(a0)).l, filler=0.l, dev=0.w, sect=1.w, track=(a0).w, side=0.w, count=10.w)   20 B incl. the opcode
007876: addi.l #$1400,2(a0) ; addq.w #1,(a0) ; dbra d7,$784c      ; 6 x Floprd of one track (10 sectors) to $40000 + n*$1400, starting at track 1
007884: ori.w #$700,sr ; clear $400-$66000 ; copy 25,600 B from $40000 to $78000 ; jmp $78000.l
0078c4: 0001 00040000        ; the loader's DATA: track word = 1, buffer long = $40000 (read by the relocated copy; do not overwrite)
```
so **stage 1 = the tracks read here, 25,600 B copied to $78000**. It is a scatter loader: raw FDC trace of a full boot (`build/logs/floppy_flow.log`,
1127 read records, PC $786ea-$7870c = inside $78000):

```
$ fdc read sector addr=0x1000  track=5  sect=4  side=0     ; loader reads sector-by-sector into game addresses
$ fdc read sector addr=0xc000  track=14 sect=2  side=0
$ fdc read sector addr=0x1ec00 track=29 sect=2  side=0
$ ... 1110 distinct sectors, tracks 0-61, both sides, into $1000-$4E600 (last read VBL 666)
```
No FAT, no GEMDOS: the loader owns the disk. It then plays the intro/credits (`WELCOME PARTNERS ... GAME DESIGN BY PEAK STAR`),
shows the manual question, and — after a correct answer — loads the game (tracks 62-79) and starts it exactly like the HD build:
`$1000` = `60005f4e bra.w $6f50`, the game's trap #2 hand-over, with **the game code at the same addresses as the HD release**
(measured after a correct answer: `work/floppy/ram_answered.bin` contains the bytes of disk A $C350/$E16A/$189CA at RAM $6f50/$796a/$d1ca,
and RAM `$7000` is byte-identical to the HD dump). So every RAM patch site of the HD build applies unchanged.

Disk B is the data disk: its first 772,096 bytes are **exactly `FILES/MS2` of the HD release** (same md5 content, `cmp` finds
identical blocks at identical offsets); everything above that is unused.

## 3. The protection (still live in this release; PP's HD build bypasses it)

Random per boot, printed by the loader from a template on disk A (`$E6FD "MANUAL"`, `$E72B "PARAGRAPH"`, `$E79E` table):

```
FROM THE MOONSHINE RACERS MANUAL, TYPE IN THE WORD AT
     PAGE  4, PARAGRAPH  5, LINE  5, WORD  9.        <- two boots gave 9/5/3/1 and 4/5/5/9 and 5/6/1/8
REMEMBER TO IGNORE BOLD TYPE AND PUNCTUATION.
FOR EXAMPLE, THE WORD AT PAGE 5, PARAGRAPH 5, LINE 3, WORD 1 IS 'BARRELS'.
>
```
The answer table follows the text **in plain ASCII on disk A at `$E7D2`** (and in RAM at `$7FD3` when the question is up):

```
 3 2 3 2DRIVE       4 1 2 5CHICKENS     4 4 412PLYMOUTH    9 3 1 6ADVANTAGE   7 5 1 4COOKING
 7 3 115OCTANE     6 1 3 5BUDDIES      5 1 2 4BEERS       5 3 8 3WAKEY        4 7 2 8VARMINTS
 ... 64 entries ... 5 6 1 8SORE         5 6 4 6THE         6 6 114DAWG        3 1 1 4COMPUTER
```
Format: space, page, space, paragraph, space, line, space, word, then the answer with no separator, NUL-terminated. 64 entries;
`ACCESS DENIED.` is the failure message (same text block).

**Behaviour measured**: typing the right word is accepted and the game starts (screenshot `build/shots/ask7.png`, "Hi, I'm I"
title after answering `SORE` for 5/6/1/8); a wrong answer (or none) leaves the machine on a black screen with no further disk
activity — the loader does not load the game. The question is regenerated every boot, so it cannot be answered once and for all.

`tools/msrfloppy.py auto` boots the original disk, reads the question **out of RAM** (the loader builds the text with the numbers in
`$7EF0..`), looks the answer up in the table (also in RAM), types it and continues to the race: that is the baseline gate for the
original floppy (section 6).

## 4. Where the payload lives on disk A (free sectors)

The loader's 1,127 FDC reads touch tracks 0-61 only (`build/logs/floppy_flow.log`: last read `addr=0x4e600 drive=0 track=61 sect=10 side=1`).
Sectors of disk A that are **never read in a boot and are blank** (fill `6d b6 db 6d b6 db ...`), computed from that log and the image:

```
blank sectors on disk A: 490, unread among them: 490
runs (track, side, first sector, count): (0,0,2,9) (49,0,10,1) (50..61,0,1,10) and every track-side 62..79 (both sides, 10 each)
```
(all of tracks 62-79 are blank on disk A: the game itself sits on tracks 0-61; disk B is the data disk). `msrpatch.py` allocates, in order,
`FLOPPY_FREE = (0,0,2..10) + (t,0,1..10) for t in 50..61` = **129 sectors = 66,048 B >= IMG_MAX_LEN (61,440 B)**, and **verifies each is
the blank fill in the original before writing** (`blank_sector()`; refuses otherwise). Tracks 80-81 cannot be used (a standard drive only
addresses 0-79).

## 5. The build (`msrpatch.py build --floppy`)

1. **Disks**: `stx_disk("A"/"B")` converts the STX to plain .ST in memory (never writes `originals/`). Disk B is shipped byte-identical
   (checked: `disk B identical: True`).
2. **Payload**: the HD image builder (`build_image`) with the site table placed right after the core (`TABLE = IB+$120 = $B2820` instead of
   `$B7000`) so small images are small; the default set (incl. the three `mt_*` tick patches, blobs at `$B8000-$B8F0B`) is 26,636 B = 53 sectors.
   The RAM patches' blob/data addresses are unchanged. The trampoline is `patches/core_floppy.s`.
3. **Stage-0 payload loader** (in the boot sector, `floppy_loader()`): the boot sector's *first instruction of the original program*
   (offset `$18`, `lea.l $7f830.l,a6`) becomes `bra.w loader` + `nop`; the loader sits in the sector's free area (offsets `$CA-$1F3`; the
   original's own data at `$C4-$C9` and the stale bytes at `$1F4-$1FF` are untouched), reads the payload runs with XBIOS `Floprd`
   (`move.w count / side / track / sector / dev(0) ; clr.l filler ; move.l buf ; move.w #8 ; trap #14 ; lea 20(a7),a7`) to `$B2700` upwards, executes
   the displaced `lea.l $7f830.l,a6` and `bra.w` back to offset `$1E` of the original program. **The original header (`60 04`, "MOON", offset
   `$6`-`$17`) is unchanged** because the game itself recognises disk 1 by the long at offset 2 (`$d77a cmpi.l #'MOON',$68002`).
   A read error hangs (`bne.b *`), exactly like the original's own loop (`$7874`).
4. **Boot checksum**: `fix_boot_checksum()` restores `sum = $1234` by adjusting a pad word inside the loader area.
5. **Disk patches** (`; disk: A <offset> <orig hex>`, verified against the STX conversion before applying, refuses otherwise):
   `fl_hook` (the delivery hook, always part of a floppy build) and `fl_deprot` (the protection neutraliser, `; media: floppy`, default yes).
6. **RAM patches**: the same `patches/*.s` sites as the HD build, applied by the trampoline (all-or-nothing, `MSPO`/`MSPF` at `$B2700`).
   `build --floppy` additionally refuses a RAM site whose original bytes differ in the *original floppy's* RAM (`work/floppy/ram_answered.bin`;
   `verify` prints that witness for every site: all of them match, `mt_clock $d128`, `mt_sync $7b74`, `mt_pre $7b0a` included).
7. **Output**: `build/floppy/disk_a.st`, `disk_b.st` (and `--zip` -> `dist/MoonshineRacers_floppy_v<version>.zip`, folder `MOONSHR_floppy/`).

Sectors of disk A that differ from the original (checked with a byte diff): the 53 payload sectors, the boot sector, `(4,1,8)` (= disk `$C350`,
`fl_hook`) and `(5,1,4)` (= disk `$E3D0`, `fl_deprot`).

Command: `python3 tools/msrpatch.py build --floppy [--only N ...] [--out build/floppy] [--zip]`.

## 6. The protection neutraliser `fl_deprot` (`patches/fl_deprot.s`)

**Where the question lives.** It is not in the stage-1 loader at `$78000`: a *second* loader phase (PC `$741b4`, after the intro) reads
disk A track 5 side 1 sector 4 into RAM `$7A00` (`fdc read sector addr=0x7a00 drive=0 track=5 sect=4 side=1 VBL=1436 ... pc=741b4`), and that
sector holds the question routine. Proof of the mapping: the RAM dump at the prompt (`work/floppy/ram_prompt.bin`) `[$7A00:$7C00]` equals disk A
track 5 side 1 sector 4 byte for byte (`ram 0x7a00 == disk t5.1s4: True`), and the 22-byte pattern `7e02 3f07 4eb9 0000d866 4a78 3a88 66fa 4eb9 0000d8e0`
occurs exactly once on disk A, at **disk offset `$E3D0` (= sector offset `$1D0` = RAM `$7BD0`)**.

**The routine (disassembly of `ram_prompt.bin`, RAM addresses):**

```
0071a2: 4eb900007bd0         jsr $7bd0.l                  ; the only caller (after the credits screen); $719c jsr $d8e0 = clear screens before it
007bd0: 7e02                 moveq #$2,d7                 ; three attempts
007bd2: 3f07                 move.w d7,-(a7)
007bd4: 4eb90000d866         jsr $d866.l                  ; fade palette out
007bda: 4a783a88             tst.w $3a88.w / 007bde: bne.b $7bda      ; wait for the fade
007be0: 4eb90000d8e0         jsr $d8e0.l                  ; clear screens
007be6: 4eb90000d84e         jsr $d84e.l                  ; set the question palette
007bf0: 41fa0213             lea.l $7e05(pc),a0           ; "FROM THE MOONSHINE RACERS MANUAL TYPE IN THE WORD AT ..." text, drawn by jsr $12268
007c14: 0240003f             andi.w #$3f,d0               ; d0 = counter incremented in the loop `007c02: addq.w #1,d0 / 007c04: tst.b $60ff.w / 007c08: beq.b $7c02` until a key arrives: random 0..63
007c1a: 43fa0112 lea $7d2e(pc),a1 / 007c1e: 41fa03b3 lea $7fd3(pc),a0 / 007c22: d0f10000 adda.w (a1,d0.w),a0   ; a0 -> answer entry (table $7fd3)
007c26..007c52: 8 x move.b (a0)+,$7f27..$7f52.l          ; page/paragraph/line/word digits into the question text
007c56: 2f08                 move.l a0,-(a7)              ; a0 now = the ANSWER WORD
007c7a: 4a10                 tst.b (a0)                   ; \ typed everything -> accept
007c7c: 6700009a             beq.w $7d18
007c90: 0c00001c             cmpi.b #$1c,d0               ; RETURN
007c94: 67000042             beq.w $7cd8
007cd8: 4219 clr.b (a1)+ ; 007cda: 43fa0119 lea $7df5(pc),a1 (typed text)
007cde: 1010                 move.b (a0),d0
007ce0: 8011                 or.b (a1),d0
007ce2: 67000034             beq.w $7d18                  ; both strings ended together with no difference -> ACCEPT
007ce6: b308                 cmpm.b (a0)+,(a1)+           ; the compare
007ce8: 67f4                 beq.b $7cde                  ; equal so far -> next character
007cea: 7c0e ... 007cf8: addq.l #4,a7 ; 007cfa: move.w (a7)+,d7 ; 007cfc: dbra d7,$7bd2     ; mismatch: next attempt
007d00..007d12: lea $7de2(pc),a0 ("ACCESS DENIED.") ; jsr $12268.l ; 007d12: bra.b $7d12    ; third failure: print and HANG
007d18: 5c8f                 addq.l #6,a7                 ; ACCEPT exit: drop saved d7.w + a0.l
007d1a: 4eb90000d866         jsr $d866.l                  ; fade out
007d20: 4a783a88 / 007d24: 66fa                           ; wait for the fade
007d26: 4eb90000d8e0         jsr $d8e0.l                  ; clear the screens
007d2c: 4e75                 rts
```

**The patch (4 bytes, disk A `$E3D0`, RAM `$7BD0`):**

```
orig: 7e02 3f07      moveq #2,d7 ; move.w d7,-(a7)
new : 6000 0148      bra.w $7d1a         ; $7bd0 + 2 + $148 = $7d1a
```
It jumps into the routine's own accept exit *after* `addq.l #6,a7` (`$7d18`), because at entry the stack holds nothing but the caller's return address
(the `d7`/`a0` words that `$7d18` drops are never pushed). `$7d1a-$7d2c` then fades the credits screen out, waits, clears the screens and
returns to `$71a8` — exactly the state after a correct answer, with the question never drawn, no key asked, no random draw and no failure path.
The displacement is hand-encoded in the patch file (the file offset `$E3D0` is not the RAM address `$7BD0` the branch is relative to).
`msrpatch.py` verifies the 4 original bytes in the STX-converted disk image before applying (and `verify` prints them); it only ever edits its
in-memory copy, `originals/` and the user's zip are untouched (md5 `19d5b545...`/`83b66b2d...` unchanged after the builds).
Alternative considered: patching only the `beq.w $7d18` conditions/`bne` at `$7ce8` would still draw and ask the question; the entry bypass is the
smallest patch that never shows it. [INFERENCE: a later phase might read the state the question screen leaves (`$d84e` palette, `$7f27..` digits);
the swap and race gate below runs from `$71a8` through a race with no ill effect on the three machines tested.]

## 7. Disk 2 (the swap) - the game asks for it, the harness swaps it

The game *does* ask for disk B, on the way into the first race: `$72c4 jsr $76f4` -> `$76f4: jsr $d788` reads the boot sector of the disk in **drive A**
(`$d798`: `moveq #0,d1 ; moveq #1,d2 ; lea $68000,a0 ; jsr $d6fa`) and compares the long at offset `$E` with `$66055505` (`$d78a-$d790`; present at
disk B offset `$E` and nowhere else on either disk: `b ['0xe']`, A only in code `0x18f92`); on mismatch it shows
`"Insert Disk 2 and press a key."` (text at RAM `$6143`, `jsr $735a`) and loops `$76fc-$770e`. The game's disk driver (`$cac0`) takes the drive from bit 0
of the device word the callers pass (0 or 4), i.e. **always drive A**: a single-drive machine swaps the disks in A. The way back is the same
(`$d778`: `cmpi.l #'MOON',$68002` = "Insert Disk 1"), which is why the boot sector header bytes stay as shipped.

Raw evidence (patched build, STE 1 MB, only A inserted): after the story/intro screens the screen shows `Insert Disk 2 and press a key.`
(`build/shots/floppy_ste_1024_prompt.png`), the FDC trace repeats `fdc read sector addr=0x68000 drive=0 track=0 sect=1 side=0` every key press
(VBL 2435, 2550, 2749, 2952, 3157, ...: the boot-sector check failing on disk A).

**Harness steps (Hatari)**: boot with disk A only, SPACE through the intro until the prompt, then
`hatari-option --disk-a <path of a COPY of disk_b.st>` through the command fifo (Hatari log: `Floppy A: has been removed from drive.` ...
`Inserted disk ... to drive A:`), then SPACE. Hatari refuses (`Cannot insert same floppy to multiple drives!`, and then stops answering) when the image is also
the one in drive B, so the copy is needed. After the key the game loads the race (100 sector reads follow, first `addr=0x70000 drive=0 track=12 sect=5 side=0`, last `addr=0x62400 drive=0 track=22 sect=3`: all from drive A = the swapped disk) and the race is on screen (`build/shots/floppy_ste_1024_race.png`). Implemented as `tools/msrfloppy.py gate`.
On a real machine: swap the disk in drive A when asked, press a key. [Not tested here: the game asking for disk 1 again and swapping back.]

## 8. Gates (raw outputs: `build/logs/floppy_*`)

Commands: `python3 tools/msrpatch.py verify` (-> `build/logs/floppy_verify.log`), `python3 tools/msrpatch.py build --floppy --out build/floppy --zip`
(-> `build/logs/floppy_build.log`, `dist/MoonshineRacers_floppy_v1.0.zip`, 2 files, 898,137 B), then per machine
`python3 tools/msrfloppy.py gate build/floppy/disk_a.st --disk-b build/floppy/disk_b.st --machine M --mem N --tos T --name NAME`
(`build/logs/floppy_gate_NAME.log`; the gate boots disk A alone, presses SPACE every 3 s, saves every screen from VBL 900 on to
`build/shots/floppy_NAME/NN_vblV.png`, waits for the game's own "Insert Disk 2" prompt, swaps, presses SPACE, waits 30 s).

`verify`: last line `verify: ALL OK` (includes `fl_deprot disk A +$0e3d0 original disk image: 7e023f07 (match)`, `fl_hook ... 21fc00006f5a00884e42 (match)`, and the
floppy-RAM witness for every RAM site).
Build (disk patches line of `build_floppy.log`): `disk A+$e3d0   4 7e023f07 -> 60000148   [fl_deprot]` and
`disk A+$c350  10 21fc00006f5a00884e42 -> 4ef9000b27084e714e71   [fl_hook]`; `floppy: disk A 819200 B, disk B 819200 B; payload 26636 B (53 sectors)`.

| machine | marker `$b2700` at the swap prompt | story screen, then prompt, **no question** | after swap + 30 s | `$b2700` after | tick clock `$b8f00` | log |
|---|---|---|---|---|---|---|
| STE TOS 1.62 1 MB | `4d 53 50 4f` MSPO | mode 2 at VBL 2035, prompt at VBL 2405 | race on screen, `$1021/$100e` = 2/182 | MSPO | `00 00 33 5a` | `floppy_gate_ste_1024.log` |
| STE TOS 1.62 4 MB | MSPO | VBL 2037 / 2408 | race, 2/182 | MSPO | `00 00 33 72` | `floppy_gate_ste_4096.log` |
| Mega STE TOS 2.06 4 MB | MSPO | VBL 2446 / 2891 | race, 2/183 | MSPO | `00 00 33 f9` | `floppy_gate_megaste_4096.log` |
| ST TOS 1.04 1 MB | MSPO | VBL 2035 / 2406 | race, 2/182 | MSPO | `00 00 33 5a` | `floppy_gate_st_1024_tos104.log` |

(Raw lines, e.g. `marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00 ... MSPO....`, are in the logs. The race screenshots are
`build/shots/floppy_<name>_race.png`: the in-race view with the HUD and the "Ike and Billy Joe are sure in for a chase this time!" text; the
prompt screenshots are `floppy_<name>_prompt.png`, the sequence screens are in `build/shots/floppy_<name>/`: sunrise intro, black fade,
title with "Hi, I'm", then "Insert Disk 2 and press a key." - **no manual question screen anywhere**.)
Notes: `in_race` in the old harness sense (`$1021 == 2`) is the story/title screen with "Hi, I'm Ike"; the *real* race needs disk 2 on this release, so
the gate goes on through the swap to the first race. The marker is `MSPO` before and after the 30 s race, and the `mt_clock` long `$b8f00` advances (the
three `mt_*` tick patches are active in the floppy build, default set), i.e. the payload area is not overwritten by the floppy game.
The original floppy baseline (`msrfloppy.py auto`, in_race True, VBL 3029) was not touched: `originals/` and `work/floppy/disk_*.st` are unchanged
(md5 of the two STX: `19d5b545...` / `83b66b2d...`).

## 9. Final design, and what is unproven

Design: stage-0 loader in the boot sector (position independent, original header intact, original first instruction displaced) reads the payload from
129 allocated blank sectors (53 used) of disk A to `$B2700` before the original boot code; the original loaders run unchanged, with the question routine's
first two instructions replaced by `bra.w $7d1a` (`fl_deprot`) and the game's entry stub at `$6f50` replaced by `jmp $B2708.l` (`fl_hook`) into the same
all-or-nothing trampoline as the HD build (marker `MSPO`/`MSPF`); disk B untouched, disk swap by the game itself.

Unproven / not done:
- Real floppy hardware and real machines: only Hatari 2.6.1 (STE TOS 1.62 1 MB/4 MB, Mega STE TOS 2.06 4 MB, ST TOS 1.04 1 MB). 2 MB, TT/Falcon not run on the floppy build.
- A real 1-drive swap with real media; the "Insert Disk 1" swap back (`$d778`) was not exercised (the boot-sector header it tests is unchanged).
- The state the (now skipped) question screen leaves behind: no difference found through the first race, but nothing beyond the first race was played.
- Read errors during the stage-0 payload load hang the machine (as the original loader does).
- `--zip` ships the two `.ST` images only (no README).

**Relabel (MSRMegaSTE):** the "Mega STE TOS 2.06 4 MB" floppy gate above is the only Mega STE floppy result here (4 MB only); 1 MB Mega STE: `integration.md` section 10.
