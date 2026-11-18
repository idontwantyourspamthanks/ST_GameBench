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
