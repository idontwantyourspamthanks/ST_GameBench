# Nebulus: junk RAM (MiSTer does not clear RAM between runs) -- inventory, fix, evidence  (NebJunkRam)

Tags: **[obs]** raw output of this session (harness and raw rows in `work/junkram/`: `jr.py` matrix, `relaunch.py`, `capture.py`, `dumpcmp.py`, `*.jsonl`, `nepatch.diff`), **[disasm]** read from the sources,
**[INFERENCE]** not proven.  Background: `inputstall.md` section 6 / 12 (first junk-RAM finding), `boot.md` section 5 (delivery), `editor.md` 13.5 (RS/V map).

## 0. Result
1. Every STATE cell our patch layer owns is now zeroed by the loader itself, unconditionally, in the stage-2 step that writes the sites (new `nepatch` directive `clear ADDR LEN`; RS+V `$77c80..$77dbf`, the trainer flags `$76c00..$76c07`,
   the fire latch `$76d00..$76d03`).  Before: junk only in RS made the **editor open by itself at boot** (3/3 seeds, `$70 = $75a32`) and would also have trusted an unvalidated campaign store (`rsOk`) and used a junk TOS-copy pointer
   (`rsTosP`) at the first Load/Save; junk in a blob zone switched the whole layer off (`NEPF`, stock game).
2. **Idempotent relaunch** (implemented, 12 instructions): pass 1 accepts a site that holds its ORIGINAL bytes **or already its NEW bytes** (RAM that kept the blobs of an earlier patched run); the number of such sites is
   published in `$B0026` (word, new; `$B0024` stays the site count).  A relaunch no longer falls back to the stock game.
