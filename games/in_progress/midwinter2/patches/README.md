# MW2 patches — format and boot mechanism

## Patch format (patches/*.s, vasm mot syntax)
Header comment lines before the first `org`; then one code segment per `org`:
`; name: X` `; default: no|yes` (default yes) `; site: $addr` (RAM site, required)
`; orig: <hex>` (expected original bytes; optional, tool derives+cross-checks)
`; phase: boot|deferred` (optional; auto: boot if in FFA file8/9, deferred if the
address is re-loaded later from an overlay, e.g. FFB f1 -> $18d96)
`; data: $addr len` (blob-owned zero-init data reservation, repeatable);
`; media: floppy` (optional: built only by `build --floppy`, see "Floppy build");
`; blobedit: $addr <orig hex>` (optional, repeatable: the segment with that `org` rewrites bytes of ANOTHER patch's blob in the image, applied only if the bytes there equal
`<orig hex>`; all zero = that patch is absent, skipped; anything else aborts the build; used by `jag_poll` on `p5_ctl_vbl`).
The segment whose `org` equals the site yields the NEW bytes (must be <= orig
length, nop-padded). Segments with org in $b31c0-$b31ff are BLOB code at a fixed
org in free RAM: the payload `$B3000-$BAFFF` (32 KB; blob code from `$B3400`, see "Payload is $8000 bytes"
below). `patches/core.s` holds the mechanism (trampoline / load-hook exit / deferred applier).

## Where PP's patcher comes from and how it is modified
RUNME.TOS is shipped UNPACKED (= work/dumps/RUNME_unpacked.tos; its LZ expansion
is byte-identical, reloc table valid). Its stack-phase installer (text
$370-$3C4, running from a copy at $B1F44) copies text $3DC-$7C3 to RAM
$200-$5E7; that block holds PP's patcher (RAM $4BC-$59C) ending in
`jmp $3104.w` at $59C. mw2patch.py edits the unpacked image (reloc-aware):
1. text $754 (RAM $594-$59F): PP's last patch + patcher tail (12 B) ->
   `jmp $B3000.l` + nops; the displaced `move #$6002,$2c574` is replayed by the
   trampoline first thing.
2. text $3A8 (RAM $59C area is 1; this is the stack-phase fallthrough `jmp
   $4d9a6.l`): replaced by `jmp $4536.l` (6 B + one new reloc entry) into a
   26-byte copy routine appended to the DATA segment, which copies the
   payload image (appended after it) to $B3000 and then jumps
   to the boot stub. Staging runs before the stub, i.e. before file8/9 erase
   RUNME's low base; the appended data is untouched by boot loads.
   (Text slack $7C0-$9BF is HAGA's runtime data area and the $3CC/$3D4 longs
   are live stack-block data: both must stay exactly as shipped.)
3. The data segment grows by N = 26 (copy routine) + 8 (bss pointers) + `PAYLOAD_LEN` ($8000) = 32802 B:
   header data len, every relocated long that addresses bss (>= text $4536) is adjusted by +N, and the
   reloc table is re-encoded (round-trip verified by the tool). A signed 16-bit pc displacement cannot span
   that, so the four `lea d(pc),aN` that address bss (text $98, $C24, $41EA, $41FC) become `movea.l d(pc),aN`
   (same 4 bytes, same registers, no flag change) loading a relocated pointer from two slots (text $4550 =
   bss+$220, $4554 = bss start; both are new reloc entries) that sit right behind the copy routine,
   within 32 KB of all four. `build_runme` scans the whole text for any other `d16(pc)` operand that
   reaches bss and aborts if one is not handled. (Before the payload grew, the list also contained text
   $22E and $4514; those are not pc-relative operands (the low word of `jsr $43d2.l`, and `lea $40(a2),a2`)
   and the old +N edit corrupted `bra.b $238` at $230 and the `lea $40(a2),a2` stride of the
   intro-picture loop at $4514; both are left as shipped now. Evidence: `work/notes/payload32k.md`.)
$B3000-$BAFFF is zero at staging time and nothing but our trampoline/hook/blobs writes there afterwards
(1 MB and 4 MB cold boots through gameplay: `work/notes/payload32k.md`).

