# HANDOVER 2: payload reaches `$72000`; next is play.sh

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

`python3 tools/wwbuild.py build` depacks, verifies all **7 tick sites**, and writes a plain
PRG (text 152986, data segment = the copy stub plus `tick.bin`). See below for where that
payload actually runs.

The sites stay as they are (`list` shows `$13eb0` / `$8f6` — text offsets, i.e. runtime
`$13da0` / `$7e6` + `$110`). They read `jsr $72000` (`4e b9 00 07 20 00`). Do not retarget
them at `load_base + offset`.

## Payload placement: fixed

The earlier build appended the tick image **after the reloc table** and pointed the sites at
`$37B10` (`$12576 + text offset`). TOS loads only `28 + text + data`, so those bytes never
reached RAM: at the name screen `$37B10` was zeros and the signature was nowhere, while the
game itself ran and jumped into empty memory.

That address was also the wrong home. The startup at text `$14` copies the game from text
`$686` to **`$576`** and jumps there, which is why a site at text `$13eb0` executes at
`$13da0` (`text_offset - $110`). An in-text payload left behind at `load_base + offset`
is not where the copied sites jump, and `load_base` is not stable across machines. The tick
image was assembled for `$72000`, with its own jumps aimed at the map-view addresses.

`tools/wwbuild.py` now does what that implies:

- the proven `work/tickproto/tick.bin` rides in the **data segment**, behind a 26-byte stub
- the entry `jmp` (its existing reloc) is aimed at the stub; one new reloc sends the stub
  back to `$24054`
- the stub copies the image to `$72000` (PC-relative source, fixed destination) and the
  sites keep `jsr $72000`

Checked on a cold boot of that PRG (STE, 1 MB, TOS 1.62), at the options screen: `$72000`
matches `tick.bin` 338/338, all 7 sites hold their `$72xxx` targets, and `PASS`/`ACC`/`KIND`
are still zero. The signature is already at `$72000` during the intro and is still there
after it. `play.sh` and the live gates are the remaining work.

Two constants, still not one:

| mapping | value | source |
|---|---|---|
| text offset -> map-view address | **`- $110`** | the copy from text `$686` to `$576`; text `$13eb0` executes at `$13da0` |
| relocated long -> its runtime value | **`+ load base`** | TOS adds it; the capture's delta was `$12576`. Not a place to put the payload |

## What is already done and must not be redone

| thing | where | state |
|---|---|---|
| ATOMIK depacker, 100.00% | `tools/atomik.py` | **done** |
| Ground-truth image | `work/dumps/c26_image_full.bin` | done |
| 7 tick sites + verified originals | `tools/wwbuild.py list` | done, still `jsr $72000` |
| Payload in the PRG, copied to `$72000` | `tools/wwbuild.py` data segment + stub | **done, seen at the options screen** |
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
# First shipped-PRG gate, Cobra #26 build via wwbuild.py

Build: python3 tools/wwbuild.py build
  wrote build/patched/WW1.PRG (154091 bytes, 152986 text, 422 data, sites: 7)
  data segment = 26-byte copy stub + tick.bin (338 B); sites are `jsr $72000`

Cold boot (PMWW, STE 1 MB TOS 1.62, folder run of build/play):
  $72000 == tick.bin: True (checked at boot and at the name screen)
  $13DA0 holds `4e b9 00 07 20 00` (jsr $72000); breakpoint on $13DA0 fires
  payload entry $72000 fires; PASS increments

Map view, after the standard navigation:
  in_game: True
  8 MHz : 45 ticks / 563 vbl = 4.00 ticks/s   (PASS 85)
  16 MHz: 45 ticks / 563 vbl = 4.00 ticks/s   (PASS 232)
  screen mean 67.3, 160876 bright px (picture live, no bus errors)
