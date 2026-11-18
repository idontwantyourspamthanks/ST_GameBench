# Nebulus / Tower Toppler: floppy release (NebFloppy)

Tags: **[obs]** raw output this session (files in `work/floppy/res/`, scripts in `work/floppy/`); **[INFERENCE]** not proven.
Tools: `tools/nefloppy.py` (image patcher, mine), `tools/nebrelease.py floppy|build --floppy|check` (mine), harness `work/floppy/nebfloppy.py`
(subclass of `stharness.Hatari`: `--disk-a` on a LONE image, `--fastfdc no`, no GEMDOS drive) and gate `work/floppy/fgate.py`.
Hatari 2.6.1; real FDC timing everywhere. Real hardware untested.

## 0. VERDICT: Option A (patch the user's own disk), static in-file patching, no loader/stub files
Evidence below: the floppy's game is the same program as PP's (same code base, other build): **every one of our patch sites holds the same instructions at
a shifted address**, the loader is plain GEMDOS (no Gamex, no hard-disk driver), and the game file can simply be rewritten. Option B (PP's files + our START.TOS
on a floppy) also works [obs, section 4] but does not use the user's disk, so it is only the fallback.

## 1. The disk [obs]
`alt/floppy/Nebulus (1988)(Hewson)[cr Atari Legend].st`, 419,840 B, md5 `32469782608f012a88dfa6a50de1e10f`. It is NOT 80x9: BPB = 512 B/sector, 2 sectors/cluster,
1 reserved, 2 FATs of 5 sectors, 112 root entries, **820 sectors = 82 tracks x 10 sectors, 1 side**, media F9. Boot sector: starts `60 62` (bra), 256 words sum
**$1234** (executable). Its code (`$64`): `cmpi.l #$31415926,$426.w / bne` -> clears `$420,$426,$42a` and jumps through the reset vector (kills reset-resident programs), sets
`$825e`, prints "Legends never die!" (Cconws) and returns (a "boot sector virus remover" / signature; harmless).
```
$ mdir -i orig.st ::
AUTO         <DIR>       BOOTDISK PRG       448   PLANE    NEO     32212   TOPPLER  JMP    271839   TOPPLER  NEO     32128
$ mdir ::AUTO     TOWERTOP PRG   6670   BOOTDISK PRG   448
```
All files contiguous (AUTO dir cl 2, BOOTDISK 10, PLANE.NEO 11..42, TOPPLER.JMP 43..308, TOPPLER.NEO 309..340, free from 341); the two BOOTDISK.PRG entries share one cluster.
**Hidden program**: the first free sector (cluster 341, logical sector 696 = track 69 sector 7) holds a `601a ... 41f9 00078000` 448-byte program (same bytes as BOOTDISK.PRG)
that the loader's GEMDOS calls read (FDC trace `fdc read sector addr=0x5cd0 ... track=69 sect=7`). My first rewrite put TOPPLER.NEO on top of it and the loader hung after that read
(`work/floppy/` run `nf_A1`: 21 reads, black screen); NEO is now placed at cluster 342 and the sector is untouched.

## 2. Loader chain [obs: FDC trace, RAM dumps `ram_wait.bin`, `ram_150.bin`]
1. TOS 1.62 boots the sector (reads sector 0 at `$185c`), then runs `AUTO\BOOTDISK.PRG` and **`AUTO\TOWERTOP.PRG`** (6670 B, **Atomik v3.3 by Altair/MCS**: string `ATOMIK v3.3 by ALTAIR VMAX/MCS` at file `$215`).
2. TOWERTOP.PRG = the Atari Legend intro (screens: "ATARI LEGEND PRESENTS / TOWER TOPPLER / This game is also known as Nebulus ... Game cracked by Avenger / July/04/2005") which **waits for a key**
   (one SPACE; reads jump 19 -> 84 after the key, `base3.py`). Then, with plain GEMDOS (`Fopen/Fseek/Fread/Fclose`, names `PLANE.NEO`, `TOPPLER.NEO`, `TOPPLER.JMP` in the unpacked code at `$ac18..`):
   PLANE.NEO -> `$33b00` (shown), TOPPLER.NEO -> `$33b00` (the "TOWER TOPPLER ... US GOLD" picture), **TOPPLER.JMP -> `$33b00`** (FDC: `addr=0x33b00 ... 0x75f00`, 530+1 sectors) and `jmp $33b00`.