## Runtime behaviour
Trampoline ($B3000, entered at $59C): replays PP's displaced patch, presets
'MWPF' at $B2FF8, verifies every phase=boot site's ORIGINAL bytes in RAM; all
match -> apply all + 'MWPO'; any mismatch -> apply NOTHING. Then `jmp $3104.w`.
Deferred sites: boot site $2789A (sub_2783E single success exit, 6 B) -> hook
$B3070 restores exactly like the original exit, then applier $B3090 walks the
table after every file load; sites whose [addr,addr+len) lies inside
[$6918],[$6914) are applied idempotently (orig -> apply, new -> already done,
else 'MWPF' + skip). Zero patches = original behaviour + 'MWPO' marker.

The 6-byte splice at $2789A MUST be `jmp $B3070.l` ($4EF9), never `jsr`: the
replaced bytes are `move.w (a7)+,sr; move.w (a7)+,$62f2.w`, followed in the game
by `movem.l (a7)+,d0-d7/a0-a6; rts`, so hookexit replays them from the unchanged
(a7). A `jsr` pushes a 4-byte return address, hookexit then pops the wrong frame
and the game crashes right after the first deferred load (found with test_sky;
fixed in build_image, "<load-hook>" entry).

## Test patches
- `test_framecount` (boot phase, $3159c): blob-owned frame counter at $B31F0;
  compare its rate with `Hatari.fps()`.
- `test_sky` (deferred, $1B9A8, 2 B `moveq #$ff,d0` -> `moveq #0,d0`): the fill sub
  $1B996 seeds d1-d5/a0-a5 from d0 and reloads only d0/d1 at $1B9C0, which feed
  just bytes 0-7 of every line. Patching $1B9C0 (the earlier version of this test)
  therefore only changed a 16-px column at the left edge of the view; patching the
  seed recolours the whole background fill (lines 58-199, wherever terrain/HUD do
  not overdraw it). Wrong-orig failure path (-> 'MWPF', nothing applied) is tested
  with a throwaway copy of the patch plus `mw2patch.cmd_verify` stubbed out.
- `test_blob16k` (boot phase, `default: no`, site $2B4C0: an existing `nop` rewritten with `nop`): payload-capacity
  test. A 16 KB blob at $B6000-$B9FFF, i.e. in the part of the payload that only exists since it grew to $8000
  bytes: the signature `MW2-TEST-BLOB16K`, then 8184 words, each the low 16 bits of its own address ($6010, $6012,
  ... $9FFE). Check in RAM: `m $b6000 32` shows the signature, and `savebin` of $B6000-$B9FFF must equal that
  pattern. Build it with the defaults: `build --only <defaults> test_blob16k [pp_bigram_cache pp_nofade]` (add
  `floppy_copybuf` and `--floppy` for the floppy set). Results: `work/notes/payload32k.md`.

## Tool
`python3 tools/mw2patch.py build [--only N ...] [--out build/game] | list | verify`
verify/build cross-check each site's orig against FILES/FFA f8/f9 (plus PP's
patches, loading.md 6) or FILES/FFB f1 (overlays) AND work/dumps/ram_ingame_lobos.bin;
mismatch aborts (build runs the verify step first; a declared `orig:` was previously
only checked by an explicit `verify`). build/game is a full patched copy; originals
never modified.
Capacity: `PAYLOAD_LEN` = $8000 bytes ($B3000-$BAFFF): core $B3000-$B30FF, site table + byte pool
$B3100-$B33FF, blob code/data from $B3400 (`BLOB_MIN`) to $BAFFF (`BLOB_MAX`).

