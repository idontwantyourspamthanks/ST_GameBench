# Bullfrog family: Powermonger, Populous, Populous 2

Powermonger evidence is its own notes. Populous evidence is `games/in_progress/populous/work/notes/`. Populous 2 evidence is `games/in_progress/populous-2/work/notes/`. HAGA is byte-identical in all three PP conversions that have it (md5 `b34607ed…`); Powermonger is not a HAGA game.

## Portability of the Powermonger patches

| patch | Populous | Populous 2 |
|---|---|---|
| `p4_ptr` | not portable. VBL is still TOS (`$70`=`$d018e`). The pointer is drawn by the frame's sprite blit, not by the VBL. | not portable. The VBL is three instructions at `$2e9b4` (`st.b $345bb`, `addq.w #1,$345bc`, `rte`). |
| `p4_spr` | adapt. `$16eaa` is a `ror.l d5` / `and.w` / `or.w` masked blit, ~60% of non-wait cycles, and there is no blitter literal in RAM. Same idea as Powermonger's sprite blit, different code, so the blitter HOG chunk limit in `buserr.md` applies if a blitter version is written. | not the hot path. The in-play cost is the unrolled `move.l` copy at `$2f4fe` (42%). No blitter literal. |
| `p6_slope`, `p6_tri`, `p6_cpy` | not portable. No triangle setup and no 32,000-byte window copy. The screen base `$40000` never changed in 250 VBL. | not portable. The copy is a stride shift of the game's own buffer, not a 3D window. |
| `snd_*` | no timer sample player found. The only `$ff8800` site in the profiled RAM is `$16418`, a port-A update. | no `$ff8800` literal in the 2 MB dump. |
| `tick_*` | not portable as code. The loop measured 2 calls of `$180f4` per 200 VBL at 8 and at 16 MHz, because it spins on `$3d566` until the ACIA handler clears it. World units per second were not measured. | the loop is already one pass per VBL (193 and 192 passes per 200 VBL at 8 and 16 MHz). A tick patch only helps a scene whose pass overruns one VBL. Not measured on a busy scene. |
| `qol_keys`, `qol_keys2` | the mechanism (write the click words the mouse path writes) is sound, but the click words and the icon table were not found. Keys typed at the book menu must not be replayed on the map: same bug as `phantom_click.md`. | same. The game also polls `$fffc02` itself, so a key injector has to coexist with that poll. |
| `pm_tooltip` | the book page in `d3.png` is not a flat colour; no blank band came out of a per-row average. The rect is not known yet. | in `skip1.png` screenshot rows 0–15 of the picture are one colour, `(34,34,102)`, all 640 pixels. That is ST rows 0–7, x 0–319, in that one view. |
| `p4_clamp` | adapt only. Populous parses the IKBD packet itself at `$16c96` (`tst.w $3d566`, buttons in `$2478a`, position copied from `$24786`/`$24788` to `$3c556`/`$3c55a`). A bad position can be dropped there. | the game reads `$fffc02` directly and the ACIA vector is still TOS. Different path. |
| `p7_triple` | not as-is. One buffer, and `$ff8201` did not change. | not as-is. Screen at `$f0000`; no flip was observed. |

Nothing in either Populous profile suggests a new Powermonger change. Powermonger's costs (triangle fill, window copy, VBL pointer, YM interrupt) are not these costs.

## Tooltip areas

- Populous 2, query-panel view: ST rectangle (0, 0)–(319, 7), flat. One 6-pixel text line fits; an 8-pixel font does not. Other views were not checked.
- Populous 1: not located. The parchment in the one in-play shot has no blank row.

## Draft keys

Not wired to anything. The icon under the pointer was not hit-tested, and neither game's click latch was found. Labels follow the icons visible in the shots, in the Powermonger style (one letter, the letter does the click).

Populous, from `d3.png`: S shield, K knight, P ankh, B book, M magnifier, H house, C compass, ? help. The divine effects (flood, swamp, volcano, earthquake, armageddon) are not on that screen, so they get no key until the icon page that holds them is found.

Populous 2, from `skip1.png`: the query panel and the small icon column. No key letters until each icon has a rectangle.

## What to build first

1. Finish the UI map (click words, icon rectangles) before any key or tooltip patch.
2. Populous sprite blit (`$16eaa`) is the only performance item with a measured share.
3. Populous 2's stride copy (`$2f4fe`) is the only performance item there, and it is a copy, so a blitter version has to be chunked the way `p6_cpy` was.
4. Timing patches wait until a busy scene shows the 8 MHz pass missing VBLs. The opening scenes do not.
