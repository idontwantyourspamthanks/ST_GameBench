# HANDOVER: Powermonger WW1 — state, and the one thing blocking a release

Written at the end of the session that chose the base and hit the depacker wall. Read this
first, then `cobra26.md`, `carrier.md`, `tickgate.md`, `tickproto.md`, `frameloop.md`,
`input.md`, `baseline.md`.

## TL;DR

- **Base is decided: Cobra #26** (`games/in_progress/powermonger-ww1/disks/cobra26.st`,
  extracted to `extracted/cobra26/`). It runs `WW1.PRG` standalone from a folder — no floppy,
  no chunk archive, no single-part crack.
- **The tick patch already works on it, unmodified**: `work/tickproto/tick.bin` gives
  **4.02 ticks/s at 8 MHz and 4.02 at 16 MHz** (unpatched 3.60 / 7.62). The game is address-
  identical to the Pompey build, so nothing needed porting.
- **Nothing shippable yet**, because there is no way to get the patch into `WW1.PRG` without
  first depacking it. **That single blocker is `tools/atomik.py`** (the ATOMIK depacker).
- Everything else — patch sites, original bytes, tool, harness, snapshots, the play.sh
  interface — is in place. See "What is already done" below.

## Your first hour: make the depacker exact

Goal: `python3 tools/atomik.py` prints **`100.00%`**. It compares against a captured
ground-truth image, so it needs no emulator and each attempt takes ~10 s.

```
cd games/in_progress/powermonger-ww1
python3 tools/atomik.py
#   unpacked 153665 bytes
#   vs the live capture: N/153665 identical (x.xx%)
```

**Reference image**: `work/dumps/c26_image_full.bin` — 153,665 bytes captured live at the
ATOMIK hand-over (`$12896`). It starts `43 f9 00 00 d8 c2` (`lea $d8c2,a1`) and contains
`d:\samples\ste.tos`, the keyboard tables, etc. **This is the acceptance oracle.**

**Source**: `extracted/cobra26/WW1.PRG`, text = bytes `[28:28+61622]`. Header at text `$274`:
unpacked `153665` (`$25841`), packed `60985` (`$ee39`), stream runs to the end of the text.

**Already established about the format** (full listing in `carrier.md`): adaptive,
block-based LZ; bits MSB-first from bytes taken **backwards** from the stream end; per block a
length table (`$1d8`), a 16-byte model (`$204`) and a span (`$222`), then a loop of literals
(`bit 0` -> byte from the stream) and matches (`bit 1` -> `d5 = getbits(3)`, copy from
`a5+d5+1` backwards). A parameter search over bit order / class bits / distance width / table
offset / length addend reached **40,434/153,665**, so the skeleton is right and one
block-metadata detail is wrong.

**The three things worth checking first** (in order):

1. **`$152`'s Z flag.** `getbits` loops `d6+1` times, `d7 <<= 1`, `addx.w d5,d5`, refilling
   from `-(a6)`, and the callers branch on **Z** (`6720`, `6712`), not on the value. The
   `addx`/refill interplay may make the first bit read inverted relative to the naive reading.
2. **The span at `$222`.** Three bytes are read: `d3 = byte`, then `d0 = (byte<<8) | byte`;
   the loop uses `a3 = a5 - d0`, but `d3` is read and unused in my transcription — the block may
   actually be `d3`-driven.
3. **The model at `$204`.** `lea -$10(a2),a1` then `move.b -(a6),(a1)+` 16 times: a **forward**
   store from a **backward** read, so the table is reversed relative to stream order.

**The fastest way to settle it, if the loop stalls**: single-step the real routine on a tiny
block. Set a breakpoint at `$1265E + $1d8` (= `$12836`) and step, logging `d3/d5/d7/a5/a6`
around the `$222`/`$1c4` block. Four bytes of output is enough to pin the semantics by hand.
That is how the 1990 project validated its `pm_depack` and it will not fight you like the
listing does.

Do not trust the parameter search's "best" figure as progress; it is a coincidence of matching
literal runs. The oracle is the percentage at 100.00%.

## Then: build and play (a few hours, all mechanical)

Once the depacker is exact:

1. `tools/wwbuild.py` already has everything it needs: `list` prints the 7 tick sites with
   their verified `orig` bytes; `build` verifies each site against the depacked image and writes
   a new **plain** PRG (no depacker, no reloc table problem). It currently refuses with a clear
   message until the depacker is exact — keep that gate.
2. Add `tools/play.sh` matching the other games' convention (interface already specified in
   `carrier.md`): `--original`, `--machine`, `--ram`, `--cpu`, `--tos`, `--only A B`, `--print`,
   `-- OPTS`. It must build via `wwbuild.py` into `build/play/` and boot that folder as drive C:
   with `--fast-boot yes` (this base is a folder run, not a floppy).
