# Moonshine Racers patches — format, boot mechanism and address map

Tool: `python3 tools/msrpatch.py list | verify | build | live | version | doc`. Design copied from Midwinter 2 (`mw2patch.py`) and
Populous 2 (`pop2patch.py`), re-derived for PP's Moonshine Racers HAGA conversion. Evidence (disassembly, hook instants, boot logs) is in
`work/notes/delivery.md`.

## Patch format (`patches/*.s`, vasm mot syntax)
Header comment lines before the first `org`; then one code segment per `org`:
`; name: X` · `; default: no|yes` (default yes) · `; site: $addr` (RAM site, required for a RAM patch) ·
`; orig: <hex>` (expected original bytes; optional, the tool derives them from the RAM dump and cross-checks both dumps) ·
`; phase: boot` (optional and the only phase: every patch site is loaded when the trampoline runs) ·
`; data: $addr len [free]` (zero-initialised blob-owned data, repeatable; `free` = outside the payload image, not zeroed) ·
`; media: floppy` (built only by `build --floppy`, `work/notes/floppy.md`; a `--only` list for the HD build refuses it) · `; disk: A|B $offset <orig hex>` (floppy disk patch: an edit of the .ST image at that file offset, no `; site:`; the segment whose `org` equals the offset gives the new bytes, same length; `build --floppy` and `verify` check the original bytes in the STX conversion; repeatable) · `; note: ...` (repeatable) · `; doc: ...` (one line for PATCHES.TXT).
`; ram: $lo-$hi [label]` (RESERVED run-time work RAM, inclusive end, repeatable: NOT part of the payload image and not zeroed by it, so it does not count against `IMG_MAX_LEN`; the tool still checks it like a blob: it must lie inside the free run of every layout the build supports (1 MB; 4 MB only with `pp_bigram_cache` or in the floppy build; a HD build without that file patch is refused), must not overlap any other patch's site/blob/data/ram or the site table (`verify` pairs every patch with every other; `build` the selection), and `verify` demands that it is zero in the stock game's RAM dumps (hook instant, entry, three race dumps)) ·
`; requires: A B ...` / `; conflicts: A B ...` (patch dependencies: `build`/`live` (also `--only`), the default selection and `verify` refuse a selection that lacks a required patch or holds a conflicting one, with a message naming both; unknown names are an error; a pair of patches whose footprints overlap must declare `conflicts`, `verify` refuses undeclared overlaps).
Equates (`NAME equ value`) may precede the first `org`. The tool predefines `IB` (payload image base `$B2700`) and `TABLE` (site table `$B7000`).
The segment whose `org` equals the site gives the NEW bytes (at most the orig length, nop-padded). Every other segment is a BLOB at a fixed
absolute org inside a blob area (below). `org` takes `$B2800` or `IB+$100`.
`@VERSION@` in any source (and in docs, via `msrpatch.py doc FILE`) is replaced by the release version; the token `{PATCHES}` in a doc expands to
the default patch list, `{RAM}` to the payload/reserved-RAM map of the default set (the same map is the tail of `msrpatch.py list`).