## Game-speed patches (P3: 5 Hz world, 25 Hz player view for EVERY vehicle type; work/notes/vehicles_p3b.md)
Background: work/notes/tick_inventory.md (sections 4-6), work/notes/timing.md. The original game runs its whole
logic block once per rendered frame, so the world speeds up with the frame rate. The patches below run the world at a
fixed 5 Hz (the original speed on a 1 MB 8 MHz STE, about one tick per 10 VBL) and show the player's motion at 25 Hz.
- `tick_vbl` ($262d0): a free-running VBL clock at $B3400 in the VBL handler (blob $B3700), in units of 1/300 s (+6 per 50 Hz VBL, +5 per 60 Hz VBL).
- `p3cp_head` ($31486, `default: yes`): the scheduler, PREDICT-AHEAD. Per group of five 40 ms passes (PH = 1..5, 60 clock units):
  PH 1 is the ORIGINAL tick, unmodified and complete (pre-calls, player sim, post-calls, render, flip, post-flip handler), so the world, the
  player and the picture at PH 1 are the unpatched game's for every vehicle type. PH 2-5 show the pose extrapolated from the tick that just ran
  (`T_end + (T_end - T_start) * (PH-1)/5`), refresh the view words, and run the HUD gauge draw + render + flip; no game logic runs in them. The
  live pose, view words, NPC table and sea-wave phase/pointer are put back to the end of the tick before the next PH 1, so every group end equals
  the 5 Hz game's. An extra pass renders only when it ends no more than SLACK (1 VBL, tuning word SLKX) after the next PH 1 is due, so the tick starts (the only place keys and the mouse are
  read: Esc, J/K/mouse steering) stay on the original's 5 Hz schedule. Overshoot limits: no prediction after a type change, a jump (map re-centre,
  landing, eject), a collision/arrival result; altitude is never extrapolated downwards; the lean never. TAB[type] = 0 puts a type on the plain 5 Hz pass.
  Data: block D = $B42E0 (+0 LAST.l, +4 ACC.w, +6 PH, +8 SUB (1 = PH 1 of a group), +12 SKIP), own data $B8F00, NPC snapshot $B8700, code from $B8000 (below $B8700).
- `p3c_sim` ($31570): the second site of p3cp_head; the sim call becomes `jsr $b8000.l`, the hook that records the pose before the tick.
- `p3c_render` ($3158c, blob $B4102): the HUD gauge draw ($19f54) runs once per presented frame (its dirty counters are per screen buffer) and a pass with
  SKIP set (another pass owed, or an extra pass past its deadline) skips the render and the gauge draw together.
- `p3c_head` (`default: no`): the interpolated alternative (not shipping, not re-gated after the p3cp fixes; do not combine with p3cp_head).
- `p5_ctl_x` consumes fresh input once per tick (the player sim runs once per group).
- Option A (`tick_head` at $31486 + `tick_render` at $3159c, with `tick_vbl`) remains in the tree with `default: no` as the reference build
  (every gate compares p3cp against it); it cannot be combined with p3cp_head (same site).
- Gone (v1.2, helicopter only, `git log` has them): `p3b_head`, `p3b_pos`, `p3b_hdg`, `p3b_alt`, `p3b_bank`, `p3b_save`, `p3b_probe`, `p3b_alt_fix`, `p3b_head_fix`.
  `p3b_render` is now `p3c_render`.

Payload is $8000 bytes ($B3000-$BAFFF). The site table + byte pool may use $B3100-$B33FF; blob code
starts at $B3400. Blob owners in $B3400-$B4EFF are listed in the mw2-patching skill; $B4F00-$BAFFF
(about 26 KB) is free for new patches, except $B8000-$B8FFF (p3cp_head).

## Blitter experiments (blob $B4700-$B4BFF; work/notes/blitter.md)
- `p4_blit_sky` ($1b996, `default: no`): sky fill through the STE blitter in HOG mode, pixel-identical,
  saves 5.5 % of the fill (0.15 % of a frame). Runtime detection (68000 + blitter present +
  not Mega STE, via bus-error probes) cached in FLAG $B4BFE; a plain ST/Mega STE/TT/Falcon runs the original
  body. `HOG equ 0` gives the non-HOG variant (about twice as slow as the CPU).
- `p4_blit_hist` ($38d14, measurement only): histogram of interior-group counts per span row at $B4B00.

