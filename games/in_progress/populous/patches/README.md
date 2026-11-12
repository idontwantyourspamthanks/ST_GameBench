# Populous patches: format and delivery mechanism

Tool: `python3 tools/poppatch.py verify | list | build [--hd|--floppy] [--only NAME...] [--out DIR] | live [--only ...] [--out build/live/x] | version | doc FILE`.
Design copied from Midwinter 2 (`mw2patch.py`); evidence and test logs: `work/notes/delivery.md`.

## Patch file (`patches/*.s`, vasm mot syntax)
Header comments before the first `org`: `; name:` `; default: yes|no` `; prog: populous|demo` (default populous) `; site: $addr`
`; orig: <hex>` (optional, cross-checked) `; data: $addr len` (zero-init reservation) `; media: floppy|hd` `; version:` (only pop_credit.s).
The `org <site>` segment holds the NEW bytes (shorter than orig = nop padded); every other `org` is a blob in `$B4000-$C7FFF`
(`$C0000-$C7FFF` is reserved for the land-score code). Addresses are RAM addresses with the text base `$AD96`.
File patches (`; image: HAGA`, `; edit: $off <orig>`, `org HB+$off`) edit PP's resident loader HAGA in the build copy.

## What a site is checked against
`POPULOUS.TOS` / `DEMO.TOS` are read out of the disk image `FILES/POP` (FAT12; AUTO\LOADER.PRG, DEMO.TOS, POPULOUS.TOS ...), relocated at `$AD96`
(what Pexec(3) leaves in RAM), plus PP's three run-time patches (`$1DC4A`, `$1E11C`, `$2006C`), cross-checked with `work/dumps/g0.bin` if present.
A site may not overlap the words that change at run time (`$16D2C-D`, `$16F13-5`, `$20063-5`).

## Delivery (HD)
* `FILES/POLA` (PP's launcher): its data holds the original LOADER.PRG LZ-packed; replaced by `patches/loader.s` (same footprint: text `$240`).
  The loader does Pexec(3) (load+relocate), calls the payload's `apply`, then Pexec(4); it also Mfree's what mode 3 leaves behind. The Mshrink size
  ends its block at `$AC92`, so the game base page is `$AC96` (text `$AD96`) wherever RUNME was started.
* `RUNME.TOS`: unpacked image + the used parts of the payload (segment table + segments, `runme_segments`) appended to its data; a `jmp` at text `$360` runs a stage routine
  copying every segment to its address (bss pointers fixed as in MW2). Only the copied bytes (16.9 KB for the full release set, whose image spans 88 KB from `$B3000` to
  `$C8964`) move RUNME's bss: PP's own low-RAM check (`Too much low RAM occupied`, RUNME text `$ca`-`$d0`) counts it, and it failed on a 1 MB STE with TOS 2.06 once the whole
  contiguous image (88 KB) was carried (82 KB passed, 86 KB failed; bisected with a dummy data block); the gaps between segments are not written. The payload (`patches/core.s`): header `'POPP'`, marker `$B3004` (`POPO` all applied, `POPF` mismatch/preset,
  `POPT` text base differs), flags `$B3008` (bit0 DEMO, bit1 POPULOUS), `apply` at `$B3010`, site table `$B3100`, blobs `$B4000+`.
  Verify-then-apply, all or nothing per program.
* `HAGA`: `pp_bigram_cache` (default yes; without it the 4 MB whole-image cache overwrites `$B1D40-$CFC36`), `pp_nofade` (default no).
* `POM` and `POP` are byte-identical to PP's (saves stay compatible).

## Delivery (floppy)
Physical disk 80x10x2: side 0 = POP's first 800 sectors (FAT volume, BPB 800 sectors, AUTO\LOADER.PRG replaced), side 1 = POM (title music; the game reads it raw).
Payload: raw in POM's empty tracks 52-77 (directory on track 52); the floppy loader reads it after each Pexec(3) (Pexec clears all free RAM), keeps
`$B3000..` away from the game with Mshrink + Malloc. **The payload read and `apply` run on a stack inside the payload block** (1 KB below the directory buffer; PSPAN = segments
+ 1536): the BIOS trap handlers run on the caller's user stack, the loader's own stack is the 128-byte command-line area of its base page, and on TOS 4.04 the process descriptor
words right below it (handle count `$3a`, handle table `$3c`) were overwritten by a deep Floprd + interrupt nesting; the next `Pexec` then failed with ENHNDL (-35) on the Falcon
(`work/gates/release_falcon_diag.txt`). `Populous_save.st` is a blank 720K save disk (swap it in when the game saves; it asks for the original disk back).

## Patches
`pop_noprot` (yes), `pop_credit` (yes, version), `pp_bigram_cache` (yes, HD), `pp_nofade` (no), `pop_land_score`, `pop_land_mul` (no, PopLandScore).

## pop_ptr and pop_bgcopy (PopDisplay; both `; default: no`, blobs `$C2000-$C26CB`, data `$C2400` + 448)
Evidence, gates and cycle counts: `work/notes/display.md`; the pixel gate is `tools/popabtest.py` (`gate`, `fps`, `copy`, `cpytest`, `mutants`).
* `pop_ptr` (site `$16d80`, 8 bytes -> `jsr $c2000` + `nop`; blob `$c2000`-`$c2211`, data block `$c2400`): the VBL routine `$16d70` restores
  the pointer's saved background (`$16dea`) and redraws it (`$16e20`) into the displayed buffer in every VBL (11.5 k cycles, 7.4 % of a busy
  frame at 8 MHz). The blob skips both when the result is provably the same bytes (address of the last draw `$16f12`, displayed buffer `$3c50c`,
  pointer words `$24786/8`, shape `$2169a`, sheet `$3d572`, `$2498c/e` equal to what the last draw saw, the screen rectangle under the pointer ==
  the image that draw left, the 160 shape bytes it read == the copy taken then); otherwise it runs the two original routines and records
  what they left (the images only when the draw before had the same inputs, so a moving pointer pays about 0.7 k cycles per VBL). A flip changes
  `$3c50c`, so the first VBL after a flip, the restore into the old buffer and every hide are the original path. Measured 11,470 -> about 5,100
  cycles per VBL with a still pointer; +3 to +5 % turns/s at 8 MHz.
