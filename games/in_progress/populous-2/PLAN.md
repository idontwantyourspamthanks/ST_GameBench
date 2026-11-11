# Populous 2: plan

Study: `work/notes/boot.md`, `baseline.md`, `hotpaths.md`, and `../populous/work/notes/bullfrog_family.md`. No patches yet.

Patch delivery: the Midwinter shape. HAGA is the same file. The game needs 2 MB (1 MB bus-errors at `$ffff8e21`, PC `$13968`). The intro polls `$fffc02` while TOS still owns `$118`, so a harness cannot leave those screens with a keypress; the boot notes record the debugger write that works. Fixing that poll is a reasonable first patch and it is not a Powermonger port.

Screen in play is `$f0000`. VBL is `$2e9b4`.

## Ranked

| # | item | from | gain (guess) | risk |
|---|---|---|---|---|
| 1 | the unrolled stride copy at `$2f4fe` (42% of the opening scene) | `p6_cpy`, adapted, and only if the copy is a plain memory move | up to that 42%, less the blitter setup | pixel gate; chunk the blitter so the ACIA is serviced (`buserr.md`) |
| 2 | keys and tooltips | `qol_keys`, `pm_tooltip` | none | tooltip rect (0,0)–(319,7) is measured on one view only; click words unknown |
| 3 | let the intro see a real keypress | none | the harness can boot unaided | the poll is the game's; change only the read |
| 4 | fixed tick | `tick_*` | none while a pass fits in one VBL (193 vs 192 passes per 200 VBL at 8 and 16 MHz) | measure a full map first |

## Slices

- A. Delivery and the free-RAM test at 2 MB and 4 MB.
- B. Intro keyboard: stop TOS consuming the byte the intro polls, or point the poll at the TOS buffer.
- C. Icon rectangles and click words, then keys. Tooltip text in ST rows 0–7.
- D. `$2f4fe` copy, blitter in short chunks, pixel gate.
