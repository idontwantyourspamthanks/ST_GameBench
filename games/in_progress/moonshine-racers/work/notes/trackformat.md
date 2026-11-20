# Moonshine Racers: track block, track JSON and campaign file (`MSTRACKS.TRK`) specification

Stage 1 of the track editor (user decisions 2026-11-20: tracks from a file first; editable = curves, hills, road widths L/R, roadside objects; race length not editable; a track set REPLACES the 15 tracks and every custom track names a base level; no minimap work; campaign disk like Nebulus).
Tool: `tools/msrtrack.py` (pure Python 3 + PIL). Tests/fixtures: `work/trackedit/`. Evidence of the game side: `work/notes/trackeditor.md` (the viability study; section numbers below refer to it). Everything big-endian (the 68000's order); words are 16 bit, "signed" means two's complement.

## 1. The three representations

| name | what | where |
|---|---|---|
| **track block** | the game's native byte stream, six streams back to back; the game parses it in place (`$fda2`) | `FILES\MS2` at `sector*512` (stock), a campaign file entry |
| **track JSON** | editable text form of exactly the same data (`msrtrack.py decode/encode`); lossless | `work/trackedit/fixtures/edit1.json` |
| **campaign file** | `MSTRACKS.TRK`: header + table + 1..15 track blocks; the artifact users exchange | campaign disk root, later `FILES\MSTRACKS.TRK` |

## 2. Track block (native, what the game reads)

Order and encoding (all words big-endian):

| # | stream | content | terminator |
|---|---|---|---|
| S0 | curve | repeated `count.w, delta.w(signed)` | `count = 0` word |
| S1 | left half-width | repeated `count.w, target.w` | `count = 0` word |
| S2 | right half-width | repeated `count.w, target.w` | `count = 0` word |
| S3 | hill | repeated `count.w, accel.w(signed)` | `count = 0` word |
| S4 | objects | `first.w`, then repeated `type.w, lateral.w(signed), gap.w` | the `gap` word `0` of the last object |
| S5 | object types | repeated 12-byte entries `ff00, kind, size, sprite(signed), w4, w5` | (see below) |
| end | | one zero word `0000` | |

Stream semantics (from the game's own code, study 1.2 / `$fda2 $fde0 $ff3a $ffe4 $e1e4`; the tool's `expand_*` reproduces the arithmetic bit for bit):

* **S0 curve**: one pair = `count` steps; every step `c += delta` (16-bit, wraps harmlessly), `c` = the road direction ring `$1bbc`; `delta` is curvature. Start value 0.
* **S1/S2 width**: one unit of distance = one step. The half-width byte starts at the FIRST target and then slews 1 per step toward the current pair's target (`$fe1c/$fe50`), so a width change of N takes N steps (a ramp). Stored as a byte: 0..255 possible, 10..85 stock.
* **S3 hill**: 32-bit integrator, `d3 += d2; d2 += accel` per step, start 0; height byte = `clamp(d3 >> 16, 0, 127)` (negative -> 0). `accel` is the second derivative, so a hill that returns to the ground needs `+a for n, -a for 2n, +a for n` (edit1: 50/100/50 at 1600). The integrator keeps running while the byte is clamped.
* **S4 objects**: `first` = distance of the first object from the start; each object is `(type, lateral, gap)` where `gap` = distance from THIS object to the NEXT one; the last object has `gap = 0`. So the JSON uses absolute `at` positions: `at[0] = first`, `at[i+1] = at[i] + gap[i]`. `type` is a **1-based** index into the S5 list (`type-1`, spawner `$e230-$e25e`); `lateral` is a signed word, -128..127 (half-road units, multiplied by the perspective factor in `$e38c`). The spawner reads the distance counter `$1346`: it takes the next object when the counter reaches <= 0 (an object whose slot is still busy is skipped: 32 scenery slots). The last object IS a real object (a gap of 0 only ends the list after it was spawned).
* **S5 object types**: 12-byte entries `ff00` (constant tag, never read), `kind` (0 plain, 1/3 variants, 2 two-sided), `size` (1..6), `sprite` (signed: >= 0 table `$3d16e`, < 0 per-level frames at `$5a402`), `w4`, `w5` (collision/size words). The game never scans for the end of S5 (it indexes it by type), the tool ends it at the first word that is not `ff00`. **A custom track carries its base level's table unchanged** (the sprites are the base level's graphics), enforced by `validate` through count + CRC32 constants (section 5).
* **end word**: all 15 stock blocks have `0000` after the last S5 entry. The game ignores it; the format requires it (it makes a block self-terminating for the validator).

