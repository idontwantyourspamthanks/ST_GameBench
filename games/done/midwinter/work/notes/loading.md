# Midwinter 1 (PP/HAGA HD build) — loading pipeline, file system, patch hook points, free RAM

Date 2026-11-08. Hatari 2.6.1; STE TOS 1.62 1 MB unless stated; Mega STE TOS 2.06 4 MB.
Tools: `tools/m68dis.py`, `games/done/midwinter/tools/{mw1patch,mw1harness,mw1cell,mw1pal,mw1floppy,t6_wrongorig}.py`,
`work/dumps/RUNME_unpacked.tos` (made with `tools/pp_depack.py`), `work/dumps/ram1mb_options.bin` (1 MB STE TOS 1.62,
unpatched cold boot, Game Options screen). Anything marked [INFERENCE] was not proven. RAM addresses are `$hex`.
"text $x" = offset into the unpacked RUNME text (text length `$44BA`, data 22, bss 111206; MW2: `$4520`).
Midwinter 2 notes for comparison: `games/in_progress/midwinter2/work/notes/{loading,payload32k,bigram,load_fade,floppy}.md`.

**TL;DR**

| Question | Answer |
|---|---|
| Image files | `FILES/MWA` `MWB` `MWC`, 409600 B = 800 sectors, 10 sectors x 1 side x 80 tracks, linear: **offset = (abs_sector-1)·512**, abs_sector 1-based = track·10+sector |
| Boot chain (HD) | RUNME (HAGA, `FMW273.HST`, `FILES\MWA` +512 4608 B) -> stack-phase installer `$B1F44-$B2853` -> boot stub copy at `$CFE4` (`jmp $D000`) -> stage-2 program `$3DF28` (`jmp $3DF44`) -> resident game `$7E4-$2DD32` (`jmp $800`) |
| PP's patcher | two blocks inside the stack copy: text `$3B0` (RAM `$B1FA0`, after the stub load, patches stage-2) and text `$3EE` (RAM `$B1FDE`, after the game load, patches the game); tail `jmp $800.w` at text `$482` (RAM `$B2072`) |
| PP's patches in the game | 12 RAM patches (list in section 4), incl. the security-check bypass `$12050 <- rts` |
| Game's file system | directory tables of 10-byte entries `{start_sector.w, nsect.w, length.l, xor16.w}` embedded in the resident game (`$258A6` MWA, `$2590C` MWB), contiguous raw files, **no compression** (51/51 MWB files xor-verify against the raw image) |
| Per-file load routine | `sub_010cd2` (25 call sites), single success exit `$10D6C` `33df 000062b8` = `move.w (a7)+,$62b8.l` (6 B), splice `jmp $B3070.l` |
| Resident ranges | `$7E4-$2DD32` game (MWA file at sector 195), `$CFE4-$E1E3` stub (dead after boot), `$3DF28-$50655` stage-2 (dead after boot), HAGA at `$F8000` (1 MB) / `$1F8000` / `$3F8000` (4 MB) |
| Free RAM 1 MB, in game | `$B2854-$E844B` (220152 B, all zero at the Options and Team screens); payload `$B3000-$BAFFF` intact there |
| 4 MB | original: whole-image cache `$81000-$E5000` over the payload; with `pp_bigram_cache` chunked `$81000-$B1D40`, payload intact |
| Floppy | MWA is bootable (sum `$1234`); `build --floppy` implemented and tested, see `floppy.md` |

---

## 1. Boot flow, HD build

### 1.1 Files read (`--trace gemdos`, cold boot 1 MB STE; raw)

```
GEMDOS 0x4B Pexec(0, "C:\RUNME.TOS", [0]"", 0x0) at PC 0xE1E962
GEMDOS 0x3D Fopen("HAGA", read-only) at PC=0xF182
GEMDOS 0x3F Fread(64, 14000, 0x13866) at PC 0xF1B0            <- HAGA into RUNME's bss (text base $F176 + $46F0)
GEMDOS 0x3D Fopen("GSAU.TOS") / Fopen("FILES\D15H5.FIC") / Fopen("C:\GAMEX\D15H5.FIC")   all "not found" (normal)
GEMDOS 0x3D Fopen("FMW273.HST", read-only) at PC=0xFBE0
GEMDOS 0x3F Fread(64, 69888, 0x13866) at PC 0xFBFC             <- intro picture (STE hi-colour .HST)
GEMDOS 0x3B Dsetpath("FILES") at PC 0xF3C4
GEMDOS 0x3D Fopen("MWA", read-only) at PC=0xF40A
GEMDOS 0x42 Fseek(512, 64, 0) at PC 0xF422
GEMDOS 0x3F Fread(64, 4608, 0x81000) at PC 0xF438               <- boot stub, MWA +512, 4608 B
GEMDOS 0x3D Fopen("MWA") at PC=0xF9022 / Fseek(209600) / Fread(64, 200000, 0x81000) at PC 0xF910E   <- HAGA service, chunk cache
  ... Fseek 5120, 99328, 90112, 39424, 33280, 32256 (MWA), then MWB 209600, 150016 ...
```
(`LMW273.HST`, `MW240R.BMP` are the Mega STE / TT-Falcon intro variants, not read on STE.) RUNME is not
packed in RAM beyond its own start-up: the unpacked image is byte-compatible (reloc table round-trips).
HAGA service PCs `$F9022/$F9046/$F910E/$F9120` are `$F8000+$1022..` on a 1 MB machine, identical to MW2.
Seeks of 209600 = 409600 - 200000 are the end-of-image clamp.

