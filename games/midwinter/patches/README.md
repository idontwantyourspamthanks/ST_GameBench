# MW1 patches — format and boot mechanism

Midwinter 1, PP's HAGA hard-disk version. Ported from `games/midwinter2` (same HAGA file, md5 b34607ed…).
Evidence for every address below: `work/notes/loading.md`.

## Patch format (patches/*.s, vasm mot syntax)
Header comment lines before the first `org`; then one code segment per `org`:
`; name: X` `; default: no|yes` (default yes) `; site: $addr` (RAM site, required)
`; orig: <hex>` (expected original bytes; optional, the tool derives and cross-checks them)
`; phase: boot|deferred` (optional; auto: `boot` unless a `; load:` line is present)
`; load: MWB 33 $53bf0` (deferred sites: image, directory file number, RAM destination of the file that
carries the site; the tool takes the original bytes from that file in the image)
`; data: $addr len` (blob-owned zero-init data reservation, repeatable)
`; media: floppy` (built only by `build --floppy`; `orig` = raw image bytes, see "Floppy build").
The segment whose `org` equals the site yields the NEW bytes (must be <= orig length, nop-padded).
Segments with another `org` are BLOB code at a fixed org in the free payload area `$B3100-$B9FFF`.
`patches/core.s` holds the mechanism (trampoline / load-hook exit / deferred applier).
File patches (`; image: HAGA`, `; edit: <offset> <orig hex>`, `org HB+$<offset>`) edit PP's loader
service in the build copy; they are identical to MW2's.

## Sites: what the original bytes are
- **Boot sites** lie in the resident game: MWA file 1 of the stage-2 table (sector 195, 185 kB, loaded to
  `$7E4-$2DD32`). RAM after boot = image bytes + PP's 12 RAM patches (`PP_PATCHES` in the tool). The tool
  checks every `orig` against image+PP **and** against `work/dumps/ram1mb_options.bin` (unpatched 1 MB STE
  boot at the Game Options screen).
- **Deferred sites** lie in a file the game's own loader `sub_010cd2` brings in later (directory tables
  `$258A6` = MWA, `$2590C` = MWB, inside the resident game). They need `; load:`.
  Only memory that is *unchanged after loading* may be patched (files MWA 6 and MWB 36 are rewritten in
  place after the load; MWB 33/47/30/31/48 and MWA 1-5 were found byte-identical to the image in RAM).

## Where PP's patcher comes from and how it is modified
`RUNME.TOS` ships LZ-packed; `work/dumps/RUNME_unpacked.tos` is its unpacked image (`tools/pp_depack.py`),
which the tool edits reloc-aware. Its stack-phase installer (text `$2EC-$352`) copies text `$354-$C63`
to `$B1F44-$B2853` and jumps into it (chunk-cache mode; evidence `A3 000B1F44 A7 000B1F40`). That block
holds PP's patch code and the end of the chain is the one we hook:
1. text `$3AA` (RAM `$B1F44+$56`): `jmp $d000.l`, the fallthrough into the boot stub, becomes
   `jmp <data start>.l` (+1 reloc entry). The 26-byte copy routine appended to RUNME's **data segment**
   copies the payload image to `$B3000` and then does the original `jmp $d000.l`.
2. text `$482` (RAM `$B2072`): PP's patcher tail `jmp $800.w` (the game entry) plus the two zero pad bytes
   behind it (6 bytes, verified) become `jmp $B3000.l`. The trampoline verifies, applies, then `jmp $800.w`.
   By then stage-2 has loaded the whole game and PP's second patch block (text `$3EE-$481`) has run, so the
   trampoline sees exactly the bytes in `expected_ram()`.
3. The data segment grows by N = 26 + 8 + `$8000` = 32802 bytes: header data length, every relocated long
   that addresses bss (>= text `$44D0`) is adjusted by +N, and the reloc table is re-encoded (round-trip
   asserted). A signed 16-bit pc displacement cannot span that, so the four `lea d(pc),aN` that address bss
   (text `$98`, `$BBE`, `$4184`, `$4196`) become `movea.l d(pc),aN` (same 4 bytes, same registers, no flag
   change) loading a relocated pointer from two slots (text `$44EA` = bss+`$220`, `$44EE` = bss start; two new
   reloc entries) behind the copy routine. `check_bss_pcrel_complete` scans the whole text for any other
   `d16(pc)` / `d8(pc,Xn)` operand reaching bss and aborts if one is not handled (six words that merely look
   like one are listed in `NOT_CODE`, each justified in `work/notes/loading.md` section 7).
`$B3000-$BAFFF` is zero at staging time and nothing but our trampoline/hook/blobs writes there afterwards.
RUNME's "HAGA buffer + $8000 below `$38270`" check (text `$98-$C8`) still passes: TPA grows by 32 KB.

