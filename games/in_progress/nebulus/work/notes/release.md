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
| `dist/Nebulus_hd_v1.0.zip` | `NEBULUS/` = START.TOS (patched, 32975 B), NEPATCH.BIN, PP's NEBEXE.FIC / NEBULTIT.FIC / NEBULUS.PCH / GXUT270.PRG / NEBCHEAT.TXT, README.TXT (ours + PP's appended, CRLF), PATCHES.TXT; `NEBLEVEL.OVL` (8192 B) is added only when `ed_overlay` is in the set. Zip timestamps = the git HEAD commit time, so builds are byte-reproducible |

## 2. Credit line `vX.Y enhanced by dad_prg` (user's choice: the frog-on-a-plinth title page)
Hook [disasm of `work/dumps/title_1mb.bin`]: the title page is built at `$3d66a` (lines 0..2 = `$3cf91 "Design,Programming & Audio-Visuals"`, `$3cfb4 "by John M Phillips"`, `$3cfc7 "(c)1987,8 Hewson"` via `sub_03b360`, then `sub_03d81c` = "Mission #n" line 4 / "Sound On" line 5), falls to `$3d698 move.w #$fffe,$38212.l` (8 bytes), then the first flip `$3868a`. The same label `$3d698` is also reached by the High Scorers page (`$3d61c`) and the Options page (`$3d666`); the page word `$3d5b6` is 0 only on the frog page.
`sub_03b360(a0 = string, d0 = line 0..5)` centres the string and sets the screen offset through the row table `$3b3a0` (rows 84,104,124,144,164,184); glyphs are the game's 8x16 font (`$5c13c`, `sub_03b20a`), whose per-row plane pattern and the per-line palette give the colour. Line 3 (row 144) is the empty line between the copyright (line 2) and "Mission #n" (line 4).
Patch: site `$3d698` -> `jsr $77a00 / nop`; blob (64 B at `$77a00`, zero gap; the editor owns `$75740..$7779f`/`$77c80+`, trainers `$76c00`, latch `$76d00`): redo the `move.w`, `tst.w $3d5b6.l`, `bne` out, `lea str(pc),a0 / moveq #3,d0 / jsr $3b360.l` with `movem.l d0-d2/a0` saved. Text = `v<VERSION> enhanced by dad_prg` (24 chars, fits the 40-column line). **Change the screen/line**: edit `patches/cr_credit.s` (`moveq #3,d0` = the line; line 5 is "Sound On", rows are 20 apart) and run `nebrelease.py credit`.
Gate [obs, cold boot STE 1 MB, `work/release/credit_gate.py`; before = same set minus cr_credit, 24 screenshots each through the attract cycle, picture area 640x400]: all 12 title frames differ from the `before` run ONLY inside the box x 128..510, y 288..318 (= ST x 64..255, rows 144..159 = the credit line, 3284 pixels, identical in every title frame); the High Scorers and Options frames are pixel-identical (0 differing pixels); two frames differ in the frog's eye (46..82, 298..334), the frog's blink animation (timing, present in the before-run too: frames 2/12 vs 2/11). Screenshots `work/release/credit_before_title.png` / `credit_after_title.png`. In-game: the hook runs only on the title page, the blob redoes the displaced instruction exactly; every shipped-zip cell below reached a tower with the credit build.
Survives the attract cycle in the sense that it is redrawn each time the frog page is drawn and is absent on High Scorers / Options (user's choice: frog page only).

## 3. Shipped-zip cells (unzipped fresh from `dist/Nebulus_hd_v1.0.zip`, `work/release/zip_verify.py`, harness ACSI+HDDRIVER image of the unzipped folder, Hatari 2.6.1, raw outputs `work/release/zv_{ste,mste,st}*.txt`)
```
STE 1 MB TOS 1.62:     title 14 s, credit band lit 3284 px; tower; marker NEPO sites 10; $39ffa=602a $38514=4ef9 00076d04 $3dcf4=4eb9 00076c08 $3d698=4eb9 00077a00;
                       E: noen ffff states (8,2,0,0)->(0,0,0,0) stays; timer counts with E on; T: frz ffff timer (24,40,42) x3 over 6 s mid-count; T again runs; E again states (8,2,0,0) back; play 6 walk+jump rounds alive, timer runs
Mega STE 4 MB TOS 2.06: title 17 s, 3284 px; tower; NEPO 10; same hooks; E/T identical behaviour (frozen (24,56,35) x3); play alive
ST 1 MB TOS 1.04:       title 17 s, 3284 px; tower; NEPO 10; same hooks; E/T identical behaviour; play alive
Plain Hatari GEMDOS drive (no HDDRIVER, `work/release/gd2.py`, STE 1 MB): tower True, NEPO, 10 sites   <- the release needs no hard-disk driver
```
(the first STE run before the trainer order was changed showed the timer (32,0,0) = frog killed and timer reset, so the T check was redone with enemies off; final order above.)
Not run: real hardware, TT, Falcon, 512 KB (START forces phystop `$80000`; the patch loader writes `$B0000`, above 512 KB: [INFERENCE] a 512 KB machine would not take the payload; README says untested), AUTO folder start.

## 4. Content-vs-gate
Two builds of the same tree are byte-identical (`build/release/b2` vs `b3`, every member `cmp` equal). `nebrelease.py check dist/Nebulus_hd_v1.0.zip` -> 9 of 9 members `same` (size + md5) vs a fresh build. md5 of the cell payload (`zv_st/unz/NEBULUS`):
```
2bf76f6677da80e725d76db4e8da0528  GXUT270.PRG        e0f232cd7c3be9d1a520900f2171ebe5  NEBCHEAT.TXT
0dd818c552aedc5a2501a7a9a718906e  NEBEXE.FIC         e1a2b20a5a441c0b7bf99ad7d94f375d  NEBULTIT.FIC
693c1810a4142fcc64448f51afa3bc88  NEBULUS.PCH        846d87b55b23d6d471c9723a6aad7be3  NEPATCH.BIN
abbd673b750eed387d9660d750636dba  PATCHES.TXT        123033f32887b8fe94bf144e519b6a4a  README.TXT
4ecf26d8b38049738a4b1b7448276e10  START.TOS
```
zip md5 `563ecb8093cd6f380dd526eb8ac75d9a`, sha256 `a4881244eb9b2100597783632538e0b9135c5a3735aaf72ba0bb07133134311d`, 273,977 B (default set: cr_credit, ni_jump, ni_latch, nt_trainers; build line `git ebb0ee7 + uncommitted changes`: after the lead commits, rebuild so it reads a clean `git <hash>`; only README.TXT/PATCHES.TXT change). Payload files equal PP's originals (GXUT270/NEBEXE/NEBULTIT/NEBULUS.PCH/NEBCHEAT) byte for byte; the only changed game file is START.TOS (4 bytes + stub, `nepatch.py`).

## 5. `tools/play.sh`
Options as Moonshine's: `--original`, `--machine st|megast|ste|megaste`, `--ram`, `--cpu` (boots at 8 MHz, switches after TOS init), `--tos`, `--no-editor`, `--only A B..`, `--keep-ovl`, `--print`, and `-- HATARI OPTS` passthrough. Default patched set = `nepatch.py list` defaults + `ed_overlay` (so the editor is playable before its default is flipped). Builds `build/play-<variant>/` with `nebrelease.py`, the 16 MB ACSI/HDDRIVER image `build/play-<variant>.img` with `nebulus.build_hd`, runs Hatari on it (`--gemdos-drive skip --acsi 0=img`, `--joy1 keys`).
`--keep-ovl`: NEBLEVEL.OVL is taken from `$NEBULUS_OVL`, else `~/.nebulus/NEBLEVEL.OVL`, else `work/play/NEBLEVEL.OVL` (first that exists) into the image; after Hatari exits the image's copy (`mcopy -i img@@1024`) is written back to that path (or `~/.nebulus/NEBLEVEL.OVL`, created) when it changed. Use "Save to disk" in the editor before quitting Hatari.
Verified [obs, private Xvfb, `work/release/playtest/run.py`]: `--print` lines for ste and `megaste --ram 4096 --cpu 16`; a real run with `--keep-ovl`: build + image, boot, marker `High`, F10 (xdotool, held 1 s: **a Hatari `hatari-event keypress` is too short for the game's once-per-2-VBL poll**), Down x3 + fire = "Save to disk" -> log `campaign file saved: .../NEBLEVEL.OVL`, the file went from 8192 zero bytes to header `4e434d50 0001...` (NCMP v1). The first copy-in (`campaign file in: ...`) and the copy-back both exercised.
Pitfall seen while testing: more than ~7 host-pressed spaces during the loader screens made a later F10 do nothing; the harness presses a space every 2 s only until the title marker shows.

## 6. START.TOS and the floppy (what is known; not built)
[disasm of the unpacked START.TOS, 32975 B; `tools/pp_depack.py`] Nebulus' START has NO hard-disk driver stage (Hunter's has): the unpacked text contains no `'PPHD'`, no reference to `$472`/`$4c2`/`$476` as an instruction operand, no `$ff8604` access, no Rwabs/DMAread. Its file access is `trap #1` only: Fopen/Fread/Fclose of NEBULUS.PCH (`S+$121e`), NEBULTIT.FIC (`$2b4..`), NEBEXE.FIC (`$308..`) with the current drive/directory; the only HD-flavoured code is the 128-Vsync wait at `$34c..$35a` ("HD settle", also where nepatch's stub is called). [obs] START.TOS from an unmodified originals folder on a plain Hatari GEMDOS drive (`--harddrive`, autorun `C:\START.TOS`, `work/release/gdtest.py`, `--trace gemdos` in `work/release/gd_trace.txt`) reaches the game's title in 17 s: Fopen NEBULUS.PCH, NEBULTIT.FIC, NEBEXE.FIC, Fread 27406 -> `$70000` and 166648 -> `$81000` as in boot.md; marker `High` present. **So the lead's earlier belief that START needs HDDRIVER / re-runs the HD root sector (harness.md s1) does not hold for this START (it was copied from Hunter's notes); the HDDRIVER image is only the harness's convenience.**
Consequence for a floppy [INFERENCE, not run]: START.TOS probably needs no code change on a boot floppy; ship it as `AUTO\START.PRG` (TOS runs AUTO\*.PRG, not .TOS) or via a DESKTOP.INF `#Z` autorun, with the five files in the root; the 128-Vsync wait is harmless; floppy load time and the AUTO-time environment (START runs before the desktop; F9's TOS-state copy then returns into the AUTO sequence) are untested. A scratch 720 KB test image (mformat, `AUTO\START.PRG` + files) was built and deleted unbooted. The user's real floppy image decides the rest; the tool's `floppy` subcommand is the stub for it.

## 7. Open for the lead
- `ed_overlay` default is `no`: the zip above does NOT contain the editor / NEBLEVEL.OVL; once the lead flips it (ask NebEditor/lead), `nebrelease.py build --zip` includes the editor README block, PATCHES.TXT line and the zero `NEBLEVEL.OVL` automatically; re-run `zip_verify.py` on STE and Mega STE. `ni_hop`, `ni_shoot`, `ni_turn` are `default no` (documented in `DOCS`).
- Commit: `patches/{VERSION,cr_credit.s,cr_credit.nep,README_HD.TXT,PATCHES.TXT}`, `tools/{nebrelease.py,play.sh}`, `work/notes/release.md`, `work/release/*.py` + `make_hd_image.patch`; then rebuild the zip (clean build line).
- Apply `work/release/make_hd_image.patch` (`patch -p0 < ...` from the gamebench root).
- README/harness.md correction about HDDRIVER (section 6).
