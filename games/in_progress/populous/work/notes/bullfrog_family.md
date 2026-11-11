# Bullfrog family: Powermonger, Populous, Populous 2

Second pass, 2026-11-11; it replaces the first draft, most of whose table was wrong (it never reached Populous 2's game, and it profiled Populous 1's GAME LOST dialog). Evidence: Powermonger `games/in_progress/powermonger/work/notes/` and `work/dumps/get_men.bin`; Populous `work/notes/` here and `work/dumps/busy.bin`; Populous 2 `../../populous-2/work/notes/` and `work/dumps/busy1.bin`. HAGA is byte-identical in both Populous conversions (md5 `b34607ed…`); Powermonger is not a HAGA game.

## The three games side by side

| | Powermonger | Populous | Populous 2 |
|---|---|---|---|
| code | assembly | compiled C + assembly blits | assembly |
| world step | 1 per pass | 1 per pass (`$db96`) | 1 per pass (`$22f9c`) |
| pacing | VBL wait at the loop top | VBL wait inside the flip (`$16f48`) | VBL wait at the loop top (`$12548`); 9-VBL floor only with the pointer at (0,0) |
| stock world rate, 8 / 16 MHz | 3.8 / 7.86 per s | start 7.3-8.7 / 16.4; busy 3.2 / 6.8; hilly 3.0 / 6.4 | start 8.5-8.9 / 16.6; busy 6.0-6.1 / 12.4-12.5 |
| verdict | coupled | **coupled** (2.1x) | **coupled** (2.05x) |
| frame, busy, 8 MHz | 13-21 VBLs | 15.7 VBLs | 8.1 VBLs |
| drawing | triangles into a window, window copy | full background copy + 91 masked tiles | full background copy + 191 masked strips |
| pointer | restore + draw every VBL | the same code | the same code |
| commands | click words | 3 bytes in a player record | bytes in a player record |
| icon hit test | line tables | iso cells, computed | iso cells, computed |
| keys in the original | 4 cursor keys | keypad scroll | F1-F6, 1-5, keypad, and every other key is sent as a command |

## Shared code (byte patterns found in all the dumps)

Search: the hex pattern at even addresses in the three dumps (session script; `??` = any byte).

| Routine | Pattern | Powermonger | Populous | Populous 2 |
|---|---|---|---|---|
| IKBD reply parser | `0c0000f6 65.. .... 0c0000f7 66` (`cmpi.b #$f6,d0 / bcs / cmpi.b #$f7,d0 / bne`) | `$18f2` | `$20000` | `$1c76` |
| packet store | `123c0005 9239........ 4881 41f9........ 11801000` | `$1924` | `$20020` | `$1ca8` |
| VBL pointer restore | `28de 28de 0c460090 6600 0006 28de 28de d8c6 51cf ffec` | `$13ae` | `$16e08` | `$1a38`, `$1b78` |
| pointer row clip | `044200b8 6f00 .... 9e42` | `$13d4` | `$16e30` | `$1a5e` |
| pointer shift + merge | `eab8 eab9 eaba eabb eabc 3cd4 c154 835c` | `$1472` | `$16ebe` | not this form |
| IKBD poll `$0d` per VBL | `1d7c000d0002` / `11fc000dfc02` | `$1380` | `$16dd0` | `$1a0a` |
| flip | `e048` + `move.l d0,$ff8200` | `$1892` | `$16f32` | `$1c16` |
| VBL flag wait | `4a79........ 67f8 4e75` | `$1870` | `$16f48` | `$1bf4` |
| YM sample interrupt | `e748 223b00.. 3[04]3b00..` + `movep.l d1` | `$1af4e` | `$1719c` | `$2aa6a` |
| masked sprite, `ror.l` per word | `76ff 3619 e0bb 7800 3819 e0bc` | `$123b2`.. (7 variants) | absent (older `e0b9 e0ba e0bc..` form at `$169dc`) | `$212ba`.. (7 variants) |
| masked tile row | `381e 3c10 cc44 8c5e 30c6` / `3018 3216 c240 8258 3cc1` | absent | first form `$14352` | second form `$1e172` |

## Portability of the Powermonger patches

