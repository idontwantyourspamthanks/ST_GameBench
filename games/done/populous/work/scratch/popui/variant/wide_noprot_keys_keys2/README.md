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
* `RUNME.TOS`: unpacked image + the payload appended to its data; a `jmp` at text `$360` runs a stage routine copying the payload to `$B3000`
  (bss pointers fixed as in MW2). The payload (`patches/core.s`): header `'POPP'`, marker `$B3004` (`POPO` all applied, `POPF` mismatch/preset,
  `POPT` text base differs), flags `$B3008` (bit0 DEMO, bit1 POPULOUS), `apply` at `$B3010`, site table `$B3100`, blobs `$B4000+`.
  Verify-then-apply, all or nothing per program.
* `HAGA`: `pp_bigram_cache` (default yes; without it the 4 MB whole-image cache overwrites `$B1D40-$CFC36`), `pp_nofade` (default no).
* `POM` and `POP` are byte-identical to PP's (saves stay compatible).

## Delivery (floppy)
Physical disk 80x10x2: side 0 = POP's first 800 sectors (FAT volume, BPB 800 sectors, AUTO\LOADER.PRG replaced), side 1 = POM (title music; the game reads it raw).
Payload: raw in POM's empty tracks 52-77 (directory on track 52); the floppy loader reads it after each Pexec(3) (Pexec clears all free RAM), keeps
`$B3000..` away from the game with Mshrink + Malloc. `Populous_save.st` is a blank 720K save disk (swap it in when the game saves; it asks for the original disk back).

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
