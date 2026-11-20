# Nebulus release (NebRelease): HD zip, credit line, launcher, floppy findings

Tags: **[obs]** raw output this session; **[INFERENCE]** not proven. Floppy release: dropped by the user's decision (a real floppy image will be supplied); only the findings below are kept.

## 1. Files
| file | role |
|---|---|
| `patches/VERSION` | the ONE version (`1.0`): README/PATCHES.TXT, zip name, on-screen credit all read it |
| `tools/nebrelease.py` | `credit` (regenerate `patches/cr_credit.nep`), `build [--out DIR] [--only P..] [--zip]`, `check ZIP|DIR` (content-vs-gate), `version`, `floppy`/`build --floppy` = stub that says it needs the user's floppy image in `alt/floppy/` |
| `patches/README_HD.TXT`, `patches/PATCHES.TXT` | templates (`{WHATSNEW}`, `{PATCHES}`, `{GIT}`, `@VERSION@`; `@@EDITOR ... @@END` blocks kept only when `ed_overlay` is in the set). Per-patch user text = `DOCS` dict in `nebrelease.py`; a patch without an entry refuses to ship |
| `patches/cr_credit.s` -> `cr_credit.nep` | the credit line (generated; default yes) |
| `tools/play.sh` | Hatari launcher (section 5) |
| `work/release/make_hd_image.patch` | diff for the lead's `tools/make_hd_image.py` (NEBULUS + NEBORIG folders; `nebrelease.py version` feeds the README table). Tested on a sandbox copy: `build_nebulus()` -> 9 files, `build_nebulus_orig()` -> 7 files |
| `dist/Nebulus_hd_v1.0.zip` | (final md5 in section 3) `NEBULUS/` = START.TOS (patched, 32975 B), NEPATCH.BIN, PP's NEBEXE.FIC / NEBULTIT.FIC / NEBULUS.PCH / GXUT270.PRG / NEBCHEAT.TXT, README.TXT (ours + PP's appended, CRLF), PATCHES.TXT; `NEBLEVEL.OVL` (8192 B) is added only when `ed_overlay` is in the set. Zip timestamps = the git HEAD commit time, so builds are byte-reproducible |