3. TOPPLER.JMP is the **unpacked GEMDOS image** of the game (`601a`, text `$a85e`, data `$373a6`, bss 0, reloc table 2495 B; NOT packed, no PP-LZ/ICE/Atomik layer). The same relocator as PP's NEBEXE
   (`lea $33b1c(pc),a2 / cmpi.w #-1,$1a(a2) / beq -> jmp`, then the `add.l d2,(a0,d0.l)` loop, final `jmp $4b08+base` = `$38624`).
4. After the jump the game runs on bare hardware (TOS data is clobbered by the game's init as in PP's flow). Measured: RAM at the title (`ram_150.bin`) = the relocated file, **418 of 269,316 bytes differ** (runtime variables only:
   `$33c09..`, `$3820d`, `$382c8`, `$3875a`, `$3d5b1`, ... groups listed by `work/floppy/` script output in the session); no hidden patch, no Gamex hook. VBL `$70=$382d8`, ACIA `$118=$384fc`, `$42e`=`$100000`.
5. Free RAM above the file after load: zero from `$760de` to `$78015` (7991 B) [obs]; the file end is `$760df`. Same dead zone as PP's build (`$75720..$77ec0` once the table is gone).

## 3. Is the floppy game PP's game? Not byte for byte, but every patch site matches [obs]
`TOPPLER.JMP` (271,839 B, md5 `8c9a62a4a2261a46d5c3a2d54639819b`) vs PP's `NEBEXE.FIC` unpacked (271,849 B): headers equal except text size (`$a85e` vs `$a866`), 1564 vs 1566 relocs.
Differences (resync diff, `res/map_mismatch.txt`, `sitecmp.py`):
* text `$4c46`: PP has a 50-byte 50/60 Hz routine (`tst.w d0 / bmi / move.w d0,$38218 / ... move.b d0,$ffff820a`), the floppy a 14-byte `clr.w d0 / move.w d0,$46fc / move.b d0,$ffff820a` = **always 60 Hz** (Hatari status bar says "RGB 60 Hz"); +36 bytes in PP;
* text `$83e2`/`$841e`: the floppy has two extra `add.w $338f2.l,d0` / `sub.w $338f4.l,d0` (a cursor/bonus speed difference), `$84f9` 4 bytes; so PP is 36, then 24, 12, 8 bytes longer; the data segment is shifted by 8; the sprite data of the data segment differs a lot.
Address map `floppy = PP - 0 / 36 / 24 / 12 / 8` after PP text offsets `$4c46 / $8406 / $8436 / $850a` (`SEG` in `nefloppy.py`). With every relocated long normalised through that map, 109 bytes still differ in the mapped text: all are pc-relative displacements/16-bit
operands across a displaced block (checked per site below), none is a code difference.
**Site comparison** (`res/sites_orig_compare.txt`; `nefloppy` repeats it as a disassembly comparison with mapped absolute operands/branch targets before writing anything): all 17 sites have the same instructions:
```
$377a2 -> $377a2  41f9000327f0 | $37a90 -> $37a90 | $3792c -> $3792c | $38514 -> $38514 13c000038498 | $3855a -> $3855a | $3851a -> $3851a 301f08b80006
$3adb4 -> $3ad90 | $3b0a4 -> $3b080 | $39ffa -> $39fd6 4e75 | $3a332 -> $3a30e 4e75 | $3d110 -> $3d108 | $3d698 -> $3d690 33fcfffe00038212
$3d6c4 -> $3d6bc (bsr.w disp ae74 -> ae7c, same target) | $3d662 -> $3d65a (bsr.w/bra.w displacements differ, same targets) | $3dcf4 -> $3dcec 4eb90003853a | $3dfd6 -> $3dfce | $3e352 -> $3e34a
```
The 25 distinct game addresses in our assembler sources (`ed_editor.s`, `nt_keys.s`, `ni_latch.s`, `cr_credit.s`) map to places with the same content (`res/literals.txt`; two "DIFF" lines are a data variable followed by different code and a bsr displacement).
The tables the editor uses (`$3ad9e` BCD times `0400 0450 ...`) are at `$3ad7a` (dump: `0400` there), the keyboard ISR `$384fc..$38522` and poll `$3853a` are byte-identical to PP's UNHOOKED file, the flip `$3868a` is at the same address; **PP's Gamex hook (`jmp $200` over `cmp.b #$f6,d0 / bcc` at `$3850c`) does not exist on the floppy**, the original compare is there.
Timer words are at `$3ad74` (PP `$3ad98`). Title marker for the harness: the VBL vector `$70 = $382d8` (the string "High Scorers" is in the file from load time on, so it cannot mark "game is up").

