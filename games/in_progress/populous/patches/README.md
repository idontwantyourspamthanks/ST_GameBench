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