## 2. Credit line `vX.Y enhanced by dad_prg` (user's choice: the frog-on-a-plinth title page)
Hook [disasm of `work/dumps/title_1mb.bin`]: the title page is built at `$3d66a` (lines 0..2 = `$3cf91 "Design,Programming & Audio-Visuals"`, `$3cfb4 "by John M Phillips"`, `$3cfc7 "(c)1987,8 Hewson"` via `sub_03b360`, then `sub_03d81c` = "Mission #n" line 4 / "Sound On" line 5), falls to `$3d698 move.w #$fffe,$38212.l` (8 bytes), then the first flip `$3868a`. The same label `$3d698` is also reached by the High Scorers page (`$3d61c`) and the Options page (`$3d666`); the page word `$3d5b6` is 0 only on the frog page.
`sub_03b360(a0 = string, d0 = line 0..5)` centres the string and sets the screen offset through the row table `$3b3a0` (rows 84,104,124,144,164,184); glyphs are the game's 8x16 font (`$5c13c`, `sub_03b20a`), whose per-row plane pattern and the per-line palette give the colour. Line 3 (row 144) is the empty line between the copyright (line 2) and "Mission #n" (line 4).
Patch: site `$3d698` -> `jsr $77a00 / nop`; blob (64 B at `$77a00`, zero gap; the editor owns `$75740..$7779f`/`$77c80+`, trainers `$76c00`, latch `$76d00`): redo the `move.w`, `tst.w $3d5b6.l`, `bne` out, `lea str(pc),a0 / moveq #3,d0 / jsr $3b360.l` with `movem.l d0-d2/a0` saved. Text = `v<VERSION> enhanced by dad_prg` (24 chars, fits the 40-column line). **Change the screen/line**: edit `patches/cr_credit.s` (`moveq #3,d0` = the line; line 5 is "Sound On", rows are 20 apart) and run `nebrelease.py credit`.
Gate [obs, cold boot STE 1 MB, `work/release/credit_gate.py`; before = same set minus cr_credit, 24 screenshots each through the attract cycle, picture area 640x400]: all 12 title frames differ from the `before` run ONLY inside the box x 128..510, y 288..318 (= ST x 64..255, rows 144..159 = the credit line, 3284 pixels, identical in every title frame); the High Scorers and Options frames are pixel-identical (0 differing pixels); two frames differ in the frog's eye (46..82, 298..334), the frog's blink animation (timing, present in the before-run too: frames 2/12 vs 2/11). Screenshots `work/release/credit_before_title.png` / `credit_after_title.png`. In-game: the hook runs only on the title page, the blob redoes the displaced instruction exactly; every shipped-zip cell below reached a tower with the credit build.
Survives the attract cycle in the sense that it is redrawn each time the frog page is drawn and is absent on High Scorers / Options (user's choice: frog page only).

## 3. FINAL shipped zip (HEAD `1fee418`, build line `git 1fee418`, clean tree for patches/ and tools/)
`dist/Nebulus_hd_v1.0.zip` 282,529 B, md5 `e8a98eb1d52b65e8a67b32c16069ced7`, sha256 `a1c687fc791f7a723356b96cc5b67dbe4ca0421f66740d5794d7d10c0d129ae8`. Default set = cr_credit, ed_overlay, ni_jump, ni_latch, ni_shoot, nt_trainers (18 sites/blocks; `ni_hop`, `ni_turn` default no).
```
GXUT270.PRG  12990 2bf76f6677da80e725d76db4e8da0528   NEBCHEAT.TXT   219 e0f232cd7c3be9d1a520900f2171ebe5
NEBEXE.FIC  166648 0dd818c552aedc5a2501a7a9a718906e   NEBULTIT.FIC 27406 e1a2b20a5a441c0b7bf99ad7d94f375d
NEBULUS.PCH 102470 693c1810a4142fcc64448f51afa3bc88   NEBLEVEL.OVL  8192 0829f71740aab1ab98b33eae21dee122 (all zero)
NEPATCH.BIN  32564 4fc662116656b38e01462b4036a40ac4   START.TOS    32975 4ecf26d8b38049738a4b1b7448276e10
README.TXT    9715 ce00d129a95424be386af89c946d6e45   PATCHES.TXT   5343 d94efc9411965f80edf933045a1fed5f
```
Content-vs-gate: `nebrelease.py check dist/Nebulus_hd_v1.0.zip` -> 10 of 10 members `same` (size+md5) against a fresh build; two builds `b2`/`b3` byte-identical (`cmp`); the unzipped cell payload (`work/release/fin_ste/unz/NEBULUS`) has the md5s above. Game files equal PP's originals; START.TOS = PP's + 4 bytes + stub.
Cells (`work/release/final_cell.py`; each = fresh unzip of that exact zip -> harness ACSI+HDDRIVER image -> cold boot; raw outputs `work/release/fin_{ste,megaste,st}.txt`):
```
                       STE 1MB TOS1.62   Mega STE 4MB TOS2.06   ST 1MB TOS1.04
title (s)              14                17                     17
credit band lit px     3284              3284                   3284
F10 manager            title rows 0 px, menu text 5784 px (all three)
editor, zero OVL       Levels > <new level> > cell (Pillar) > Save: store RAM 4e434d50 00010001 (NCMP v1, 1 level) (all three)
tower                  timer 0x18        0x1e                   0x18
NEPO / sites           NEPO 18           NEPO 18                NEPO 18
hook bytes             $39ffa 602a, $38514 4ef9 00076d04, $3dcf4 4eb9 00076c08, $3d698 4eb9 00077a00, $3a332 4e71, $377a2 4ef9 00075740 (all three)
E                      noen ffff, states (0,0,0,0), timer counts (24,72,64)->(24,71,79) | (24,45,77)->(24,40,25) | as STE
T                      frz ffff, (24,64,63) x3 frozen | (24,40,13) x3 | (24,64,63) x3; T again runs (all three)
20 s drive             14 rounds, vbl +1044 | +1251 | +1044; crash lines in the Hatari log: 0 (all three)
file after Hatari exit 8192 B, head 4e434d50 0001 0001, NCMP, nlevels 1 (read from the image with mcopy; all three)
reboot with that file  store at boot 4e434d5000010001; Levels list has a third line (752 lit px); Play -> timer (32,40,0), RS 0000000000010000 (all three)
```
(Editor navigation: F10 held 1.0 s; Down x2 + fire = Levels; fire = `<new level>`; cursor Right x2 Up x2, fire, Down x2, fire = Pillar; fire, Down x10, fire = Save; Down, fire = Leave editor; Left; Up x4, fire = Original game. Joystick keys held 0.2 s: 0.4 s auto-repeats and skips an item.)

## 3b. F9 gates (STE 1 MB, harness, `work/release/ez*`; interactive, raw observations)
- (a) title -> F10 (manager open, `$b0020` poked to 0) -> F9 x3 -> GEM desktop reached [obs `ez2/a1.png`]; after F9 `$b0020` = `00000000` and `$bc000` = `00 10 66 00 00 06 32 3c ...` (no NCMP). RE-LAUNCH of START.TOS from that desktop was NOT achieved: select START.TOS + File > Open (and double-click) returned to the desktop without starting any program, marker stayed 0. The same happens for PP's GXUT270.PRG and for the ORIGINAL unpatched build (control: original game, F9, GXUT270 selected + File > Open / double-click: nothing starts) => [INFERENCE] my mouse automation (Hatari's relative mouse + TOS double-click timing; the first click of every xdotool double-click is lost), not the release; unresolved. So `NEPO` after a desktop re-launch is NOT proven.
- (b) in a tower playing a custom level (store loaded from the saved file, level started from Levels > Play, timer t-450): F9 x3 -> desktop [obs]; the store at `$bc000` is overwritten by F9 (its swap area `$80008..` receives game RAM, which lands on `$bc000`). GXUT270 restore NOT run (same GUI problem). Simulation of the effect [obs `ez2/s1..s3`]: boot, `loadbin` the real post-F9 `$bc000..$bdfff` bytes (`ez2/f9store.bin`) over the store at the title, F10 -> Levels: only `<new level>` / `< back` (custom level gone), F10 back to the title (VBL alive), Right + fire -> original tower 1 plays (timer (32,72,57) -> (24,64,17), tower 0, RS 0). So: store invalid after F9, the original game keeps playing, F10 does not crash. NebEditor's own simulation (editor.md s10, e120 B) agrees. README.TXT says exactly this and that GXUT270 and a desktop re-launch were not tried.