* `pop_bgcopy` (site `$14a28`, 8 bytes -> `jmp $c2600` + `nop`; blob `$c2600`-`$c26cb`): the 32,000-byte copy `$3b016` -> `$3c510` at the start of
  every pass by 13-register `movem` (247,619 -> 138,712 cycles per frame measured); flags, `d0` and all other registers as the original leaves
  them (`popabtest.py cpytest`: 96 of 96 trials identical). +5 % turns/s on busy scenes, +13.5 % on the idle start.
* Both together: +10.3 / +9.7 / +16.9 % turns/s (busy_castles / busy_quake_volcano / genesis_start), +12.5 / +12.4 / +18.3 % on top of the land patches.
* Gate: `python3 tools/popabtest.py gate` (three snapshots, 289 flips each, both buffers + world RAM per flip, two mid-frame samples per flip,
  injected pointer script, junk / shape / x injections under a still pointer): IDENTICAL for every set; `--mutant NAME` runs a deliberately
  broken patch, which must fail (all 7 do). The gate removes two timing races of the original game from both runs (display.md section 3).
* `pop_ptrfix` (PopDisplay; `; default: no`; site `$2003e` 30 bytes -> `jmp $c2800` + nops, blob `$c2800-$c283d`): the IKBD packet handler stores a reply into the
  pointer variables unchecked; when the ACIA loses a byte (HAGA swaps the vector table, `$118` included, on every disk call) the next reply's `$f7` header lands in a data slot
  and the pointer draw gets y = `$6e00` / `$f708` / 247: its row count `15 - (y - 184)` goes negative, `dbra` runs ~65,500 rows through memory (`Bus Error ... PC=$16eca` on an
  STE with `pp_nofade`, `Address Error` on a Mega STE, stock PP included). The blob stores buttons <= `$0f`, x <= 319, y <= 199 as before and drops anything else.
  Gate: garbage packets after 8 flips (`popabtest.py gate --garbage MASK`), IDENTICAL; mutants and unpatched controls fail (`work/notes/display.md` section 9).
  `pp_nofade` should only be switched on together with it.

## Other machines: relocation, machine mask, pop_fal_ym_demo + pop_fal_ym (PopMachines; `; default: no`, blob range `$C4000-$C4FFF`)
Evidence and cell outputs: `work/notes/machines.md`, `work/gates/machines_*.txt`.
* **The text base moves.** TOS puts the Pexec'd program at the first free address: `$AD96` on ST/STE/Mega STE (the loader steers it there), but TOS 3.06 on a TT
  has its own data up to `$E6FC` (text `$EBDE`, delta `$3E48`) and TOS 4.04 on a Falcon up to `$FA04` (text `$FFAC`, delta `$5216`). That is why the payload
  reported `POPT` (nothing patched) there. The game itself is position independent (it Mallocs its buffers and takes the screen from Physbase).
