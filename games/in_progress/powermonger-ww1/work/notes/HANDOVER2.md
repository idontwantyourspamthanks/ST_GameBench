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

## play.sh (done)

`tools/play.sh` follows the convention of the other games (cf. `../../nebulus/tools/play.sh`):

```
tools/play.sh                    # patched (default set = tick), STE, 1 MB, TOS 1.62
tools/play.sh --original         # the unpatched Cobra WW1.PRG, for comparison
tools/play.sh --machine megaste  # st, megast, ste, megaste, tt, falcon
tools/play.sh --ram 2048
tools/play.sh --cpu 16           # boots at 8 MHz, raised at VBL 200 (a real Mega STE powers up at 8)
tools/play.sh --tos FILE
tools/play.sh --only tick        # exactly these patches; `--only` alone = the unpatched set
tools/play.sh --print            # print the Hatari command line, no build
tools/play.sh --fresh            # discard build/play-*/ and rebuild
tools/play.sh ... -- OPTS        # pass through to Hatari
```

How it runs: `wwbuild.py build --out build/play-<variant>` writes the patched (or copies the
original) `WW1.PRG`, `WW1_FUZI.LFB` is copied beside it, and Hatari mounts that folder as C:
with `--auto "C:\WW1.PRG"` (the Cobra disk has no AUTO folder, so the game is normally launched
from the desktop). Verified: `--print` for every variant, `--fresh` builds, and Hatari starts
with the right command line under Xvfb.

**Remaining for the release**: the rest of the gate matrix (`pmtick_series.py` state equality
on this build, 50/60 Hz, pause), then saves (the game's save-disk code wants a disk in A:; a
blank `savedisk.st` plus `--disk-a` is the next step if saves matter for testing), then the
other three ports (keys next - the prototype already works and the addresses are identical).

## The release gate: PASS on real builds

`tools/release_gate.py` is the gate that matters — it boots **two real PRGs** (not debugger
patches) and compares them:

| build | command |
|---|---|
| reference | `wwbuild.py build --only noprot` |
| patched | `wwbuild.py build --only tick noprot` |

The reference also carries `noprot` because the stock game stops at the protection question
and can never reach the map; both builds therefore have the protection removed and the **only**
difference between them is the tick.

```
world ticks captured: stock 18, patched 17, common 6

tick  pass(stock/tick)  differing bytes
   64     64/64         0
   65     65/65         0
   67     67/67         0
   69     69/69         0
   70     70/70         0
   72     72/72         0

negative control 64 vs 65: 63 differing bytes (must be > 0)

PASS
```

Six consecutive world ticks, **byte-identical over the whole low 1 MB**, with the pass counter
identical at every tick, and the negative control proving the gate is sensitive.

### What the gate had to exclude (each justified)

| range | why |
|---|---|
| `$0-$7ff` | TOS low memory |
| `$7e6`, `$842`, `$144b4`, `$13da0`, `$13e24`, `$13e36`, `$13e42` | the tick's own patch sites |
| `$1b900-$1b907` | the weather animation phase |
| `$1d2a0-$2d5ff` | IKBD state, pointer words, both screen buffers (the pixel gate's job) |
| `$2d600-$2dfff` | the stack |
| `$2ed90-$2edbf` | world counter, click stamp, latches |
| `$5ef00-$5efbf` | the sound sequencer |
| `$71b7c-$71b83` | the VBL counter |
| `$72000-$72fff` | the tick payload |
| `$e7c2`, `$11dc6`, `$82c4` | the buffer pointers (flip parity) |
| `$1bc9a-$1bc9f` | the **YM sample player's self-modified operand** (`$1bc92` stores its advancing pointer inside `movea.l #0,a0`, frameloop.md section 2) |
| `$e518-$e523` | a self-modified operand in the icon/pattern draw |
| `$1194e-$1195f` | a zero-padded gap after an `rts` in the chart code: uninitialised memory |

### Traps this gate exposed (all harness, not patch)

1. **The navigation is flaky.** The island click sometimes lands before the chart is ready.
   `to_map()` now clicks until the world counter is *observed advancing* and retries the whole
   series three times.
2. **The camera cell differed between runs**, which changes every projected coordinate
   (`$44830`-table, `$0f5xx`). The camera is re-derived from the pointer each pass, so it must
   be pinned **inside the capture command file** (write `$50fd4/$50fd6` then `savebin`), not
   once before the loop — the next pass overwrites a one-off write.
3. **Runs reach the map at different tick numbers** (the patched build's intro is a few frames
   different), so the series must be long enough to overlap; 20 dumps each gives ~6 common.

## The remaining matrix, and one pre-existing limitation

**8 and 16 MHz at 50 Hz: PASS.** 4.00 ticks/s both, from the shipped PRG (gate output above
and the earlier `PASS 85` / `PASS 232` runs).

**Mega STE / 60 Hz: the STOCK game does not run on Hatari's Mega STE.** Confirmed on the
completely unpatched Cobra build (`files_from=extracted/cobra26`, `machine=megaste`,
`tos=TOS["2.06"]`): the screen stops at the cracktro (mean 23.8, never reaches the name
prompt or the map). The same build on a 60 Hz *STE* is fine (TOS 1.62 + `--machine ste`), and
the 1990 game ran on a Mega STE at 60 Hz (its `regression.md` has 4.62/4.02 there), so this is
specific to the Cobra/Fuzion release rather than the engine.

`tools/rate_check.py` automates the matrix; its Mega STE rows will keep failing until that
release-level problem is investigated. Options: use an STE forced to 60 Hz for the 60 Hz tick
test (TOS 1.62 does 50 Hz; EmuTOS or a US TOS 1.04 gives 60), or chase the cracktro/loader
problem. **Neither is a defect in the tick patch** — it is worth saying plainly in the release
notes, as the 1990 project did for its own machine quirks.

**Pause: not yet tested.** The tick reads the game's own pause gate (`$5a856`) and passes
through to the original path when it is set, so pausing should freeze the world; the check to
run is that a paused game shows 0.00 ticks/s and resumes at 4.00 without a burst.

## Where this leaves the release

| gate | state |
|---|---|
| builds from source, cold boots | **PASS** |
| 4.00 ticks/s at 8 MHz | **PASS** |
| 4.00 ticks/s at 16 MHz | **PASS** |
| per-tick state equality, real builds | **PASS** (6 ticks, 0 bytes, negative control) |
| protection removed | **PASS** (flag `$2c`, no question box) |
| play.sh | **PASS** (`--original`, `--machine`, `--only`, `--print`, `--fresh`) |
| 60 Hz (Mega STE) | **blocked by the stock game**, not the patch |
| pause | to test |
| pixel-identical frames vs unpatched | to test (needs a frame gate on the patched build) |
