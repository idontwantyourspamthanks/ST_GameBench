# Populous: plan

Study: `work/notes/boot.md`, `baseline.md`, `hotpaths.md`, and `work/notes/bullfrog_family.md`. No patches yet.

Patch delivery: the Midwinter shape. HAGA is the same file, so the fade and 4 MB chunk-mode edits apply as HAGA file patches. The payload address comes from a free-RAM pattern test; `$B3000` is not assumed. Screen is `$40000` and the game runs from about `$10000` to `$22000`.

## Ranked

Gains are guesses from the one opening-map profile, marked as such.

| # | item | from | gain (guess) | risk |
|---|---|---|---|---|
| 1 | `$16eaa` sprite blit: STE blitter, or a pre-shifted cache on ST | `p4_spr`, adapted | the blit is ~60% of non-wait work; the opening scene spends most of its time waiting, so the fps gain is small until a scene is CPU bound | pixel gate; blitter chunks per `buserr.md` |
| 2 | keys and tooltips | `qol_keys`, `pm_tooltip` | none | needs the click words and a real blank rect; the book page has no blank band in the one shot |
| 3 | fixed tick | `tick_*` | none on the opening scene (0.5 loop/s at 8 and 16 MHz, and that loop is waiting on the mouse flag) | do not start until a walker rate is measured on a busy map |
| 4 | YM sample player | `snd_*` | unknown; no player found | find it before writing anything |

## Slices for implementation

- A. Free-RAM pattern test, payload, trampoline, HAGA file patches. No gameplay patches.
- B. Map the click latch and the icon rectangles; draft keys stay in `bullfrog_family.md` until then.
- C. `$16eaa` blitter blit, with the chunk limit, gated pixel-identical.