3. **Decision for the lead (not taken by me):** a code blob in the dead gap that holds *random* junk (another program's RAM, which is what a MiSTer shows after any other game) is still refused (`NEPF` = stock game, as designed).
   That is the realistic MiSTer case, not the leftover of our own earlier run.  `nepatch.ZONE_STRICT = False` (one constant) writes those blobs like blocks: junk can then never switch the layer off.  Measured below, both ways.
   I left `ZONE_STRICT = True` because the assignment said to keep the verified-zero rule; my recommendation is to flip it (section 5).

## 1. Inventory: every cell the patch layer reads before it writes it
Method: read `patches/*.s`, `ed_editor.s`, the stub/core in `tools/nepatch.py`; each cell then tested with random junk (section 3).
| cell / area | owner | read-before-write / assumption | effect of junk (old build) | now |
|---|---|---|---|---|
| RS `$77c80..$77cbf` (64 B): `rsCamp rsPos rsLvl rsEd rsTest rsSlot rsMis rsTow rsRows rsTime rsCx rsCy rsTop rsFrom rsName` | ed_overlay | title poll `ed_title` tests `rsTest` (+8), `rsKey` (+42) with no init; `ed_next` tests `rsTest`/`rsCamp`/`rsLvl`; `rsEd` (+6) picks "resume playtest" | **editor opens by itself** at the first title poll (`$70 = $75a32`, 3/3) [obs] | `clear` |
| RS `rsOk` (+40) | ov_ok (`ed_editor.s:2225`) | `tst.w rsOk / bne` = "store already validated" | junk non-zero: a **junk store with a valid-looking `NCMP` is used unvalidated** (lvl_ptr/camp_ptr walk it) [disasm] | `clear` (0 = validate first) |
| RS `rsTosP/rsTosN/rsMfpP` (+52/+56/+58) | disk_op (`:2711`) | `tst.l rsTosP / bne .have`: non-zero = "already known" | junk: the TOS-state swap uses a junk pointer: crash at the first Load/Save [disasm] | `clear` (0 = read `$ffd80/$ffd86/$fffaa`) |
| RS `rsKey rsKb rsPv rsLast` (+42,+44,+46,+48) | ed_key / editor | latches consumed without init | junk `$44` in rsKey opens the manager, junk rsKb acts as a shortcut key [disasm] | `clear` |
| V `$77cc0..$77dbf` (256 B) | editor | cleared by `ed_run` at every entry (`.zv`, 64 longs) before any read | none | `clear` as well (cheap, covers the lift/disk vars until first entry) |
| trainer cells `$76c00..07` (`prev`, `frz`, `noen`) | nt_trainers | inside the verified-zero blob site | junk -> `NEPF`; (a leftover run with T/E on would also have made the blob mismatch) | `clear`, the blob site now starts at `$76c08` |
| fire latch `$76d00..03` (`sticky`, pad) | ni_latch | inside the verified-zero blob site | junk -> `NEPF`; junk non-zero would turn the first poll into a fire press | `clear`, blob site starts `$76d04` |
| `ni_ikbd` blob `$7726c`, credit blob `$77a00` | ni_ikbd, cr_credit | no mutable cell (code + constants only) [disasm] | blob zone must be zero (verified) | unchanged (verified-zero / or equal NEW bytes) |
| editor code blocks (CODE1..CODE5, DATA) | ed_overlay | plain `block` copies: overwritten, no read before write; DATA holds constants only (grep of `dc`/`ds` in `ed_editor.s`) | none | unchanged |
| editor scratch `ES $A0000`, `MB $A8000`, `ETILE $A8800` | editor | written before read (`tiles_init` per entry, menus built into MB, ES drawn); these addresses hold the raw NEBEXE.FIC residue (`$81000..$A9AF7`) in EVERY run, so they are never zero anyway | none | unchanged |
| `BUF $AA000` (8 KB), `STK $AD000` (excursion stack), `TREC $BE000` | editor | `Fread` fills BUF fully before the validation (a short file is rejected); STK is a stack; TREC is written by `enc` before `rsLvl = $7fff` is ever set | none (junk-filled in the matrix) | unchanged |
| campaign store `OVS $BC000` (8 KB) | loader stub | the stub zeroes `$BC000..$BDFFF` then reads `NEBLEVEL.OVL`; `ov_ok` validates once (`NCMP`, version, counts, ranges, popcount); every hook re-checks the magic | junk cannot be there (zeroed by the stub); a junk FILE is the fuzz case below | unchanged |
| payload `$B0000..` / `MARKER $B0020` | stub / core | marker written (`NEPF`) at the start of core2; `$B0024/$B0026` written before any read; the stub checks `NEPA` after a successful Fread | a stale `NEPA` could only survive a SHORT successful read (corner, ignored) | unchanged |
| the game's own workspace | game | `$8700..$33a4f` cleared by the game's init, the rest comes from the depacked image | not ours | -- |

## 2. The change (full diff: `work/junkram/nepatch.diff`, 244 lines)
`tools/nepatch.py` (backward compatible: old `.nep` files and the floppy tool load unchanged):
- **`clear ADDR LEN`** (hex, even address and length, inside the dead gap `$76b10..$77ec0`).  `plan_install()` (shared by `build`/`verify`/`live`) splits every gap site around the clear ranges it contains (the new bytes there must be zero), so the
  blob sites become `$76c08..` (trainers), `$76d04..` (latch); it also checks, for the first time, that clears, blocks and gap sites are pairwise disjoint.  The clear table follows the site table in `NEPATCH.BIN` (no size change, payload 33972 B as before).
- core2 pass 1: `cmpm` loop against ORIG; on a mismatch a second loop against NEW (`p1n`); neither = `NEPF`.  Pass 2 writes the sites, **zeroes the clear ranges** (`clr` loop, word stores), sets `NEPO`, copies the blocks.  `$B0026` = number of sites found already in their NEW state.
- `ZONE_STRICT` (see section 0, 5), `verify` prints the clear ranges and checks the stage-2 dump is zero there.
`.nep` files: one added line each, `ed_overlay.nep` `clear 77c80 140`, `nt_trainers.nep` `clear 76c00 8`, `ni_latch.nep` `clear 76d00 4`; the three generators (`work/editor/gen_ed.py`, `work/train/gen_nep.py`, `work/input/gen_ni.py`) emit them
(regeneration reproduces the files byte for byte).  Site count is unchanged (22 in the default set minus np_lift; the split keeps one fragment per blob).  `ed_editor.s`, `nefloppy.py`, `nebrelease.py`, `ni_ikbd.*`: not touched.

## 3. Junk-RAM cold-boot matrix [obs] (`work/junkram/jr.py`, raw rows `before.jsonl`, `after.jsonl`, `after_mega_nojunk.jsonl`; table by `summarize.py`)
Method: Hatari 2.6.1, the HD image of `tools/nebulus.py`, run_ste-like options (`--fast-boot yes`, `--joy1 keys`); at START's stub call (`S+$34c`, STE `$1B162`, Mega STE `$213DE`; BEFORE the stub reads NEPATCH.BIN / NEBLEVEL.OVL) a debugger breakpoint `loadbin`s a seeded random
pattern: `all` = `$75728..$77ec0` (blobs, RS, V) + `$AA000..$BFFFF` (BUF, STK, payload area, store area, TREC); `rs` = only RS+V `$77c80..$77dbf`.  (`$A0000..$A9AF7` holds the raw NEBEXE.FIC at that moment and cannot be junked; it is non-zero in every run anyway.)
Per boot: marker `$B0020`, `$B0024/26`, `$70` (editor VBL = self-opened editor), trainer cells, latch, RS, input alive (ISR `$384fc` entries for a key tap = 2), VBL advancing, F10 opens and closes the manager, exception lines in the log after the title.
Builds: `before` = tree before my change (copy `work/junkram/nepatch_before.py`), `after` = this change (`ZONE_STRICT=True`), `after_relaxed` = same with `ZONE_STRICT=False`; all = default set minus np_lift (ni_latch ni_jump nt_trainers ni_ikbd cr_credit ed_overlay, 22 sites).
```
build          machine mode  boots NEPO NEPF selfopen trainers deadinput noVBL exc F10ok
before         STE     rs        3    3    0     3        0        0       0    0   (F10 not tested: editor already open)
before         STE     all       3    0    3     0        0        0       0    0   0   (stock game runs, junk in blobs)
before         STE     none      1    1    0     0        0        0       0    0   1
after          STE     rs        4    4    0     0        0        0       0    0   4
after          STE     all       4    0    4     0        0        0       0    0   0   (NEPF = by design, ZONE_STRICT)
after_relaxed  STE     all       4    4    0     0        0        0       0    0   4
after          Mega STE rs       2    2    0     0        0        0       0    0   2   (+1 control without junk, NEPO, F10 ok: after_mega_nojunk.jsonl)
after          Mega STE all      3    0    3     0        0        0       0    0   0
after_relaxed  Mega STE all      4    4    0     0        0        0       0    0   4
after          Mega STE none     1    1    0     0        0        0       0    0   1
```
After the fix: **0 self-opening editors, 0 trainer cells active, 0 dead inputs, 0 stopped VBLs, 0 exception lines** over 12 STE + 9 junked (+2 control) Mega STE boots (the 12-per-machine target was not reached on the Mega STE: 9 junked boots, 142 s each).
`NEPO` with sites `0016`/`0012` (STE/Mega, strict / relaxed: 22 / 18 verified sites, the 4 blobs became blocks) and `$B0026 = 0000`: nothing was "already new" in a junk boot.
The Mega STE rows are the first with real junk: my first Mega attempt used a wrong breakpoint (`$213E0`, never hit, 0 bytes injected, 262 s): those rows are kept apart in `after_mega_nojunk.jsonl` and count only as a control.
The old tree on junk RS: the editor opened by itself in 3/3 boots (`$70 = $75a32`); input stayed alive (the ACIA path is untouched).

## 4. Relaunch (idempotent pass 1) [obs / open]
- Hatari's warm reset (`hatari-shortcut warmreset`) and cold reset ZERO RAM (second run: `$B0026 = 0000`, blobs zero, old build also `NEPO`), so they cannot show the scenario; F9 on the title keeps RAM (cells `trainers 0000ffffffff0000` and the dirty RS were still there at the desktop,
  `relaunch.jsonl` kind f9) but this harness could not start START.TOS again from the desktop (mouse automation unreliable, 150 s without START).
