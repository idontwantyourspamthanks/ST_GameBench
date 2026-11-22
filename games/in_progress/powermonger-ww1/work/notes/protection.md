# Powermonger WW1: the copy-protection question, and `noprot`

The WW1 edition has the **same protection as the 1990 game**, at the same relative place, and
the 1990 project's `pm_noprot` port applies almost verbatim
(`../../done/powermonger/work/notes/protection.md`, `patches/pm_noprot.s`).

## What the original does

Not a disk check. The "protection passed" state is **one long word at runtime `$15998`**
(text offset `$15AA8` = runtime + `$110`). It sits in a run of identical `bra.w` slots in the
people-state jump table:

```
text $15AA0: 16 0a 16 3e
text $15AA4: 16 72 16 72
text $15AA8: 60 00 15 ea     <- bra.w $15ea  = runtime $15998, the pass flag
text $15AAC: 60 00 15 e6     <- bra.w $15e6  (the slot after it)
```

This is instruction-for-instruction the same as the 1990 game's `$14e4e` (`bra.w $161c4` in a
run of identical slots). The flag reads `$60` as a byte and `$0000002c` as a long.

The trigger is the same too: the sprite-frame handler tests it with
`cmpi.b #$60, $154(a0)` where `a0 = $15844`, i.e. `cmpi.b #$60, $15998`:

```
text $12B98: lea.l  $15844.l, a0
text $12B9E: cmpi.b #$60, $154(a0)      ; still the untouched bra.w opcode?
text $12BA4: bne.b  $12bca               ; no: normal sprite frame only
text $12BA6: move.b #$2a, $6(a3)         ; else: state := $2a + 4 = $2e
text $12BAC: addi.b #$4, $6(a3)
text $12BB2: move.w #$1, <click word>    ; fake a click
             ... jsr (a0) -> the check
text $12BC4: move.b #$e, $6(a3)          ; back to state $0e
```

So: until the flag is `$2c`, the first time a person in state `$0e` is drawn the game builds a
decoy land, asks "how many Houses/People?", and either writes `$2c` (right) or prints
"Demo mode now activated" and continues in the decoy land with Save/Format disabled.

The strings are all present at the same relative offsets as 1990:

| string | WW1 text offset | 1990 |
|---|---|---|
| `Please Wait For The Protection Check` | `$BD14` | `$BF12` |
| `Protection` | `$BD2C` | — |
| `Demo mode` | `$B53C` | `$B9AC` region |
| `Houses` | `$AFEA` | `$B4D0`-ish |

## The patch

`noprot` writes `$0000002c` at text `$15AA8`. There it disassembles as `ori.b #$2c,d0` and
falls through into the next `bra.w` — exactly the bytes a *correct* answer stores. Every
reader of the word then sees the answered state, the `cmpi.b #$60` branch never takes the
check path, and the question is never asked. Save/Format stay enabled.

```python
NOPROT_SITES = [
	(0x15AA8, bytes.fromhex("600015ea"), bytes.fromhex("0000002c"), "protection pass flag"),
]
```

`tools/wwbuild.py build --only noprot` builds a plain PRG (no tick payload needed — the patch
is entirely in-text).

## Verified [obs]

Cold boot of `--only noprot`, STE 1 MB TOS 1.62, through the standard navigation:

```
flag $15998 at the chart: 0000002c
after clicking the island: 0000002c      (the question box never appeared)
screen mean 66.4 = the map view, not black
```

The unpatched build shows the question box at that point instead.

## Not ported (yet)

The 1990 project also has `pm_noprot_box` (its `$bee0`), which turns the
"Please Wait For The Protection Check" box into a no-op. With the flag preset the box routine
is never reached, so the box patch is cosmetic — worth adding only if the box is ever seen
(e.g. on a machine where the flag is written late). The WW1 box routine was not located: the
box text is at `$BD14` but no `lea`/`pea` references it by address, so it is indexed from a
table rather than referenced directly.
