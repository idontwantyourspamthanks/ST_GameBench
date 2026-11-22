# Powermonger WW1 on Cobra #26: carrier status (and exactly where it stopped)

## What is proven and working

- **Base**: `extracted/cobra26/` (`WW1.PRG` 61650 B + `WW1_FUZI.LFB` 217708 B). Runs standalone
  from a folder, no floppy needed.
- **Boots with the harness**: `PMWW(disk=None, no_floppy=True, autorun_f="C:\\WW1.PRG",
  files_from=Path('extracted/cobra26'))`; the standard navigation
  (`at_gate("name")` -> type -> `at_gate("opt")` -> `poke_click(112,72)` ->
  `poke_click(130,88)` -> `poke_click(60,20)`) reaches the map view.
- **Snapshot**: `work/snapshots/c26_mapview.sav`.
- **The game runs at the SAME addresses as the Pompey build.** Unmodified `tick.bin` gives
  **4.02 ticks/s at 8 and 16 MHz** (unpatched 3.60 / 7.62). No porting needed.
- **The stub load base is `$1265E`** — measured: the lowest PC in the TPA during the load is
  `$1265E`, and a breakpoint there hits. The ATOMIK hand-over is therefore at **`$12896`**
  (`base + $238`), which is `unlk a2 / move.l (a7)+,d6 / rts` — confirmed by disassembling
  text `$236..$23c` (`4e5a 2c1f 4e75`).
- **A ground-truth depacked image is captured**: `work/dumps/c26_image_full.bin`, 153,665
  bytes, taken at the hand-over breakpoint. It begins `43 f9 00 00 d8 c2` (`lea $d8c2,a1`)
  and contains `d:\samples\ste.tos`, the keyboard tables, etc. This is the reference for any
  depacker work.

## The blocker: the file cannot be patched in place or by appending

`WW1.PRG` layout: header 28 + text **61622** + bss 92679, and **28 + 61622 == the file length**.

- There is **no relocation table** (TOS reads the reloc table immediately after text+data; here
  that is the end of the file). So a **data segment cannot be appended** — TOS would treat the
  first 4 bytes of the appended data as a relocation list.
- The text is **ATOMIK-packed**, so the sites (`$13da0` etc. are *runtime* addresses in the
  depacked image) cannot be edited in the file directly either.

So a carrier needs either (a) a working ATOMIK depacker at build time (depack -> patch ->
write a new plain PRG), or (b) a runtime hook. (b) needs a place for the hook code, which
needs either a data segment (impossible, above) or the 6-byte entry (too small).

**Therefore (a) is the only route, and it needs `tools/atomik.py` to be exact.**

## The ATOMIK format, as established

Reverse-engineered from text `$0c4..$23c`:

```
header at text $274:  unpacked.l (153665), packed.l (60985)
the packed stream runs to the end of the text; bits are MSB-first from bytes taken
BACKWARDS from that end.
per BLOCK (the block's own metadata arrives in the stream at the block's position):
  $1d8  if bit: a code-length table is rebuilt: n = byte(); d1 = 1;
              repeat 7x { if d1 == n: d1 += 2 ; d1 += 2 }   (entries used at $16e via a4)
        else: the table is cleared
  $204  if bit: 16 bytes are copied into a model table at a2-$10 ; else "no model"
  $222  span = (byte << 8) | byte ; the block writes down to a5 - span
  $1c4  loop: bit 0 -> a literal byte from the stream (`move.b -(a6),-(a5)`)
              bit 1 -> a match: d5 = getbits(3) ; copy from a5+d5+1 backwards
                       (`lea 1(a5,d5.w),a4` then two `move.b -(a4),-(a5)` per dbra)
```

`getbits` (`$152`) is: loop `d6+1` times, `d7 <<= 1`, `d5 = (d5<<1) | carry`, refilling d7 from
`-(a6)`; it returns 0 (Z set) when the first bit read is 0.

### What was tried

A parameter search over bit order / class-bit count / distance width / length table offset /
match length addend got 40,434 of 153,665 bytes matching at best — so the *skeleton* is right
and one of the block-metadata steps is wrong. A straight transcription of the above
(including the corrected `$1ec` loop) runs out of stream, which points at the block span or the
`$152` return-value semantics.

**The three candidate misreadings, in the order worth testing next:**

1. **`$152`'s Z flag.** It returns `d5 = 0` when the first bit is 0. The callers test *Z*
   (`6720`, `6712`), not the value. The refill/`addx` interplay means the first bit read may be
   inverted relative to the naive reading.
2. **The span at `$222`.** Three bytes: `d3 = byte`, then `d0 = (byte << 8) | byte`, and
   `a3 = a5 - d0`. `d3` is read but the loop uses `a3`; the block may instead be `d3`-driven.
3. **The model table order at `$204`.** `lea -$10(a2),a1` then `move.b -(a6),(a1)+` for 16
   bytes — a forward store from a backward read, so the table is *reversed* relative to the
   stream order.

## The fastest way to finish it

The reference image is already captured, so the loop is: fix one of the three items, run
`python3 tools/atomik.py`, read the percentage. A perfect run prints 100.00%. That is a
30-second loop per variant and needs no emulator.

## Tooling that is already in place

- `tools/wwbuild.py` — `list` shows every patch site (7 for the tick) with its original and
  replacement bytes; `build` refuses unless the depacker is verified (`--allow-unverified`
  writes the unverified rebuild and says so). It parses the PRG, checks the no-reloc-table
  shape, verifies each site's original bytes, and writes a plain rebuilt PRG.
- `tools/atomik.py` — the depacker under construction.
- `tools/pmww.py` — the harness, with `files_from=` for the Cobra folder.

## The play.sh that will ship (follows the convention of the other games)

```
tools/play.sh                    # patched (default: tick), STE, 1 MB, TOS 1.62
tools/play.sh --original         # the unpatched Cobra WW1.PRG
tools/play.sh --machine megaste  # st|megast|ste|megaste|tt|falcon
tools/play.sh --ram 2048
tools/play.sh --cpu 16
tools/play.sh --tos FILE
tools/play.sh --only tick        # or no patches: --only (empty)
tools/play.sh --print            # print the Hatari command line only
tools/play.sh ... -- OPTS        # pass through to Hatari
```
It builds via `tools/wwbuild.py build --out build/play/` then boots that folder as drive C:
with `--fast-boot yes` (the Cobra base is a folder run, not a floppy).