- Emulated instead: `capture.py` boots the patched build, uses the editor, dirties RS/trainer/latch cells and dumps `$75728..$77ec0` + `$AA000..$BFFFF`; `jr.py BUILD MACHINE leftover:TAG` then injects exactly that RAM at the stub call of a fresh boot (`leftover.jsonl`: see section 6 for the rows).
- Not investigated: a START relaunched from the desktop in the same TOS session sees `phystop = $80000` (START forces it) and probably runs as memory class 1 (editor.md 11 [INFERENCE]); the idempotent pass does not change that.

## 5. Strict zone rule: recommendation (decision for the lead)
With `ZONE_STRICT = True` a blob zone that holds anything but zero or our own NEW bytes gives `NEPF` = stock game with no sign except the missing credit line (matrix: `after ... all`, 7/7 NEPF).  After another game on a MiSTer this is the likely case (any program that touched `$76b10..$77ec0`).  The check protects nothing the
game-image sites do not already protect (they pin the exact game build, and the stock game never writes the zone: zero at stage 2 and in the tower, boot.md 4).  `ZONE_STRICT = False` (one constant in `tools/nepatch.py`; `nebrelease.py` calls `cmd_build` so it follows the constant) writes the four blobs like blocks; matrix `after_relaxed`: 8/8 `NEPO`, 0 bad.
Side effects of flipping: the site count word drops from 22 to 18 (gates that compare it, e.g. `e170.py` expects a number), the `PATCHES.TXT` wording "zero before" for blobs becomes untrue.  Floppy: unaffected (see 7).