* **Every patch is relocated automatically.** poppatch assembles each site and blob twice, the second time with every hex literal in the program's own address range
  (`$AD96` .. text+data+bss end) written `($lit+GD)`, GD = `$10000`; the 32-bit fields that differ by exactly GD are the game addresses. Their addresses go into a
  relocation list at the top of the image (`$B3100` = list pointer, delta applied); `apply` adds `p_tbase - $AD96` to each once, then verifies and applies as before.
  The original bytes of a site are relocated by the program's own relocation table. With delta 0 (ST/STE/Mega STE) nothing is touched.
  Rules for sources: write game addresses as plain hex literals (a long immediate address with 5+ digits, `#$0b6f4`; a 4-digit `#$xxxx` is taken for a 16-bit
  value, `dc.b/dc.w` operands and `$xxxx(An)` displacements are never shifted); no pc-relative reach between game text and a blob; no fixed addresses
  outside the program's range and the payload ($B3000-$CFC36) for things that are not game variables (e.g. `$78000`, `$4f500` are Malloc/Physbase results, they move).
  `poppatch verify` prints the relocated longs of every patch and fails on any other use of a game address.
* **Machine mask.** Header `; machine: st, ste, tt, falcon` (megaste = ste): the site is verified and applied only on those machine classes (`_MCH` high word,
  read by `apply` once with Supexec; `_CPU` too). Skipped sites leave the original bytes. `live` keeps only sites valid on an STE.
* `apply` empties both CPU caches after the sites are written on a 68020+ (`movec cacr`, `cpusha bc` on 040/060).
* `pop_fal_ym_demo` (DEMO `$cf98`) and `pop_fal_ym` (game `$171a8`), Falcon only: the sample interrupts write the three YM volumes with `movep.l d1,-$7800(a0)` =
  `$ff8800/02/04/06`; a Falcon bus-errors on `$ff8804`. The blob (`jsr` + `nop` over 8 bytes) does the same register writes through `$ff8800/02` only.

## pop_tick set: the world at 5 turns per real second (PopTiming; six patches, all `; default: no`, blobs `$C5000-$C59FF`, data `$C6000` + 3680)
Evidence, tables, gates and cold boots: `work/notes/timing.md`; gate tool `tools/poptick.py` (`ab`, `rate`, `cold`, `clicks`, `input`, `pause`); raw outputs `work/gates/tick_*.txt`.
The game is frame coupled: one pass of the play loop (`$b632`-`$bc06`) = one world turn (`addq.w #1,$3c506`, `$db96`) = one full redraw = one flip, as fast as the CPU goes
(3.2 turns/s on a busy 8 MHz STE, 25 on a TT, 42 on a Falcon). The user's choice is FIVE TURNS PER REAL SECOND on every machine, at 50 and 60 Hz (10 resp. 12 VBL per turn).
Time base: the game's VBL counter `$16d2a` in units of 1/300 s (6 per VBL at 50 Hz, 5 at 60 Hz; `btst #1,$ffff820a.w`, read at every look). Every pass is T (a turn: the original pass),
S (catch-up: world, no frame), R (ahead of real time: frame and UI, no world) or P (paused, paint mode or a link game: the original pass, clock parked).
* `pop_tick` (`$b632`, 6 B -> `jmp $c5000`): the look at the pass top; kind, accumulator (clamp 3 turns), data block `$c6000` (flags SKIP `+14`, RON `+16`, REC `+18`, FLAGS `+20`, counters `+28..+44`, dot-list pointer `+48`, dot list `+$100`).
* `pop_tick_render` (`$b6f4`, `jsr $14a28` -> `jmp $c5200`): S passes skip the render stage (jump to `$b800`).
* `pop_tick_logic` (`$b800`, `jsr $12fc2` -> `jmp $c5300`): R passes skip the world (`$12fc2`, `$db8a`) and the block `$b8ec-$b93a` (shield countdown `$3b03e`, event of turn `$1000`), replay the minimap dots and go on at `$b93a`.
* `pop_tick_flip` (`$b940`, `jsr $16f16` -> `jmp $c5400`): S passes skip flip, keys and UI (they run the command executor and loop); R passes hide FRESH click latches (`$3d566`, `$3c514` = 0) from the UI of the pass.
* `pop_tick_cmd` (`$bbf8`, 8 B -> `jmp $c5500` + `nop`): R passes skip the command executor `$1e750` (one command per turn) and put the hidden latches back.
* `pop_tick_dot` (`$1672a`, `jsr $167b0` inside `$166f0` -> `jsr $c5600`): records the minimap dots of a turn pass (560 entries), S passes plot nothing.
* Test only (never in a build): `test_pwalk` (`$b6e2`: pointer and view as a function of the turn; `SPINN` burns cycles per turn = a slow machine), `test_rtog_a/b` (`$b6fa`, `$b7f0`: water phase toggled for the render-only compare).
* The tick is off (kind P) while `$3b2b2` (pause), `$3b2b4` (paint mode) or `$3c524` (link game: `$1e7e6 tst.w $3c524` selects the serial command exchange `$1ff14/$1fe4c`) is set.
* Other agents' sites kept intact: `$b93a` (`jsr $d4c0`, pop_tooltip) is entered by R passes with `jmp $b93a`; `$bb7c` (pop_keys) and `$200a6` run once per UI pass (T and R passes), not in S passes.

