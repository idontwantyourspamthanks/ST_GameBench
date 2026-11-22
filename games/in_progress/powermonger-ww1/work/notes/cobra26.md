# Powermonger WW1 on the Cobra #26 / Fuzion build: a far better base

Evidence tags as usual. **[obs]** = raw emulator/file output.

## 1. Why switch base

The Pompey Pirates #106 release (`disks/pp106.st`) is a **single-part crack**: `WWIEDITN.PRG`
is a compressed stub whose payload is a 12-chunk `POPI` archive, and the code that reads it
lives in the runtime-expanded text. Building a patch carrier for that needs a working chunk
depacker first (`delivery.md`), which is unfinished.

The **Cobra #26** disk (`disks/cobra26.st`) ships the same game as **plain files**:

| file | bytes | what |
|---|---:|---|
| `WW1.PRG` | 61650 | the game: GEMDOS header + text 61622 + bss 92679, **self-contained** |
| `WW1_FUZI.LFB` | 217708 | the data (the `.LFB` container the game reads) |
| `*.SCO`, `*.RAW` | | the cracktro's own pictures/music |

`WW1.PRG`'s text is an **ATOMIK v3.5 (Altair) linkfile**: a small stub (`text $0..$0c3`) and
one LZ depacker (`text $0c4..$240`) that expands the whole game to the program base in a
single pass. No payload file, no chunk archive, no nested chain.

**[obs] It runs standalone from a folder** (`PMWW(disk=None, files_from='extracted/cobra26',
autorun_f='C:\\WW1.PRG')`): the Fuzion cracktro appears, then the game. So the base is one PRG
plus one data file — exactly the shape the 1990 game's carrier assumed.

## 2. The two builds are the SAME ENGINE — at the SAME addresses in-game [obs]

Careful: the `+$12686` offset seen in a first comparison was measured against a dump taken
**while the cracktro was running** (the game had not loaded yet). With the game actually in the
map view, the Cobra build's image sits at **exactly the Pompey addresses**:

- the pass head pattern `4a79 0005a856 6624 52b9 0002ed90` is found at **`$13da0`** in the Cobra
  map-view dump — identical to the Pompey build;
- the pointer words `$1d2b2/$1d2b4` are at the same address too;
- the runtime variables (`$2ed90` world counter, `$2edaf` buttons, `$2edb6` latch, `$50fd8`
  pass counter) are all at their Pompey addresses.

**Therefore the tick patch needs NO porting.** The unmodified `work/tickproto/tick.bin` applied
to the Cobra build gives **4.02 ticks/s at 8 MHz and 4.02 at 16 MHz** (unpatched: 3.60 and
7.62), with the game live — the same result as on the Pompey build.

The earlier `+$12686` region differences (`$1b000+`, 77-81% identical) are the asset tables:
the two releases load different data files, as expected.

## 2a. The cracktro phase looks different (but it does not matter)

While the Fuzion/ATOMIK intro plays, the image is at a different base, so a dump taken then
shows every address shifted. That is what produced the `+$12686` figure. For patch purposes
only the in-game state matters, and that is address-identical.

## 3. The Cobra data files

The game reads `WW1_FUZI.LFB` (217708 bytes) — the same `SPRITE8.PAK`-family data the Pompey
build keeps under `DATA\`. **[obs]** the strings `SPRITE8.PAK` and
`POWERMONGER WORLD WAR ONE DATA DISC` appear in both builds' memory at the same layout. The
`*.SCO`/`*.RAW` files belong to the cracktro and are not needed by the game.

## 4. Status: the tick is testable on this base

- **Base**: `extracted/cobra26/` (`WW1.PRG` + `WW1_FUZI.LFB`), runs standalone from a folder.
- **Harness**: `PMWW(disk=None, no_floppy=True, autorun_f="C:\\WW1.PRG",
  files_from=Path('extracted/cobra26'))` boots it; the standard navigation
  (`at_gate("name")` → type → `at_gate("opt")` → `poke_click(112,72)` → `poke_click(130,88)` →
  `poke_click(60,20)`) reaches the map view exactly as on the Pompey build, **with the default
  `delta=0`**.
- **Snapshot**: `work/snapshots/c26_mapview.sav`.
- **The tick patch**: the existing `work/tickproto/tick.bin`, applied live at `$72000`, gives
  4.02 ticks/s at both clocks.

## 5. Next steps for a deliverable

1. **Build the patched PRG**: `WW1.PRG` is a plain PRG with no payload and room to grow, so the
   1990 carrier design applies directly — append a data segment holding the patch code, a
   small front stub that copies it to `$72000`, and patch the seven sites at build time (they
   are the same file offsets the live test used: `$13da0` etc. are *runtime* addresses; the
   file offsets come from the ATOMIK depack of `WW1.PRG` — see item 2).
2. **The carrier problem that remains**: `WW1.PRG`'s text is ATOMIK-packed, so patching a site
   inside it requires re-packing (or patching the depacked image at run time from a front
   stub). The front-stub route avoids the repack entirely: the stub runs first, depacks as
   normal, and then a hook at the depack's hand-over applies the sites in RAM. That is
   exactly the 1990 `hook2` design, and the hand-over point is a single `jmp` at the end of the
   ATOMIK depacker (`text $1d4`-ish — to be confirmed).
3. Then `play.sh` with patch selection, and the floppy build (`cobra26.st` with `WW1.PRG`
   replaced).