## 7. Floppy [obs: `python3 tools/nefloppy.py selftest` all `yes` (5 generators == the `.nep` blob/block bytes, `clear` lines parse); `nefloppy.py verify` fails only on `np_lift: no floppy translation` (NebLiftPerf's new default patch, not mine)]
The floppy build needs nothing for junk RAM: there is no stage 2 (sites are written statically into TOPPLER.JMP) and the loader reads the whole file `$33B00..$78100` raw, which covers RS/V (`$77c80`), the trainer cells (`$76c00`) and the latch (`$76d00`) with the file's zeros, so those cells are initialised by the load itself; `ed_floppy_capture.s` only writes (`rsTosP/N/MfpP`, the copy at `$C0108`, V+vMfp) and the stub's `NEPO`/`NEPS` words are in the file ([INFERENCE for the stub: the stub writes `NEPS` only on a 512 KB machine, after the load]).  Idempotent relaunch is moot there.
The loader's `clear` lines are ignored by `nefloppy.Plan` (it reads `p.sites`/GENS only), so no change to `nefloppy.py` is needed; its `selftest` still compares `nt_trainers`/`ni_latch` blob sites (`a >= ZONE_LO`) with the generators: the unchanged `.nep` site lines keep that true.

## 8. Gates run / open items
Run (all raw above): `nepatch.py verify` default set: `271849 game bytes compared, 0 differ`, 30 verified sites all `dump-orig OK`, 3 clears (332 B) stage-2 dump zero there; `nefloppy.py selftest`; `nebrelease.py build` (30 sites, 3 clears, payload 33972 B as before); cold boots STE 1 MB and Mega STE 4 MB `NEPO` with 22 sites (matrix rows `none`), title, F10 opens and leaves the manager (4/4 + 4/4 + control rows).
**Open (not run in the time given): `e170.py` (D key, hooks), `e150.py` (T/E), the in-tower equivalence `e97.py`, `e91.py` (6 boot-time fuzz stores; a private copy `work/junkram/gates/e91_jr.py` that uses my build and does not poke `rsOk` is ready), `e161.py` (22 fuzz disks + disk gate, STE and Mega), the build-vs-build RAM comparison `dumpcmp.py`.**
Reasoning only [INFERENCE]: the loader change adds no byte to any game site or editor block (same site table, same blocks; `.nep` data lines unchanged), so the game code path is the old one; `clear` only zeroes cells that were zero in every previous (Hatari) run.  The junk-store path: the stub zeroes `$BC000` before reading the file, `ov_ok` validates because `rsOk` is now 0 (e91 `magic+random` rejects it).

## 6. Relaunch evidence (leftover RAM of an earlier patched run injected at the stub call; STE 1 MB) [obs, `leftover.jsonl`]
Leftover = `capture.py after ste`: editor opened/left once, then `trainers 0000ffffffff0000` (T and E "on"), latch `00010001`, RS dirty (rsOk=1, rsTosP junk), dumped `$75728..$77ec0` + `$AA000..$BFFFF` and replayed into a fresh boot:
```
after  (idempotent pass 1)  marker NEPO  sites 00160004 (22 verified, 4 already NEW = the 4 blobs)  $70 = $382d8 (no editor)  trainers 0000000000000000  latch 00000000  RS all zero  input alive  F10 opens + leaves  exc []
before (strict, no idempotence) marker NEPF  sites 0000  = STOCK game; the stale cells stay: trainers 0000ffffffff0000, latch 00010001
```
Mega STE relaunch/leftover and `ZONE_STRICT=False` + leftover were not run (time); the mechanism is machine independent (stub + core2 do not read the machine).