## File patches: PP's resident loader service (file HAGA; work/notes/load_fade.md)
The grey palette fades seen on every screen transition come from PP's loader service, which is the
file `HAGA` (RUNME.TOS only copies it to RAM: HAGA offset 0 = $1F8000 on 2 MB, $F8000 on 1 MB), not
from RUNME and not from the game. Nothing at a fixed RAM address can be patched, so a file patch
edits HAGA bytes in the build copy (`build` copies the originals first; they are never written):
```
; name: pp_nofade
; image: HAGA
; edit: $0ffc 61000168          ; HAGA file offset + expected ORIGINAL bytes (hex); repeatable
        org     HB+$0ffc        ; one segment per edit, same length as its orig
        bsr.w   HB+$1278        ; HB = RAM base of HAGA, used only for pc-relative references
```
`verify` checks each edit's original bytes against the shipped HAGA AND the 2 MB RAM dump (HB+off),
that the new bytes have the same length, that edits do not overlap, and that each segment assembles to
identical bytes with HB = $1F8000 and HB = $F8000 (position independence; absolute RAM addresses other than
low memory are rejected by that check). `build` refuses to apply over different bytes. File patches are
not applicable to `live` (no snapshot support: the service code is already resident in a snapshot).
Use `--only <all defaults> pp_nofade` until it is made default.
- `pp_nofade` (`default: no`): the service's fade-to-grey / fade-back bracket (`bsr HB+$1166` / `bsr
  HB+$1372`) ran once per Fread chunk (cache miss, 200 KB) plus once per Fsfirst, about 2 per loaded file
  (directory window + data window): 2 x up to 7 steps x 2 VBL each. The patch skips both fades in the service
  paths and leaves the savestate/exit-to-desktop path (its own callers of the same routines) as it was.
- `pp_bigram_cache` (`default: yes`, 2 bytes at HAGA+$3228, `move.l (a2),d2` -> `bra.b HB+$3254`): fixes the hang at
  the "Flames of Freedom" title on ST/STE/Mega STE (68000) with >= 4 MB RAM. PP's HAGA init switches the stub's disk cache
  to whole-image mode when ST-RAM >= 4 MB (`Fread(64, 737280, $81000)`: `$81000-$135000`), which zeroes our payload at
  `$B3000-$BAFFF`. The patch makes 68000 machines keep PP's chunked cache (200000-byte chunks, `$81000-$B1D40`, as on 1/2 MB).
  68020+ machines (TT/Falcon) already cache at `$300100` and are unchanged. Cost at 4 MB (service VBLs measured with
  breakpoints on HAGA+$fc4/$1164): original 2 calls/54 VBL until the M/J/K screen, 6 calls/194 VBL until the 3D view; with this
  patch alone 11 calls/361 VBL and 56 calls/1816 VBL; with the default set (pp_nofade) 127 and 639 VBL. Details: `work/notes/bigram.md`.

## HUD overlay (cockpit visor + dashboard replay $30f2c; work/notes/cockpit.md)
Blobs in the hole $B44C0-$B46BF (code $B44C0-$B467A, data block $B4680-$B4693), which no other patch uses;
they needed 380 B, more than the $B4E00-$B4EFF that was left when the payload was $1F00 bytes.
- Pixel-identical "clean prefix" set (`default: yes`), apply ALL FOUR together: `p4_hud_pfx_ymin` ($38cd0,
  smallest polygon row of the frame), `p4_hud_reset` ($28cc0, 3D-view entry: forget which rows are clean),
  `p4_hud_pfx_fill` ($1b996 sky fill, deferred phase: skips the rows already clean) and `p4_hud_pfx_replay`
  ($30f2c: replays only the rows terrain can have touched). abtest `--flips 10` and `--flips 40` exit 0 on
  both default snapshots; 1000-VBL abtest fps is within noise, 3000-VBL runs: foot 253 -> 263 flips,
  walking 276 -> 288 (+4 %).
  The clean prefix is also dropped whenever the cockpit replay is skipped, i.e. for `$6220` in {5, $15, $11}
  (on foot, Swimming, Parachute: `$1dbee-$1dc04`), because those states change type without the 3D re-entry
  `$28cc0`, so nothing redraws the overlay and the rows above the terrain would keep the previous overlay
  (the half diving mask on exiting a boat). `work/notes/mask.md`.
- Visual-tradeoff experiment, NOT for shipping without sign-off: `p4_hud_reset` + `p4_hud_crop_fill`
  ($1b99e) + `p4_hud_crop_clip` ($38c86) + `p4_hud_crop_replay` ($30f2c): the 3D window ends at line 181
  (foot mode only) and the dashboard band is drawn once per buffer. Excludes the `pfx` set (same sites).

## Floppy build (`build --floppy`)
`python3 tools/mw2patch.py build --floppy [--only N ...] [--out build/floppy] [--zip [PATH]]` writes
`FFA_boot.st` (patched), `FFB_graphics.st`, `FFC_missions.st` (verbatim copies of FILES/FFB, FFC),
`FFD_campaign_blank.st` (verbatim FILES/FFD: a blank TOS-formatted 720K disk) and `README.TXT` (from
`patches/FLOPPY.TXT`, with the patch list and md5s). `--zip` also writes
`dist/Midwinter2_v<version>_patched_floppies_<date>.zip`. Evidence and test log: `work/notes/floppy.md`.
- **Boot path.** The FFA boot sector (word sum `$1234`) loads FFA file 1 (the 4096-byte stub, image offset
  `$200`) to `$4D9A6`; the stub loads file 8 (`$806`) and file 9 (`$3104`) with its own FDC code and ends with
  `jmp $3104.w` at `$4DAA0`. RUNME, PP's patcher (`$4BC-$59C`) and the HAGA service never run, so none of
  `PP_PATCHES` exist in RAM on floppy: the game runs its original FDC driver.
- **Sites.** Every default site has the same original bytes on floppy (none overlaps a `PP_PATCHES`
  address; `build --floppy` aborts if one does, and the in-game RAM of an unpatched floppy boot was compared
  site by site). `pp_nofade` is skipped: it edits HAGA, which does not exist on floppy, and nothing fades.
- **Injection.** The payload (`build_image(..., floppy=True)`: same site table and blobs as the HD build, core
  assembled with `FLOPPY equ 1`; the trampoline applies PP's security-check skip `move.w #$6002,$2c574` on both media) becomes FFA **file 10**: directory entry 10 (`[xor-cksum][0][track-side 72][len $8000]`)
  and data on the blank track-sides 72-79 (all 8 of the free ones; `floppy_ffa` aborts if a payload would need
  track-side 80, which holds data). A 32-byte stage 1 in unreferenced stub code (`$4DDAA`, 64 dead
  bytes) calls the stub's own loader (`$4DB52`, a6 = `$4E9D8`, dest `[$4E9AC]` = `$B3000`, file number
  `$16(a6)` = 10) and jumps to `$B3000`; the stub's final `jmp $3104.w` becomes `bra.w $4DDAA`. The trampoline
  verifies and applies the boot sites exactly as in the HD build and ends in `jmp $3104.w`. The deferred hook
  at `$2789A` (`sub_2783E` exit) is the game's own loader code and unchanged on floppy.
