# Populous: plan

Study (second pass, 2026-11-11): `work/notes/boot.md`, `baseline.md`, `hotpaths.md`, `algorithms.md`, `ui.md`, `bullfrog_family.md`. No patches exist yet. Harness: `tools/populous.py` (`busy_scene()` builds the benchmark scene). Snapshots: `genesis_start`, `busy_castles`, `busy_quake_volcano`.

Facts the plan rests on: the world is frame-coupled (3.2 turns/s busy, 8.7 at the start, on 8 MHz; 2.1x at 16 MHz); a busy frame is 15.7 VBLs, 47% world logic, 39% drawing, 7.4% pointer.

## Ranked work

Gains are shares of the busy frame at 8 MHz and are [INFERENCE] unless a measurement is named; days are [INFERENCE].

| # | Item | Ports from | Gain | Risk | Days |
|---|---|---|---|---|---|
| 0 | **Protection trap**: make the `$24` check at `$ee16` pass. Without it the game falls into Armageddon once 19 peep slots are used. | `pm_noprot` (idea) | playable game | none; one branch byte, verify on a cold boot that towns grow | 0.5 |
| 1 | **Delivery**: MW2-style payload in RUNME, trampoline over PP's patcher tail with verify-then-apply, HAGA file patches (no fade, chunked cache at 4 MB), free-RAM pattern test of `$b1d40`-`$cfc36` and `$5eefc`-`$77fc7` through a busy game and a save / load on `POP`, release credit line. | Midwinter 2 `mw2patch.py` | none | PP's `$d0000` resident copy and the 4 MB whole-image cache are new ground | 3 |
| 2 | **Land score** `$18244` + `$181d6` rewritten with identical outputs. | new | about 30% (they are 33.0%) | low; gate: outputs for every cell and owner on several dumps, then turn-by-turn RAM equality | 2 |
| 3 | **Pointer** only when something changed. | `p4_ptr`, adapted | 7.4% measured cost | low; Powermonger's gate | 1.5 |
| 4 | **Background copy** with `movem`. | `p6_cpy` idea, CPU only | 4% busy, 10% idle (257,000 -> about 153,000 cycles) | low | 0.5 |
| 5 | **Multiply helper** `$20796` fast path. | new | 2% | low | 0.5 |
| 6 | **Fixed tick** in real time (VBL counter `$16d2a`, 50 / 60 Hz aware, catch-up without drawing, render-only passes on fast machines). Rate is the user's choice: the stock game has no single speed (8.7 -> 3.0 turns/s); after items 2-5 an 8 MHz machine can hold about 5 turns/s in the busy scene. Proposal: 5 per second. | `tick_*` design | constant speed | medium: two-player link games exchange commands per turn (exclude or test), Armageddon and effects must stay per turn, water animation is per pass (`$3b260`) | 4 |
| 7 | **Keys** (table in `ui.md`) and **tooltips** at the top of the book pages (rect to be confirmed by the user from `work/shots/tt_candidate_*.png`). | `qol_keys`, `qol_keys2`, `pm_tooltip`, adapted | none | low: phantom keys from typed text (Powermonger's fix applies) | 3 |
| 8 | **Cached terrain** (dirty-rectangle redraw). | new | up to 20% in a static view | medium: exact sprite / tile overlap, every writer of the clean background must invalidate | 5 |
| 9 | IKBD position clamp. | `p4_clamp`, portable | none | none | 0.3 |
| 10 | DMA sound for the effect samples (STE). | `snd_*`, adapted | 5% while a sound plays | medium | 3 |
| 11 | Triple buffering. | `p7_triple`, adapted | small at 8 MHz | low | 1.5 |
| 12 | Other machines: Mega STE 16 MHz, TT, Falcon (the TT did not boot in Hatari with a GEMDOS drive: `boot.md`). | Powermonger `tt_ptr`, cache-off | | unknown | 2+ |

Floppy version: the base is HD-only (PP's conversion of the STX). A floppy build needs the original disk image and the protection handled; not planned until the HD build is done (user to decide).

## Delivery plan

HAGA shape as Midwinter 2: payload appended to `RUNME.TOS`, copied to free RAM by a stage in RUNME's stack phase, boot patches applied by a trampoline that replaces PP's patcher tail `jmp <entry>` after comparing every site's original bytes, marker word, HAGA patched as a file. To prove first: the payload address (candidates above), that the game's file loads (worlds, save disk `POP`, sound) do not cross it, and the 4 MB behaviour with PP's cache.

## Delegation slices

- A. Delivery + item 0 + pattern test + cold-boot checks at 1 / 2 / 4 MB (owner of the patch tool).
- B. Logic: items 2 and 5, with the equality gates (needs only snapshots and live patching).
- C. Display: items 3, 4, then 8.
- D. Timing: item 6, after B and C land; owns the world-rate gate.
- E. UI: item 7 (needs the user's choice of tooltip rect and font).
- F. Machines: item 12, last.