## 4. Feasibility of both paths [obs]
* **A**: pre-relocated, patched TOPPLER.JMP in the original disk layout -> title in 63 s (incl. 20 s wait for the key), tower playable (`fbis.py`, bisect runs: no patches -> timer counts; everything but the editor -> timer counts).
* **B** (PP's files, our START.TOS from `nepatch build` as `AUTO\START.PRG`, files in the root of a 720 KB image, no hard disk, STE 1 MB): title reached (`$3d00f` = "High") ~59 s, `$b0020 = NEPO`, 18 sites. [obs: `probeB.py` output `0003D00F: 48 69 67 6.. / 000B0020: 4e 45 50 4f`]
  So B is possible, but: a different game build (PP's, 50/60 Hz F5/F6) and none of the user's disk.
**Choice: A** (same code => patches apply; the loader allows injection by rewriting the game file; nothing runs from other files; no stub reading the disk).

## 5. Design of the floppy delivery (`tools/nefloppy.py`) [obs, built and gated]
* TOPPLER.JMP is **relocated at build time** to `$33b1c` (the loader never loads it elsewhere) and the header word `$1a` (the relocator's `cmpi.w #-1,$1a(a2)` absolute flag) is set to `$ffff`; the relocation table is dropped. The final `jmp` operand (text offset `$50`) is set to the stub.
* All sites (`patches/*.nep`, in-image ones) are written at the mapped addresses; blobs sit at the SAME addresses as the HD build (`$75740` editor, `$76c00` trainers, `$76d00` latch, `$76d40` tables, `$77300`, `$77a00` credit), i.e. in `$75720..$77ec0` behind the data. The file grows 271,839 -> **279,552 B** (= `$77f00-$33b00`, 546 sectors, 273 clusters); the loader reads by the directory size.
* Blobs are assembled from the SAME sources as the HD build with the 25 game addresses mapped (`remap_source`); **`nefloppy.py selftest` proves the pipeline** (unmapped generators reproduce `patches/*.nep` blocks byte for byte for cr_credit, ni_latch, nt_trainers, ed_overlay).
  The floppy editor replaces `save_file` (a TOS excursion needing PP's Gamex TOS image, `$ffd80`/`$ffd86`, which does not exist on the floppy path) by "Kept in RAM (no disk)"; that changes the code size, so entry points the `.nep` sites jump to directly (`ed_key` `$3851a`, `ed_opt` `$3d662`) are translated **by symbol** (HD listing vs floppy listing).
  **A first build without that translation jumped into the middle of other code: F10 / the Options page crashed to "11 bombs" (Line-F, TOS `Pterm(-1)`, stacked PC in the credit blob)** [obs: `dbgf10*.py`, `Pterm(-1)` in the GEMDOS trace]; fixed, gated.
* Entry stub (40 B at `$77ec0`, only when the editor is in the set): marker `NEPO`; `cmpi.l #$c0000,$42e.w` (phystop): on a 512 KB machine it writes the original 10 bytes of the editor's title hook back and the marker becomes `NEPS`, then `jmp $38624`.
  Reason: the editor draws at `$A0000`, the store is `$BC000`, so it needs more than 512 KB.
* FAT: TOPPLER.JMP rewritten in place at cluster 43..315, TOPPLER.NEO moved to 342..373 (cluster 341 = the hidden sector is left alone), FATs rewritten, dir entries' size/cluster updated; boot sector, AUTO\, PLANE.NEO, BOOTDISK.PRG untouched
  (`cmp`: sectors 0, AUTO dir clusters 2..42 identical; `fsck.fat -n -F 1`: same state as for the original).
* **Static patching has no runtime "original bytes" check** (the HD build's NEPF fallback). The equivalent is at BUILD time: the tool refuses an input image whose md5 differs, and compares every site's original instructions with PP's:
  `res/negative_control.txt`: a flipped source byte -> "original instructions differ ... nothing written", no output file; a changed boot-sector byte -> "md5 differs ...". There is no on-disk "wrong game" case to boot.
* Campaign disk: `Nebulus_campaign_disk.st` (720 KB FAT12, deterministic, all-zero `NEBLEVEL.OVL` 8192 B), per the lead's message; **nothing in this build reads or writes it** (section 8).

## 6. Gates [obs; raw files `res/`; STE cell = the exact image that is in the zip, md5 `5c832194c7602348d105cb21e08569d5`]
Cold boot from the LONE image (`--disk-a`, `--fastfdc no`, no hard disk, `--joy1 keys`), one SPACE at the intro (20 s), `fgate.py`.
```
                          STE 1MB TOS1.62   ST 1MB TOS1.04    Mega STE 4MB TOS2.06   ST 512KB TOS1.04      control (original floppy, STE)
title (s, incl. 20 s wait) 63                63                69                     63                    63
credit band lit px         3284              3284              3284                   3284                  0
marker $77ec0 / sites      NEPO, all 8 hook   NEPO, same        NEPO, same             NEPS (editor hook out) original bytes at every site
                           bytes as built
F10 manager (menu px /     5784 / 0          5784 / 0          5784 / 0               not opened (expected)  -
 title rows px)
editor: new level, cell,   playtest timer (32,24,68), rsTest 1, rsLvl $7fff; F10 back (rsTest 0); Save -> store RAM 4e434d5000010001 (STE, ST, MSTE identical)
 Playtest, F10 back, Save
tower (timer words)        (30,78,78)        (30,78,78)        (30,78,78)             (30,78,78)            (30,78,78)
E / T                      noen ffff, timer counts (24,56,69)->(24,56,16); frz ffff, (24,56,3) x3 frozen; T again runs (all four cells; control: not applicable)
20 s drive                 14 rounds, vbl +1248, no crash   +1250      +1244                  +1247                 +1254
FDC reads / drives /       695 / {0} / 0     695 / {0} / 0     700 / {0} / 0          695 / {0} / 0         678 / {0} / 0
 sector writes
crash lines in log         0                 0                 0                      0                     0
```
Raw files: `res/ste_1mb_tos162.txt` (copied from the console output of the same image), `res/st_1mb_tos104.txt`, `res/megaste_4mb_tos206.txt`, `res/st_512k_tos104.txt`,
`res/control_ste.txt`; screenshots `shots/` (manager, editor, cell menu, playtest, tower; original cracktro / title). The 512 KB cell reaches the same tower with the editor off; its "F10 menu px 8564 / title rows 4340" are
just the title page text (the manager did not open, the page was still the game's; same numbers as the unpatched control).
Credit band = 3284 lit pixels, exactly the HD release's figure (the same blob, same line).
**Negative control** (section 5): build-time, `res/negative_control.txt` (no `NEPF` runtime fallback exists in a statically patched disk).
**Baseline** (the unpatched original floppy in the same harness): title 63 s, credit 0 px, original bytes at all sites, tower, F10 does nothing (`Pterm` trace empty), 678 FDC reads, 0 writes.

## 7. Release
`dist/Nebulus_floppy_v1.0.zip` (git-ignored): `NEBULUS_floppy/` = `Nebulus_game_disk.st` (419,840), `Nebulus_campaign_disk.st` (737,280), `README.TXT`, `PATCHES.TXT`. Build: `python3 tools/nebrelease.py floppy --zip` (= `build --floppy --zip`).
Content-vs-gate: `nebrelease.py check dist/Nebulus_floppy_v1.0.zip` -> 4 of 4 members `same` (`res/check.txt`); two builds byte-identical (`res/determinism.txt`); the gate cells ran on the files extracted from the zip (`work/floppy/Z/`).
Build line in the docs currently says `git 613b9f6 + uncommitted changes`: **the lead must commit, then rebuild the zip** (zip member dates = HEAD commit time).

## 8. Open items
1. **No disk persistence on the floppy**: the editor's "Save to disk" only keeps the level in RAM. A campaign-disk Load/Save (the lead's UX note) needs a TOS excursion on this boot path: a snapshot of TOS low RAM (`$8..$1b960`, a TOS-state copy + the MFP block) must be taken by the entry stub BEFORE the game's init (which clears `$8700..$33a4f`), plus the F9-table layout the editor expects (`$ffd80/$ffd86`) or a rewrite of `swap_tos`; or direct FDC register access. Needs >=1 MB for the copy. Not built. (Fopen mode 1 on drive A from the game: UNTESTED.)
2. `ed_key` ($3851a) is called by ni_latch's stub1 after `andi.b #$f0,d0`, so `cmp.b #$44,d0` sees `$40` there. F10 still opened the manager in all floppy cells (the title poll also reads the game's own cell? [INFERENCE: not traced]); the F10-fix owner should check this interaction before relying on the latch.
3. Real hardware, a second drive, 2-player, TT/Falcon: untested. Real boot takes ~45 s after the key; the loader is the original.
4. The floppy game runs at 60 Hz (own build) and has no PP 50/60 Hz switch code (`$4c46`); the input-latency numbers of `input.md` were measured at 50 Hz in PP's build [INFERENCE: same loop structure, not re-measured on the floppy].
5. The Options-page hint of the editor (`ed_opt`, site `$3d65a`) is applied; its page was not screenshotted in the final gates (the options page itself is the same as in the unpatched control, only the HD build's "empty line 1" assumption was checked by looking at the floppy page: line 1 is empty).

## 9. Round-3 floppy editor: six blocks, and a TOS-state capture in the stub (this session) [obs]
`tools/nefloppy.py` now assembles the SAME six-block editor as the HD build (`gen_ed.py` LIM table): CODE1 `$75740` 5308 B, DATA `$76d40` 1324 B, CODE2 `$77300` 1768 B,
CODE3 `$77a40` 550 B, CODE4 `$77dc0` 252 B and CODE5 `$76c76` 136 B; `_asm_editor` asserts the six segment starts instead of three.  Nothing moved, so `symmap` is empty:
`ed_key`/`ed_opt` are at the same addresses as on HD (`$778e6`/`$77904` in the listing) and the site translation stays as a safety net.
The editor's campaign-disk code (`disk_op`, CODE4) needs a copy of TOS's own low RAM, its length and TOS's 24-byte MFP block; on HD these come from Gamex (`$ffd80`/`$ffd86`/`$fffaa`)
and on the floppy the editor reads them from `RS+rsTosP`/`rsTosN`/`rsMfpP`.  `patches/ed_floppy_capture.s` (the routine NebEditor3 wrote as a reference) is now part of the floppy
build, assembled with the editor's symbols (`mfp_save` resolved from the floppy listing):
* code at **`$7726c..$772d6` (106 B)**, the free gap between the DATA block (ends `$7726c`) and CODE2 (`$77300`); nothing else was free (`CODE5` has 2 free bytes, `CODE4` 4);
* **called from the entry stub** (`$77ec0`): `bsr.w $7726c` before `jmp $38624`, on the >= 768 KB path only (the 512 KB path restores the title hook and jumps on, so it never
  runs - the editor is off there anyway).  The stub no longer carries two zero words after `NEPO`, so the marker is 6 bytes (`NEPO` + `cmpi`/`bra`) and the final jump goes to
  `$77ec4`; `cmpi.l #$c0000,$42e.w` still distinguishes 512 KB (zeros before the jump, marker `NEPS`).
* it copies `$8..membot($432)` (in 48-byte units, exactly the unit `swap_tos` exchanges) to **`$C0108`**, appends the 24-byte MFP block behind the copy (**first build: directly behind it, `rsMfpP $ca968`: WRONG, `swap_tos` exchanges 24 B too many and swapped the block away; the block now sits behind a 24-byte gap at `$ca980`: section 10**) and sets
  `rsTosP`/`rsTosN`/`rsMfpP`.  Measured at the title on STE 1 MB: `rsTosP $c0108`, `rsTosN 897` (898*48 = 43,104 B from `$8` to `$a868`), `rsMfpP $ca968` (now `$ca980`).
  `$C0108..$CA980` is above the game and outside the editor's `BUF $AA000..$AC000` / stack `$AC000..$AD000`; it needs >= 1 MB (the stub's 768 KB gate is therefore a little
  optimistic for this copy: a 768 KB..1 MB machine is not a thing on the ST line, so the gate was left alone).
Gates (`work/floppy/f161.py`, the HD `work/editor/e161.py` cell adapted to the lone `--disk-a` boot): STE 1 MB TOS 1.62, campaign disks swapped in and out with
`hatari-option --disk-a`; see section 10.

## 10. Eject / swap on one drive: root cause (the MFP block was swapped away) and fix (NebFloppyEject, this session) [obs]
Raw files: `work/gate_NebFloppyEject/res/before_fix.txt` (shipped v1.1 zip), scripts `work/gate_NebFloppyEject/` (`lib.py` = own `grab` file names, `x1.py`..`x3.py` probes,
`fge.py` = the new gate, `f161_nfe.py` = `work/floppy/f161.py` unchanged apart from paths), outputs in `res/`.
**Symptom** (NebRelease3, shipped zip, `f161.py`: eject with `--disk-a /dev/null`): empty drive -> message `None` after the 30 s poll, later cells "Not a campaign disk" with a stale
directory, store != file.  It is NOT a Hatari artefact of the `/dev/null` eject and NOT a stale-media (BPB/FAT/dir cache) problem: **the first excursion on an empty drive never ended.**
(`/dev/null` is a legal eject here: Hatari removes the disk, then logs `Image '/dev/null' filename extension, or content unrecognized` and leaves the drive empty; `--disk-a none`
ejects cleanly; `--disk-a ''`/`""` through the command fifo is NOT an eject (`Image '""' not found`, the old disk stays in): do not use it.)
Evidence before the fix (`res/before_fix.txt`):
* FDC trace of the stuck excursion: after `fdc eject drive=0` the only FDC activity for 154 s (4281 -> 11985 VBL) is `fdc type I seek ... spinup=on verify=on ... pc=e017e2` + `fdc start motor with spinup`;
  it completes only at `fdc insert` (`fdc complete command VBL=12059`).  An empty drive gives no index pulses (the WD1772 waits for them, real hardware too); TOS gets out of this with its own
  timeout counted on `_hz_200` (`$4ba`, Timer C).  The later cells ran while that first excursion was still hung, so every keystroke and every result was one operation out of phase (the "stale" results).
* In the hung excursion `$4ba` read `0x21bb` in all 12 samples (3 s apart), CPU in TOS's FDC wait loop (`$e01740 bcs.b`), SR `$2500`, and **every MFP register was 0** (IER/IMR/VR/TCDCR..; GPIP only).
* The block `rsMfpP` points to (TOS's MFP state, 24 B taken by the stub at boot) was `b1 04 00 1e 64 ...  57 00 50 c0 64 ...` at the title and **all zeros inside the excursion**.
**Cause**: `swap_tos` (shared, `ed_editor.s`) is `lea 8(a0,d0.l),a6` with `a0 = 8`: it exchanges (n+1)*48 **+ 24** bytes (one `movem` chunk too many; `rsTosN 897` -> 43,128 B, not 43,104).  The
capture put the MFP block **directly behind the copy** (`$ca968`), so the extra chunk exchanged the block with game RAM `$a868..$a87f` (zeros) BEFORE `mfp_set` read it ->
the excursion ran with the whole MFP off: no Timer C, no `_hz_200`, no FDC timeout.  With a disk in the drive nothing needs a timer, which is why every disk cell passed and the HD build
(MFP block from Gamex at `$fffaa`, not adjacent to its copy) never showed it.  Everything else on the stale-media list is already done by the excursion and was not the problem: `mchg`
answers "changed" for the first two drive-A queries (Getbpb re-reads the boot sector, the Fopen re-reads FAT/dir; TOS's BPB/FAT/dir caches live in the TOS low RAM that the copy keeps between
excursions, so they DO persist and `mchg` is what invalidates them), `crit` aborts every TOS error, `Getbpb(0)` always re-reads sector 0.
**Fix** (floppy only; shared code NOT touched): `patches/ed_floppy_capture.s` leaves a 24-byte gap (`lea 24(a1),a1`) between the copy and the MFP block: `rsMfpP` is `$ca980` on STE/MSTE (`$ca950` on
TOS 1.04), block `$ca980..$ca997`; routine 106 -> 110 B (gap `$7726c..$77300`, 148 B, now 38 B free); `swap_tos`'s 24-byte overrun now exchanges game RAM with the gap and back (harmless, symmetric).
Binary delta against the shipped v1.1 game disk: 29 contiguous bytes at file offset `$4ffbc..$4ffd9` (the capture routine); nothing else differs.  New game disk md5 `193f658f5864b7d8f168e4e2628f30ba`
(`nefloppy.py build` == `nebrelease.py floppy` output); campaign disk unchanged `a45b2711500796b393be931c2adf1d99`; HD build unaffected (`ed_editor.s`/`gen_ed.py` unchanged: CODE4 still `$77dc0..$77ebc`, 252 B).
[INFERENCE] The same 24-byte overrun exists on HD: it swaps the 24 bytes behind Gamex's copy with game RAM and back; harmless there as long as nothing lives behind the copy (the HD gates `e161.py` pass).
**Real-hardware note** [INFERENCE]: on a real STE/MiSTer the empty-drive cell now ends the way it does in Hatari: TOS's own FDC timeout (`_hz_200`) fires after about 3-6 s and `Getbpb` returns the null BPB -> "No disk".
The user sequence "remove the game disk, insert the campaign disk, fire" never reads the empty drive: the first `Getbpb` already sees the new disk (forced re-read of boot sector, FAT, directory).
**Gates after the fix** (game disk md5 `193f658f...`, lone `--disk-a`, `--fastfdc no`; eject = `--disk-a none` or `/dev/null`, insert = `--disk-a IMG`; raw: `work/gate_NebFloppyEject/res/`):
```
                                            STE 1MB TOS1.62         ST 1MB TOS1.04        Mega STE 4MB TOS2.06
fge.py (res/fge_<m>.txt): S1 swap w/o eject, S2 game disk back, E1 eject 5 s 'No disk' (7.2 s), E2 empty again 'No disk',
  E3 no disk->insert->fire, E4 eject+insert nofile/short/big/blank/t3, E5/E6, W1-W3 write protect, V1/V2 save + reload,
  6 fuzz disks (random0, magic_random, flip1, version2, badentries, valid), tower + frog, FDC type II during 15 s of play = 0
                                            ALL PASS (FAILS [])     ALL PASS              ALL PASS
MFP block at the title (rsMfpP)             $ca980 intact           $ca950 intact         $ccdb0 intact
fge2.py (res/fge2_ste.txt): disk A (1 level/1 camp) and B (3 levels/2 camps): game disk out, A in, Load = A; A out, B in, Load = B (store == B, not A); Save onto B: image == store;
  A loaded, B2 inserted, Save: B2's file == A content; empty drive 'No disk' -> insert B -> 'Loaded 3 levels / 2 campaigns'; empty -> A -> A; game disk back 'Not a campaign disk'; B over game disk (no eject)
                                            ALL PASS (U1-U12)       not run                not run
f161_nfe.py (the original f161 cells incl. the /dev/null eject), STE FULL with all 22 fuzz disks (res/f161_ste_full_fuzz.txt): ALL PASS, FAILS []. Earlier skipfuzz run 1: all PASS except 'Save from the editor root menu' = None (the cell reads the message after a fixed 5 s, the
  save needs 7.2 s after an eject+insert; the image/store checks that follow PASS); the copy now polls for the end of the operation.
```
Hatari gotcha found on the way: inserting `A.st` into drive A makes Hatari auto-insert `B.st` into drive B (`bAutoInsertDiskB`), a later `--disk-a B.st` then fails with "Cannot insert same floppy to multiple drives" (the gate looked hung): test disks must not be named `...a.st`/`...b.st` pairs.
Operation times (empty drive 5.2-7.2 s; with a disk 4.3-5.3 s; save after eject+insert 7.1-7.2 s) are Hatari FDC timing.  Not run: real hardware, two-disk gate on ST/Mega STE, the full f161 matrix on ST and Mega STE (fge.py with the 6-disk subset passed on all three machines; full f161 with 22 fuzz disks only on STE), TOS 2.06 on a MiSTer.
**Rebuild needed**: the shipped `dist/Nebulus_floppy_v1.1.zip` carries the old capture routine; `python3 tools/nebrelease.py floppy --zip` after committing `patches/ed_floppy_capture.s` gives the fixed game disk (md5 `193f658f5864b7d8f168e4e2628f30ba`).
