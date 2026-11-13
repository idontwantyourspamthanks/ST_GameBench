# Populous delivery (PopDelivery, 2026-11-11)

Tool `tools/poppatch.py`, patches `patches/` (README.md = format + mechanism), `tools/package.sh`, cell scripts `tools/pop_boot_test.py`.
Shots (git-ignored) in `work/shots/`: `delivery_credit.png`, `boot_<cell>_menu.png` / `_play.png`, `delivery_noprot_patched.png` / `_stock.png`.

## What the files are (evidence: my FAT12 reader in poppatch.py, Hatari `--trace gemdos,xbios`, disassembly of POLA / LOADER.PRG / DEMO.TOS)
* `FILES/POP` (524,288 B) is a **FAT12 disk image** (BPB: 512 B sectors, 2 per cluster, 112 root entries, 1024 sectors, 10 per track, 1 side): `AUTO\LOADER.PRG` (616), `POPULOUS.TOS` (104,136), `DEMO.TOS` (25,530), LAND0-3, LEVEL.DAT, GMUSIC1, pictures, font. Clusters in use end at sector 779; 224 zero sectors follow (room for saves). It is the game disk **and** the save disk: the in-game save of "TEST" changed 17,091 bytes of it.
* `FILES/POM` (409,600 B) is **side 1 of the original double-sided disk, raw** (10 x 80 sectors, no file system). `DEMO.TOS` `sub_00b60a` (`$b60a`) reads track 0 sector 1 side 1 with Floprd and tests its first byte for `$39` (POM starts `39 35 22..`): "double sided disk"; `sub_00b580` then loads side 1 tracks 0-38 (`$30c00` bytes of title music). Sectors 392-399 and 520-779 are `$E5` (formatted-empty).
* `FILES/POLA` is PP's launcher PRG (text `$518`, data `$d2`): it copies its code to `$6600`, hooks hdv_rw (BIOS Rwabs -> POP) and XBIOS Floprd (-> POM), and runs the original `LOADER.PRG` (LZ-packed in its data at +`$20`, 178 -> 616 bytes, identical to POP's `AUTO\LOADER.PRG`) as RUNME's process. That loader: Mshrink, Setcolor 0 x16, `Pexec(0,"demo.tos")`, `Pexec(0,"populous.tos")` with the exit code + '0' in the command line.
* So `DEMO.TOS` (title, credit roll, LOAD.PIC menu) and `POPULOUS.TOS` (the game) are separate programs loaded by Pexec at text base `$AD96` (base page `$AC96`) in PP's layout, on STE TOS 1.62, ST TOS 1.04 and Mega STE TOS 2.06 alike (`m $b6f4` = `4eb9 00014a28` in every cell). The game code is NOT in RAM until START GAME: at the title `$edec` holds data. This is why the MW2 "trampoline at PP's patcher tail" does not exist here: PP's patches are 3 words applied by POLA's read hook.
* PP's patches of the game (relocated POP image vs `work/dumps/g0.bin`, text only): `$1dc4a` `4ef86890`, `$1e11c` `4ef868a2`, `$2006c` `4eb86132`; the only other text differences are run-time words `$16d2c-d`, `$16f13-5`, `$20063-5`.

## Mechanism (HD) - details in patches/README.md
Replaced: `RUNME.TOS` (payload appended + stage routine at text `$360`), `FILES/POLA` (our `loader.s` instead of the packed LOADER.PRG), `HAGA` (file patches). The loader does Pexec(3) -> payload `apply` (verify all sites of that program, apply all or none, marker) -> Pexec(4), then Mfree of what mode 3 leaves (found: without it the second Pexec fails, no memory). Mshrink size = `$AC92 - base page` so the game text base is `$AD96` wherever RUNME is started (stock footprint `$340` otherwise).