## Runtime behaviour
Trampoline (`$B3000`, entered from PP's tail): presets `MWPF` at `$B2FF8`; **pass 1** verifies the ORIGINAL
bytes of every phase=boot site, **pass 2** (only if all matched) writes them and sets `MWPO`. One wrong
original therefore applies nothing (MW2's single-pass trampoline applied sites that preceded the bad one;
T6 in `work/notes/loading.md`). Then `jmp $800.w`. With zero patches the game behaves as the original,
with the `MWPO` marker set.
Deferred sites: the boot site `$10D6C` (the single success exit of `sub_010cd2`, bytes
`33df 000062b8` = `move.w (a7)+,$62b8.l`, 6 B) becomes `jmp $B3070.l`. `hookexit` saves the registers, runs
the applier (`$B3090`) on the load that just finished — destination `[$2C34A].l`, length `[$2DB02].l` — and
then repeats the original exit. The applier writes the sites that lie inside the load range, idempotently
(orig -> apply, new -> already done, else `MWPF` and the site is left).
The splice MUST be `jmp`, never `jsr`: hookexit replays `move.w (a7)+,$62b8.l; movem.l (a7)+,d0-d7/a0-a6;
rts` from the unchanged `(a7)` frame.

## Test patches
- `test_boot_text` (boot): the Options label `MOUSE` at `$250EA` becomes `PATCH` (visible on the screen).
- `test_load_cursor` (deferred): MWB file 33 (348 B, loaded to `$53BF0` before the Options screen) gets 8 bytes
  at `$53C30` set to `$FF`; RAM proof only.
- `floppy_secbypass` (`media: floppy`, default no): `rts` at `$12050`, PP's bypass of the game's manual
  "FVPF SECURITY CHECK" which a floppy boot lacks.

## Tool
`python3 tools/mw1patch.py build [--only N ...] [--out build/game] | build --floppy | list | verify | files | live`
`build` aborts when `verify` fails. `files` prints the stage tables and the game's directory tables with their
xor checksums. `live` writes `<out>.img` (payload) + `<out>.json` (sites) for applying a patch set to a snapshot
(the load hook is omitted: in a snapshot every overlay is already loaded).
Capacity: `PAYLOAD_LEN` = `$8000` ($B3000-$BAFFF): core `$B3000-$B30FF`, site table + byte pool at the top
(`$BA000-$BAFFF`), blob code/data in `$B3100-$B9FFF`.

## File patches: PP's loader service (file HAGA)
Same HAGA, same two patches as MW2, both `default: yes`:
- `pp_nofade`: removes the grey palette fade PP's service performs around every disk read.
  MW1 measurement (T5): Capt Stark -> map (2 chunk reads) 25 palette-register changes -> 1.
- `pp_bigram_cache`: 2 bytes at HAGA+`$3228`; on a 68000 machine with >= 4 MB the unpatched HAGA reads each
  whole 400 KB image to `$81000-$E5000`, over the payload; the patch keeps the 200000-byte chunk cache.
HAGA moves with RAM size (`$F8000` 1 MB, `$1F8000` 2 MB, `$3F8000` 4 MB+), so the tool assembles each
segment at all three bases and requires identical bytes.

## Floppy build (`build --floppy`)
`python3 tools/mw1patch.py build --floppy [--only N ...] [--out build/floppy] [--zip [PATH]]` writes
`MWA.st` (patched), `MWB.st`, `MWC.st` (verbatim). Details and test log: `work/notes/floppy.md`.
- MWA is bootable (boot sector sum `$1234`): it loads 12 sectors from sector 2 to `$CFE4` and jumps to `$D000`; that
  stub loads the stage-2 program (sector 558, 75566 B) to `$3DF28`; stage-2 loads the title pictures and the
  resident game with its own FDC code and ends in `jmp $800.l` (`$3E1AA`). RUNME, PP's patcher and HAGA never run.
- Injection: payload in 64 free sectors of MWA (706..769, format filler `$E5` before). A 44-byte stage 1 sits in
  two unreferenced stage-2 routines (`$3EE3C-$3EE73`); it rewrites stage-2's table entry 2 (the second title
  picture, no longer needed), calls stage-2's own loader and jumps to `$B3000`. Stage-2's final jump now goes to
  stage 1. The trampoline is unchanged and ends in `jmp $800.w`.
- None of PP's RAM patches exist on floppy; a boot site that overlaps one aborts the build unless it is
  `media: floppy`.

## Display patch gate
`python3 tools/mw1ab.py --only <patches> [--base ...]` (see `work/notes/p4_raster.md` section 1): pixel identity of all three buffers on
`stand/walk/turn/busy` snapshots plus exact cycles/frame. P4 raster/geometry set (`p4_*`, blobs `$B3C00-$B4FFF`): `work/notes/p4_raster.md`.
