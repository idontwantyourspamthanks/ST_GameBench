# Populous 2 patches — format and boot mechanism

Design copied from Midwinter 2 (`games/in_progress/midwinter2/tools/mw2patch.py` and its
`patches/README.md`); re-derived for PP's Populous 2 HAGA conversion. Evidence for everything below is in
`work/notes/delivery.md`.

## Patch format (`patches/*.s`, vasm mot syntax)
Header comment lines before the first `org`; then one code segment per `org`:
`; name: X` · `; default: no|yes` (default yes) · `; site: $addr` (RAM site, required) ·
`; orig: <hex>` (expected original bytes; optional, the tool derives and cross-checks them) ·
`; data: $addr len` (zero-initialised blob-owned data, repeatable) · `; media: floppy` (only built by
`build --floppy`) · `; note: ...` (repeatable, free text).
The segment whose `org` equals the site gives the NEW bytes (at most the orig length, nop-padded).
Other segments are BLOB code/data at a fixed org in the payload (see the address map below).

`org` takes `$1234` or `PB+$100` (`PB` = the payload base, supplied by the tool).

## The game's image and the two kinds of site
PP's Populous 2 does not run from disk images: `RUNME.TOS` loads `FILES\P2CR.TOS` (the Bullfrog credits
program) with Pexec, and after it quits, `FILES\P2M.FIC` (104,830 B: a 32-byte header + PP's LZ stream,
unpacking to `$79c10` bytes) into `$101000` and unpacks it to **`$1770` = the game**. Then it loads `FILES\P2D`
(418,679 B) whole into `$101000`, and `RUNME`'s stage block (copied to the top of RAM) runs PP's patcher.

So there is **one phase, boot**: every game site is verified against the game as RAM holds it right after the
unpack — `P2M.FIC` unpacked plus PP's four RAM patches (below) — and cross-checked against
`work/dumps/game_start.bin` (2 MB STE, in play). Sites outside the game image are checked against the same
places.

| PP's patch (RUNME text `$3c6`-`$3d6`) | RAM | what it is |
|---|---|---|
| `move.w #$6002,$14a88` | `$14a88` | manual question (`cmp.w d1,d2` at `$14a86`): `bne` -> `bra` = any answer accepted |
| `move.w #$4ef8,$2cc98` + word | `$2cc98` | `jmp $206` low-RAM hook: the game's disk layer `$36efc` replaced by PP's RAM file stub |
| `move.w #$4ef8,$36efc` + `$140` | `$36efc` | `jmp $140` into the stub ("copy file N out of P2D in RAM") |
| `move.w #$4ef8,$1cf8` + `$2ac` | `$1cf8` | key-release path: PP's exit/statesave hook |
| `move.l #$1c42,$118` | `$118` | the game's ACIA handler vector (replayed by our trampoline) |

Two sites are **not** in the game image but in that low-RAM stub block (`$140`-`$3fb`), which the stage block
copies from RUNME text `$3f8`; the tool derives their original bytes from there.