### 1.2 RUNME flow (disassembly of `RUNME_unpacked.tos`, text offsets)

```
$000-$0A0  open+read HAGA to bss+$220 ($46F0), HAGA entry 0 (hardware detect), checks (below)
$098  lea.l $46f0(pc),a1 ; $09c adda.l #$8000,a1 ; $0a2..$0c8: RAM-size dependent sanity check of a1 (<$38270 on 1 MB)
$0de-$15c  pick HAGA base: $F8000 (1 MB), $1F8000 (2-3 MB), $3F8000 (>= 4 MB); copy HAGA there ($d48+1 longs)
$188..$1ee  hardware-detect/clock menu via HAGA entries
$254  lea $80000.l,a3 / lea $93e(pc),a4 / lea $64000.l,a0 / move.l #$1200,d7 ; HAGA entry 13 (record {buf,len,flag}) copied to text $620/$624/$628
$288  Fopen "MWA" ($702 string) ; $29c Fseek(0x200) ; $2ac Fread(len $1200 = 4608, buf [$620] = $81000) ; Fclose
$2d0  HAGA entry 1 ; wait for the ACIA to drain
$2ec  move.w #$2700,sr ; $2f0 move.b #7,$8201 ; $2f6 move.b #$80,$8203
$2fc  movea.l $620(pc),a1 ; $300 move.l $624(pc),d1 ; addq.l #1,d1 ; andi.b #$fe,d1 ; adda.l d1,a1    a1 = buf + len (even)
$30c  lea $200(a1),a1 ; $310 movea.l a1,a7 ; $312 move a1,usp                                     stack = buf+len+$200
$314  lea $4(a7),a2 ; $318 lea $354(pc),a1 ; $31c movea.l a2,a3 ; $31e move.w #$243,d2 ; $322 move.l (a1)+,(a2)+ ; dbra   copy text $354..$C63 (580 longs)
$352  jmp (a3)
```
Stack-phase block position, chunk mode (`$620 = $81000`, `$624 = 200000`): a7 = `$81000 + $30D40 + $200` = **`$B1F40`**, copy at
**`$B1F44-$B2853`** (observed `A3 000B1F44 A7 000B1F40` at the stub entry; non-zero bytes of `$B1D40-$B2FFF` are exactly
`$B1F44..$B2853`). Whole-image mode (>= 4 MB, unpatched) would put it at `$E5200+4` (section 5).
Text `$354` = RAM `$B1F44`, so RAM = text + `$B1BF0` inside that block.

The block `$354-$C63` contains, in order:
```
$354-$3AF  stage A (stack-phase code, runs once, then jumps into the stub):
  $354 movea.l $620(pc),a1 ; $358 lea.l $cfe4.l,a2 ; $35e move.w #$47f,d2 ; $362 move.l (a1)+,(a2)+ ; dbra      stub buffer -> $CFE4 (4608 B)
  $368 lea $498(pc),a1 ; $36c lea.l $200.l,a2 ; $372 move.w #$f9,d2 ; copy                                           low-RAM stub block text $498-$87F -> RAM $200-$5E7
  $37c lea.l $d0fa.l,a1 ; move.w #$4ef8,(a1)+ ; move.w #$200,(a1)                                                    stub: $D0FA <- jmp $200.w  (its sector-read body)
  $38a move.w #$4e75,$d406.l ; $392 move.w #$4e75,$d18c.l                                                            stub: drive-select and seek -> rts
  $39a move.w #$4e71,$69ec.w            <- no effect, see 4
  $3a0 lea $3b0(pc),a1 ; $3a4 move.l a1,$d060.l                                                                     stub: operand of its final `jmp $3df44.l` := PP's block B
  $3aa jmp $d000.l                                                                                                    <== STAGING POINT (we replace it)
$3B0-$3ED  patch block B (RAM $B1FA0): stage-2 patches ($3ED06 <- jmp $200, $23E <- $1A, $242 <- $16, $3EF8E/$3ED98 <- rts,
           $3E1AC <- $B1FDE), move #$2300,sr, jmp $3df44.l
$3EE-$481  patch block C (RAM $B1FDE): the game patches (section 4); $476/$47c: the $64D2 hook; $482 jmp $800.w   <== PATCHER TAIL (we replace it)
$498-$87F  low-RAM stub block (copied to $200): $200 sector-read stub, $25C/$27C/$2FC/$308/$31C/$328/$32E/$392 hooks, cache descriptor ($37A), HAGA pointer ($408) ...
```
RAM addresses of RUNME's stack copy (chunk mode): `$3AA -> $B1F9A`, `$3B0 -> $B1FA0`, `$3EE -> $B1FDE`, `$482 -> $B2072`.

