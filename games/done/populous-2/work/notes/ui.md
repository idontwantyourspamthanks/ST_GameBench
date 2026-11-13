# Populous 2: mouse, clicks, icons, keys, text, tooltip area

Second pass, 2026-11-11. Dump `work/dumps/busy1.bin`.

## Mouse and buttons

Same IKBD code as Populous 1 and Powermonger (`bullfrog_family.md`): absolute mode, `$0d` sent every VBL (`$1a0a`), reply parsed at `$1c68` into buttons `$2023`, position `$393fa` / `$393fc`. The VBL (`$18fa`) runs a button state machine through the jump table at `$1936`:

| Word | Meaning |
|---|---|
| `$39402` | left click latched (cleared by whoever handles it) |
| `$39404` | right click latched |
| `$39406`, `$39408` | left, right held |
| `$393f6`, `$393f8` | position at the click |
| `$3940a` | turn at the click; `$22f84` drops a latch older than the current turn |

Keys: `$392f4` is a 128-byte key-down table indexed by scan code (`st` / `sf` at `$1d0a` / `$1cfc`), `$393f4` counts keys down, `$392ec` holds the last make code. PP's exit / save-state hook sits in the release path (`$1cf8  jmp $2ac.w`).

## Click dispatch (`$12cca`-`$13340`, normal view only)

Iso-cell hit tests, no rectangle tables: `u = dy + dx/2`, `v = dy - dx/2` from an origin, then `>> 4`.

| Area | Origin (x, y) | Cells | Action |
|---|---|---|---|
| minimap | (`$44`, 4) | 0 <= u, v < 64 | left: step the view towards it; right held: view = (u-3, v-3) |
| scroll pad | same, (u+6)/25, (v+6)/25 in 0..2 | 3 x 3 | scroll one cell |
| command strip | (`$13d`, `$8c`) | u>>4 = 0, v>>4 = 1..6 (jump table `$12e0c`) | 1: command `$76`; 2: left = pointer mode `$c`, right = `$14074`; 3: command `$12`; 4: `$14`; 5: `$0e`; 6: left = command `$10`, right = view to the leader |
| category row | (`$3b`, `$89`) | v>>4 = 0, u>>4 = 0..5 | effect category (`$39794` = 2 x n), `$134fc` |
| effect row | (`$2a`, `$97`) | v>>4 = 0, u>>4 = 0..5 | `$13bd2(n)`: select effect n of the category; with the Help key down (`$39356`) `$1695a` shows the game's own help text |

A command is a byte at +1 of the record `$473c4` points to (arguments at +2, +3), as in Populous 1; pointer mode / armed effect is `$47372`. The names of commands `$0e`, `$10`, `$12`, `$14`, `$76` were not established in this pass.

## Keys the game already has (`$1279e`-`$12cca`)

| Key (scan) | Action |
|---|---|
| F1-F6 (`$3b`-`$40`) | effect category 0-5 |
| 1-5 (`$02`-`$06`) | effect 1-5 of the category |
| keypad ( ) / * (`$63`-`$66`) | commands `$0e`, `$12`, `$14`, `$10` (the command strip) |
| / (`$35`) | pointer mode `$c` |
| keypad + / - (`$4e`, `$4a`) | view size; keypad Enter (`$72`) toggles 8 / `$17` |
| cursor keys and keypad 1-9 | scroll |
| [ ] (`$1a`, `$1b`) | commands `$5a` / `$5c` at the cursor cell (`$5e`/`$60` and `$62`/`$64` with two modifier keys) |
| F7, F8 (`$41`, `$42`) | `$1f816`, `$1f7fa` when `$39768` is set |
| F9 (`$43`) | command `$78` |
| F10 (`$44`) | with the pointer at (0,0): leave (`$39604`); otherwise toggle `$39798` or command `$68` |
| = (`$0d`) | `$4739e` = 4 |
| any other | command `$72` with the typed character (`$22036`) |

So Powermonger's letter keys are not free here: every unassigned key is sent as command `$72`. Draft key map: **keep the game's keys; add nothing until command `$72` is understood** (it may be the link chat). What is missing compared with Powermonger is only discoverability, which the tooltip gives ("Earthquake (F3, 2)"-style texts built from the category and slot).

## Text renderer and font

`$168b6(a0 = screen, a1 = string, d0 = column 0..39, d1 = row)`: opaque 8 x 8 cells on byte columns, `$0a` = next line, font at `$37c84`, 32 bytes per character (8 rows x 4 planes, written with `movep.l`):

```
0168e2  subi.w #$20,d0 ... lsl.w #5,d0 / lea (a3,d0.w),a4
016912  move.l (a4)+,d0 / movep.l d0,$0(a0) / move.l (a4)+,d0 / movep.l d0,$a0(a0) ...   ; 8 rows
```

## Tooltip area in normal play

Clean background `work/shots/tt_bg_clean.png`. The top of the screen between the floating minimap and the colosseum is palette 0 (black):

| Rows | x from..to | Character columns | Characters |
|---|---|---|---|
| 0..2 | 114..265 | 15..32 | 18 |
| 0..7 | 118..258 | 15..31 | 17 |
| 8..15 | 129..252 | 17..30 | 14 |
| 20..40 | 154..252 | 20..30 | 11 |

The draft's "rows 0-7 flat (34,34,102) over the full width" was the title screen. Candidate: **(120,0)-(255,7), 17 characters of the game's own font** (`work/shots/tt_candidate_top_text.png`, outline in `tt_candidates_rects.png`), second line (136,8)-(247,15), 14 characters. The frame is rebuilt from the clean background every pass, so a tooltip drawn into the back buffer after `$1e7b2` needs no erase. Not checked: other landscapes' backgrounds, the zoomed views (`$39766` != 8), dialogs.

Draft wording (17 + 14 characters), ours: `Raise/lower land`, `Query (/)`, `People effects F1`, `Plants F2`, `Earth F3`, `Air F4`, `Fire F5`, `Water F6`, then per armed effect its name with `F<n> <slot>`; the game's own Help-key texts stay as they are.