## 3c. all-games image
`python3 tools/make_hd_image.py` (35 s) -> `dist/AtariST_enhanced_games_2026-11-18.img` 32,769,024 B, md5 `8e4fd5895b7f2be79eeadd968e76e789` (+ .vhd, .md5, .layout.txt); NEBULUS 394 KB, NEBORIG 314 KB. Booted on STE 1 MB on COPIES of the image whose DESKTOP.INF got an extra `#Z 01 C:\NEBULUS\START.TOS@ @` (resp. `C:\NEBORIG\START.TOS`) line (the real image starts nothing by itself; launching from the desktop with the mouse is the unreliable automation above): NEBULUS: title reached, `$b0020` NEPO, credit band 3284 px; NEBORIG: title reached, `$b0020` 0 (unpatched), credit band 0 px.

## 5. `tools/play.sh`
Options as Moonshine's: `--original`, `--machine st|megast|ste|megaste`, `--ram`, `--cpu` (boots at 8 MHz, switches after TOS init), `--tos`, `--no-editor`, `--only A B..`, `--keep-ovl`, `--print`, and `-- HATARI OPTS` passthrough. Default patched set = `nepatch.py list` defaults + `ed_overlay` (so the editor is playable before its default is flipped). Builds `build/play-<variant>/` with `nebrelease.py`, the 16 MB ACSI/HDDRIVER image `build/play-<variant>.img` with `nebulus.build_hd`, runs Hatari on it (`--gemdos-drive skip --acsi 0=img`, `--joy1 keys`).
`--keep-ovl`: NEBLEVEL.OVL is taken from `$NEBULUS_OVL`, else `~/.nebulus/NEBLEVEL.OVL`, else `work/play/NEBLEVEL.OVL` (first that exists) into the image; after Hatari exits the image's copy (`mcopy -i img@@1024`) is written back to that path (or `~/.nebulus/NEBLEVEL.OVL`, created) when it changed. Use "Save to disk" in the editor before quitting Hatari.
Verified [obs, private Xvfb, `work/release/playtest/run.py`]: `--print` lines for ste and `megaste --ram 4096 --cpu 16`; a real run with `--keep-ovl`: build + image, boot, marker `High`, F10 (xdotool, held 1 s: **a Hatari `hatari-event keypress` is too short for the game's once-per-2-VBL poll**), Down x3 + fire = "Save to disk" -> log `campaign file saved: .../NEBLEVEL.OVL`, the file went from 8192 zero bytes to header `4e434d50 0001...` (NCMP v1). The first copy-in (`campaign file in: ...`) and the copy-back both exercised.
Pitfall seen while testing: more than ~7 host-pressed spaces during the loader screens made a later F10 do nothing; the harness presses a space every 2 s only until the title marker shows.

## 6. START.TOS and the floppy (what is known; not built)
[disasm of the unpacked START.TOS, 32975 B; `tools/pp_depack.py`] Nebulus' START has NO hard-disk driver stage (Hunter's has): the unpacked text contains no `'PPHD'`, no reference to `$472`/`$4c2`/`$476` as an instruction operand, no `$ff8604` access, no Rwabs/DMAread. Its file access is `trap #1` only: Fopen/Fread/Fclose of NEBULUS.PCH (`S+$121e`), NEBULTIT.FIC (`$2b4..`), NEBEXE.FIC (`$308..`) with the current drive/directory; the only HD-flavoured code is the 128-Vsync wait at `$34c..$35a` ("HD settle", also where nepatch's stub is called). [obs] START.TOS from an unmodified originals folder on a plain Hatari GEMDOS drive (`--harddrive`, autorun `C:\START.TOS`, `work/release/gdtest.py`, `--trace gemdos` in `work/release/gd_trace.txt`) reaches the game's title in 17 s: Fopen NEBULUS.PCH, NEBULTIT.FIC, NEBEXE.FIC, Fread 27406 -> `$70000` and 166648 -> `$81000` as in boot.md; marker `High` present. **So the lead's earlier belief that START needs HDDRIVER / re-runs the HD root sector (harness.md s1) does not hold for this START (it was copied from Hunter's notes); the HDDRIVER image is only the harness's convenience.**
Consequence for a floppy [INFERENCE, not run]: START.TOS probably needs no code change on a boot floppy; ship it as `AUTO\START.PRG` (TOS runs AUTO\*.PRG, not .TOS) or via a DESKTOP.INF `#Z` autorun, with the five files in the root; the 128-Vsync wait is harmless; floppy load time and the AUTO-time environment (START runs before the desktop; F9's TOS-state copy then returns into the AUTO sequence) are untested. A scratch 720 KB test image (mformat, `AUTO\START.PRG` + files) was built and deleted unbooted. The user's real floppy image decides the rest; the tool's `floppy` subcommand is the stub for it.

## 7. Open
- The zip contains the editor (`ed_overlay` default yes since the lead flipped it) and the zero `NEBLEVEL.OVL`.
- Not proven: desktop re-launch of START.TOS after F9; GXUT270 restore (both need a reliable desktop mouse driver, see 3b); real hardware, TT, Falcon, 512 KB, AUTO-folder start, floppy.
- Mouse/desktop automation notes for whoever retries: Hatari mouse = `h.goto` (homes and moves; the pointer lands 17,17 px off the requested point) + `h.rel`; relative moves need two nudges before a menu row highlights; the first click of a double-click pair is lost.

## 8. v1.1 release (lead, built from clean commit `1892cbf`)
- Default set: cr_credit ed_overlay ni_ikbd ni_jump ni_latch ni_shoot ni_turn np_lift np_shot nt_trainers (27 verified sites + 3 clears + 10 blocks, marker NEPO, count word 27, ZONE_STRICT=False).
- `dist/Nebulus_hd_v1.1.zip` 289,037 B md5 `928a699a8a2aeab8181f1780b2231332`; `dist/Nebulus_floppy_v1.1.zip` 216,599 B md5 `fe70ea25adfcd622e17968ee45b32fcc`; each built twice, identical; `nebrelease.py check` all members `same`; README build line `git 1892cbf`.
- HD game files in the final zip are byte-identical to the ones the gates ran on (NEPATCH.BIN `6b122b9b…`, START.TOS `4ecf26d8…`, NEBLEVEL.OVL `0829f717…`, NEBEXE.FIC `0dd818c5…`): the later floppy fix touched only `patches/ed_floppy_capture.s` (floppy game disk md5 `193f658f…`, campaign disk `a45b2711…`).
- All-games image `dist/AtariST_enhanced_games_2026-11-18.img/.vhd` md5 `78f26a9f31ad7e19067296a3ffdde2ab` (overwrote the interim image of the same date); C:\NEBULUS (campaign disk NEBCAMP.ST), C:\NEBORIG.
- Gates: NebGateEditor (e170/e150/e140 on STE, Mega STE, ST; e161 incl. 22 fuzz on STE and Mega STE; boot-time fuzz; original-game entry; hint and credit screenshots), NebGateCore (equivalence, build-vs-build RAM, junk matrix 26 boots, input-stall sweep, np_shot sweep, trainers, cold boots on STE/ST/Mega STE), NebFloppyEject (floppy eject/insert/swap/two-disk/fuzz on STE; swap+eject subset on ST and Mega STE).
- Known and accepted: tower-6 lift ride still has 1 of 92 loops at 3 VBL on the full set (busy max 320,196 of 320,512; stock 16 of 92): the user accepted this ('works well enough').
- Not run / not proven: real hardware and MiSTer, ST/Mega STE equivalence and np_lift/np_shot, the full f161 matrix and two-disk gate on ST and Mega STE, the 16 other floppy fuzz disks on ST/Mega STE, Mega STE input random-tap set, desktop relaunch after F9, GXUT270 restore, drive B, 2-player.

## 9. v1.1.1 (odd-record crash fix; base HEAD `d2e6976`, lead builds from the clean commit)
- Change: the editor/level manager read 8 words at odd addresses (Address Error on F10/edit) when a campaign had an odd-size level record and 2+ levels; now byte-wise reads, level flags byte preserved on edit/save; file format unchanged (v1.1 and v1.1.1 files are interchangeable). See `work/notes/editor.md` §13.10. Nothing else changed.
- Release edits: `patches/VERSION` 1.1 -> 1.1.1; "What is new in v@VERSION@" paragraph in `patches/README_HD.TXT`/`README_FLOPPY.TXT` and a one-line note in `PATCHES.TXT`/`PATCHES_FLOPPY.TXT`.
- Credit blob: `v1.1.1 enhanced by dad_prg` is 2 bytes longer, so the blob became 66 B and no longer fits at `$77a00` (it would hit editor CODE3 `$77a40`; `nebrelease.py build` refused: "site $77a00..$77a42 overlaps block $77a40"). Moved to `$779FA` (gap between CODE2 end `$779f8` and CODE3 `$77a40`; `CREDIT_ADDR` in `tools/nebrelease.py` and `tools/nefloppy.py`). Hence NEPATCH.BIN md5 differs from v1.1 (`11520b15…`) by design (new string + new address); the $76b10 "gap" start in older notes is wrong: `$75740..$76c00` is editor CODE1.
- Title render (STE, TOS 1.62, 1 MB, `work/release/credit_gate.py`, shots `work/gate_NebRelease111/credit/s00..s23.png`): the whole line fits, x≈207..622 of 832 px (box art/plinths at 130..190 and 640..700), no overlap with the copyright or "Mission #1".
- Gates on the committed fix (before the version bump): `work/gate_NebOddGateCore/out` (HD equivalence, boots, junk RAM, input stall, lift, shot, trainers; floppy STE/ST/Mega STE incl. odd-record files), `work/gate_NebOddGateEd/logs` (editor STE).
- Release 20e26f7 (clean): `dist/Nebulus_hd_v1.1.1.zip` 289,360 B md5 `415b7743247fa23a9c95f2b538b26eaf`; `dist/Nebulus_floppy_v1.1.1.zip` 216,925 B md5 `27001951c424f18abf5298325b38c6ae`; each built twice, identical; README `build: git 20e26f7`. NEPATCH.BIN `f6ba0b30937aefabf1ad0ac694eb378a` (v1.1: `11520b15…`; differs: new credit string and blob at $779FA). Floppy game disk md5 `46365410d93e680fbb08b78472d3d490`.
- Shipped-zip gates (unzipped zips; logs `work/gate_NebRelease111/logs`, shots `work/gate_NebRelease111/flcredit/`): HD STE/Mega STE/ST e170 (cold boot NEPO, count 27, F10, D) + e180 --disk (odd2/looks via editor Load from campaign disk) all `FAILS []`; floppy STE/Mega STE fgate (title, NEPO, F10, editor, tower, 0 crash lines) and fo180 odd-record Load `FAILS []`; floppy STE title shows the credit line. Note: run fo180 one at a time (shared /tmp/oddcore/nfe_x.bin); parallel runs failed spuriously (`*_FAIL.txt` logs kept).

## 10. v1.2 (per-level colours and enemy set in the editor; base HEAD `6ca8dd9`, lead builds from the clean commit)
- Change: level flags nibbles choose the colour scheme (palette, raster bars, skyline, tower texture of any of the 8 original towers) and the enemy set (4 eye designs) per level; editor Tower > Colours / Enemies, panel shows `S<colours> E<enemies>`. Built by NebLooksBuild (`work/looks/deliver/looks_build_notes.md`), gated and hand-merged onto the v1.1.1 tree by NebLooksGate (`work/looks/gate/REPORT.md`, `merge_list.txt`; `PATCH.diff` was NOT applied: it would undo v1.1.1). Sites 27 -> 33, `nepatch verify`: 33 verified sites, 3 clear ranges, 11 blocks. Level files compatible both ways (old = "as base tower"; older versions ignore the look).
- Release edits: `patches/VERSION` 1.1.1 -> 1.2; credit blob `v1.2 enhanced by dad_prg` (smaller again, `CREDIT_ADDR` stays `$779FA`); "What is new in v@VERSION@" paragraph in `patches/README_HD.TXT`/`README_FLOPPY.TXT`; ed_overlay text in `PATCHES.TXT`/`PATCHES_FLOPPY.TXT` (generator tables in `tools/nebrelease.py`) mentions colours and enemies; repo-root `README.md` row.
- Budget (bytes, limit-based): CODE1 `$75740` 5312 -> 5306 (free 0 -> 6); DATA `$76d40` 1324 -> 1314 (free 10); CODE2 `$77300` 1784 -> 1786 (free 6); CODE3 570 (free 6); CODE4 252 (free 4); CODE5 136 (free 2); new CODE6 `$772da` 28 (free 10); total 9378 -> 9392, free 20 -> 44.
- Gates by path: `work/looks/gate/logs` (raw logs: c0 build/verify, c1 noise, c2 look gate STE/Mega STE/ST, c5 12-level file and eyes, c6 e98/junk RAM, c7 floppy), `work/looks/gate/REPORT.md`, shots in `work/looks/gate/shots`.
- Gaps of the looks gate (to be closed by the release gates, section below if filled): no negative control of the look gate; e180/e190 not run on Mega STE/ST in the gate; `fl_look.py` not run on floppy; f161 fuzz skipped; same-build-noise outlier: the hooked build's `new1~new2` capture pair shows max |delta| 58 in soft vars/timer bytes (strict regions 0 B) while the un-hooked pair shows max 1 (`logs/c1_noise.txt`).

## 11. v1.2 release (editor pick lists, crumble, paired doors, conveyors; base HEAD `1f521b1`, lead builds from the clean commit)
- In it: v1.2 per-level colours/enemies (section 10) + editor `Level >` pick lists (Colours / Enemies / Copy tower: the game's 16 towers, both missions), Crumble ledge cell (`$91`), paired doors (a door cell places the opposite door at col+8; the exit door is 3 cells, no partner), Conveyor left/right ledges (N/M), editor size pass; v1.1.1 odd-record crash fix included. `patches/VERSION` 1.2. Sites 33, `nepatch verify`: 33 verified sites, 3 clear ranges (332 B), 11 blocks.
- Editor budget (gen_ed.py): `CODE1 free 36; DATA 108; CODE2 $77300..$779a0 1696 B free 90; CODE3 34; CODE4 4; CODE5 2; CODE6 4 | total 9152 B` = 278 B free; CODE2 ends `$779a0` < credit `$779fa`.
- Gate (cf52f4f, reports `work/looks/gate12/HD_REPORT.md`, `FLOPPY_REPORT.md`; raw PASS/FAIL counts). HD, STE / Mega STE / ST: e200 38/0 x3; e201 17/0 x3; e203 30/0 x3; e204 22/0 x3; e205 STE 2 PASS+2 FAIL, ST same, Mega 8/0 (script timing; fixed script 8/0 on STE and ST); e206 7/0 x3 (STE after boot-probe filter fix; first run 6/1); e208 46/0 x3; e150 32/0 x3; e170 12/0 x3; e180 odd2+looks 176/0 x3, all12 --quick 25/0 x3, odd2+stress --quick 65/0 x3; looks15 15/0 x3 (negative controls: swapped reference FAILS 15, v1.1.1 build FAILS 27); e202 Mega 17/0; e98 `74 of 74 not explained: []`; junk RAM 12/12 + 4/4 (STE, Mega); input stall STE all alive; lift 1 of 92 at 3 VBL; shot 59/1 HIT/MISS. e190 retired (obsolete UI).
- Floppy (STE 8/16 MHz, Mega STE 8/16 MHz): fl_ui 29/0 x4; rt.py 26/0 x4; fge 35/1 (MFP check, identical on the v1.1.1 floppy) on STE and Mega; fge2 21/0; f161 48/0 STE, 25/0 Mega (skipfuzz; run with the old Down count, fixed afterwards to select by name); fl_look 75/0 STE, 30/0 Mega; fo180 358/0 x2. Game disk md5 `7a3b6341c59a3d53ae7506596347e35f`. HD NEPATCH.BIN `f471dd18e595932c00fdb0222eb6cc77`.
- Known gaps: real hardware and MiSTer untested; e205 needed a script timing fix (wait for the game loop before `q`); Mega STE first two input-stall sweeps showed alive false for every spec incl. the control (re-run on a fresh snapshot 6/6 alive; root cause unproven, [INFERENCE] snapshot artifact); fge MFP check identical on the v1.1.1 floppy (environmental, [INFERENCE]); ST not run for junk RAM / stall / e98; 16 MHz floppy only fl_ui + rt round trip; enemy sets 3 and 4 shown on screen on STE only; `f161_nfe.py` name-based Save fix committed after the gate and not yet run (done in the shipped-zip gate).

### 11b. Shipped v1.2 zips (clean commit `d0fdd51`; README `build: git d0fdd51`, no `-dirty`)
Each zip built twice with `nebrelease.py build --zip` / `floppy --zip` (identical md5), `nebrelease.py check` all members `same`.
```
dist/Nebulus_hd_v1.2.zip      290,531 B  md5 1806aee91aa55c0ee894a89876b53c85
dist/Nebulus_floppy_v1.2.zip  218,007 B  md5 353a2485984544e7be781d45ca92c8e6
HD NEBULUS/: NEPATCH.BIN 34118 B f471dd18e595932c00fdb0222eb6cc77  START.TOS 4ecf26d8b38049738a4b1b7448276e10  NEBLEVEL.OVL 0829f71740aab1ab98b33eae21dee122
             NEBEXE.FIC 0dd818c552aedc5a2501a7a9a718906e  NEBULTIT.FIC e1a2b20a5a441c0b7bf99ad7d94f375d  NEBULUS.PCH 693c1810a4142fcc64448f51afa3bc88
             GXUT270.PRG 2bf76f6677da80e725d76db4e8da0528  NEBCHEAT.TXT e0f232cd7c3be9d1a520900f2171ebe5  Nebulus_campaign_disk.st 22686d0d6cf9c26f125c0db615d3e4b8
             README.TXT 8e5412f623949dbbf9460b19b56da7c9  PATCHES.TXT 7ceb4526f6bb7ff1381014d123467468
floppy NEBULUS_floppy/: Nebulus_game_disk.st 419840 B 7a3b6341c59a3d53ae7506596347e35f  Nebulus_campaign_disk.st a45b2711500796b393be931c2adf1d99
             README.TXT aadfcdade7d5ef6aa4ad494841fe9f26  PATCHES.TXT 3d115e9867464e7d513c6405f16a133e
```
NEPATCH.BIN and the floppy game disk md5 equal the ones the gate12 reports tested. `nepatch.py verify`: `33 verified sites, 3 clear ranges (332 B), 11 blocks; ZONE_STRICT=False`.
Gate on the UNZIPPED shipped artifacts (fresh snapshots made from them, `SNAP_EXPECT=0203131402020202` = conveyor tile table; v1.1.1 snapshot made from `dist/Nebulus_hd_v1.1.1.zip`: signature ABSENT, e180 with the guard died with `AssertionError: stale snapshot ... 0203131402020202 not found`; the v1.2 snapshots on all three machines contain it). Raw logs `work/gate_NebRelease12/shipped/`. PASS/FAIL = raw `PASS`/`FAIL` line counts; every log ends `FAILS []`:
| gate | STE TOS1.62 | Mega STE TOS2.06 | ST TOS1.04 |
|---|---|---|---|
| e170 cold boot (marker NEPO, count word 33, hooks) | 12/0 | 12/0 | 12/0 |
| e200 pickers/crumble/round trip | 38/0 | 38/0 | 38/0 |
| e203 door pairs | 30/0 | 30/0 | 30/0 |
| e205 crumble probe (committed, with the wait) | 8/0 | 8/0 | 8/0 |
| e206 crumble+exit (committed, with the boot-probe filter) | 7/0 | 7/0 | 7/0 |
| e208 conveyors in play | 46/0 | 46/0 | 46/0 |
| e180 odd2 --quick | 23/0 | 23/0 | 23/0 |
| looks15 (15 cells vs base8 run of the same shipped build) | 15 equal, FAILS 0 | 15, FAILS 0 | 15, FAILS 0 |
| floppy (cold boot, real FDC) | STE 8 MHz / +16 MHz | Mega STE 8 MHz / +16 MHz | |
| fl_ui | 29/0 / 29/0 | 29/0 / 29/0 | |
| rt.py round trip | 26/0 / 26/0 | 26/0 / 26/0 | |
| f161_nfe (committed name-based Save fix; STE with the 22 fuzz disks, Mega skipfuzz) | 48/0 | 25/0 | |
| fge2 | 21/0 | 21/0 | |
Notes: the first e200 runs were launched before the base8 reference dump existed (script exception `FileNotFoundError .../base8_*/lvl5.bin`, kept as `e200_first_noref.log`); re-run after base8 on all three: 38/0. The first floppy chain failed at start (scratch path: missing `alt/floppy` dir and campaign-disk path) and was rerun; the failed outputs were not counted. Scripts run were the committed ones with path rewrites only (`work/gate_NebRelease12/shipped/scripts`). Not run here: fge (MFP check), fl_look, fo180, junk/stall/e98 (gate12 covered the same game files), real hardware.
