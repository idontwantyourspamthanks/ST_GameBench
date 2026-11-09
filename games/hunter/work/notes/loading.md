# Hunter: boot chain, patch delivery, free RAM (HunterLoader)

Tags: **[obs]** observed in Hatari 2.6.1 / RAM dump; **[disasm]** read from `tools/m68dis.py` / capstone disassembly; **[INFERENCE]** not verified.
Tool: `tools/huntpatch.py` (verify, list, build, live, boot, taildump, fillcheck). Core/stub source: `patches/core.s`.
Addresses below are from the 1 MB STE / TOS 1.62 reference run unless stated. START.TOS is relocated by the loader, so its own addresses move with the machine (`START_BASE = $1AE16` there); the game's addresses ($150, $800.., $c0100..) are fixed.

## 1. Boot chain

### 1.1 START.TOS
- 8098 B, PP's LZ packer (230-byte stub + packed data). `tools/pp_depack.py` unpacks it to a normal GEMDOS program: text `$82ae`, data 0, bss `$1b046`, 173 relocations [obs: `pp_depack.py START.TOS` -> "unpacked 33765 bytes: text $82ae"]. The unpacked text matches RAM at `$1AE16` of the HW-screen dump (22 of 22 sampled chunks, the only base that matched).
- Flow, in order [disasm of the unpacked text; addresses = reference run]:
  1. `$1ae16` Supexec(`$1ba0a`) = machine detect: reads the OS header (`$4f2`): version -> `$1b4a6`; phystop>>19 -> `$1b4a6+7`; copied to `$1ae72` (memory class; `>= 4` = 2 MB or more, TOS 3/4 -> 8, 512 KB refused). On 1 MB it also checks `START < $28ce8` ("too much low RAM"). Sets the basepage himem to `$78000`.
  2. Save MFP/palette state to `$fff8a..` (Gamex F9 menu, `jmp $ffd20`), HW-detect screen (`$1c300`), 25 s countdown, keys: **U** = unlimited stamina (`st.b $1b4b8`), **M** = machine settings (`$1be08`).
  3. Picture 1: `HUNTER.PCH` (`Fopen "HUNTER.PCH"`, `$1c34a`/`$1c8b8`), wait for a key.
  4. `$1b068..$1b09a`: Fopen **D15R_H5.FIC** (`D15R_F5.FIC` if M was used; names at `$1b832/$1b83e`), `Fread $c738` bytes to `$230c4` (= text end, the bss), PP-LZ depack (`$1b5cc`, same format as `tools/pp_depack.py`) from `$230e4` (32-byte header) to **`$c0100`** = the game's mini-OS / HD loader "D15R" (section 2).
  5. Fopen **HUM.FIC**, `Fread $a8e8` (EOF stops at 43140) to `$81000`. Dgetdrv -> `$c0734`, `Dsetpath("FILES")`, Dgetpath -> `$c0760` (`'\FILES'`).
  6. Install the HD driver: `$1b158 cmpi.l #'PPHD',-8(a1)` with `a1 = ($472)` (PP's own driver already resident?). Not the case with HDDRIVER: `$1b2b6`: TOS 1.x reads physical sector 0 of the disk with its own ACSI code (`$1b65e`), TOS >= 2 uses XBIOS DMAread (`$2a`, `$1b2d2`); the root sector is checked with `$1b648` (word sum over 256 words must be `$1234`; this is the "checksums sectors" routine, buffer `$230ca`). Then START hooks trap #1 (`$84 = $1b606`: Malloc/Mshrink emulation, everything else chains to the old vector, which START stores into the operand at `$1b618`), sets `$4c2 = 3`, and **runs the root sector** (`jsr (a0)`, `d7 = dev<<5`, `d5 = $80`) so HDDRIVER installs itself. The Malloc emulation hands out a private pool: **`$af100`, size `$10eb4` (1 MB)** or **`$186000`, size `$1f914` (>= 2 MB)** (`$1b31c..$1b338`).
  7. After 29 Vsyncs START copies the 8 live hd vectors ($472 $476 $47e $4b2 $4b6 $516 $5a0, `$4c2`) into the D15R's saved-TOS-state buffer (`$c07e6.l + $c0800`) and calls D15R init (`$c0100 + ($6(a0))`, copies the 24 MFP bytes at `$fffaa`).
  8. Tail (runs from a **copy of `$1b44e..$1b8a2` at `$80100`**, because the depack overwrites START's neighbourhood): mask the MFP, `$80100`: depack HUM.FIC (`lea $81020,a1`, `lea $800.w,a4`; header `4333 0000a864 00011804 ...` = 'C3', packed 43108, unpacked 71684) to **`$800..$12003`**; PP's RAM patches:
     - `$aff0`: `4ef8 01ae` (was `102e 7c02`) -> `jmp $1ae.w` (keyboard ISR hook),
     - `$d542`: `4ef9 00000150` (was `4278 0080 b67c`) -> `jmp $150.l` (file loads of the game),
     - `$a09e`: `move.w #$302d` only if U was pressed (**never patch it**, `huntpatch.py` refuses),
     - 724 bytes (`$1b4ba..`) copied to **`$150..$423`** = the file hook (section 2) + Gamex F9 handler + copies of START's depacker/trap code.
     Then `lea $7e800,a7` (`4ff9 0007e800`, text `$686`) and `jmp $800.w` (`4ef8 0800`, **`$80154`**).
- At the tail: SR `$2704`, a7 `$7e800`. **This is "all resident code in place"**: the game has not run one instruction yet. [obs: breakpoint `pc = $80154`, `huntpatch.py taildump`; dump `work/dumps/boot/ram_tail_1mb.bin`]
- Rebuilt-from-files check: HUM.FIC depacked + the two PP patches == dump bytes `$800..$12003` (71684 B, 0 differences); START text `$6a4..` == dump `$150..$423` except 7 machine-dependent longs: the 3 relocated absolutes inside the block (`$2e0 $2f6 $3f6`, they hold START's own TPA addresses) and 4 operands START patches at run time (`$2ae` old trap-1 vector, `$2be/$2c6/$2ce` pool base/size). `huntpatch.py verify` masks them and **refuses sites that overlap them** (their value differs per machine).

### 1.2 The game's own file loader (D15R at `$c0100`)
- `$c0100`: header words `+0 = $0010` ($c0110: swap the vector table), `+4 = $0052` (**`$c0152` = file read**), `+6 = $0260` (`$c0360` = init).
- `$150` hook [disasm of the dump]: `clr.l $c0736` (Fseek offset); `move.l #$11170,$c073a` (max 70000 B; FILES/0 is exactly 70000); `move.l a0,$c073e` (destination); `d0` hex digit -> ASCII (`+$30`, `+7` if > '9') -> `lsl #8` -> `$c0752` = `"X",0`; save SR at `$1ac`; `sr = $2700`; `jsr ($c0100+4)`; `clr.w $c0734`; `move.l #$5b4e748b,$1e02.w`; restore SR; **`jmp $d60a.l` at `$1a6` = the single exit**, back into the game.
- `$c0152`: saves all registers and the MFP, swaps the vector table `$8..$7fc` with the saved TOS image (so TOS runs in its own world), restores the MFP image, `sr = $2300`; on the first call (`$c0734 != 0`) sets `$4ba = $e000` and Dsetdrv + Dsetpath(`$c0760`); `Fopen($c0752)`, `Fseek($c0736)`, `Fread($c073a bytes -> $c073e)` (result stored in **`$c0358`**, negative if Fopen failed), `Fclose`, swaps back, returns. Dest < `$800` goes through `$80400`. `$c0742 == $5772` = write mode (save games).
- The game calls it only through the `$d542 -> $150` patch. Observed destinations on a normal boot (boot.md): 6->$23000, 4->$10FB2, 3->$11656, 7->$79714, 8/9->$2AD00, 1->$61514, 2->$48004, E->$23000.

## 2. Patch delivery design
```
START.TOS (shipped UNPACKED, ours)           FILES\P (payload image, ours)
  text $686: lea $7e800,a7 -> jmp stub  --->  $8BA00 'HNPA' hnentry: verify all sites, apply all or none, STE probe
  text $7f20: 142-byte stub                   $8BB40 hookexit/apply (deferred sites)   $8BC00 site table
                                              $8BFF0 FLAGS  $8BFF8 MARKER   $8C000.. blobs   $90000.. sample bank
```
1. **Carrier = a patched copy of START.TOS, payload = an extra file `FILES\P`**, not appended to START: START's bss addresses (`$230c4`, `$230ca`, `$230e4`...) sit right behind its text, so growing the text/data would need the bss relocations rewritten (as mw1patch had to). Instead START keeps its exact layout: only 6 bytes change (`4ff9 0007e800` -> `4ef9 <text offset $7f20>`, one extra relocation entry at text `$688`, the reloc table is re-encoded and round-trip checked) and the stub lives in the **zero run `$7f10..$80d0`** of START's text. Proof that the run is dead: it is all zero in the tail dump (first non-zero byte `$80d0`; START writes variables only from `$80d0`) and no relocation or pc-relative operand points into it (`$80d0` is the lowest target). Shipped as an unpacked program (33766 B): no repacker needed; START's loader checksums are not involved (START has none on itself; the only `$1234` sums are on the disk's root and partition sectors, which are untouched).
2. **Stub** (position independent, asserted by assembling at two orgs): saves d0-d7/a0-a6/SR, then reads `FILES\P` in <= 70000-byte chunks **through D15R's `$c0152`** (sets `$c0736/$c073a/$c073e/$c0752`, `jsr`, `clr.w $c0734` like `$150`, reads `$c0358`), up to `$23600` bytes ($8BA00..$AEFFF). This is the game's own FAT/HD path: it works on every machine the game works on, with the right vectors/MFP/interrupt state, whereas a bare GEMDOS call at the tail runs with SR `$2700` and START's masked MFP. Then it checks the magic `'HNPA'` at `$8BA00`, `jsr $8BA04`, restores everything and does START's original `lea $7e800,a7 / jmp $800.w`. **Missing file or no magic -> the game starts unpatched** and no marker is written.
3. **Core** (`hnentry`): presets `'HNPF'`, probes the STE hardware (section 4), pass 1 compares the original bytes of EVERY phase=boot site, pass 2 (only if all matched) writes them and sets `'HNPO'` at `$8BFF8`. Verified: one wrong original = nothing from the boot phase is written (section 6).
4. **Load hook** (only built in when a `; load:` patch exists): the file hook's single exit `4ef9 0000d60a` at **`$1a6`** becomes `jmp $8bb40` (a normal boot site). `hookexit` saves all registers, runs `apply` (destination `$c073e`, byte count `$c0358`; sites fully inside the file just read: orig -> write, already new -> skip, other -> `'HNPF'`), then repeats the original `jmp $d60a`. It is `jmp`, never `jsr`: the exit has no frame of its own.
5. **Site table** `$8BC00..$8BFEF` (1008 B): entries `{addr.l len.w phase.w orig[len] new[len]}` (inline bytes, `8+2*len` each; a 6-byte `jmp` hook = 20 B, ~45-50 sites), end `addr = 0`. Overflow is a build error that names the numbers. If more is needed the table can move behind `$8BFFF` (it is an `equ`), tell the loader owner.
6. **File patches** (`; image: FILES/n`, `; edit: $off orighex`, `org HB+$off`; HB = the file's RAM destination from the load map, or `; base: $addr`): edit the build copy of a FILES/n file (e.g. the sound driver) and are verified against the shipped file. HUM.FIC and START.TOS are packed and unsupported (use boot-phase RAM sites for the resident game).
7. **Sample bank**: `build|live --samples FILE` places FILE at **`$90000`** (max `$AF000-$90000 = 126976` B) inside the same payload, so it is read by the same stub in the same load (3 chunks for the full 144896-byte image; tested with a pattern-filled image). No second mechanism needed. Blob orgs are range-checked per name prefix (`p4_` `$8C000-$8DFFF`, `snd_` `$8E000-$8FFFF`, `test_` `$8DC00-$8DFFF`); overlaps are build errors.
8. **Commands**: `verify` (derived original bytes vs rebuilt tail image AND vs the dump; deferred sites vs the file), `list`, `build [--only] [--out build/game] [--samples F] [--fill] [--corrupt]` (originals untouched; writes START.TOS, FILES/P and copies the rest; `build/game.json` manifest), `live` (stharness `capture_frames(live=)` format: `.img` at `$8BA00` with FLAGS=3/MARKER=HNPO and `.json` with the sites; `--no-ste` for a plain-ST FLAGS), `boot` (cold boot a build in Hatari), `taildump` (regenerate the dump), `fillcheck` (free-RAM proof). Default patch set empty: all patches in `patches/` except `core.s` are `; default: no` until the lead flips them. Self-tests (default no): `test_boot_poke`, `test_defer_poke`.

## 3. Results (all [obs], cold boots of `build/game` = empty patch set, 0 sites)
| machine | TOS | RAM | result |
|---|---|---|---|
| STE | 1.62 | 1 MB | boot to the 3D view, `MARKER='HNPO'`, `FLAGS=3`, in_game True, 4.6 fps (same as the unpatched game, boot.md) |
| Mega STE | 2.06 | 4 MB | `HNPO`, `FLAGS=3`, in_game True, 8.2 fps (Hatari Mega STE runs 16 MHz) |
| ST | 1.04 | 1 MB | `HNPO`, **`FLAGS=6`** (probe ran, bus error, no DMA sound), in_game True, 4.6 fps |
- **TOS 2.06 / HDDRIVER**: it already worked with the existing image (`hunter.py build_hd`); nothing had to be fixed. It is only slow: the 4 MB Mega STE memory test takes ~100 s before the HW screen (the harness stage timeouts are raised to 400 s inside `huntpatch.py boot`; `boot_to_game()` with its 90 s default would not have waited). The HW screen reports "Mega STE, 8/16 MHz, TOS 2.06, 4 MB".
- **Plain ST**: the harness' reference crops are STE pictures (12-bit palette), `boot_to_game()` fails its `title1` gate on a plain ST although the game runs; `boot --machine st` therefore uses `blind_boot()` (same inputs, fixed waits).
- Hunter on TT/Falcon was not run: Hatari here only has EmuTOS for those; START's `M` path (D15R_F5.FIC, Falcon) and real hardware are untested [INFERENCE: the stub uses only D15R, so it follows whatever START/D15R do].
- **Wrong orig byte** (`build --only test_boot_poke test_defer_poke --corrupt`, first site's orig byte flipped in the payload): cold boot on STE/1 MB: `MARKER='HNPF'`, in_game True (game runs unpatched), `$86a8 = 506c65617365` ("Please", unpatched), `$11642 = 0000000000000000` (deferred site not applied), `$1a6 = 4ef90000d60a` (load hook not installed).
- **Positive** (same patches, no corruption): `HNPO`; `$86a8 = 504c45415345` ("PLEASE"), `$11642 = 484e444546455221` ("HNDEFER!", applied by the load hook after FILES/4 was read), `$1a6 = 4ef90008bb40`.

## 4. STE detection
`probe` in `core.s` (cookies are not trustworthy under Gamex): temporarily points the bus error vector `$8` at a handler that resets the stack, reads `$ffff8901` (DMA control; bus error on a plain ST), and if the DMA is stopped writes `$5a` / `$a5` to the frame start mid byte `$ffff8905` and requires read-back (original restored). Result word **`FLAGS` at `$8BFF0`**: bit0 STE-class DMA sound present, bit1 probe ran, bit2 bus error seen. [obs] STE 1.62 and Mega STE 2.06: `3`; ST 1.04: `6`. TT/Falcon: [INFERENCE] bit0 set (STE-compatible registers), not run. `live` images carry `FLAGS=3` (snapshots are STE). The Audio code should test bit0.

## 5. Free RAM re-proved (pattern method)
`build --fill` makes `FILES\P` a full 144896-byte image whose every unused byte is a non-zero position-dependent pattern (`fill_byte`): `$8BA00..$AEFFF`, 144548 pattern bytes. Cold boot, menus, new game, walk to the car and drive 25 s with Up+Left held, dump RAM `$0..$fffff`, `huntpatch.py fillcheck` compares every pattern byte:
| machine | TOS | RAM | pattern bytes | changed | `$AF000..$BFFFF` non-zero bytes |
|---|---|---|---|---|---|
| STE | 1.62 | 1 MB | 144548 | **0** | 20012 in `$AF000..$B81FF` (HDDRIVER pool at `$af100`), **0** in `$B8200..$BFFFF` |
| STE | 1.62 | 2 MB | 144548 | **0** | **0** (pool moved to `$186000`) |
| Mega STE | 2.06 | 4 MB | 144548 | **0** | **0** (pool at `$186000`) |
So `$8BA00..$AEFFF` is free through boot, loading, menus and driving on 1, 2 and 4 MB; `$B8200..$BFFFF` is free at all three sizes (the stub does not load there; HDDRIVER's pool starts at `$af100` on 1 MB, so the payload ends at `$AEFFF`). Limits: one 25 s drive, not the ~19000 VBL demo run of sound.md §3.3; plain ST 1 MB was not poisoned (same layout as STE 1 MB [INFERENCE]).

## 6. Gotchas / for the next agent
- Sites in the START-copied hook block `$150..$423` outside `$1a6` are allowed but not the 7 volatile longs; U-pressed `$a09e` refused.
- Only the 1 MB dump exists for verify; the HUM image and the hook block are machine independent except the volatile operands (checked by reasoning, 2 MB/4 MB cold boots boot identically).
- `huntpatch.py boot` needs an unused display; at most 2 Hatari at once. A `UnidentifiedImageError` from a screenshot is harness flakiness, rerun.
- `work/dumps/boot/ram_tail_1mb.bin` is git-ignored: `huntpatch.py taildump` regenerates it (only the verified ranges `$150..$423`, `$800..$12003`, `$8ba00..` reproduce byte-for-byte; low RAM differs run to run).
- `build/` and `START.TOS` unpacked are git-ignored; originals untouched (md5 of START.TOS, HUNTER.PCH, GXUT251.PRG, HUM.FIC, FILES/4 equal the README values after all builds).