## Where PP's patcher tail is, and how it is modified
`RUNME.TOS` is shipped LZ-packed; `pp_depack.py` unpacks it (text `$440e`, data 22, bss 111206).
The stage block is copied to the top of RAM (2 MB: `$131d40`) and runs **inside the game's unpack**:
1. text `$318`-`$31b` `move.w #$2700,sr` -> **`bsr.w copy`** (our routine, appended to RUNME's data segment):
   copies the payload image to `$80000`, then replays the displaced `move.w #$2700,sr` and returns.
   It has to run here: the unpack that follows overwrites RUNME's whole TPA, payload bytes included.
2. text `$3da`-`$3e5` (`move.l #$1c42,$118.w` + `jmp $1770.w`, PP's tail) -> **`jmp $80000`** + nops.
3. The data segment grows by `copy_len + 8 + $8000`; the bss (and the stack top seeded from `$6`, the Mshrink
   size and every relocated long that reaches the bss) moves up by the same amount. The four
   `lea d(pc),aN` that address the bss (text `$98`, `$C24`, `$41EA`, `$41FC`) cannot span it as 16-bit
   displacements, so each becomes `movea.l d(pc),aN` (same 4 bytes, same register, no flags) reading a
   relocated pointer from the two slots behind the copy routine. `build` aborts on any other `d16(pc)`
   operand that reaches the bss (the other hits of that scan are displacement words / data, listed in the tool).

## Runtime behaviour
Trampoline (`$80000`, entered by the `jmp` that replaced PP's tail): replays PP's `move.l #$1c42,$118.w`,
presets `P2PF` at `$7fff8`, verifies **every** site's ORIGINAL bytes against the game just unpacked; all match
-> applies all of them and writes `P2PO`; any mismatch -> applies **nothing** and keeps `P2PF`. Then
`jmp $1770.w`, the game entry, exactly as PP's tail did.
A zero-patch build therefore behaves like PP's build plus a marker (`P2PO`) and the payload.

There is no load hook and no deferred phase: everything the game runs on is in RAM at that point.

## Address map (payload `$80000-$87FFF`, 32 KB, copied by the `copy` routine)
| Range | Contents |
|---|---|
| `$7fff8` | marker: `P2PO` = all applied, `P2PF` = a site mismatched, nothing applied |
| `$80000-$800FF` | core: the trampoline (`patches/core.s`) |
| `$80100-$86FFF` | blob code/data (`PB+$100` and up) |
| `$87000-$87FFF` | site table (16 B/site + a 0 terminator) + orig/new byte pool (4 KB) |
| `$84000-$86FFF` | display patches: `pop2_spr` (`$84000-$853xx`), `pop2_ptr_a/b` (`$86000`, `$86200`), `pop2_clamp` (`$86400`), test drivers `test_walk*` (`$86800`, data `$86f00`); work/notes/display.md |
| `$88000-$8FFFF` | **data only, outside the payload image** (declare it with `; data: $88000 N`; the copy routine does not zero it, so a patch must init lazily behind a magic long): `pop2_ptr_a` `$88000-$881FF`, `pop2_spr` `$88200-$8FFFF` (blitter mode, cache tags, 16 slots). Free in play at 2 and 4 MB: delivery.md section 3 covers `$88000-$f7fff` |

Chosen because it is free in play (see "Free RAM" in `work/notes/delivery.md`): it sits above the game image
(which ends at `$7b380`) and below everything PP uses (`$81000` chunk cache at 4 MB, `$101000` P2D image,
`$131d40` stage block, `$1f8000` HAGA on 2 MB). Free at 2, 4 and 8 MB, and it is below `$100000` so HAGA's
statesave (which writes the first 1 MB) contains it.

## Builds
`build --hd` (default): a game folder — patched `RUNME.TOS`, `HAGA`, the pictures, `LOG.TXT`, `README.TXT`,
`MANUAL.TXT` and the original `FILES\` (P2CR.TOS, P2D, P2M.FIC).
`build --floppy`: one bootable 720K .st: `AUTO\RUNME.PRG` (the patched RUNME, so TOS runs it at boot),
`HAGA`, `FP2273.HST` (the STE cover picture) and `FILES\`. RUNME's own file names are relative, so it finds
them on drive A exactly as on a hard disk. 681,179 bytes of files, 43,008 free. The other two cover pictures
(`LP2273.HST` for a plain ST, `P2240R.BMP` for TT/Falcon) do not fit; RUNME skips a picture it cannot open.
No HAGA file patches are shipped, so the floppy build has no HAGA edits.

## Test patches (`default: no`)
- `pop2_save_a` (`$140`) + `pop2_save_b` (`$20e`): prototype for the in-game save/load, which PP's build
  breaks (see `work/notes/delivery.md`); applied together or not at all (same flag).
- `pop2_ntsc` (`$183c`): the game's own PAL check (`btst.b #1,$820a.w` / `bne.w $186e`); on a 60 Hz machine
  the untouched game shows "SORRY PAL MACHINES ONLY" and loops forever. Makes the branch unconditional.