## Free RAM (candidates `$b1d40-$cfc36`, `$5eefc-$77fc7`; pattern = word `(addr>>1)*$9E37+$1234`, loaded by the debugger at the loader start `pc=$aa52`, payload bytes kept)
```
1 MB STE, play start:                 b1d40-cfc36: 2 bytes differ ($b3007,$b300b = our marker), 5eefc-77fc7: 102,200 differ (all)
1 MB after save + load + next map:    b1d40-cfc36: same 2 bytes; after quake+volcano+flood: same 2
busy_castles.sav (pattern loaded after restore, quake, volcano, flood, 840 turns): b1d40-cfc36 0 differ; 5eefc-77fc7 4 differ ($5eefc-$5eeff)
2 MB at play start:                   b1d40-cfc36: same 2 bytes; $70 = $1c0a8e, $d0000 = 0 (PP's resident copy moves with phystop)
4 MB (HAGA pp_bigram_cache applied):  play start, save, load, next map: b1d40-cfc36 same 2 bytes
4 MB original game (no patch):        b1d40-cfc36: 122,120 of 122,615 bytes differ  -> pp_bigram_cache is required
```
Verdict: `$b1d40-$cfc36` is free (payload `$B3000`, blobs to `$C7FFF`, `$C0000-$C7FFF` reserved for PopLandScore, told by message). `$5eefc-$77fc7` is zeroed at game start (Pexec/startup), so unusable for boot-staged code; written after start it survives (only `$5eefc-$5eeff` is live). Save/load tested through the game's own dialogs (GAME SETUP globe icon -> SAVE A GAME / LOAD A GAME / MOVE TO NEXT MAP). 2 MB save/load not repeated (play start only).

## No-protection proof (cold boot, hd build; busy scene = 78 walkers placed with the game's paint routine, `Populous.busy_scene()`)
Stock game (same scene, `$ee16` untouched): `turn npeeps armageddon used inbuilding walking`
```
turn    96 npeeps   6 armageddon 0 used   6 inbuilding [2, 3] walking [1, 0]
turn   166 npeeps  84 armageddon 1 used  70 inbuilding [0, 0] walking [34, 36]
turn   356 npeeps  78 armageddon 1 used   9 inbuilding [0, 0] walking [3, 6]
turn   726 npeeps  12 armageddon 1 used   1 inbuilding [0, 0] walking [1, 0]   (game over)
```
Patched build (`$ee14` = `b081 6052`):
```
turn    95 npeeps   6 armageddon 0 used   6 inbuilding [2, 3] walking [1, 0]
turn   165 npeeps  89 armageddon 0 used 110 inbuilding [14, 17] walking [35, 44]
turn   306 npeeps 110 armageddon 0 used  91 inbuilding [31, 38] walking [12, 10]
turn   439 npeeps 110 armageddon 0 used 100 inbuilding [33, 36] walking [16, 15]
turn   570 npeeps 110 armageddon 0 used  96 inbuilding [34, 40] walking [9, 13]
```
(peep records at `$3b2b6`, 22 B: +0 bit0 in building, +1 owner, +4 life; `$3d562` Armageddon flag.) Shots: `delivery_noprot_patched.png`, `delivery_noprot_stock.png`.

## Credit
`pop_credit.s`, `; version: 1.0` (the one place), prog DEMO: site `$b42a` (`33fc 0002 0004c576`, second instruction of the menu loop `sub_00b426`), blob `$b4000` draws `v1.0 enhanced by dad_prg` with our own 3x5 font (4x6 cells, colour 8 = $444) at x 72, y 193 of the LOAD.PIC menu (`$12fa4` = screen `$78000`), right of "COPYRIGHT BULLFROG 1989". Shot `work/shots/delivery_credit.png`.

