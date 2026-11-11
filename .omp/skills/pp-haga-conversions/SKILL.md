---
name: pp-haga-conversions
description: How PP's HAGA hard-disk conversions of Atari ST games work (RUNME.TOS + HAGA + FILES/ disk images) and how to patch them safely. Covers the LZ-packed loader, the HAGA resident disk service, chunk caching and the >=4 MB whole-image mode, the load-time grey fade, boot-time patch injection, free RAM, and the floppy-image path. Use when a game under gamebench/games/ has RUNME.TOS + HAGA (e.g. Midwinter, Midwinter 2).
---

# PP's HAGA hard-disk conversions

Layout: `RUNME.TOS`, `HAGA`, `FILES/<disk images>`, an intro picture (`*.HST` STE hi-colour, `*240R.BMP` TT/Falcon), and PP's `README.TXT`/`LOG.TXT`.
- PP converted the original STX floppies to raw images and removed the protection ("manual deprot").
- He applies his game fixes in RAM at boot. The image files are original, apart from his modified boot stub.
- Worked example with full evidence: `games/in_progress/midwinter2`. See its `work/notes/loading.md`, `bigram.md`, `load_fade.md`, `payload32k.md`, `floppy.md` and `patches/README.md`.

## Components
- **RUNME.TOS**
  - It is LZ self-packed. Unpack it with `python3 tools/pp_depack.py RUNME.TOS out.tos`, which verified on MW2 and MW1.
  - It loads HAGA and the intro picture, then FFA's boot stub. It installs low-RAM stubs at `$200..$5E7` (PP's patcher at `$4BC-$59C` ends `jmp <game entry>`). Then it runs the game.
- **HAGA**
  - It is identical across games: md5 `b34607ed…` in both Midwinter 1 and 2.
  - It handles hardware detection and the clock/cache menus, then is copied verbatim to `phystop-$8000` as the **resident disk service**.
  - The service Freads 200000-byte chunks of the image files into a cache at `$81000-$B1D40`, and the game's loader copies sectors from there.
- **Image files** are raw sector dumps; their geometry is per game:
  - MW2: 9 sectors × 2 sides × 80 tracks = 737280, track-interleaved.
  - MW1: 10 sectors × 1 side × 80 tracks = 409600.
  - The game's own file system sits inside them: MW2 has a directory with xor checksums and no compression.

## Known PP-service behaviours (all fixed in MW2 by HAGA file patches; the same HAGA means the same fixes)
- **Grey fade on every chunk read** (`HAGA+$1166` fade to grey, `+$1460` fade back).
  - It is PP's loading indicator, and the cause of repeated fades on screen changes.
  - `patches/pp_nofade.s` redirects the 2 call sites. Loads got about 2× faster.
- **≥4 MB on 68000 machines: whole-image cache mode.**
  - `HAGA+$321c` tests `RAM/512K ≥ 8` and switches to reading each 720 KB image whole into `$81000-$135000`.
  - That **overwrites anything you put above `$B1D40`**.
  - `pp_bigram_cache.s` (`HAGA+$3228`: `2412` → `602a`) keeps chunked mode. TT/Falcon (68020+) use `$300100` instead and are untouched.
  - The pristine game works at 4 MB; only added code breaks.
- **The security-check bypass** is one of PP's RAM patches (MW2: `move.w #$6002,$2c574`).
  - PP's patcher installs it on HD only, so the floppy boot path doesn't get it.

## Injecting your own code (MW2 design; reuse it)
- **Payload:** staged into free RAM at `$B3000-$BAFFF` (32 KB).
  - It is appended to RUNME's data segment and copied there by a 26-byte routine spliced into RUNME's stack-phase fallthrough.
  - PP's stack-phase installer copy sits at `$B1F44-$B2853`, just below.