Stock facts used by the tool (verified by `msrtrack.py selftest` against the PP conversion's `FILES\MS2`, md5 `cc3ff52922aed94663c5e03949921688`):

* Level n's track block starts at `MS2 + sector*512`, descriptor (sector, sectors) = table `$28a2` (embedded in the tool). The canonical block (S0..S5 + end word) is 3364..5770 bytes; the descriptor spans 3584..6144 bytes. **The bytes between the end word and the end of the descriptor are NOT free data**: in all 15 levels they hold the first 12..374 bytes of the next asset (the `Ice!`-packed object graphics, `Ice!` header at block offset `end+2`; the real copy starts at the next sector). The game never reads them as track data (the object graphics are loaded at `$5a400` afterwards), so they are padding for the tool. (The "free in block" column of study 1.3 counted this padding as spare room; it is the same spare room, but it is junk, not zeros.)
* **Race length** (not editable) = word 0 of the minimap header block of the level (`$57890`); table of the 15 values embedded: 19472 19720 19800 19000 19375 18000 18626 20000 19000 20000 20000 22000 18500 22000 23000.
* every ring stream of all 15 stock tracks sums to exactly **32768** units, the object lists end at 18.6k..22.4k, stock objects are 333..462 per level (3-word gaps 1..351).

## 3. Track JSON (`format "msr-track/1"`)

```
{
  "format": "msr-track/1",
  "name": "EDIT1 BEND HILL",          1..24 printable ASCII (campaign entry name)
  "base_level": 0,                    0..14: scenery/colours/sky/object types/race length come from this level
  "race_length": 19472,               informational; if present it must equal the base level's (not editable)
  "curve": [[count, delta], ...],     S0
  "left":  [[count, target], ...],    S1
  "right": [[count, target], ...],    S2
  "hill":  [[count, accel], ...],     S3
  "objects": [{"at": 71, "type": 38, "lateral": -41}, ...],   S4, increasing "at"
  "types": [[kind, size, sprite, w4, w5], ...]                S5, index = type-1; must equal the base level's table
}
```
Unknown keys are errors. `decode` writes every key; the JSON is lossless: `encode(decode(level))` == the stock block, byte for byte (15/15, `selftest`). The tool writes a hand-editable layout (one segment / object per line).

## 4. Campaign file `MSTRACKS.TRK` (version 1)

```
offset size  field
0      4     magic "MSTK"
4      2     version = 1
6      2     count   = 1..15 (entries, in campaign order: entry 0 = first race)
8      4     file length (bytes, the whole file)
12     4     CRC-32 (IEEE 802.3, zlib) of bytes 0..11 followed by the entry table (16 .. 16+40*count-1)
16     40*count   entry table, entry i at 16 + 40*i:
         +0   24   name  ASCII 0x20..0x7E, NUL padded (1..24 chars; 24 chars have no NUL)
         +24  2    base level 0..14
         +26  2    flags = 0 (reserved, must be 0)
         +28  4    block offset from the start of the file (= 16 + 40*count + sum of the lengths of the earlier blocks)
         +32  4    block length in bytes (even, 2..8192)
         +36  4    CRC-32 of the block
16+40*count  the blocks, back to back in entry order, each exactly the track block of section 2 (canonical: no padding)
```
Maximum file: 16 + 15*(40 + 8192) = **123,496 bytes** (a stock 15-track campaign is 64,676). A reader checks, in this order: magic, version, count 1..15, file length == actual, table CRC, per entry flags == 0, name, base < 15, offset == running position (blocks are contiguous), length even and within 2..8192, block CRC; the file must end at the last block. Any failure refuses the whole file (`E-CAMP`).

**Why 8192 bytes per block**: the stock working buffer is 6144 bytes (`$58c00-$5a3ff`, the largest descriptor = level 0), the largest canonical stock block is 5770 bytes (level 0: 417 objects x 6 + 131 types x 12 + 421 pairs x 4 + terminators). 8 KB leaves ~2.4 KB (about 400 more objects, or ~600 more segments) on the biggest level and is a power of two (a 15-slot working set = 120 KB at >= 2 MB). The loader copies a block as is to its working buffer and points `$23c0/$1bb0/$1bb4/$27da/$133a/$1342` at it (`$fda2`).

Entry order = campaign order; **a track set replaces the 15 stock tracks** (several entries may share one base level in the stage-2 loader; `patch-ms2` cannot, see section 7).

## 5. Limits and validation rules (`msrtrack.py validate`)

`ERROR` = refused by `encode`, `campaign new/add`, `patch-ms2` (override `--force`); `WARN` = printed only. `--lenient` demotes the "stock-envelope" range errors (marked *R*) to warnings.

| code | rule |
|---|---|
| E-FORM | JSON shape: required keys, integer fields, `objects` entries exactly `{at,type,lateral}`, 5-field `types`, values fit their 16-bit word, no unknown keys, `format` = `msr-track/1` |
| E-BASE | `base_level` integer 0..14 |
| E-NAME | name 1..24 printable ASCII |
| E-RACELEN | `race_length` present and different from the base level's |
| E-STREAM | stream not empty; every `count` 1..65535 (0 is the terminator) |
| E-RANGE *R* | curve `delta` -9..10; width `target` 10..85 (left and right); hill `accel` -6000..4000 - exactly the envelope of all 15 stock tracks (study 2.2); anything else is untested in the game |
| E-SUM | each of the four ring streams must cover at least **race length + 1024** units (the ring is filled 1024 ahead; stock tracks pad to 32768) |
| E-HILL | the 32-bit hill integrator must not overflow (it would wrap the height byte to garbage) |
| E-OBJ | at least one object; first `at` 1..32767 (the first gap word must be non-zero) |
| E-GAP | objects strictly increasing in `at`; every gap 1..32767 (gap 0 would end the list early) |
| E-TYPE | `type` 1..N where N = number of object types of the base level (131, 77, 93, 63, 37, 31, 30, 34, 28, 32, 42, 40, 53, 36, 32) |
| E-LAT *R* | `lateral` -128..127 |
| E-TABLE | `types` identical to the base level's (count + CRC-32 of the 12-byte entries) |
| E-SIZE | block <= 8192 bytes (campaign) / <= the slot's sector budget (`patch-ms2`); no unused bytes after the end word; even |
| E-TERM | (raw blocks) a stream, the object list or the end word is missing/truncated |
| E-CAMP | campaign file structure (section 4) |
| W-SUM | the four streams cover different lengths (stock: all 32768) |
| W-CURVE | curve value `c` leaves the stock range -4473..8876 |
| W-HILL | the height byte sits at the 127 clamp for > 300 race units |
| W-DENS | >= 32 objects inside 888 units (the pool has 32 scenery slots; stock maximum 31); extra objects are skipped by the game |
| W-OBJEND | the last object lies beyond the ring streams |

Not checked (unknown/unproven): the exact win/finish rule (study 1.4), opponent behaviour, whether strongly off-envelope values break the road renderer.

## 6. Campaign disk

`msrtrack.py disk CAMP.trk -o X.st|X.msa`: 720 KB double-sided FAT12 floppy (80 tracks x 2 sides x 9 sectors; BPB 512 B/sector, 2 sectors/cluster, 2 FATs x 3 sectors, 112 root entries, media `$F9`), volume label `MSRTRACKS`, **one root file `MSTRACKS.TRK`** (contiguous clusters from 2), non-executable boot sector, boot-sector serial = first 3 bytes of md5(file) (TOS notices a swapped disk by the serial), fixed timestamps (deterministic output). Same geometry/serial rule as the Nebulus campaign disk (`nebcampaign.py`), implemented in-tool (no mtools needed to build; checked with `mdir/mcopy`). `.msa` = uncompressed Magic Shadow Archiver. `validate X.st` extracts and checks the file.

## 7. `patch-ms2` (test aid, no game patch)

`msrtrack.py patch-ms2 CAMP.trk -o MS2.new` copies `FILES\MS2` and writes each entry's block at `sector*512` of the slot of its **base level**, refusing a block larger than that slot's sector run (3584..6144 bytes) and two entries with the same base level; bytes after the block stay as they were. This replays exactly what the game loads when it parses the slot (proof: `trackeditor.md` section 3 for one edited word; this stage's Hatari run for a full edited track). The scenery/sky/colours/object graphics are tied to the slot, so the campaign order cannot change this way: that is the stage-2 loader's job (it redirects `$77da`/`$fda2` to a working copy of the entry). A stock campaign (`campaign new --stock`) patched into MS2 reproduces the original byte for byte (`selftest`).

## 8. Tool reference

```
msrtrack.py decode [N|--all] [-o OUT]      stock MS2 -> JSON (one level to stdout/-o FILE, --all to a directory)
msrtrack.py encode|build TRACK.json -o OUT.bin    validate, then write the track block
msrtrack.py validate FILE...               .json | .bin --base N | .trk | .st | .msa ; exit 1 on any ERROR
msrtrack.py render SRC -o OUT.png          SRC = level N | track.json | FILE.trk --entry K  (path, curve, elevation, widths, objects; no minimap)
msrtrack.py campaign new OUT.trk [--stock] [track.json ...] | add CAMP track.json [--at I] | remove CAMP I | list CAMP | extract CAMP I -o OUT [--bin]
msrtrack.py disk CAMP.trk -o OUT.st|.msa [--label NAME]
msrtrack.py patch-ms2 CAMP.trk -o MS2.new [--check-only]
msrtrack.py selftest                       15-level round trip + campaign/disk/patch self checks
global: --ms2 FILES/MS2   (default originals/MOONSHR/FILES/MS2)   per command: --lenient, --force
```
Tests: `python3 work/trackedit/test_msrtrack.py` (18 tests). Fixtures: `work/trackedit/make_fixtures.py` regenerates `edit1.json` (level 0: new S-bend units 100-400, hill 100-300, left road wider 100-250, right narrower 300-500, three moved objects) and the three `broken_*.json`.
