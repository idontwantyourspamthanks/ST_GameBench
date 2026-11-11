# Populous 2: plan

Study (second pass, 2026-11-11): `work/notes/baseline.md`, `hotpaths.md`, `algorithms.md`, `ui.md`, and `../populous/work/notes/bullfrog_family.md`. The first draft never reached the game; its plan (stride copy at `$2f4fe`, intro keyboard patch, tooltip rows 0-7 full width) is withdrawn. No patches exist. Harness: `tools/populous2.py`. Snapshots: `game_start`, `busy1` (2 MB STE).

Facts the plan rests on: frame-coupled (6.0 turns/s busy, 8.9 at the start, 8 MHz; 2.05x at 16 MHz); a busy frame is 8.1 VBLs: 47% drawing, 32.5% world logic, 8.4% interrupts.

## Decisions (user, 2026-11-11)

- Tooltip: the black sky (120,0)-(255,7), second line (136,8)-(247,15), the game's font, as in `work/shots/tt_candidate_top_text.png` (approved as shown).
- Fixed tick: 6.25 turns per real second (8 VBLs at 50 Hz).
- Floppy build wanted as well as HD (the game fits one disk).

## Delivery findings (2026-11-11, `work/notes/delivery.md`)

- Done: `tools/pop2patch.py`, payload `$80000-$87FFF`, free RAM proven at 2 and 4 MB, `pop2_credit` (main menu), HD and floppy builds (720K, one disk), `tools/package.sh`.
- Works: STE 2/4 MB, Mega STE 4 MB (TOS 1.62, 50 Hz), Falcon 4 MB (TOS 4.04, 50 Hz), the floppy build on STE 2 MB.
- **60 Hz is broken in the stock game**: "SORRY PAL MACHINES ONLY" (`$1836`/`$183c`), and with that branch forced (`pop2_ntsc`, `default: no`) the game draws garbage and dies; the same on the TT (60 Hz) with zero patches. Making it run at 60 Hz is a new work item, with the fixed tick (item 5).
- **In-game SAVE/LOAD is broken in PP's build** (bus error; PP's README says so): PP replaced the disk layer at `$36efc` with a stub. HAGA's statesave works on HD only. Fixing it means routing the game's save through PP's file service (`pop2_save_a/b` are a partial start, `default: no`). New work item.

## Ranked work

Gains are shares of the busy frame at 8 MHz and [INFERENCE] unless a measurement is named; days are [INFERENCE].

| # | Item | Ports from | Gain | Risk | Days |
|---|---|---|---|---|---|
| 1 | **Delivery** at 2 MB and 4 MB: payload, trampoline, HAGA file patches, free-RAM pattern test (`$7b37f`-`$f7fff`, `$167cfa`-`$1d89f7` are zero in the busy dump), credit line. Decide whether to skip the manual question. | Midwinter 2 tool; shared with Populous | none | the game sits at `$2300`-`$48000`, far from Midwinter's layout; 1 MB is out | 3 (1.5 after Populous) |
| 2 | **Sprites**: pre-shifted cache / STE blitter. | `p4_spr`, portable (site bytes identical at `$213b0`) | most of 10.0% | low-medium; blitter chunks and `p4_clamp` per `buserr.md` | 2 |
| 3 | **Pointer** only when something changed. | `p4_ptr`, adapted | 6.9% measured cost | low | 1 |
| 4 | **Land score**: remove the `divu #$34` (1.2%), then study `$252d8` (7.3%). | new | 1-5% | low for the divide; unknown for the scan | 2 |
| 5 | **Fixed tick** (VBL counters `$392d8` / `$392d4`). Rate is the user's choice (stock 8.9 -> 6.0 turns/s); proposal 6.25 per second (8 VBLs at 50 Hz). | `tick_*` design | constant speed | medium: link games, the click-age test at `$22f84` counts turns | 4 |
| 6 | **Tooltips** in the black sky at the top, (120,0)-(255,7), built from category and slot, showing the game's existing keys. No new keys until command `$72` is understood. | `pm_tooltip`, adapted | none | low; other landscapes and zoomed views unchecked | 2.5 |
| 7 | **Cached terrain**. | new, shared design with Populous | up to 20% in a static view | medium | 5 |
| 8 | IKBD clamp, triple buffering, DMA sound. | `p4_clamp` portable; `p7_triple`, `snd_*` adapted | small | low / low / medium | 0.3 / 1.5 / 3 |
| 9 | Other machines (TT, Falcon, Mega STE). | | | untested | 2+ |

Still to study before items 4-7 are firm (one read-only slice, about 2 days): landscape generation, walker pathing, effects, the computer player, command numbers `$0e`-`$78`, the zoomed views, a scene with effects running.

## Delegation slices

- A. Delivery (after or together with Populous slice A; same HAGA patches).
- B. "P2 world code" study, then item 4.
- C. Display: items 2, 3, then 7.
- D. Timing: item 5.
- E. UI: item 6.
