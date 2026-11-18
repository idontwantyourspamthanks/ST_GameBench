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