- **Floppy-only patches** carry `; media: floppy` and are built only with `--floppy`. `floppy_copybuf`
  ($e566, `0050` -> `0028`): on a >= 1 MB machine the game copies disks (Start New Campaign, Create Back-up)
  through a 80-track-side buffer at `$80000-$DA000`, which would overwrite the payload at `$B3000`; 40
  track-sides end at `$AD000`, 24 KB below the payload (`$B3000-$BAFFF`).
- **Security check:** skipped on floppy too (user decision); verified by a floppy cold boot without the debugger bypass (`work/floppy_tests/leadcheck_*`).
- **Tests** (`work/floppy_tests/run_cell.py`, results in `work/notes/floppy.md`): unpatched and patched floppies reach
  the Lobos 3D view on STE TOS 1.62 and Mega ST TOS 1.04 (1 MB), `MWPO` set, all 25 sites hold the patch bytes in RAM
  (deferred ones too), world rate 27.3 (8 MHz) / 27.5 (16 MHz) units/s on the STE, mouse turn turns then stops.
  Campaign creation (4 passes) keeps the payload intact; Hatari 2.6.1 discards the campaign image's writes after the
  first pass, so a creation cannot be completed there.

## Cockpit cull (P7 items 1+2; work/notes/p7_cockpit_cull.md)
All `default: no`, blobs `$B5000-$B57FF` (data `$B5000-$B525F`). Terrain polygons, object polygons and fill rows that lie wholly under opaque cockpit pixels
are not drawn (pixel-identical on the 32000 visible bytes per buffer; the invisible row 200 after each buffer differs, see the note).
- `p7_ck_tab` (`$30f26`, encoder exit) builds the per-row opaque-run / edge-key tables from the live overlay list (per vehicle type); `p7_ck_enter` (`$1fa54`) / `p7_ck_exit` (`$1dcae`)
  set EN only inside a main-renderer terrain pass whose cockpit replay follows, and build the table lazily. Base of the group.
