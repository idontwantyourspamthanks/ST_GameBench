# Populous 2: algorithms (what was read), and better ones with the identical result

Second pass, 2026-11-11. Dump `work/dumps/busy1.bin`. Populous 2 is hand-written assembly (no C frames), a rewrite of Populous 1's design: compare `../../populous/work/notes/algorithms.md`. This pass reached the game late; items not read are listed as such, not guessed.

## Data (from the listings)

| What | Where | Shape |
|---|---|---|
| map | `$3979e` | 64 x 64 cells x 4 bytes, index `((y << 6) + x) * 4` (`$1df6a`): byte 1 = tile type, bytes 2-3 = offset of the first object on the cell (`$25302`), byte 0 not identified |
| tile flags | `$3697a` | word per tile type (`$252ee`: walkable / flat bits), `$36b7a` byte per type |
| people | `$3ff1a` | 400 x `$34` bytes: +0 kind, +1 building level, +2 next object on the cell, +6 x, +8 y, +`$c` owner + 1 (0 = free), +`$16` state (jump table `$2311c`) |
| effect objects | `$4505a` | same record, state table `$26668` |
| third list | `$3e7aa` | same record (`$27faa`), not identified |
| players | `$470fe` | 2 x `$13a` bytes: +0 long (population or manna, grows), +`$70` effect availability bytes |
| command record | `$473a6` + 10 x player, pointer `$473c4` | +1 command, +2.. arguments |
| turn | `$3979a` | long |
| view | `$3e79e`, `$3e7a0` | 0..56 each; view size `$39766` (8 = normal, 1..`$17`) |

## Rendering

Same design as Populous 1: every pass copy the clean background (`$1e7b2`), then draw the terrain back to front as masked tiles, then sprites; the pointer lives in the VBL. Differences read in the code:

- The background copy is a `movem.l` loop (152,700 cycles) instead of `move.l/dbra` (257,000 in Populous 1).
- Tiles are cut into strips of 16 x 8 pixels addressed through offset lists (`(a3)+`), so `$1e15e` blits two half-strips per call and skips empty halves (`beq` to the one-sided loops at `$1e1c0`, `$1e1fa`). 933 rows per frame against Populous 1's 2,184.
- Parts of the frame are copied from the clean background with `move.l (a0)+,(a1)+` runs in `$1df44` (edge columns).
- Sprites: `$2122e`, 32 pixels wide, `ror.l` shift of mask and 4 planes per word, clipped variants; byte-identical in form to Powermonger's (`bullfrog_family.md`).

Better, identical pixels: the cached-terrain scheme of Populous 1 (`algorithms.md` there, change A) applies unchanged in principle: 62-64 of 64 view cells did not change between consecutive turns. Gain [INFERENCE] most of 19.8% + 1.8% in a static view. Risk: medium (animated tiles: 0-2 view cells change their tile byte per turn; the same sprite / later-tile overlap rule). Not read: how the strip lists are built, the zoomed views (`$39766` != 8, `$1e75e` / `$1e300`).

## World

- `$2309a`: per player bookkeeping, then every used people record through its state routine.
- Land score: `$25168` (per building) -> every 4th turn `$251d8`, which scans rings of 1, 8, 16 and 24 cells (`$252d8`, offsets from the list at `$2549a`), counts usable cells, picks the building level from the table `$2547e` and turns the collected cells into fields. Populous 1 does the same thing with 17 cells every turn; here it is staggered by `(record index & 3) == (turn & 3)`.
- Commands go through a per-player record (`$473c4`), as in Populous 1.

Better, identical state:

- The index for the stagger is computed with `divu #$34` on every call (1.2% of all cycles): table or carried index, exact.
- `$252d8` is 7.3% on its own: 457 ring scans per frame at about 200 cycles per cell visited. Not analysed further; a rewrite needs the same per-cell side effects (it converts walkers standing on the cell, `$25318`).

Not read in this pass: landscape generation, walker path choice, the effects, the computer player. They are the delegation slice "P2 world code" in `PLAN.md`.

## Per-frame work with unchanged inputs

| Work | Share | Evidence |
|---|---:|---|
| pointer restore + draw every VBL | 6.9% | 12.2 per frame; no input in the run |
| all terrain strips + full background copy | 33.4% | 0-2 of 64 view cells changed per turn |
| manna marks: divide per effect + pixel plots | 0.7% + part of 2.8% | depends on manna and costs only [INFERENCE: not traced] |