## Keys and tooltips: pop_keys, pop_keys2, pop_keys3, pop_keys4, pop_tooltip (PopUI; all `; default: no`; blobs `$C7000-$C7901`, data `$C8000+32` and `$C8200+1184`)
Evidence, key table, wording and gates: `work/notes/ui_impl.md`, raw outputs `work/gates/ui_*.txt`, shots `work/shots/ui_*.png`; tool `tools/popuitest.py`.
* **Keys: take all four** (`pop_keys` = pass hook + tables, `pop_keys2` = key recorder in the ACIA interrupt, `pop_keys3` = typed-text guard, `pop_keys4` = dialog guard; each checks that `pop_keys`
  is installed before it touches its data). Keys (physical positions): `R` raise / lower, `Q` query, `P` papal magnet mode, `M` `S` `G` `T` walkers go to the magnet / settle / gather / fight,
  `E` earthquake, `W` swamp, `K` knight, `V` volcano, `F` flood, `A` twice Armageddon, `L` view leader, `Z` view magnet, `B` view battle, `N` view knight, `H` view own building, `Space` pause, `U` music, `X` effects.
  The keypad scroll is the game's own and unchanged.
  * `pop_keys` (site `$bb7c` = `move.w $21d8e.l,d0`, 6 bytes -> `jsr $c7000`): once per pass takes the next key from the ring and calls the game's own icon handler `$c420(left?)` with the click position at
    the icon's cell centre (both click latches 0 for the length of the call, because the VBL routine `$16c96` copies the live pointer into the click position while a latch is idle), so mana checks,
    greyed icons, mode changes and the 3 order bytes at `$21e4a` are the game's. A key waits while the player's order byte is non-zero (one order at a time) and while a real click is latched.
  * `pop_keys2` (`$2008c` = `move.b d0,$37eec.l`, the make-code store): scan code -> action number into a 16-entry ring (`KD+12`), only while `$16d2a` - LASTV <= 150 VBLs (a pass stamps LASTV).
  * `pop_keys3` (`$200a6`, 10 bytes -> `jmp` + 2 nops): a poll of the text-key converter from anywhere but the main loop (return address `$b94c`) empties the ring; `pop_keys4` (`$1a508`, 10 bytes): the same at every poll of the dialog button test.
  * Armageddon: the first `A` arms (`KD+4`), the second within 150 VBLs fires; any other key disarms.
  * Data `KD` `$c8000`: +0 LASTV.l +4 ARMT.l +8 spare.w +10 QH.b +11 QT.b +12 Q[16].
* **`pop_tooltip`** (site `$b93a` = `jsr $d4c0.l`, 6 bytes -> `jsr $c7400`): hovering an icon prints its name, key and (spells) manna cost in the game's own 8x8 font (`$2364a`): line 1 in (84,0)-(213,7)
  (16 characters), line 2 in (100,8)-(171,15) (9 characters), merged into the BACK buffer after `$d4c0` and before the flip (every pass starts from the clean-background copy, so nothing is erased and nothing is left
  behind when the pointer leaves; with the pointer off the icons the frames are byte-identical to the original). Hit test = the game's own `$c420` geometry. The key labels appear only with `pop_keys` installed.
  Data `T` `$c8200`: +0 CX +2 CY +4 CID +6 SHOWN +8 KEYS +10 NG1 +12 NG2 +14 TXT1[24] +38 TXT2[16] +56 C1[720] +776 C2[400].
* Blob map: `pop_keys` `$c7000-$c7143` (hook), `$c7200-$c7229` (KT), `$c7243-$c72bd` (ACT); `pop_keys2` `$c7300-$c7377`; `pop_keys3` `$c7380-$c73b5`; `pop_keys4` `$c73c0-$c73ff`; `pop_tooltip` `$c7400-$c7901`.
* Gates (all passed, see ui_impl.md section 6): key == click 23/23 identical in both mana scenarios (control mutant 17/23); real keys through IKBD / ACIA for all 23 presses; pointer-away pixel gate IDENTICAL (3 snapshots,
  both buffers + world + mid-frame samples; mutant fails); tooltip diffs confined to the two rectangles (mutant fails); typed text / dialog keys never act (control without the guards: they act); cold boots STE HD + floppy, TT floppy, Falcon floppy.
