# HANDOVER 2: the depacker is fixed; the remaining blocker is payload placement

Successor notes. History: `HANDOVER.md` (written before the fix), `carrier.md`, `cobra26.md`,
`tickgate.md`, `tickproto.md`, `frameloop.md`, `input.md`, `baseline.md`.

## What Grok fixed (verified, do not reopen)

**`tools/atomik.py` is now exact.** `python3 tools/atomik.py` prints:

```
unpacked 153665 bytes
vs the live capture: 152182/152182 identical (100.00%)
relocation delta $12576, 57 relocs, compared through the last text byte
```

The last bug was that **short length codes were decoded as matches because the transcription
always added `d3`; the real routine skips that add** (the byte read before the span is the
short-length limit, not part of the span). It also handles the nested PRG's 57-entry reloc
table and the `$12576` load delta. The oracle is `work/dumps/c26_image_full.bin`.

`python3 tools/wwbuild.py build` now depacks, verifies all **7 tick sites**, and writes a
patched plain PRG at `build/patched/WW1.PRG` (text 152986 + the payload). That part works.

**One correction to Grok's note**: the sites are correct as they stand (`list` shows
`$13eb0`/`$8f6` etc. — *text offsets*, i.e. runtime `$13da0`/`$7e6` + `$110`), and after a
build the site really does read `4e b9 00 03 7b 10` (`jmp $37B10`). Do not "fix" the table.

## The remaining blocker (small, well-bounded)

**The patch code never reaches RAM.** Measured:

- The build appends the tick payload to the PRG and points the sites at `$37B10`
  (`$12576 + payload text offset`) — the address the payload had in one measurement.
- At the name screen of that build, `$37B10` is **all zeros**, and a whole-RAM scan for the
  payload's signature (`2f 08 2f 00 2f 01 52 b9`) finds it **nowhere**.
- The game itself runs fine (options screen, render loop at `$8362`, chart at `$1197c`, no bus
  errors). So the *sites* are patched into a working game that then jumps into empty memory.

Conclusion: **TOS only loads `28 + text + data` bytes**, and the payload was appended *after*
the reloc table — past the declared text length — so it is never loaded.

### The fix

Put the payload **inside the declared text length**: `header.text = len(game_text) +
len(payload)`, payload immediately after the game text, and the **reloc table after that**.
TOS then loads it (`28 + text` covers it).

Then the payload's runtime address is `load_base + payload_text_offset`. `load_base` is
measured, not assumed: put the payload in, boot, find the signature in a RAM dump, and read
`found_address - payload_text_offset`. (It was `$12576` in one build; verify it for the final
one — the base depends on what TOS has free, so it may not be constant across machines. If it
is not constant, that is the moment to switch to a **base-independent** payload: instead of
`jmp <abs>`, have the site `jmp` to a small relative stub in the game image that computes the
target from its own PC. The 6-byte entry at text `$0` is available and plaintext.)

`tools/wwbuild.py` is at the point where this is one edit: the working version of the day is in
this commit's parent, and the change is `plain_prg()` — append `payload` to `body` **before**
packing the header's text length, keep `reloc` after it, and return the payload's text offset
so `build()` can compute `base = payload_off + LOAD_BASE`.

### A trap that cost an hour

My first attempt used `runtime = text_off - $110` for the payload. That is the mapping
**inside the game image** (the stub's `$110` bytes precede the game), not from the file. Two
constants, not one:

| mapping | value | source |
|---|---|---|
| game image offset -> its own runtime address | **`- $110`** | the sites: text `$13eb0` is runtime `$13da0` |
| file text offset -> loaded runtime address | **`+ $12576`** | measured: payload at text `$2559a` ran at `$37b10` |

Do not mix them.

## What is already done and must not be redone

| thing | where | state |
|---|---|---|
| ATOMIK depacker, 100.00% | `tools/atomik.py` | **done** |
| Ground-truth image | `work/dumps/c26_image_full.bin` | done |
| 7 tick sites + verified originals | `tools/wwbuild.py list` | done |
| Tick payload source | `work/tickproto/tick.s` (`PAYLOAD_BASE` equ) | done |
| Payload assembled at a given base | `work/tickproto/tick_intext.s` (uses `-D PAYLOAD_BASE=$...`) | done |
| Tick patch, live, on the stock base | `work/tickproto/tick.bin` applied by debugger | **4.02 ticks/s at 8 and 16 MHz** |
| Tick state equality | `tools/pmtick_series.py` | **PASS, 12 ticks, 0 bytes** |
| Map-view snapshot | `work/snapshots/c26_mapview.sav` | done |
| Navigation for this base | `tools/pmww.py` (`files_from=`) | done |
| Command grid (20 cells) | `tools/pwwgrid.py` | done |
| Keys prototype | `work/keyproto/keys.s` | works live |

## Then: play.sh + gates (mechanical, ~half a day)

Interface matches the other games (`carbos26.md` has it written out):

```
tools/play.sh [--original] [--machine M] [--ram K] [--cpu N] [--tos F]
              [--only A B] [--print] [-- HATARI_OPTS]
```

It should `wwbuild.py build --out build/play/`, copy `WW1_FUZI.LFB` beside it, and boot that
folder as C: with `--fast-boot yes` (this base is a folder run, not a floppy).

Gates before shipping: cold boot to the map view with the marker `PMPO` set; **4.00 ticks/s at
8 and 16 MHz**; `pmtick_series.py` equality; 50 and 60 Hz; pause; save/load round trip.

## Notes for the next ports

- **Keys**: `work/keyproto/keys.s` works live. Same addresses as the Pompey build, so it ports
  by being added to `wwbuild.py` as a second patch set.
- **Tooltips**: `tools/pwwgrid.py` has all 20 icon cells; the WW1 font routine is still
  unfound (the job strings are at `$8f42` in the runtime image — `Get Men`, `Supply`, …).
- **Performance**: profile in `frameloop.md` — terrain 39.8%, YM sample IRQ 14.2%, window copy
  7.6%. The DMA-sound and `p6_cpy` blitter ports transpose from the 1990 project; the renderer
  does not (block-pattern combiner, not a triangle walker).