- `p7_ck_poly` (`$1fa9a`): terrain polygons clipped at the window bottom, tested with one F-table lookup before clip/walk/fill. `p7_ck_obj` (`$3bb6e`): object polygons.
  Cycles/frame vs the p4 set: foot -2.9 %, walking -3.1 %, banked turn -1.3 %.
- `p7_ck_fill` (`$38c6e`): drops bottom fill rows under opaque runs and row 200; -0.6 % foot, +0.2 % walking after the cull: not recommended as default.

## Release credit (`mw2_credit`, st-game-speedup "Release credit"; work/notes/credit.md)
`mw2_credit` (`default: yes`, boot site `$1f5f0`, blob `$B9000`): a dim `v<VERSION> enhanced by dad_prg` at the bottom (rows 188-196, colour
index 2 = `$630`, the game's own font, centred) of the orange MIDWINTER II logo screen, drawn into both screen buffers so it stays up on the
floppy "Insert Graphics Disk" prompt and on the HD loading screen. The palette and the logo art are untouched.
- **One place for the version:** the `; version:` header of `patches/mw2_credit.s`. `mw2patch.py` replaces `@VERSION@` with it in that
  source's string, in `PATCHES.TXT` and in the floppy `README.TXT` (`FLOPPY.TXT`); `mw2patch.py version` prints it and `mw2patch.py doc FILE`
  renders a doc; `tools/package.sh` uses it for the zip names `Midwinter2_v<VERSION>_patched[_floppies]_<date>.zip`.
- **Boot site inside an overlay range:** `$1f5f0` is in the FFB f1 overlay range (`$18d96-$210b2`, loaded long after), so the in-game dump
  `ram_ingame_lobos.bin` shows overlay code there. For a `phase: boot` site in such a range `verify` compares against
  `work/dumps/ram_boot_hd1mb.bin` (RAM at game entry `$312a8` of an unpatched 1 MB HD boot; the floppy boot dump
  `ram_boot_fl1mb.bin` differs only at PP's patch addresses).

## Vehicle work (2026-11-10; `work/notes/vehicles_p3b.md`)
- Default set: `p3cp_head`, `p3c_sim` and `p7_skip_render` are `default: yes` since 2026-11-11 (cold boots on STE, Mega STE, TT, plain ST, floppy STE/TT: `work/notes/vehicles_p3b.md` sections 9-12).
- `p7_skip_render`: the static-frame skip, now gated by a per-type table (all 22 types) instead of the Helicopter-only test of v1.2.
- `p4_hud_crop_{clip,fill,replay}` and the `_t` variants: the REJECTED visual-tradeoff crop experiment; they stay `default: no`.

## Jaguar pad (`jag_poll` + `jag_dir` + `jag_btn`, all `default: no`; work/notes/jagpad.md)
A Jaguar pad in an STE enhanced joystick port (read directly by the hardware, not through the IKBD) acts in **joystick mode (J) only**; the mouse
and keyboard modes are untouched. Apply the three together. Design as Hunter's `jag_pad`: one row group per VBL, round robin, select written at the end of one VBL
and read at the start of the next (a whole VBL of settle time, no wait loop), decoding only on a change, original bytes written back at every site when the probe says no.
- `jag_poll` (`$262f6`, the end of the VBL handler, `movem.l (a7)+,d0-d7/a0-a6 / rte` -> `jmp $B9500`; the blob replays them): reads group 4, 3, 2, 1 in turn (each every
  4th VBL, 80 ms at 50 Hz), port A and B OR-ed. Directions go to `PADJ` (`$B9EE1`), B to `PADBTN` (`$B9EE2`), every other changed button makes / breaks a key through the game's own key
  bookkeeping (`$7684`, `$7686`, `$75ac`, `$770a/$770c`, `$7708`; interrupts masked): A `,` (nose down / dive), C `.` (nose up / climb), Option Esc (leave the vehicle; the break is held
  back until 16 VBL after the press, because the game polls `$7687` once per logic tick), Pause P, keypad 1-9 F1-F9, 0 F10, `*` keypad `-`, `#` keypad `+`; B = fire.
- `jag_dir` (`$26b66`): ORs `PADJ` into the joystick byte of `$26b58`, so the ramps `$75b2..$75be` and `$6fb6/$6fba` see the pad like the stick. `jag_btn` (`$26bea`): ORs `PADBTN` into the
  mouse-header buttons that become the select/fire event `$6872`.
- **`p5_ctl_vbl` is untouched.** `jag_poll` carries a `; blobedit: $b433a 123875a9` header: `tools/mw2patch.py` rewrites those 4 bytes of p5_ctl_vbl's blob (`move.b $75a9.w,d1` ->
  `bsr.w jag_rd`, stick | pad) only when both patches are in the set, and aborts if the bytes there are not the declared ones (all zero = target absent: skipped). A set without the jag
  patches is byte-identical to the one before them (`cmp` of RUNME.TOS / HAGA of the default build, work/notes/jagpad.md section 11).
- **Detection** (first VBL, any mode, cached in `J_ST` `$B9EA0`): guarded `tst.b $ff8901` (DMA sound; ST / Mega ST bus-error = no) and guarded `tst.b $ff8e01` (SCU: answers on a Mega STE and a TT = no, bus-errors on
  an STE and a Falcon), vector at VBR+8 (`movec` on a 68020+), then a guarded word write/read of `$ff9202` / `$ff9200` with every group deselected must read idle (`$ffxx` / `$xxxf`). Words only: a byte read of
  `$ff9200` bus-errors on a real STE. On a no the probe writes the ORIGINAL bytes back to `$262f6`, `$26b66`, `$26bea` (and `$b433a` if redirected): the unpatched code, 0 cycles. **Falcon:** the code
  path exists (`FALCON equ 1` at the top of `jag_poll.s`) but is off: MW2 does not run on a Hatari Falcon (HD: black screen; floppy: garbled intro, game never starts), so it could not be tested.
- Blobs: `$B9500-$B97BB` (700 B), `$B9E00` (`jag_dir`), `$B9E20` (`jag_btn`), `$B9E40` (`jag_rd`, 12 B), data `$B9EA0-$B9EEF`.
- Cost, STE 8 MHz (Hatari profile, 220 VBL): M / K mode 40 cycles per VBL; J mode 354 cycles per VBL (poll 196, three merge splices 158) = 0.22 % at 50 Hz, 0.27 % at 60 Hz, the same with or without a
  pad pressed. Machines without pad ports: 0.

## `p8_tt_ptr`: pointer on the 2D screens of a TT / Falcon (`default: yes`, site `$26ea2`; notes: work/notes/map_pointer.md)
- **Symptom (Hatari TT, any control mode):** on the island MAP screens (Raids map, campaign Control map) the menu pointer is not drawn at all, stock game included; it is visible on the screens that flip rarely
  (level of play, island text pages, book, boss screen), which is why it seems to "disappear" after the pointer was seen on the previous page.
- **Cause:** the pointer is drawn by the VBL handler (mode 0/1 routine `$264f0` -> `$266d4`) into the buffer `$67aa` = the buffer on display, at the start of the frame (HBL line 2). The map's main loop flips with `$26e98` at line 220 of the
  same frame (`movep` to `$ff8201/03` first, swap after), so the display is switched to the other buffer, which holds no pointer. An ST / STE latches the base at the next frame start, so the handler draws into the buffer
  that is shown; Hatari's TT/Falcon video takes the register at once.
- **Fix (68020+ only):** the site is the first instruction of the base write (`lea $ff8201.l,a0`, 6 B), `jsr`'d into `$B4F00`: in modes 0/1 it sets `$67aa` to the buffer about to be shown, then does what the VBL handler does
  (`$2684e` restore if `$6fc2`, then `$264f0`) with the VBL masked (IPL 4), so the pointer is already in the buffer when it goes on the display. The next VBL handler restores/redraws as usual. 3D view (mode 2): plain path.
- **Detection:** the first call classifies the CPU with the index-register scale trick of `cpulib.s` (no exception, no cookie jar: HAGA remaps low RAM on a TT). A 68000/68010 (ST, STE, Mega STE) writes the 6 original bytes back to `$26ea2`:
  those machines run the unpatched flip afterwards, 0 cycles. Data `TT_F` `$B4F80` (0 unprobed, 1 68000, 2 68020+); blob `$B4F00-$B4F7F` (128 B).
- Cost on a TT: one pointer restore + draw (~12 k cycles at 8 MHz, 0.4 ms at 32 MHz) per 2D flip.