| Patch (Powermonger site) | Populous | Populous 2 |
|---|---|---|
| `p4_ptr_a/b` (`$1390` `2039 0001c49a`; `$14c4`) | **adapted**: same routine; restore entry `$16dea` (`2039 00016f12`), VBL body `$16d78`-`$16d84`. Worth 7.4% of the CPU. | **adapted**: restore `$1a1a` (`2039 0000202e`), IKBD wait `$1a02` has Powermonger's own site bytes `0838 0001 fc00`. Worth 6.9%. |
| `p4_spr` (`$124a8` `7278 4401 5342`) | **no**: different sprite code and only 6 sprites per frame (1.8%). | **portable**: the site bytes `7278 4401 5342` are at `$213b0`; the routine has the same 7 variants. 10.0% of the frame goes through it. |
| `p6_slope`, `p6_tri` | **no**: no triangles. | **no**. |
| `p6_cpy` (blitter window copy) | **adapted to `movem`**, not the blitter: the 32,000-byte copy `$14a40` is `move.l/dbra` (10.2%); Populous 2's `movem` loop does the same job in 59% of the cycles. | **no**: already `movem` (`$1e7c6`). |
| `snd_*` (DMA instead of the timer-A YM player) | **adapted**: same player technique (`$1717e`, rate by timer data from `$16ffc`), different stream format (pointer, index, length, repeat). Costs 5.4% only while an effect sound plays. Low priority. | **adapted**: player at `$2aa4e`; 0 cycles in both profiles. Lowest priority; not studied. |
| `tick_*` | **design yes, code no**: hook the C loop at `$b7f0`-`$b806` (world) and split passes; VBL counter `$16d2a`. Needs the logic fix first (below). | **design yes, code no**: world calls at `$12746`-`$12786`, VBL counter `$392d8`, and the game's own per-pass VBL count `$392d4`. |
| `qol_keys`, `qol_keys2` (`$199c` `13c0 0001c490`) | **adapted, simpler**: a key writes the command bytes / mode word (`ui.md`); the key store is the same instruction at `$20086` (`13c0 0002005f`). All letters free. | **mostly not needed**: the game has keys for effects, scrolling and zoom, and sends every other key as command `$72`; the store is at `$1d14` (`13c0 000392ec`). |
| `pm_tooltip` | **adapted**: hit test = the game's iso-cell arithmetic; text with the game's masked 8 x 8 font (`$180f4`, font `$2364a`) or our own 4 x 6; area = top of the book pages. | **adapted**: iso cells; opaque 8 x 8 font (`$168b6`, `$37c84`); area = black sky at the top. |
| `p4_clamp` (`$1942` `13f9 0001c491 0001c48f`) | **portable**: the same instruction at `$2003e` (`13f9 00020061 0002478a`). Needed as soon as anything holds the bus (blitter) or masks interrupts longer. | **portable**: `$1cc6` (`13f9 00002025 00002023`). |
| `p7_triple_*` (`$13090` `jsr $1870`, `$1386c` `jsr $187a`) | **adapted**: wait and flip are one routine (`jsr $16f16` at `$b940`); a third 32,000-byte buffer fits the zero run `$5eefc`-`$77fc7` if the pattern test confirms it. Gain small at 8 MHz. | **adapted**: the same two call sites exist (`$12548 jsr $1bf4`, `$1278c jsr $1bfe`). |
| `pm_noprot` | **new patch, required**: the `$24` key check at `$edec`-`$ee16` is live in PP's build and starts Armageddon once 19 peep slots are in use (`baseline.md`). | optional: the manual question is shown but accepts anything. |
| `tt_ptr`, cache-off for 68030 | [INFERENCE] likely needed (pointer drawn in the VBL into the shown buffer, as in Powermonger); the TT did not boot in this pass. | the same, not tested. |

## What Populous needs that Powermonger did not

- The land-score rewrite (`algorithms.md` D1): 33% of a busy frame, exact.
- The multiply-helper fast path: 3.0%.
- The cached terrain (both Populous games): the largest remaining render item, medium risk.

## Tooltip areas

- Populous: the book pages at the top, (84,0)-(213,7) = 16 game-font characters, optional second line (100,8)-(171,15); shots `work/shots/tt_candidates_rects.png`, `tt_candidate_A_text.png`, `tt_candidate_B_two_lines.png`, `tt_book_top_zoom4.png`.
- Populous 2: the black sky at the top, (120,0)-(255,7) = 17 characters, optional (136,8)-(247,15); shots `../../populous-2/work/shots/tt_candidates_rects.png`, `tt_candidate_top_text.png`.

## Keys

Populous: `ui.md` (table and `work/shots/ui_left_panel_keys.png`). Populous 2: keep the game's own keys (`../../populous-2/work/notes/ui.md`).