### 1.3 Breakpoint evidence (cold boot, `b pc = $X :trace :file r.txt`)
```
$D000  (boot stub entry)       D0 00000000 ... A1 000B1FA0 A3 000B1F44 A6 000F7F2C A7 000B1F40 SR=2700   (before the stub runs)
$D05E  jmp $000b1fa0           (the stub's final jump, operand patched at text $3A4)
$B1FA0 lea.l $0003ed06,a1      SR=2700   A6 0000D458 A7 0000D618          (block B)
$3DF44 lea.l $0005064a,a7      SR=2300   A1 000B1FDE                      (stage-2 entry, stack $5064A)
$3E1AA jmp $000b1fde           A6 00048650 A7 0005064A                    (stage-2's `jmp $800.l`, its operand was patched to $B1FDE)
$B1FDE lea.l $00010e5c,a1      A1 00010120                                (block C)
$B2072 jmp $00000800.w         SR=2300                                    (the tail)
$000800 lea.l $0002d446,a7                                                (game entry)
```
Stage chain: the stub (`$D000`) reads the stage-2 program from MWA sector 558 (75566 B) to `$3DF28`; stage-2 reads two title pictures
(`$486B2`) and the whole resident game (file 1 of its table, sector 195, 185678 B) to `$7E4`. All are raw copies (stage-2 table
at `$48632`, section 3).

### 1.4 What lands where (resident ranges)
| RAM | Source | Notes |
|---|---|---|
| `$CFE4-$E1E3` | MWA +512, 4608 B | boot stub, copied by RUNME (`$354`), dead once stage-2 runs |
| `$200-$5E7` | RUNME text `$498-$87F` | PP's `$200` stub block |
| `$3DF28-$50655` | MWA sector 558, 75566 B | stage-2 program (code at `$3DF44`), dead after `$800` |
| `$486B2` | MWA sectors 11 and 177 | title pictures |
| `$7E4-$2DD32` | MWA sector 195, 185678 B | **the whole resident game**; entry `$800` (TOS header at `$7E4`) |
| `$B1F44-$B2853` | RUNME text `$354-$C63` | PP's stack-phase block (also its stack, `$B1F40` downward) |
| `$81000-$B1D3F` | HAGA service | 200000-byte chunk cache |
| `$F8000-$FFFFF` | HAGA | 1 MB machine (service entry `$F8FC4`) |

---

## 2. PP's patcher: location, list, tail

Two code blocks inside the stack copy (listing in 1.2/1.3). Block B (text `$3B0-$3ED`) runs after the stub has loaded stage-2; block C
(text `$3EE-$481`) runs when stage-2 jumps to `$3E1AC` (its `jmp $800.l` operand `$800` was replaced by `$B1FDE`) after the game is
loaded. Block C ends in the tail **`jmp $800.w` at text `$482` (`4ef8 0800`)**, followed by zero padding (`$486-$497` are zero).
Raw bytes `text[$482:$49a] = 4ef808000000 0000 0000 0000 0000 0000 0000 6100` (RUNME text; asserted by the tool).

---

## 3. The game's own disk file system