3. Gates before calling it done: cold boot to the map view with the marker (`PMPO`) set; world
   rate 4.00 ticks/s at 8 and 16 MHz; the state-equality gate
   (`tools/pmtick_series.py`, currently written for the Pompey addresses — it works unchanged
   because the addresses are identical); 50 and 60 Hz; pause; a save/load round trip.

## What is already done (do not redo)

| thing | where | state |
|---|---|---|
| Base chosen, extracted, boots | `extracted/cobra26/`, `README.md` | done |
| Harness for this base | `tools/pmww.py` (`files_from=`, `delta=`) | done |
| Map-view snapshot | `work/snapshots/c26_mapview.sav` | done |
| Tick prototype (proven) | `work/tickproto/tick.s` / `tick.bin` | done, 4.02 ticks/s both clocks |
| Tick **state equality** | `tools/pmtick_series.py`, `work/notes/tickgate.md` | **PASS, 12 ticks, 0 bytes** |
| All 7 tick sites + orig bytes | `tools/wwbuild.py list` | done |
| STUB LOAD BASE = `$1265E` | `carrier.md` | measured |
| ATOMIK hand-over = `$12896` | `carrier.md` (disassembly `4e5a 2c1f 4e75`) | measured |
| Ground-truth depacked image | `work/dumps/c26_image_full.bin` | captured |
| Patch tool skeleton | `tools/wwbuild.py` | done, gated on the depacker |
| **ATOMIK depacker** | `tools/atomik.py` | **NOT EXACT — the blocker** |
| Command-icon grid (all 20 cells) | `tools/pwwgrid.py` | done, oracle-verified |
| Keyboard-shortcut prototype | `work/keyproto/keys.s` | works live (key -> the game's own click) |
| Profile + baselines | `work/notes/{baseline,frameloop}.md` | done |
| Inputs, latch, overlay map | `work/notes/input.md` | done |

## After the tick ships: the other three ports

1. **Keyboard shortcuts** — `work/keyproto/keys.s` already works live on the Pompey build
   (pressing M makes the game report cell `$da`). Since the builds are address-identical it
   should port as-is; fold it into `wwbuild.py` as a second patch set.
2. **Tooltips** — the command grid is fully mapped (`tools/pwwgrid.py`, 20 exact cell
   centres) but the WW1's text/font routine was not found. The 1990 game's approach is in
   `../done/powermonger/work/notes/tooltip.md`; the job strings are at `$8f42`
   (`Get Men`, `Supply`, …) so the font is near them.
3. **Performance** — profile in `work/notes/frameloop.md`: terrain 39.8%, **YM sample IRQ
   14.2%**, 32K window copy 7.6%. The DMA-sound port and the `p6_cpy` blitter port transpose
   directly from the 1990 project; the 40% renderer does not (the WW1 uses a block-pattern
   combiner, not the 1990 triangle walker — see `frameloop.md` 6a).

## Traps that cost this session time (do not repeat)

- **The game runs twice at two bases**: the cracktro/intro first, then the game. A memory dump
  taken during the intro shows every address "shifted by `+$12686`". At the map view the game is
  at the Pompey addresses. Always verify a site at the **map view**, not while the intro plays.
- **Hatari breakpoints test at instruction boundaries**, so `b ($addr).l = N` never fires for a
  counter; `> N-1` fires late (a dump named 272 held 279). The reliable gate is a **series** of
  dumps at a fixed PC, aligned by the counter recorded inside each file
  (`tools/pmtick_series.py`).
- **Do not rewrite a counter then dump**: pinning `$2ed90` without pinning `$50fd8` manufactured
  a fake 8-pass animation offset.
- Hatari's `w` takes **decimal**; hex needs `$`. `m` output has an ASCII column to strip.
- A short/stale dump is silently repeated by Python — always check `len(dump)`.
- `vasmm68k_mot` `equ` does not move the assembler's position; use `org` per block.
- The `hatari-stop`/`hatari-cont` remote commands are **not** available via `hatari-debug` in
  this build.

## Suggested division for a stronger model / parallel wave

The depacker is a tight, self-contained problem — give it to the strongest model alone with
the oracle, no emulator contention. In parallel, a second agent can do the **tooltip font
hunt** (pure static disassembly over `work/dumps/c26_image_full.bin`, no emulator) and a third
can prepare the **play.sh + packaging** skeleton against `wwbuild.py` with the tick patch
disabled. That way a working `play.sh --only tick` is one depacker fix away.
