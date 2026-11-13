# Populous: boot, memory, delivery facts

Second pass, 2026-11-11 (the first draft's errors are listed at the end). Machine: 1 MB STE, TOS 1.62, Hatari GEMDOS drive C: = `originals/POPULOUS`.

## Files and loader

HAGA md5 `b34607ed9baecc5982a5a01ecaf5a3dd`, the same file as Midwinter 1 / 2 and Populous 2, so the HAGA file patches of Midwinter 2 (no grey fade, chunked cache at 4 MB and more) apply as file patches. `RUNME.TOS` unpacks with `tools/pp_depack.py` (`work/scratch/runme_unp.tos`: text `$404e`, data 22, bss 111206). `FILES/POM` is 409,600 bytes ([INFERENCE] a 10-sector, 1-side, 80-track image, the size of Midwinter 1's); `POP` is the save disk (PP's README).

## Path to the game

PP's hardware screen (hold Space: a tap of one VBL is not seen), Bullfrog logo, the book menu (TUTORIAL / CONQUEST / CUSTOM), CONQUEST, START GAME. No manual question on this path. `tools/populous.py` `boot_to_game()` replays it (CONQUEST at screenshot (641,407), START GAME at (254,408), home (96,58)).

## Memory map in play (dumps `work/dumps/g0.bin`, `busy.bin`)

| Range | What | Evidence |
|---|---|---|
| `$a84e` | `_membot` | `$432` |
| `$af40`-`$21100` | game code (C main `$af44`, loop `$b54e`) | listings |
| `$21480`-`$3d58e` | data: strings, tables, font `$2364a`, maps, peeps | `algorithms.md` |
| `$3f4e0` | supervisor stack in play | `r` |
| `$4f500`, `$57200` | the two screen buffers | `$3c510`, `$3c50c` |
| `$5eefc`-`$77fc7` | zero in both dumps (100 KB) | zero-run scan |
| `$78000` | clean background, 32,000 bytes | `$3b016` |
| `$80000` | `phystop` as PP sets it (`$42e`), `$436` = `$78000` | dump |
| `$81000`-`$b1d3f` | HAGA chunk cache | pp-haga-conversions skill |
| `$b1d40`-`$cfc36` | zero in both dumps (122,615 bytes) | zero-run scan |
| `$d0000`-`$dffff` | PP's resident copy: `$70` = `$d018e`, bus-error stubs `$d0578`, `$400` = `$dac2a` | vectors in the dump |
| `$f8000` | HAGA resident service (phystop of the machine - `$8000`) | skill |

Vectors in play: `$70` = `$d018e` (runs the VBL queue; the game's routine `$16d70` is in it), `$118` = `$1ffc8` (the game's ACIA handler), `$134` = the sample player `$1717e` while a sound plays.

Free RAM for a payload is **not proven**: the two zero runs are candidates (`$b3000` as in Midwinter 2 lies inside the second). The pattern test (fill, boot, play into a busy game, save and load through `POP`, compare) is the first task of the delivery slice in `PLAN.md`.

## Other machines

Hatari TT, 4 MB, GEMDOS drive, EmuTOS and TOS 3.06: PP's hardware screen appears ("Machine: TT"), then a white screen and an endless pair of bus errors (`reading $ffff8a00, PC=$3b3422`, `writing $fffffc3b, PC=$3b4474`); with TOS 3.06 Hatari then stops answering. Shots `work/shots/boot_tt_0.png`-`3`. Not followed up (ACSI image route, Falcon, Mega STE not tried in this pass).

## Corrections to the first draft

- "Screen base `$40000`" was a misreading of `$ff8200` = `00 04 00 f5`: the base is `$4f500`, and there are two buffers that flip.
- "A keypress never leaves the hardware screen" style problems are the tap length: the game (and Populous 2) read the key once per pass or per VBL, so hold it.
- The copy protection is not fully removed in PP's build: `baseline.md`, "The copy-protection trap".