## HD cold boots (final build, `tools/pop_boot_test.py`)
```
{'cell': 'ste1mb',    'in_play': True, 'marker': 'POPO', 'flags': '00 00 00 03', 'ee16': '60 52', 'membot': '00 00 a8 4e', 'main_loop': '4e b9 00 01 4a 28'}
{'cell': 'st1mb' (ST TOS 1.04),   same fields, all identical}
{'cell': 'ste4mb',    same}
{'cell': 'megaste16' (Mega STE TOS 2.06, set_cpuclock(16)), same}
```
Credit visible in `boot_<cell>_menu.png` of all four. (`--cpuclock 16` on the command line crashes TOS 2.06's boot: use the fifo option after start.)

## Floppy (`build --floppy`: `Populous_boot.st` 819,200 B, `Populous_save.st` 737,280 B)
Physical 80x10x2 disk: side 0 = POP's first 800 sectors (BPB nsect 800, `AUTO\LOADER.PRG` replaced), side 1 = POM, tracks interleaved; the BPB keeps 1 side so TOS uses side 0 as the original. Payload: raw in POM's empty tracks 52-77 (dir on 52). The floppy loader must read it AFTER Pexec(3): TOS clears all free RAM in Pexec (found: breakpoint `($b3000).l !`, `movem.l -(a2)` at `$e0210e`), and it reserves `$B3000+` with Mshrink(program, to `$B3000`) + Malloc (GEMDOS hands out exactly `$B3000`). The loader stack lives in the base page's command-line area (text `$1d6`; the AUTO base page is `$A99A`, so the block `$2F8` ends at `$AC92`: text base `$AD96` again; with the stock-size floppy loader the base was `$ADF4`, marker `POPT`).
Cold boot STE 1 MB TOS 1.62 from `Populous_boot.st`: menu with credit at ~25 s, CONQUEST, START GAME: `m $b3000` = `POPP POPO`, flags 2, `$ee16` = `60 52`, `$b6f4` = `4eb9 00014a28`, turn counter 48 -> 93 -> 237.
Save and load on floppy: drive A swapped to `Populous_save.st` (`hatari-option --disk-a`), SAVE A GAME "tst": save disk root `TST.GAM` 29,646 B; with the boot disk in A the game says "ERROR IN SAVING" (disk full; the game disk has 10 free clusters); LOAD with the save disk lists TST, loads turn 237, then asks "INSERT THE ORIGINAL POPULOUS DISK IN A:" -> swap back, OK: running (turn 263 -> 298), payload header `POPP POPO` and `$ee16` intact; payload bytes differ from the built image only at `$b3007`,`$b300b` (marker).
Not done: floppy at 2/4 MB, ST/Mega STE floppy cells, a 512 KB ST (the loader skips the payload when Mshrink/Malloc fail; unpatched game then falls into the protection trap).

## TT / Falcon status
* HD (GEMDOS drive) on TT: PP's boot dies with bus errors (study, `boot.md`); not retried.
* Floppy image on Hatari TT (EmuTOS 1.4, 4 MB): boots, DEMO.TOS title runs (screenshot `/tmp/fl_tt.png` seen), payload loaded, marker `POPT` (base page differs under EmuTOS: no patches applied). Falcon (EmuTOS, 4 MB): `Panic: Bus Error addr=ffff8804 ... Crash at text+00002202` in DEMO.TOS (its hardware access, `$ffff8804` area). ACSI/IDE images not tried (budget). Both need real work (EmuTOS TPA layout, 030 caches, hardware); `[INFERENCE]` only.

## Open / for the lead
* `pp_nofade` is `default: no` (not in my list); flip it in its header if wanted.
* HD build ships POLA/RUNME/HAGA changes only; POM/POP are byte-identical to PP's.
* DEMO.TOS has no PP run-time patches known (no dump); `verify` checks demo sites against the image only.
* Final gate outputs are in this file; `verify` ends `verify: ALL OK`; `tools/package.sh` md5s: RUNME `a2cf00c2…`, POLA `4dc289a7…`, HAGA `59083376…`, boot.st `2cd2735d…`, save.st `af93f79a…`.
