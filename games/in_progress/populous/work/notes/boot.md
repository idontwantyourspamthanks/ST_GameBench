# Populous: boot

Machine: 1 MB STE, TOS 1.62, Hatari GEMDOS drive C: = `originals/POPULOUS`. HAGA md5 `b34607ed9baecc5982a5a01ecaf5a3dd`, the same file as Midwinter, so the HAGA file patches (no grey fade, keep chunked mode at >= 4 MB) apply as file patches. RUNME.TOS unpacks with `tools/pp_depack.py` (text `$404e`, data 22, bss 111206). The Midwinter-style delivery (payload appended to RUNME, trampoline over PP's patcher tail) is the right shape. Free RAM was not pattern-tested; do not reuse Midwinter's `$B3000` without that test. Screen base in play was `$40000` (`$ff8200` = `00 04 00 f5`), so the low 256 KB is not all free either.

## What the boot showed

Space on the hardware screen, then the Bullfrog logo, then the book menu (TUTORIAL / CONQUEST / CUSTOM). A click during the black load is lost. CONQUEST opens a second book page; START GAME enters the map. No manual question appeared on this path (PP's LOG.TXT says "Deprot"). Screenshots: `work/shots/b00.png` to `d3.png`.

`boot_to_game()` in `tools/populous.py` replays the clicks that worked: CONQUEST at screenshot (641, 407), START GAME at (254, 408), `home_xy` (96, 58).

## In play

Dump `work/dumps/genesis_start.bin`, snapshot `work/snapshots/genesis_start.sav`.

- PC `$181ec` (`add.w d3,d4`), inside the `$18000-$22000` game.
- VBL vector still TOS: `$70` = `$000d018e` (`addq.l #1,$466` at `$d0192`).
- ACIA vector is the game: `$118` = `$0001ffc8`.
- `$ff8201` did not change in 250 VBL (0 flips). One screen at `$40000`.
- Marker: `$1d02a` is `30 39` (`move.w $3d566,d0`) and `$ff8201` = `$04`.