File patch (PP's resident loader HAGA, `; image: HAGA`): `; edit: <HAGA file offset> <expected original hex>` (repeatable) and one segment
`org HB+$<offset>` per edit with the same length (HB = the RAM base of HAGA: `$F8000` 1 MB, `$1F8000` 2 MB, `$3F8000` 4 MB+; used only for
pc-relative references: `verify` assembles at the three bases and demands identical bytes). `build` refuses to apply over different bytes.
File patches are not applicable to `live` (HAGA is already resident in a snapshot).

## Where the game is delivered, and what runs when (details with disassembly: `work/notes/delivery.md`)
`RUNME.TOS` (shipped unpacked and edited at two points; `pp_depack` unpacks PP's LZ):
1. **Staging.** The stack-phase block (RUNME text `$352`-`$ad1`, copied by PP to `a3 = $B1F44` at 1 MB) ends the stage phase with
   `jmp $78000.l` (text `$3b4`, RAM `$B1FA6`; `$78000` = PP's stage 1 `MSR_S1.FIC`, unpacked). That `jmp` becomes `jmp copy.l` into a copy
   routine appended to RUNME's data segment, which copies the **payload image** (appended after it) to `IB = $B2700` and continues with the displaced
   `jmp $78000.l` (registers and SR preserved). The disk loads that follow (stage 1 and the game from MS1/MS2) never touch RUNME's TPA data
   before this point, and `$B2700` is above PP's chunk cache (`$81000-$B1D40`) and the stack-phase copy (`$B1F44-$B26C3`).
2. **Trampoline.** PP's patcher ends with `jmp $1000.w` (text `$45c`, RAM `$B204E`, 4 bytes + 2 zero padding bytes) — after PP's last RAM patch,
   right before the game starts (`$1000` = `bra.w $6f50`). It becomes `jmp $B2708.l`. The trampoline (`core.s`) runs in supervisor mode, IPL 3, with
   all of the game loaded: it VERIFIES every site's original bytes, APPLIES all or nothing, writes the marker, flushes the 68020+ caches and ends with
   `jmp $1000.w`.
3. **RUNME relocation.** Growing the data segment by N bytes moves the bss: the header data length, every relocated long that addresses the bss (>= text
   `$4446`) and the reloc table (re-encoded, round-trip checked) are adjusted; the four `lea d(pc),aN` that address the bss (text `$98`, `$b34`, `$40fa`,
   `$410c`) cannot span the payload as 16-bit displacements, so each becomes `movea.l d(pc),aN` (same 4 bytes, same register, no flags) reading
   a relocated pointer from two slots behind the copy routine. `verify` scans the whole text for any other `d16(pc)` operand that reaches the bss.

Marker at `$B2700`: `MSPO` = all sites applied, `MSPF` = a mismatch, nothing applied, zero = the trampoline never ran. A zero-patch build behaves like PP's
build plus the staging and the marker (**not pristine**: it still contains the staging, the HAGA file patches and the changed RUNME).

## Address map (1 MB layout; the same addresses at 2 MB, 4 MB (with `pp_bigram_cache`) and on TT/Falcon)
| Range | Contents |
|---|---|
| `$81000-$B1D40` | PP's HAGA chunk cache (loads only; 1 MB layout) — never use |
| `$B1F44-$B26C3` | PP's stack-phase block copy (running until the game starts) — never use |
| `$B2700-$B2703` | marker `MSPO` / `MSPF` |
| `$B2708-$B27FF` | trampoline + cache flush (`patches/core.s`, 248 B available) |
| `$B2800-$B6FFF` | **blob area A (18 KB)**. Allocated: `test_marker` `$B2800-$B2815` + long `$B2FF0`, `test_framecount` `$B2900-$B2913` + counter `$B2FF4`, `test_blob36k` `$B3000-$B3025` + ramp `$B3100-$B311F` (conflicts with `mr_edge`, declared), `mr_edge` `$B3040-$B3289`, `mr_map` `$B3400-$B37F1`, `mr_digit` `$B3C00-$B3CCD`, `rd_geom` `$B4000-$B444F`, `rd_draw` `$B5000-$B5719`, `rd_init` `$B6000-$B6013` (`mr_map` / `mr_digit` are `default: no` since the new HUD: dead code); **free: `$B3D00-$B3FFF`, `$B4500-$B4FFF`, `$B5800-$B5FFF`, `$B6100-$B6FFF`** |
| `$B7000-$B7FFF` | site table (16 B per site + 4 B terminator) + orig/new byte pool, 4 KB |
| `$B8000-$E83FF` | **blob area B (225 KB)**: a blob/data org here extends the payload image up to its highest byte (zero padded), up to the image limit below. Inside the image the bytes are zero in the file, i.e. zero at game start. Allocated: `mt_clock` `$B8000`, `mt_sync` / `mx_sync` `$B8100` (+`mx_sync` `$B8380 $B8400`), `mt_pre` `$B8200`, `mx_pre` `$B8300`, data `$B8F00-$B8F0B` (CLK, NEXT, PEND), `mx_sync` data `$B8F20-$B8FFF $B9000-$B9DFF`, `mx_pre` data `$B9E00-$BA8BF`, **new HUD `hd_*`: code `$BB000-$BB2xx` (+ `hd_init` `$BB700`, `test_hdref` `$BB100`), strip bitmap `$BB800`, glyph strips `$BC200`, gauge rows `$BCA40`, cell offsets `$BCD00`, decimal pairs `$BCD20`, shadows `$BCF00/$BCF40` (data), scratch `$BCF80`, dial images `$BD000-$BDFFF`**. **Reserved work RAM (`; ram:`, not in the image): `$D0000-$DAFFF` `rd_geom` (magic, product table, standing result), `$DB000-$E7FFF` `rd_draw` (window tables, WPTR `$E7040`)**; free: `$BE000-$CFFFF` (`$BA8C0-$BAFFF` too). The default set's payload is 47,360 B (`$B2700-$BDFFF`) |
| `$E8400-$F2FFF` | unused by the study's map (its free-RAM run ends at `$E8400`): treat as unavailable unless measured |
| `$F3000-$FB700` | PP's resident HAGA at 1 MB (moves with RAM size) |

Image limit `IMG_MAX_LEN = $F000` (61,440 B: `$B2700-$C16FF`): RUNME refuses to start ("Too much low RAM occupied") when its bss start + `$8000` reaches
`$38270` on a 1 MB machine (RUNME text `$98-$c8`; `lea $4666(pc),a1` + `adda.l #$8000`). Measured headroom and the capacity test: `work/notes/delivery.md` section 6.
`; data: ... free` reservations outside the image are not zeroed: initialise them lazily behind a magic long (rendering.md shows `$B2700-$E8400` zero at
game start on 1 MB, but not at 4 MB without `pp_bigram_cache`).

## Patches
- `pp_bigram_cache` (HAGA file patch, `default: yes`): PP's loader switches to a "whole image" disk cache on 68000 machines with >= 4 MB (`$81000-$C6F2B` for MS1,
  `$81000-$13D7FF` for MS2), which overwrites the payload. The patch keeps the 1 MB chunk cache (identical to Midwinter 2's patch; same HAGA md5).
- `mr_edge` (`default: yes`), `mr_map`, `mr_digit` (`default: no` since `hd_stage`: the minimap kernel and the score-digit kernel are only reached through routines the new HUD no longer calls; files kept) (pixel-identical render patches, `work/notes/render_patches.md`): `mr_edge` the road edge-colour routine `$1058a` (one of 8 generated code slots per frame), `mr_map` the minimap draw `$12690` (unrolled row loops), `mr_digit` the HUD score-digit kernel `$14d98`. `mr_negctl` (`default: no`) is the gate negative control (breaks the edge colours on purpose).
- `hd_stage`, `hd_init`, `hd_clouds` (`default: yes`, VISIBLE change, `work/notes/hud_build.md`, design `work/notes/hud_design.md` layout A): the new top-bar HUD and no clouds. `hd_stage` (site `$ef7a`, the HUD stage called once per pass from `$7b4c`; blob `$BB000`, generated by `tools/msrhudgen.py`, do not edit `hd_stage.s` by hand) replaces
  the thirteen stock HUD calls and the cloud erase/draw by one 16-row black strip with score, clock dial, race position `#`, speed `MPH` (high word of `$10d8`, 128 with turbo), gear `G` (1/2), engine temperature `T` (hot colour from 28) and the turbo gauge (cup icon + 28-pixel bar); it keeps the message ticker `$11ef0` (its state machine gates the race end),
  the face `$f90c` and the hit/sound part of the old cup routine (`$11ce` -> sound `$36`, `$11cf` slosh counter evolve exactly as stock). Every field is compared with a per-buffer shadow (`$BCF00` for `$70000`, `$BCF40` for `$78000`) and redrawn only when it differs from what THAT buffer shows. The first pass into a buffer after the race init paints the strip and the
  sky (all planes set) over rows 16-64; `hd_init` (site `$edea`, replaces the cloud init `$dd18`) clears the shadows' `painted` bytes at every race start/restart. `hd_clouds` (site `$7b3a`) removes the cloud position update `$dd50`. Palette A colour 14 (`$3cf0`) is set to `$777` every pass: white text. The occupancy map `$6f000-$6ffff` has no reader any more
  (its only readers were the cloud passes): face and message path still write it (dead work, kept: shared kernels), proof `hud_build.md` section 6. `hd_init` requires `hd_stage`; `mx_sync` requires `hd_stage` (its extra frames call TOPBAR `$BB000`, the ticker with saved state and the face).
- `test_hdref` (`default: no`, gate reference only, conflicts `hd_stage hd_init`): the stock stage reduced to ticker + face; with `hd_clouds` it draws "the stock game minus HUD and clouds", the reference of `tools/msrmask.py`.
- `rd_geom`, `rd_draw`, `rd_init` (`default: yes`, `work/notes/road.md`, `work/notes/integration.md`): the faster road, pixel-identical. `rd_geom` replaces the road geometry `$100b4` (blob `$B4000`; entry for the pass `$B4004`, pre-warm entry `$B4000`),
  `rd_draw` the span draw `$17c42` (blob `$B5000`; pass entry `$B5004`, pre-warm entry `$B5000`). Together -67 k cycles per driving pass (-8.9 %) and -123 k standing (-17.5 %) on top of `mr_*`. They need free RAM `$D0000-$DAFFF` / `$DB000-$E7FFF` (declared with `; ram:`; zero at start, tables built lazily behind a magic long / the colour-table pointer WPTR).
  The tables cost about 18 VBL once (geometry product table 0.9 M cycles, window tables 2.0 M cycles). `rd_init` (site `$78f6`, the `jsr $fde0.l` of the race setup, after the game has built `$4564 $4644 $4ff8` and set `$135a`) calls both pre-warm entries so the generation happens while the race is set up, before the race loop (`$7a88`);
  the lazy paths stay as the fallback. `rd_init` requires `rd_geom rd_draw`; `rd_geom` and `rd_draw` are independent of each other. The 4 MB layout needs `pp_bigram_cache` (the tool refuses a HD build with `rd_*` without it).
- `mt_clock`, `mt_pre`, and a pacer = `mx_pre` + `mx_sync` (`default: yes`) or `mt_sync` (`default: no`) (`work/notes/tick.md`, `work/notes/timing.md`, `work/notes/extrap.md`, `work/notes/integration.md` section 8): the fixed real-time tick. `mt_clock` (VBL clock in 1/300 s, site `$d128`) is required by the pacer (after the race pass flip, site `$7b74`) and `mt_pre` (latch guard before the first back-buffer write, site `$7b0a`); the pacer also requires `mt_pre`.
  `TICK equ 30` in `mt_sync.s` AND `mx_sync.s` (5 VBL at 50 Hz, 6 at 60 Hz = 10 passes/s; exact at both): the game runs 20 % faster than the stock 8 MHz driving speed (8.33 passes/s) by design (user-approved) and at that speed on every CPU clock; a pass that needs more than a tick just runs late (no sleep, resync after more than 2 ticks). Change both equates together.
- `mx_sync` (+ `mx_pre`, site `$7b46`; `default: yes`, user-approved): the pacer WITH extra in-between frames. In the idle time of each tick (only where the machine has spare time: 16 MHz Mega STE / accelerated STE about 2 pictures per game step, 32 MHz 3-4; an 8 MHz STE draws none and pays one byte test per pass) it draws the same logic step again at a camera pose extrapolated from the last step (road/scroll/objects/AI cars/lateral position advanced, no game logic run), then restores every word it changed. Game speed and main frames are identical to `mt_sync`'s. `mx_sync` conflicts with `mt_sync` (same site; the tool refuses both) and requires `mt_clock mt_pre mx_pre`; `mx_pre` requires `mx_sync`. `mt_sync` is the fixed-tick-only alternative: `tools/play.sh --noextrap` builds it for comparison. Known tolerance: main frames are identical to stock except up to 2 bytes (2-10 px) at the cloud/mountain edge in the sky rows on some tracks (track 1 identical; tracks 5/12 and the levels 0-14 emulator sweep measured in `integration.md` section 8.3; the cloud erase `$122e4` keeps draw history there). It goes away when the clouds are removed.
- `test_blob36k` (`default: no`): payload-capacity test at the same site as `test_marker`: a blob at `$B3000` (beyond the image's natural end)
  plus 1 byte of `free` data at `$C16FF` pads the image to exactly `IMG_MAX_LEN` (61,440 B), and the blob writes `MSTM` + a 16-word ramp at
  `$B3010`. A pass proves the bigger RUNME data segment loads on 1 MB and the copy routine covers the whole image.
- `test_framecount` (`default: no`): per-frame counter at `$B2FF4` (site `$d1ca`, the flip), for A/B work through `live` and for comparing
  against `msrbench.py`'s flip count. `tools/msr_live_test.py` runs it on a snapshot.
- `test_marker` (`default: no`): hooks the game's first run-time code (`$6f5e`, `lea.l $70000.l,a0` in the trap #2 handler `$6f5a`) with a blob at `$B2800` that
  writes the long `MSTM` to `$B2FF0`, replays the `lea` and returns to `$6f64`. It proves staging, trampoline, patch application and the blob area.
  Check in the emulator: `m $b2700 8` -> `MSPO`, `m $b2ff0 4` -> `MSTM`.
- The release credit (`v@VERSION@ enhanced by dad_prg`) is a later task; the mechanism is reserved: `patches/VERSION` is the one place of the version number
  (`msrpatch.py version [--credit]`, the `@VERSION@` token in sources and docs, zip names).

## Floppy (original STX disks, `build --floppy`)
`python3 tools/msrpatch.py build --floppy [--only N ...] [--out build/floppy] [--zip]` builds the two-disk release from the original STX disks
(`originals/floppy/*.stx`, git-ignored; never modified): `build/floppy/disk_a.st` (disk A + payload + hooks + protection neutraliser) and `disk_b.st`
(byte-identical to the original disk B). Design, evidence and gates: `work/notes/floppy.md`; summary in `work/notes/delivery.md` section 7.
- **Payload delivery**: the boot sector's first original instruction (offset `$18`) branches to a stage-0 loader in the sector's free area; it reads the image
  (`core_floppy.s` trampoline at `$B2708`, site table at `$B2820`, blobs, 26,636 B with the default set) from blank sectors of disk A (track 0 sectors 2-10 and
  tracks 50-61 side 0; 129 sectors allocated, each checked blank) to `$B2700` with XBIOS `Floprd`, then the original boot code runs. The header (`60 04`,
  "MOON") is unchanged: the game recognises disk 1 by it. The same RAM patches (`patches/*.s` with a `; site:`) apply as in the HD build (`build --floppy`
  additionally requires their original bytes in the floppy game's RAM, `work/floppy/ram_answered.bin`: all current sites match). `$B2700` marker as in HD.
- `fl_hook` (`; media: floppy`, always included): disk A `$C350` (RAM `$6f50`) `move.l #$6f5a,$88.w / trap #2` -> `jmp $B2708.l`: the trampoline runs when the loader starts the game.
- `fl_deprot` (`; media: floppy`, default yes): disk A `$E3D0` (RAM `$7bd0`, the manual-lookup routine's first two instructions `7e02 3f07`) -> `bra.w $7d1a` (`6000 0148`),
  the routine's own "accepted" exit: the question is never asked. Instruction-level evidence: `floppy.md` section 6.
- Disk 2: the game asks for it itself ("Insert Disk 2 and press a key.") and reads all disks through drive A; swap the disk in drive A and press a key. Hatari: `hatari-option --disk-a <copy of disk_b.st>` (floppy.md section 7).
- The HD-only `pp_bigram_cache` (HAGA) and RUNME edits are not part of the floppy build.

## Tool
```
python3 tools/msrpatch.py list
python3 tools/msrpatch.py verify                      # every site's orig vs both RAM dumps, RUNME edit points, bss scan, HAGA edits: must end `ALL OK`
python3 tools/msrpatch.py build [--only N ...] [--out build/hd] [--zip [PATH]]    # --only replaces the default set (`--only` alone = zero patches)
python3 tools/msrpatch.py build --floppy [--only N ...] [--out build/floppy] [--zip [PATH]]   # the floppy release (see Floppy)
python3 tools/msrpatch.py live  [--only N ...] [--out build/live/patches]         # <out>.img (load at $B2700) + <out>.json for stharness capture_frames(live=...)
python3 tools/msrpatch.py version [--credit]
python3 tools/msrpatch.py doc FILE                    # FILE with @VERSION@ and {PATCHES} replaced
```
Boot-test a build: `python3 tools/msr_boot_test.py --machine ste --mem 4096 --game build/marker --peek b2700 b2ff0` (cold boot, SPACE navigation to the first race,
raw memory printed). Instruments: `tools/msrhook.py` (registers/memory/RAM dump at given PCs during a cold boot).
