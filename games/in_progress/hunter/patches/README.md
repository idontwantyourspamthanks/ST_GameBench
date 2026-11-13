# Hunter patches: blob map and per-patch notes

Patch sources are `patches/*.s`, delivered by `tools/huntpatch.py` (`verify`, `list`, `build`, `live`; see its docstring and `work/notes/loading.md`).
Each patch has ONE splice `site` (6 or 8 bytes) and optional blobs; blob origins must lie in the range of the patch-name prefix
(`PREFIX_RANGES` in `huntpatch.py`). `huntpatch.py build` reports overlaps. `; requires: name` makes the tool refuse a selection that lacks a
partner (one feature over two sites).

## Blob map (payload `$8BA00..$AEFFF`, free RAM proved in `REPORT.md` section 2)

Re-derive the map in one step from the ASSEMBLED payload (the authority, not the table below):

```sh
python3 tools/huntpatch.py build --out build/map --fill >/dev/null && python3 - <<'EOF'
import json
m = json.load(open('build/map.json')); u = sorted(m['used']); p = m['img_base']
for a, b in u:
    if a > p: print(f"  gap  ${p:06x}-${a-1:06x} {a-p:6d} B")
    print(f"  used ${a:06x}-${b-1:06x} {b-a:6d} B")
    p = max(p, b)
if p < 0xaf000: print(f"  gap  ${p:06x}-$aefff {0xaf000-p:6d} B")
EOF
```

`python3 tools/huntpatch.py list` adds each blob's patch name, prefix window and phase. Gaps above `$90000` are the sample
bank; `$8DC00-$8DFFF` is the `test_` window and is not usable for the release set.