### 3.1 Tables
All images: raw sector dumps, **offset = (abs_sector - 1) · 512** (abs_sector is 1-based and linear over the 10 sectors/track;
PP's stub computes `track · $1400 + (sector - 1) · 512` with `mulu.w #$1400,d4` at text `$4E0`).

* Boot stub table (RAM `$D47C` = MWA file offset `$698`; entry 0 at `$D47E` = `$69A`): `{start 558, nsect 148, len $1272E, word $A42E}` = stage-2 (the stub's loader `sub_00d0b8` reads entry `$D47E + idx·10`).
* Stage-2 table (`$48632`, loader `sub_03ecce`: `a0 = $48632 + idx·10`):

```
[0] start 11  nsect 53  len 26636 ($680C)  word $8000   -> $486B2 (title picture 1)
[1] start 195 nsect 363 len 185678 ($2D54E) word $7455   -> $7E4 (the resident game)
[2] start 177 nsect 18  len 8899 ($22C3)   word $8000   -> $486B2 (title picture 2)
```
`$48650` directly behind the table is stage-2's parameter block (a6), so the table cannot grow.
* **Game directory tables** (in the resident game; `python3 tools/mw1patch.py files` prints them with checksums):
  `$258A6` = MWA (10 entries: files 0..9), `$2590C` = MWB (51 entries; the word before the table, 11 / 46, is not a count of them).
  `$258A2` holds the pointer to the current table. Entry = 10 bytes `{start.w, nsect.w, length.l, xor16.w}`; `nsect = ceil(length/512)`.
  `sub_010d80` verifies a load: XOR of the big-endian 16-bit words of the loaded file against `8(entry)`.

### 3.2 Compression: none (proven)
`python3 tools/mw1patch.py files`:
```
MWA directory table $258a6: 10 entries, xor checksums matching the raw image bytes: 8   (entries 8 = the game and 9 = stage-2 differ: PP modified them)
MWB directory table $2590c: 51 entries, xor checksums matching the raw image bytes: 51
```
All 51 MWB checksums equal the XOR of the raw image bytes; the game itself checks them after every load (all 12 loads of a boot ended at
`$10D6C` with Z=1, section 3.3). RAM compare against the Options-screen dump: MWA files 1-5 and MWB 30, 31, 33, 47, 48 are
**byte-exact** at their destinations; MWA 6 and MWB 36 are rewritten in place after loading (20644 and 5901 bytes differ later).
The resident game itself: `RAM[$7E4..$2DD31]` vs MWA sector 195: 2054 differing bytes, all inside 59 runs of game variables (`$637E`, `$683D`, `$D5D8`,
`$12129..`, `$2C291..` ...) or PP's 12 patches (section 4). [Method: Python compare of the two files.] The only compressor in the system is RUNME's
own self-depacker (`$6C0-$6F8`, used once).

### 3.3 The per-file load routine and its exit
`sub_010cd2` (25 `jsr $10cd2.l` call sites: `$4152 $D7A6 $D7CA $D800 $D832 $D860 $D8E6 $D90A $D940 $D96E $D9B2 $DA28 $DA92 $DABA $10392 $10526
$10552 $10586 $105BA $105EE $10622 $19CC2 $1B9D8 $1BA40 $1BC66` + `bsr $D9E8`). a6 = `$2C376` (the game's disk parameter block); file number `$15C(a6)` (= `$2C4D2`),
destination `$150(a6)` (= `$2C4C6`):
```
010cd2: movem.l d0-d7/a0-a6,-(a7)
010cd6: move.w $62b8.l,-(a7) ; 010cdc move.w #2,$62b8.l ; lea.l $2c376.l,a6 ; move.w #2,$134(a6)
010cf0: bsr $11344                      ; (PP: rts)
010cf4: bsr $10e1c                      ; seek + read the file: saves dest in $2c34a, length in $2db02, entry via $258a2
010cf8: cmp.b #$80,d0 ; beq $10d14
010cfe: bsr $11016 ... retry once via $10e1c at $10d0a
010d14: bsr $10d78 ; beq $10d6c         ; checksum (sub_010d80)
010d1a: error page ("Disk error", checksums) and retry loop: bra $10cf4
010d6c: move.w (a7)+,$62b8.l            <== the single success exit (33df 000062b8, 6 B)
010d72: movem.l (a7)+,d0-d7/a0-a6 ; rts
```
`sub_010e1c` (`$10E1C-$10EDA`) turns the entry into a seek (`track = (start-1)/[$107D8]`, `sector = (start-1)%[$107D8]+1`, `[$107D8] = 10` for
MWA/MWB; `$100FE` sets 9/track and a RAM directory for disk C) and ends in PP's hook `$10E5C: jmp $25C.w` (the displaced `move.w 2(a0),d0`),
i.e. PP's stub reads the bytes through HAGA. `[$2C34A].l` = destination start, `[$2DB02].l` = file length at the success exit (observed
below). **Hook point: `$10D6C`** (fires once per file load, after the checksum). Splice `jmp $B3070.l` (6 bytes, replaces `33df 000062b8`); the
`jmp` keeps the `[$62b8][d0-d7/a0-a6][ret]` frame, `hookexit` then replays exactly `move.w (a7)+,$62b8.l; movem.l (a7)+,...; rts`.
The 3 other readers (`sub_010322`, `sub_010edc` = write, `sub_01049c`) are not hooked; they do not carry code overlays.

Measured at the hook (breakpoint log of a cold boot, `m $2c34a 4 / m $2db02 4 / m $2c4d2 2 / m $258a2 4`), all 12 loads of a boot:

| # | dir | file | dest (`[$2C34A]`) | length (`[$2DB02]`) |
|---|---|---|---|---|
| 1 | MWA | 6 | `$3167C` | `$C40E` |
| 2 | MWA | 3 | `$4C878` | `$0CB6` |
| 3 | MWA | 1 | `$4D530` | `$0196` |
| 4 | MWA | 4 | `$4D6C8` | `$06CE` |
| 5 | MWA | 5 | `$4DD98` | `$006A` |
| 6 | MWA | 2 | `$4DE04` | `$0036` |
| 7 | MWB | 47 | `$404C4` | `$6056` |
| 8 | MWB | 30 | `$4F1E0` | `$2FB4` |
| 9 | MWB | 31 | `$52196` | `$1A58` |
| 10 | MWB | 33 | `$53BF0` | `$015C` |
| 11 | MWB | 36 | `$7A000` | `$1C9E` |
| 12 | MWB | 48 | `$2A14C` | `$2050` |

Options screen -> THE TEAM -> Capt Stark: **no loads** (zero hits at `$10D6C`, no GEMDOS I/O). Stark -> map icon: 2 chunk reads (T5).

---

## 4. PP's own RAM patches, and the security check

The 12 patches of block C, found by diffing the RAM of a booted game against MWA sector 195 and confirmed against RUNME text `$3EE-$481`:
```
$64D2  0240007f -> 4ef80392   jmp $392.w   key-release hook: handles scancodes $E5 / $E6 (numpad / and *) = "save gamestate" / "exit to desktop" (README.TXT)
$1011E b90000.. -> 4ef8031c   jmp $31c.w   select drive C ('C' into the file name at text $60E)
$10172 .. -> 4ef80308         jmp $308.w   select drive B ; $101C6 -> 4ef80308 (B again)
$1024A 206e0004 -> 4ef802fc   jmp $2fc.w   select drive A
$10E5C 30280002 -> 4ef8025c   jmp $25c.w   sector-read stub (sub_010e1c)
$10F86 23c20002 -> 4ef8032e   jmp $32e.w   write stub
$110FE 2e2e0150 -> 4ef8027c   jmp $27c.w   ; $111A6 2e2e0150 -> 4ef80328  jmp $328.w
$1102E 33fc -> 4e75           rts   (sub_01102e, FDC seek)
$11344 7e00 -> 4e75           rts   (sub_011344, drive select)
$12050 33fc -> 4e75           rts   (sub_012050: THE SECURITY CHECK)
```
(also, before the game loads: stub `$D0FA`, `$D406`, `$D18C`, stage-2 `$3ED06`, `$3ED98`, `$3EF8E`, `$3E1AC`, low RAM `$23E/$242`. `$69EC <- 4e71` at
text `$39A` is applied BEFORE the game loads and overwritten by it: RAM `$69EA = 43f9 00ff 8800` after boot, the same as the file. It is a no-op.)

**Security check.** The game starts with "FVPF SECURITY CHECK — Identify these two people by clicking on their names" (strings `$12178..$12234`; routine `sub_011c7e`).
`sub_012050` (called at `$11D7E`) sets the failure word `$12142 = $FFFF` (`012050: 33fcffff00012142`), lets the player click two names, and clears it
at `$120C6` only for the right answers; the caller then does `011d82: tst.w $12142.l ; 011d88 beq.b $11d9c` ("Identification correct / YOU ARE CLEARED",
`$11DEA/$11E0E`). PP's patch `$12050 <- rts` therefore always passes, which is what the cold boot shows (frame 7 of the boot sheet: "Identification correct /
YOU ARE CLEARED" with no click). The floppy boot has no PP patcher and shows the real check (`floppy.md`).

---

## 5. Free RAM and the 4 MB cache

Dumps: `savebin` of the whole RAM at the Game Options screen and again at THE TEAM; unpatched game (`/tmp/mw1/p1_*.bin`, `p4_*.bin`; the 1 MB dump is
`work/dumps/ram1mb_options.bin`). Non-zero extents (256-byte granularity):

```
1 MB STE, TOS 1.62:  $0-$2DBFF  $31600-$465FF  $48600-$544FF  $58E00-$5B6FF  $5D300-$5DAFF  $60000-$608FF  $68000-$720FF  $73400-$7FDFF
                     $81000-$B28FF (cache + PP block)  <free>  $E8400-$FB6FF (HAGA/loader)         identical at Options and at THE TEAM
```
Exact: last non-zero byte below `$B3000` is **`$B2853`** (PP's stack-phase copy `$B1F44-$B2853`), first non-zero byte above it is `$E844C`
(HAGA/loader block at `$F8000` minus its stacks): **free `$B2854-$E844B` = 220152 bytes**; the cache itself ends at `$B1D3F` (`$B1D40-$B1F43` zero).
Payload `$B3000-$BAFFF` is inside it.

**In the 3D view** (a peer's `tools/mw1.py` `boot_to_game('M')`: Options -> M -> PLAY -> Team -> Stark -> Decisions -> Skiing; RAM `savebin` in the view and again after
8 s of walking; script `tools/mw1ingame.py`, raw):
```
pr1  (original game, 1 MB STE 1.62)  in 3D view: {'x': 25600, 'z': 25600, 'speed': 0, ...}   marker 000B2FF8: 00 00 00 00
     non-zero bytes in $B2854-$E7FFF: 0 (view) / 0 (after the walk); last non-zero below $B3000 = $B2853     walk z 25600 -> 28250
t1_1 (build/t1, 1 MB STE 1.62)       marker MWPO   payload vs built image: 0 bytes differ (view), 0 (after the walk)
     non-zero outside the payload in $B2854-$E7FFF: 4 bytes = the marker $B2FF8-$B2FFB                       walk z 25600 -> 28250
t1_4 (build/t1, 4 MB Mega STE 2.06)  marker MWPO   payload 0 bytes differ (view), 0 (after the walk); only the marker outside the payload   walk z -> 28789
```
So the original game never writes `$B2854-$E7FFF` on the way to, or in, the first 3D view (1 MB), and the payload is intact there on 1 MB and 4 MB with the two HAGA patches.

**Before and after the chunk cache fills** (build with `pp_nofade pp_bigram_cache`, breakpoints on the stub entry `$D000` and the tail `$B2072`; raw):
```
Fread(64, 4608, 0x81000) at PC 0xF438                                    (stub; stage A copies the payload to $B3000 right after, before $D000)
1. CPU breakpoint ... $D000:   000B2FF8: 00 00 00 00            marker not yet written
                               000B3000: 48 e7 ff fe 40 e7 23 fc 4d 57 50 46 00 0b 2f f8   <- trampoline already in place
                               000B1D3C: 00 00 00 00 00 00 00 00 ; 00081000: 60 1a 00 00 06 46 00 00   (cache = the stub only)
Fread(64, 200000, 0x81000) x4 ...
2. CPU breakpoint ... $B2072 (tail): 000B3000: 48 e7 ff fe 40 e7 23 fc 4d 57 50 46 00 0b 2f f8   <- payload intact after 4 chunk reads
                               000B1D3C: ff ff 00 00 00 00 00 00   (cache tail = last 4 bytes of the 200000-byte chunk, nothing above)
```
After the boot (Options and Team screens): payload vs built image 0 bytes differ (T1).

**4 MB, original game** (Mega STE TOS 2.06, `--trace gemdos`): RUNME picks HAGA base `$3F8000` and the whole-image cache:
```
GEMDOS 0x3F Fread(64, 4608, 0x81000) at PC 0x14CB4
GEMDOS 0x3D Fopen("MWA", read-only) at PC=0x3F9022
GEMDOS 0x3F Fread(64, 409600, 0x81000) at PC 0x3F910E        <- $81000-$E5000
GEMDOS 0x3D Fopen("MWB", read-only) at PC=0x3F9022 / Fread(64, 409600, 0x81000)
```
Non-zero RAM of that boot: `$81000-$E5C00` (cache + the stack-phase copy at `$E5204`), against `$B2854-$E844B` free with chunking. The cause is HAGA's
init (`HAGA+$321C cmp.b #8,d1` ...), identical to MW2 (`games/in_progress/midwinter2/work/notes/bigram.md`); the image here is `$64000` bytes, not `$B4000`.
`pp_bigram_cache` (HAGA+`$3228` `2412` -> `602a`) is applied unchanged: file/dump bytes match (`verify`, section 8).
**Control, 4 MB without that patch** (`build --only pp_nofade`, payload staged): the Game Options screen is never reached in 180 s; the screen shows a scrambled
intro picture (the game running over the zeroed payload region), the same failure as MW2.

---

## 6. RUNME edit points for the patch tool (staging point, tail, data growth)

* **Staging point**: text `$3AA` `4ef9 0000d000` (`jmp $d000.l`), RAM `$B1F9A` in the stack copy. Replaced by `jmp <data start>.l`
  (`TEXT_LEN+22 = $44D0` relocated, +1 reloc entry at `$3AC`). The 26-byte copy routine at the head of the appended data copies the
  `$8000`-byte payload to `$B3000` and then jumps to `$D000` as before (MW2: text `$3A8`).
* **Patcher tail**: text `$482` `4ef9 000b3000` replaces `4ef8 0800` + the two zero bytes behind it (MW2: text `$754`, 12 B: PP's last patch + jmp).
  The trampoline ends in `jmp $800.w`.
* The data segment grows by N = 26 + 8 + `$8000` = 32802: every relocated long that points into bss (>= `$44D0`) gets +N (12 of the 63
  reloc entries: `$28 $5C $14E $A74 $A96 $41E6 $41EC $4216 $4236 $434A $43CC $4406`), the reloc table is re-encoded (63 -> 66 entries:
  `$3AC`, `$44EA`, `$44EE`).

## 7. pc-relative references into bss (scan of the whole text)
Scan: every word with `op & $3F == $3A` (d16(pc)) and `$3B` (d8(pc,Xn)) whose target is >= `$44D0`:
```
$098  lea $46f0(pc),a1   (43fa 4656)   -> bss+$220 (HAGA buffer)      $bbe  lea $46f0(pc),a2  (45fa 3b30)
$4184 lea $44d0(pc),a2   (45fa 034a)   -> bss start (palette save)     $4196 lea $44d0(pc),a1  (43fa 0338)
```
These four are the only real ones; they become `movea.l d(pc),aN` reading a relocated pointer (`227a 4450`, `247a 392a`, `247a 0368`, `227a 0356`
from the built RUNME). Six words that match the mask are not instructions: `$506`/`$5D8` (displacement word `$013A` of `move.w $13a(a6),d2`), `$706`
(the string `C:\GAMEX..`), `$C86` (address word of `move.w #$6004,$bfa.l`), `$41C4`/`$438C` ($FFFA fill words) — each checked in the disassembly.
`pea $44ba(pc)` (`$A60`) and `pea $44c5(pc)` (`$4336`) point into the data segment, which does not move. Diff of the built RUNME text against
the unpacked original (`build/t1/RUNME.TOS`): 45 bytes, all in `$3AA-$3AF`, `$482-$487`, the four leas, and the +N on relocated longs ("unexpected: []",
"reloc mismatches []"). RUNME's HAGA-buffer sanity check (`$A2-$C8`, `a1 < $38270` on 1 MB) still passes with the 32 KB larger TPA
(text base `$F176`: `a1 = $F176 + $46F0 + $8022 + $8000 = $23888`).

---

## 8. Tests (raw outputs)

Builds: `python3 tools/mw1patch.py build --only pp_nofade pp_bigram_cache --out build/t1` (T1), `... test_boot_text test_load_cursor --out build/t2`
(T2/T3), `tools/t6_wrongorig.py` (T6). Cells: `python3 tools/mw1cell.py NAME MACHINE TOS MEM GAME --live build/live/X --team`.

### T4 `verify` (HAGA patches + test patches)
```
$ python3 tools/mw1patch.py verify
floppy_secbypass   site $12050 phase boot     src resident game (MWA file 1) len 2
    declared orig : 33fc
    image  bytes  : 33fc  (match)
    ramdump bytes : 4e75  (n/a: floppy-only site, the dump is an HD boot)
test_boot_text     site $250ea phase boot     src resident game (MWA file 1) len 5
    declared orig : 4d4f555345
    image  bytes  : 4d4f555345  (match)
    ramdump bytes : 4d4f555345  (match)
test_load_cursor   site $53c30 phase deferred src MWB file 33 @ $53bf0 len 8
    declared orig : a89faca291ae005a
    image  bytes  : a89faca291ae005a  (match)
    ramdump bytes : a89faca291ae005a  (match)
pp_bigram_cache    image HAGA  1 edit(s)
    HB+$3228 len  2  orig 2412
        file  2412  (match) / dump  2412  (match) / new   602a  (same length)
pp_nofade          image HAGA  4 edit(s)  [4 edits: all file+dump match, same length]
verify: ALL OK
```
(`python3 tools/mw1patch.py verify` prints the full listing; every segment also assembled byte-identically at HB = `$3F8000`, `$1F8000`, `$F8000`.)

### T1 build with only `pp_nofade` + `pp_bigram_cache` (0 game patches, staging + trampoline present)
```
cell t1_ste1mb ste TOS 1.62 1024 KB build/t1
Game Options screen reached: True
[options] marker: 000B2FF8: 4d 57 50 4f                                      MWPO
[options] payload $B3000..+$8000 vs built image: 0 bytes differ
THE TEAM screen reached: True
[team] marker: 000B2FF8: 4d 57 50 4f                                      MWPO
[team] payload $B3000..+$8000 vs built image: 0 bytes differ

cell t1_mste4mb megaste TOS 2.06 4096 KB build/t1
Game Options screen reached: True
[options] marker: 000B2FF8: 4d 57 50 4f                                      MWPO
[options] payload $B3000..+$8000 vs built image: 0 bytes differ
THE TEAM screen reached: True
[team] marker: 000B2FF8: 4d 57 50 4f                                      MWPO
[team] payload $B3000..+$8000 vs built image: 0 bytes differ
```
Screens: `work/ref/options_play.png` (exact match of the Options screen) and `work/ref/team_title.png` (THE TEAM title).

### T2 boot-phase test patch (`test_boot_text`, `MOUSE` -> `PATCH` at `$250EA`) and T3 deferred (`test_load_cursor`)
```
cell t2_ste1mb ste TOS 1.62 1024 KB build/t2                         cell t2_mste4mb megaste TOS 2.06 4096 KB build/t2
[options] marker MWPO   payload 0 bytes differ                       [options] marker MWPO   payload 0 bytes differ
[options] site $0250ea [test_boot_text] RAM 5041544348 new 5041544348 orig 4d4f555345 -> PATCHED     (same on 4 MB)
[options] site $053c30 [test_load_cursor] RAM ffffffffffffffff new ffffffffffffffff orig a89faca291ae005a -> PATCHED
[team]    (same lines again, marker MWPO, payload 0 bytes differ)
```
T2 screenshot of the Options screen (`/tmp/mw1cell_t2_ste1mb/options.png`): the first control label reads **PATCH** instead of MOUSE.

**T3 sequence** (breakpoints `$B3000` trampoline, `$B3070` hookexit, `$B307A` after `jsr apply`; build/t2 cold boot, raw):
```
bp $B3000 (tramp entry):   000B3000: 48 e7 ff fe ...   00053C30: 00 00 00 00 00 00 00 00   000B2FF8: 00 00 00 00      <- file 33 not loaded yet
bp $B3070 (11th load, file 33): 0002C34A: 00 05 3b f0   0002DB02: 00 00 01 5c   00053C30: a8 9f ac a2 91 ae 00 5a    <- loaded, original bytes
bp $B307A (after apply):                                                        00053C30: ff ff ff ff ff ff ff ff    <- patched by the hook
(the other 11 loads: bp $B3070/$B307A with 00053C30 zero, then ff.. unchanged)
```

### T5 palette changes during one transition (Capt Stark screen -> map icon; 2 chunk Freads), STE 1 MB, `b ($ff8242).w ! ($ff8242).w :trace :file r.txt`
```
[orig]   $ff8242 changes during the transition: 25     GEMDOS Fread: 2 [('200000','81000'),('200000','81000')]
         change PCs (top): [('000f924c', 12), ('000f9494', 12), ('000061ca', 1)]          <- HAGA service (fade loop / fade back) x24, game x1
[nofade] $ff8242 changes during the transition: 1      GEMDOS Fread: 2 [('200000','81000'),('200000','81000')]
         change PCs (top): [('000061ca', 1)]                                                  <- the game's own write only
```
(Original: `$F924C` = fade-to-grey compare, `$F9494` = fade-back write; MW2 `load_fade.md` section 3 has the same instruction map.)
The Options -> Team -> Stark transitions load nothing (0 `Fread`, 0 changes in both builds); the boot (12 loads) is where the original fades repeatedly.

### T6 wrong orig => nothing applied (`tools/t6_wrongorig.py`: valid `test_boot_text` first in the table, then a site declaring `STACC` while RAM has `STICK`)
```
cell t6_wrongorig ste TOS 1.62 1024 KB build/t6
Game Options screen reached: True
[options] marker: 000B2FF8: 4d 57 50 46                                      MWPF
[options] payload $B3000..+$8000 vs built image: 0 bytes differ
[options] site $0250ea [test_boot_text] RAM 4d4f555345  new 5041544348  orig 4d4f555345  -> ORIGINAL
[options] site $0250f0 [zz_wrongorig] RAM 535449434b  new 5858585858  orig 5354414343  -> OTHER
THE TEAM screen reached: True    (same lines, MWPF)
```
Finding: the MW2 trampoline verified and applied site by site (a bad site applied everything before it). MW1's `core.s` is two-pass; this is its test.
