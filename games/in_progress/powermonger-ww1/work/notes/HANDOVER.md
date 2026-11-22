# HANDOVER: Powermonger WW1 — depacker is done, next is play.sh

Read this first, then `cobra26.md`, `carrier.md`, `tickgate.md`, `tickproto.md`,
`frameloop.md`, `input.md`, `baseline.md`.

## TL;DR

- **Base is Cobra #26** (`extracted/cobra26/`). `WW1.PRG` runs standalone from a folder.
- **`tools/atomik.py` is exact.** `python3 tools/atomik.py` prints **100.00%** (152182/152182)
  against the live capture. The routine is the stub at text `$0c4..$23a`, transcribed with
  the real `addx` refill. Do not reopen it.
- **`tools/wwbuild.py build` writes a patched plain PRG.** It depacks, checks the 7 tick
  sites, and emits the nested program's text plus its reloc table. The sites are text
  offsets, which sit **`$110` above** the map-view runtime addresses (`$13DA0` → text
  `$13EB0`). The previous table used the runtime addresses as file offsets; that was wrong.
- **Not done:** `tools/play.sh`, and the live gates (cold boot to the map with `PMPO`, 4.00
  ticks/s at 8 and 16 MHz, `pmtick_series.py`, 50/60 Hz, pause, save/load).

## What the depacker actually produces

`depack()` returns 153665 bytes. They are a nested GEMDOS PRG, not a raw memory image:

| | |
|---|---|
| header | 28 bytes, `601a`, text 152986, data 0, bss 0 |
| text | starts `jmp $24054` then the string `ww1_fuzi.lfb` |
| game entry | text `$e8` / image `$104`: `43 f9 00 00 d8 c2` (`lea $d8c2,a1`) |
| reloc table | 651 bytes at the end, 57 entries, terminated by a 0 byte |

`work/dumps/c26_image_full.bin` (160000 bytes) is a live dump that **starts at the game
entry**, not at the PRG header, taken after the stub added its load address to those relocs.
The delta in that dump is `$12576`. Comparing the raw buffer against byte 0 of the file will
not read 100%; `tools/atomik.py` does the alignment and the reloc fixup itself. The match
covers every non-zero text byte. Past that the dump leaves the depack buffer (the file keeps
going through zero padding the depacker never wrote).

Two details that the earlier notes had wrong, so they are not worth re-deriving:

- The byte `d3` read before the span is the short-length limit, not part of the span. A short
  code (a 1-bit within `d3+1` bits) is just the leading-zero count and branches to `$114`,
  **skipping** `add.w d3,d5`. Only the long form adds `d3`.
- `getbits` (`$152`) really does `add.b d7,d7` / `addx`. When the shift clears `d7`, the bit
  that emptied it is parked in the next byte's low bit and the bit returned is the new byte's
  high bit. A naive MSB reader will not match.

## Next: play.sh and the live gates (mechanical)

The interface is already specified in `carrier.md`:

```
tools/play.sh                    # patched (default: tick), STE, 1 MB, TOS 1.62
tools/play.sh --original         # the unpatched Cobra WW1.PRG
tools/play.sh --machine megaste  # st|megast|ste|megaste|tt|falcon
tools/play.sh --ram 2048
tools/play.sh --cpu 16
tools/play.sh --tos FILE
tools/play.sh --only tick        # or no patches: --only (empty)
tools/play.sh --print
tools/play.sh ... -- OPTS
```

It should `wwbuild.py build --out build/play/`, copy `WW1_FUZI.LFB` beside that PRG, and boot
the folder as drive C with `--fast-boot yes`.

Gates before calling it done: cold boot to the map view with the marker (`PMPO`) set; world
rate 4.00 ticks/s at 8 and 16 MHz; the state-equality gate (`tools/pmtick_series.py` — the
Pompey addresses, unchanged because the builds match); 50 and 60 Hz; pause; a save/load round
trip.

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
| Patch tool | `tools/wwbuild.py` | builds the plain PRG |
| **ATOMIK depacker** | `tools/atomik.py` | **exact, 100.00% vs the capture** |
| Plain patched PRG | `tools/wwbuild.py build` | builds; tick sites at text offset = runtime+$110 |
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

## Suggested split from here

`play.sh` plus the live gates is one job and needs the emulator. The tooltip font hunt is
still pure static disassembly over the depacked image (the capture starts at image `$104`,
so add that before using a capture offset as an image offset) and does not need Hatari.