| Range | Owner | Content |
|---|---|---|
| `$8BA00-$8BB5A`, `$8BB60-$8BBEA` | `core.s` | payload entry (probe, site applier, cache flush), load hook |
| `$8BC00-$8BFEF` | tool | site table (1008 B) |
| `$8BFF0` / `$8BFF8` | `core.s` | `FLAGS` (bit0 STE DMA sound, bit1 probe ran, bit2 bus error, bit3 Falcon) / `MARKER` (`HNPO`, `HNPF`) |
| `$8C000-$8DFFF` prefix `p4_` | `p4_ikbd`, `p4_edge`, `p4_poly` | raster speed-ups (`$8C000`, `$8C100`, `$8C400`, `$8CE00`, tables `$8D000-$8D35F`) |
| `$8C014-$8C0FF` prefix `pal_` | v1.2 STE palette | gap between `p4_ikbd` and `p4_edge` code |
| `$8C1B1-$8C3FF` prefix `tb_` | `tb_flip`, `tb_frame`, `tb_vbl` | triple buffering (note `work/notes/triple.md`) |
| `$8C72C-$8CDFF` prefix `sav_` | v1.2 HD save/load | gap after `p4_poly` code |
| `$8F100-$8F7FF` prefix `sky_` | v1.2 sky + panel | hole inside the `snd_` window (`snd_core` state `$8F000`, tables `$8F800`, `$8FC00`); the sky tables do not fit the sample-bank tail because the floppy stage only accepts payload code below `$90000` |
| `$8ECEA-$8EFFF` prefix `sky2_` | v1.2 sky/panel state | hole between `snd_core`'s code (ends `$8ECE9`) and its state (`$8F000`) |
| `$8CBBE-$8CFFF` prefix `help_` | `help_pause` | pause-screen controls guide: code + list A `$8CBBE-$8CDF3`, font + list B `$8CE80-$8CFF8` (around `p4_poly`'s `$8CE00` blob; site `$260a`; note `work/notes/help.md`) |
| free spare | anyone | `$8D360-$8D3FF` (160), `$8D585-$8D5FF` (123), `$8D9D4-$8D9DF`, `$8DA3A-$8DBEF` (438), `$8DBF4-$8DBFF` (12), `$8BCA8-$8BFEF` (840, the site table's slack) |
| `$8D400-$8DBFF` prefix `hn_` | `hn_credit` `$8D400-$8D584`, `hn_hz` `$8DA00-$8DA39` + state `$8DBF0` | Hunter specific |
| `$8D600-$8D9FF` prefix `jag_` | `jag_pad` code `$8D600-$8D815`, `jag_stick` code `$8D9C0-$8D9D3`, `jag_pad` state `$8D9E0-$8D9FF` | Jaguar pad (inside the `hn_` window, between `hn_credit` and `hn_hz`; `$8D816-$8D9BF` is free) |
| `$8DC00-$8DFFF` prefix `test_` | loader self-tests | not in the release set |
| `$8E000-$8FFFF` prefix `snd_` | `snd_core` | mixer code `$8E000-$8ECE9`, state `$8F000`, tables `$8F800`, `$8FC00` |
| `$90000-$AEFFF` | sample bank | built from the user's Amiga ADF |

**Outside the payload.** `$81000-$88CFF` (32 000 B, 256-aligned) is the **third screen page** for triple buffering (`tb_*`): it is
proved free (pattern method, at the game entry `pc = $800`, dump and compare) on HD STE 1.62 1 MB, HD ST 1.04 1 MB and HD Mega STE
2.06 4 MB, and on the floppy cells (`work/notes/triple.md` section 2). `$B8200-$BFFFF` (32 768 B) is free on the HD build only (the
floppy loader's file cache starts at `$AF000`). `$AF000-$185FFF` is **not** free: the game's D15R mini-OS and its buffers live at
`$C0100`, and filling that range makes the machine reset and the loader re-run. `$32A00-$3682B` (the game's arena slack, 15.9 KB) is
free in the 3D view on the tested cells but is left unused.

## Blob ends (assembled lengths of the default set + the v1.2 windows, from `huntpatch.py build --fill`'s manifest)

Start addresses alone do not say where a blob ends; these are the real ends (`build --fill`, manifest `used`) so a later agent
can pick a free gap without guessing:

| start | end | size | owner |
|---|---|---:|---|
| `$8BA00` | `$8BB55` | 342 | `core.s` entry |
| `$8BB60` | `$8BBE9` | 138 | `core.s` load hook |
| `$8BC00` | `$8BCA7` | 168 | site table (grows with each patch: 8+2*len per site, limit `$8BFEF`) |
| `$8C000` | `$8C013` | 20 | `p4_ikbd` |
| `$8C100` | `$8C1B0` | 177 | `p4_edge` |
| `$8C400` | `$8C72B` | 812 | `p4_poly` code |
| `$8CE00` | `$8CE7F` | 128 | `p4_poly` second blob |
| `$8CBBE` | `$8CDF3` | 566 | `help_pause` code + list A |
| `$8CE80` | `$8CFF8` | 377 | `help_pause` font + list B |
| `$8D000` | `$8D35F` | 864 | `p4_poly` tables |
| `$8D400` | `$8D584` | 389 | `hn_credit` |
| `$8D600` | `$8D81B` | 540 | `jag_pad` code |
| `$8D9C0` | `$8D9D3` | 20 | `jag_stick` |
| `$8D9E0` | `$8D9FF` | 32 | `jag_pad` state |
| `$8DA00` | `$8DA39` | 58 | `hn_hz` |
| `$8DBF0` | `$8DBF3` | 4 | `hn_hz` state |
| `$8E000` | `$8ECE9` | 3306 | `snd_core` code |
| `$8F000` | `$8F0FF` | 256 | `snd_core` state |
| `$8F800` | `$8FBFF` | 1024 | `snd_core` tables 1 |
| `$8FC00` | `$8FFFF` | 1024 | `snd_core` tables 2 |
| `$90000` | `$AE4DD` | 124126 | sample bank |

Free gaps from the same manifest (default set + tb_*): `$8BB56`(10), `$8BBEA`(22), `$8BCA8-$8BFEF`(840, the site table's own
slack), `$8C014-$8C0FF`(`pal_`), `$8C1B1-$8C3FF`(`tb_`), `$8C72C-$8CDFF`(`sav_`), `$8CE80-$8CFFF`(384), `$8D360`(160),
`$8D585`(123), `$8D81C-$8D9BF`(`key_`), `$8D9D4`(12), `$8DA3A-$8DBEF`(438), `$8ECEA-$8EFFF`(`sky2_`), `$8F100-$8F7FF`(`sky_`).

## jag_pad + jag_stick: Atari Jaguar pad (`default: no`; HD and floppy builds)

Source: `patches/jag_pad.s` (poll, detection, key injection, the `$c616` splice), `patches/jag_stick.s` (the `$c64c` splice, 16 bytes).
Both must be selected together (`; requires:`): `huntpatch.py build --only <default set> jag_pad jag_stick [--floppy]`.
Study: `reports/jaguar_pad_study.md` (protocol, Hatari pad emulation). Evidence, gates and measurements: `work/notes/jagpad.md`.
Gate tool: `tools/huntjag.py` (live button table, profile, cold boots on ST/STE/Mega STE/TT, Falcon floppy), pad configs `tools/jag_pad_a.cfg` (pad A) and
`tools/jag_pad_ab.cfg` (pads A and B).

**What it does.** A Jaguar pad in either enhanced joystick port (STE and Falcon only; port A and port B are read together and OR-ed) works next to the normal
joystick. The pad's stick bits are OR-ed into the game's stick byte `$d0` at the VBL world block (`$c64c`, before `$cf` and `jsr $355a` read it), so on foot
and in vehicles the pad steers exactly like the stick. Extra buttons call the game's own key decoder (`$b048`) once per press (make on press, break on
release), so every key behaves as typed. With no pad, or nothing pressed, the OR is of zero and no key is injected: nothing changes.

**Button map**

| Pad | Hunter | Pad | Hunter |
|---|---|---|---|
| D-pad | stick (move / turn / accelerate) | `1` | R radar |
| A, B | fire | `2` | Help = overlay map ("?") |
| C | Return = next weapon | `3` | L log book |
| Option | Space = leave vehicle | `4` | A observation drone |
| Pause | P = pause (also un-pauses) | `5` | F flare |
| `*` | Esc = game options | `6` | C clock |
| `#`, `0`, `8` | unassigned | `7` / `9` | cursor Up / Down = zoom (held while pressed) |

Keys are injected only while the 3D view runs or the game is paused (`$93` bit 7 / bit 5): never in menus or the name entry. Menus, the drone map
and the game options are mouse driven, as in the original: the pad has no pointer.

**Detection** (once, on the first VBL; every layer fails closed): (1) `FLAGS` bit0 (STE DMA sound answers: not a plain ST/Mega ST) and a bus error on the
SCU `$ff8e01` (the Mega STE and the TT have it; the STE and the Falcon have not), (2) bus-error-guarded word access to `$ff9202`/`$ff9200`, (3) idle sanity
(`$ff9202` high byte `$ff`, `$ff9200` low nibble `$f` with every group deselected). When the answer is no (ST, Mega ST, Mega STE, TT) the probe writes the
original bytes back to both splice sites: those machines run the unpatched code at zero cost and never touch a pad register. `FLAGS` bit3 is not used.

**Polling and cost.** One row group per VBL, round robin (group 4, 3, 2, 1): the select written at the end of one VBL is read at the start of the next, so there
is no wait loop; nothing is decoded unless the group's data changed. Every group is read every fourth VBL: a press must last 80 ms. Measured (`tools/huntjag.py prof`):
180 cycles per VBL in the blob + 52 in the merge, 212 net of the code the splices replace = 0.13 % of the CPU (pad or no pad); 0 where the probe says no.
Evidence, gates and limits: `work/notes/jagpad.md`.

## sav_hook + sav_open + sav_sync: in-game Save and Load on the HD build (`default: no`, HD only)

Sources: `patches/sav_hook.s` (site `$d542`), `patches/sav_open.s` (site `$c0268`, D15R), `patches/sav_sync.s` (site `$c02d4`, D15R).
All three carry `; hdonly: yes`, so `build --floppy` / `verify --floppy` skip them (the floppy has the cracker's loader at `$d30e` and
keeps its own, working, saving); `sav_hook` requires the other two. Blobs: `$8C72C` (hook), `$8CB2C` (open), `$8CB80` (sync) in the
`sav_` window. Study: `reports/hunter_ideas.md` idea 10; evidence, measurements and gates: `work/notes/save.md`; gate tool:
`tools/huntsave.py` (`roundtrip`, `slots`, `errors --case missing|zeros|short|valid|ro|full|init`, `kill --delay D --runs N`,
`persist`, `allgames`, `floppy`).

**What it does.** PP's HD build had saving switched off: his file hook (`$150`) ignores the write flag and always reads, so Save Game
wrote nothing and then read the file back over the game's memory, and the slot list showed his placeholder names (which live in
`FILES/0`). Now the six slots and the save directory are ordinary files in the game's folder - `FILES\SAVES.DIR` (224 bytes) and
`FILES\SLOT1.SAV` ... `FILES\SLOT6.SAV` (51,328 bytes, the game's own checksum) - created on the first save when missing, with names
typed in the game as before. A save that fails says why and leaves the old save and the slot list untouched; a damaged or missing slot
file is refused with a message instead of being loaded. Init Disk works (it clears the list). Only the disk menu's files are handled;
every other file call is byte-for-byte PP's.

**Durability.** `Fclose` alone leaves the new directory entry in GEMDOS's buffer (it is written back only when a buffer is reused), so
a machine switched off after a save could lose it: measured 0 of 3 durable when Hatari was killed 1 s after the save, and 0 of 2 after
20 s. `sav_sync` calls GEMDOS `Dfree` right after the loader's `Fclose` (still inside the loader's TOS world) on writes only - it reads
the whole FAT, which evicts the dirty buffers. After it: 10 of 10 durable at 1 s, 5 s and 20 s (`work/notes/save.md` section 3).

## key_item: one-key items and weapon keys (`default: no`; HD and floppy; gates passed, see `work/notes/keys.md`)

Source `patches/key_item.s` (site `$a534`, 6 B; blob `$8D820`, prefix `key_` = `$8D816-$8D9BF`). The game's key dispatch (`$b0b6`, only while `$93` bit 7 = the 3D loop) looks a key's ASCII up in an 8-entry table (`$a516`: c r l m f a ~); a miss
goes `jmp $2686` at `$a534`. That jump now goes to a second table: `1`-`9` (top row and keypad) = weapons 0-8, `h` = medical kit (item 14), `g` = fuel can (15), `j` = parachute (18). A hit loads d0 = item and enters the game's own
ownership test and icon click path at `$a540`, so the effect is that of clicking the icon in the item table (RAM compared key vs click for every key, owned and not owned). Keys do nothing in the item table, log book, game options
or while paused. `jag_pad.s` maps the Jaguar pad's spare buttons `#`, `0`, `8` to h, g, j (mask `$000f0f0f`; the table above that says "unassigned" predates this). Tool: `tools/hunkeys.py`.
