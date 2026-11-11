# Populous 2: hot paths

In-play profile: `baseline.md`. The 42% under `$2f4f4` is an unrolled block the disassembler decodes as:

```
2f4fc  addq.l  #8, a0
2f4fe  move.l  $2(a0), -$9e(a0)
```

repeated, then `dbra d0,$2f4f6` at `$2f596`. PC sat in this block (`$2f52c`) while the query panel was up. It is a stride copy, not a sprite and not a triangle fill. No `$ff8800` and no `$ff8a00` literal in the 2 MB dump.

The flyover before the game (profile of 300 VBL, 41.8M cycles, 90% in `$2ea52`) is the same idea done by rotating words:

```
2ea5e  move.w (a0), d0
2ea60  ror.w  #1, d0
2ea64  andi.w #$8000, d1
2ea68  andi.w #$7fff, d0
2ea6c  move.w d0, (a0)
2ea6e  addq.l #8, a0
```

with `moveq #$57,d7` at `$2ea5c`. That is the intro scroll, and it runs once per VBL until `$fffc02` reads `$39`.

Top of the in-play profile, roles:

1. `$2e9aa` — wait for the VBL flag. 50%.
2. `$2f4fe` — unrolled stride copy. 42%.
3. `$2f480` — the pass that calls it and polls space. 4%.
4. `$2f780` — 1.6%, not disassembled.
5. `$e04400` — TOS. 0.6%.

Nothing else is above 0.3%.