- **Boot patches:** a trampoline replaces PP's patcher tail `jmp <entry>`. It verifies every site's original bytes, applies all or none, and sets the marker `MWPO`/`MWPF` at `$B2FF8`.
- **Load-time patches** (code that arrives later from an image): a hook at the game loader's per-file exit. It must be a **`jmp`, not a `jsr`**, so it keeps the exit frame.
- **RUNME relocation:** growing the data segment moves the bss. PC-relative references into bss (MW2: 4 × `lea d(pc)`) overflow at about 32 KB. MW2 rewrote them as `movea.l d(pc),aN` reading a pointer table, so they stay 4 bytes. Scan the whole text for them.
- **Free RAM in game** (MW2, 1 MB): `$B2852-$E83E5`. PP's 1 MB service sits at `$F7554`/`$F8000`. 512 KB is impossible, because the chunk cache alone needs `$81000-$B1D40`.
- **HAGA file patches:** HAGA moves with RAM size, so patch it as a file with position-independent code (MW2 tool: `; image: HAGA`, `; edit: <off> <orig>`). Never patch it at fixed RAM addresses.
- **The delivery point differs per game; find it before copying MW2.** Three shapes so far:
  - MW2/MW1: the game is in RAM when PP's patcher runs, so a trampoline replaces the patcher tail `jmp <entry>`.
  - Populous: the game isn't in RAM until START GAME (PP's `POLA` runs the original `LOADER.PRG`, which Pexecs `DEMO.TOS` then `POPULOUS.TOS`). `poppatch.py` replaces `LOADER.PRG`: `Pexec(3)`, verify and apply, `Pexec(4)`.
  - Populous 2: RUNME's stage block unpacks `P2M.FIC` to `$1770`; the trampoline replaces RUNME's own tail (`move.l #$1c42,$118.w` / `jmp $1770.w`).
- **Programs that TOS loads (Pexec) move with the TOS version.** Populous's text base is `$AD96` on STE TOS 1.62, +`$3E48` on TT TOS 3.06 and +`$5216` on Falcon TOS 4.04. Every absolute address in a patch must be relocated at boot (`poppatch.py`: assemble twice, diff the 32-bit fields, add the delta in `core.s`), or nothing applies on TT/Falcon. Game images that HAGA or a boot stub loads to a fixed address (MW2) don't move.
- **HAGA file patches are NOT portable between games, even though HAGA is identical.** `pp_nofade` is fine in MW2 but makes Populous's in-game LOAD bus-error (`PC=$16eca`). Test save and load with every HAGA patch, per game, before defaulting it on.

## Floppy path
- The first image (FFA/MWA) is usually bootable: the boot sector sums to `$1234`, and it loads the boot stub, which loads the game.
- RUNME, PP's patcher and HAGA never run on floppy. The game uses its original FDC driver, with no fade and no PP RAM patches.
- MW2's floppy injection: the payload goes in a new file on disk A (free track-sides). A 32-byte stage 1 sits in dead stub code and calls the stub's own loader.
- Watch for the game's disk-copy buffers covering the payload. MW2 halved one: `floppy_copybuf`.

## PP's builds aren't always fully fixed
- Populous: the copy-protection trap is still armed (`$edec-$ee16` compares the long at `$24` with `$54ac0842`): Armageddon is forced once 19 peep slots are used. Only long play reveals it.
- Populous 2: in-game SAVE/LOAD is stubbed out (bus error; PP's README says so). Only HAGA statesaves work, and they need about 1 MB of disk.
- Populous on TT/Falcon HD in Hatari: stock PP crashes on its 68030 path (`D15RF.FIC`); the floppy build works. Unresolved.
- So: read PP's README.TXT, then test long play, save/load and every machine on the pristine build before blaming a patch.

## Checks for any HAGA game
- Run the pristine game and the patched one side by side, at 1 MB, 2 MB and 4 MB, on Mega STE TOS 2.06, STE 1.62 and Mega ST 1.04. A "fails unpatched too" result is only valid against a truly pristine copy, not a zero-patch build that still contains your staging.
- After a boot, `$B3000` must still hold your payload in game; compare the bytes.
