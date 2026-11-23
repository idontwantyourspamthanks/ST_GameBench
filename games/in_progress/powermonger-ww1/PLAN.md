# Powermonger WW1 (World War I Edition): assessment of branch `powermonger-ww1` and plan to port the Powermonger patches

Author: PMWW1Plan. Date 2026-11-23. Read-only study. Nothing in the repo or in either checkout was edited.
Evidence tags: **[obs]** I ran it or read it in this session; **[branch]** a claim the branch makes that I did not re-run;
**[INFERENCE]** reasoning only. Scratch/evidence in `/tmp/pmww1/` (listed in section 9). The branch was written by a model that
fell back to DeepSeek; every PASS in it is a *claim* until re-gated (budget in section 7).

Base decision (user, 2026-11-23): **the EA original** (`powermonger_-_world_war_i_edition_electronic_arts.zip`, Pasti `.stx`).
The cracks are comparison only.

---------------------------------------------------------------------------------------------------------------------------

## 0. Executive summary

1. **The EA original is practical, much better than the branch's Cobra base, and it is the same shape as master's Powermonger.**
   The .stx is an ordinary single-sided 80 x 10 FAT12 disk plus 4 raw tracks (80-83) with no sectors. Re-assembling the 800
   sectors (45 lines, `/tmp/pmww1/stx2st.py`) gives a 409600-byte `.st` that **boots in plain Hatari 2.6.1 (STE, TOS 1.62, no
   Pasti) straight to the "Powermonger WW1 Data Disk ... Please enter your name" title** [obs: `/tmp/pmww1/montage3.png`].
   The disk holds `AUTO\WW1.PRG` (76336 B) and 12 `.PAK/.DAT` data files; 36864 B free (room for a payload).
2. **`AUTO\WW1.PRG` has the same stage-0 stub as master's `AUTO\WAR.PRG`**: Super(0) `42a7 3f3c 0020 4e41`, and the same eight
   `move.l #imm,-(a7)` that build the 32-byte copy/hand-over routine ending `4cef7fff0020 4fef005c 4e75` (file offset 744/0x2e8) [obs].
   Master's hook1/hook2 delivery (edit the final `rts` into a `jmp hook`, payload carried in the PRG data segment, verify-then-apply at the
   first moment the game is resident) transfers almost as-is.
3. **The game proper is resident at the title screen at exactly the addresses the branch uses.** A RAM dump at the EA name prompt
   contains the Cobra depacked image at the same addresses: 1599 of 1673 sampled 32-byte windows identical, pass head `4a79 0005a856 6624`
   at `$13da0`, font at `$8406`, composer `$82c8`, window copy `$13a94`; and the originals at the branch's patch sites
   (`$15998` = `600015ea`, `$bbd2` = `43f90000bbe8`, `$13e0a` = `4eb900013a94`, `$13e6a` = `4eb90000d62a`, `$f30` = `13c00001d2b0`) are all present
   [obs, `/tmp/pmww1/ea_title_ram.bin`]. Only 13 byte clusters (1638 B in `$300-$1c000`, mostly `$763c-$793d`, `$d41f-$dd01`) differ from the Cobra build:
   the crackers' loader/protection edits [obs; cause INFERENCE]. **So the branch's address facts (frameloop.md site map etc.) are reusable on the EA base
   after a per-site spot-check.**
4. **The Powermonger engine and WW1 are the same code base with a shifted layout**: 740 of 1844 sampled 24-byte windows of Powermonger's game
   image are byte-identical in WW1, in long runs with a piecewise-constant address shift (e.g. `$8838`->`$82c8` composer, `$8976`->`$8406` font,
   `$12ce0`->`$13a94` window copy, `$ef62`->`$f342` triangle setup, `$124a8`->`$1325e` sprite blit) [obs]. Variables moved too (`$2df70` -> `$2ed90` world counter, `$57ff2` -> `$5a856` pause,
   `$2c1ba` -> `$2cfda` resource-cache cursor) [obs/branch]. Patches therefore cannot be copied verbatim; each needs re-siting, but the algorithms transfer.
5. **The branch is a mixed bag.** Good facts and a working tick/noprot/keys prototype (spot-checked below), but: wrong base chosen on its own initiative, no master
   folder layout, no floppy/HD build or release recipe, gates that cannot run on a clean checkout, a documentation set that contradicts itself, and **tooltips that are
   ugly for concrete, identified reasons** (section 3). Verdict: **salvage the facts and the tick/keys/noprot sources, redo the structure and the tooltips, re-gate everything.**
6. **Packers** (UPDATED by stage 0/1): the stub's packer is an **RNC method-1 variant with no CRC fields and a backwards bit stream**; the stub's own decoder (text `$d0..$244`) is re-implemented in `tools/wwdepack.py` and its output (118072 B resident image, md5 `694b94a1...`) is byte-identical to the Hatari hand-over dump, so a build-time reference image now exists (`work/notes/delivery.md`). The user's warning stands: nothing is built on a depacked file until it is md5-checked against a cold boot (rule R1, done).

---------------------------------------------------------------------------------------------------------------------------

## 1. Inventory of the branch (commit 80c4318, 52 commits, one folder `games/in_progress/powermonger-ww1/`, 79 files; only `.gitignore` touched outside it)

### 1.1 What is physically there
| item | where | note |
|---|---|---|
| Docs | `README.md`, `PLAN.md`, `work/notes/{HANDOVER,HANDOVER2,HANDOVER3,baseline,carrier,cobra26,delivery,frameloop,input,protection,tickgate,tickproto}.md`, `profile16.txt` (33 KB) | prose, large |
| Patch sources | `work/tickproto/{tick,tick26,tick_intext}.s`, `work/keyproto/keys.s`, `work/ttproto/{tooltip,ttprobe}.s`, `work/carrier/{carrier.s,NOTES.s}` | **not** in `patches/` with `; name/; site/; orig` headers as master does |
| Tools (21) | `wwbuild.py` (builder), `atomik.py` (ATOMIK v3.5 depacker), `wwdepack.py`, `pmww.py` (harness), `pwwgrid.py` (icon grid), gates: `release_gate.py rate_check.py soak.py keygate.py phantomgate.py tooltipgate.py pmtick_eq.py pmtick_series.py`, `crash_trace.py`, `msa2st.py`, `play.sh` | |
| Junk | 36 tracked `work/eq/*.cmds` debugger scripts (the last commit adds a `.gitignore` line for them but they stay tracked) | delete |
| Missing | any floppy/HD build, `package.sh`, `REPORT.md`, README_*.TXT, credit/version line, `patches/`, built `.bin` payloads (git-ignored), `extracted/`, `disks/`, `work/ref/*.png`, `work/snapshots/*.sav` | see landmines |

### 1.2 Claims and my judgement
(V = I re-observed something; "re-gate" = must be re-run fresh on the EA base)

| claim (source) | judgement |
|---|---|
| Base = Cobra #26, "same engine at the same addresses as Pompey" (cobra26.md, README) | Addresses: **corroborated** for the game proper (and EA matches too, section 0.3). But the base was **chosen by the model** (commit e4d7f9d "base decided"), not the user's pick (user said Pompey #106; now EA). Cobra #26's `WW1.PRG` is byte-identical to Fuzion #156's file `2` (md5 9b66a99e..., V), i.e. a Fuzion cracktro build, not Cobra's own work. Not shippable (advertises crackers). |
| ATOMIK depacker "exact, 100.00 % vs live capture" (`atomik.py`, HANDOVER2) | V partly: it produced a 153665-byte image on the real file, and a PRG built from that image boots to the title and the map in Hatari. Its 100 % oracle (`work/dumps/c26_image_full.bin`) is git-ignored, not re-run. **Irrelevant for the EA base** (different packer). |
| Tick patch, 7 sites, 4.00 ticks/s at 8/16 MHz, 50/60 Hz (HANDOVER3 table) | V weakly: I built the branch PRG (vasm for the 3 payloads; `wwbuild.py` reported "12 sites"), cold-booted it, navigated to the in-game view and the world counter went 9 -> 18 over ~2 s (~4/s) [obs, `/tmp/pmww1/run5.log`]. Rate matrix, 60 Hz, state-equality **not** re-run: **re-gate**. Design is the same as master's `tick_head` (VBL-based, `$ff820a` sync detection, T/S/R passes). Plausible. |
| State-equality gate PASS, 12 ticks, 0 bytes (tickgate.md, release_gate) | **Plausible, method sound** (it copies master's `pmtick`); excluded ranges are listed and justified. But the first runs showed 582/235 diffs "all instrument faults" (tickgate.md history) - which means it was tuned until it passed. **Re-gate.** |
| Stack-leak crash after ~90 s fixed (`addq.l #4,a7` on both exits of a jsr-entered/jmp-left hook) (HANDOVER3 4.1, commit 648693a) | **Technically right and an important catch** (master's `tick_head` has the same `addq`). Keep as a rule. Soak result "2372 ticks, 0 errors" **re-gate** (and it ends at "the battle view is not a failure" - a soft stop condition). |
| noprot: preset `$15998 = $2c`, plus `$bbd2 -> rts` (box) (protection.md) | **Corroborated**: the bytes at `$15998`/`$bbd2` are as claimed in the EA RAM [obs]; structure matches master's `pm_noprot`/`pm_noprot_box` [obs: same constants]. Not run in the EA game. Re-gate (the protection question must be shown not to appear; Save/Format must stay enabled). |
| Keys A-Y + 1/2/3, phantom-click fix (commit 29da35a, keygate PASS) | Mechanism (write the same click words a real click writes) = master's `qol_keys`. Hook sites `$f30`, `$13e6a` hold the claimed originals in the EA RAM [obs]. keygate "3 of 6 differ by 1 pixel (harness tolerance)" is a **soft pass**. No key labels in tooltips (master has them). Re-gate. |
| Tooltips PASS 6/6 (commit effb8c9, tooltipgate) | **Gate passes but the feature is ugly** (my screenshot, section 3). The gate checks only that `LINE` equals the expected 24-char name and that the bar changed by some pixels; it cannot see garbage or a box. I re-ran the hover on 5 icons: LINE strings correct (`Option, Trade, Get Men, Attack, Neutral`) [obs], picture bad. **Redo.** |
| "Confirmed on the user's real Mega STE" (HANDOVER3 sec 1) | **[UNVERIFIED]** - nothing in the repo supports it; and the same file says TT stutter/audio is reported by the user but "not investigated". Treat as hearsay. |
| 60 Hz PASS (commit c64a187) | Method: runtime switch of the timer rate in the debugger; ticks/VBL 0.0679 vs 0.0667 (1.8 % off). **Weak**. Master used a real 60 Hz boot. Re-gate. |
| Cobra stock game does not run on Hatari Mega STE (commit 268365a) | Plausibly the crack's problem (AUTO-less GEMDOS-loader crack, TOS 2.06). Irrelevant on the EA floppy base; **re-test** (master's `pm_mste` problem set). |
| "Renderer is not a triangle walker: 40 % in the block-pattern combiner `$8344..$83f0`, p6_tri/p6_slope do not transpose" (frameloop 6a) | **Partly contradicted by me**: master's triangle setup `$ef62` exists in WW1 byte-identical at `$f342` [obs, 28-byte match]. The 39.8 % hotspot sits inside `$82c8`, which is *also* master's `$8838` window/text composer (the branch itself found that while doing tooltips - HANDOVER3 5.3). So the WW1 terrain is probably drawn with that routine as well as, or instead of, triangles. Needs a **fresh profile on the EA base** before any perf decision. |
| "YM sample IRQ 14.2 % at `$1bc92`, DMA-sound port applies directly" (HANDOVER3 sec 7) | Contradicted within the branch: input.md says timer A at the map view is a border-flicker stub and the player is a *timer-C sequencer*; master's `snd_*` assume the timer-A sample player (`$1af32`). **Unverified; needs its own study** (not a straight port). |
| `tools/play.sh --fresh` "builds from source" | **False.** `wwbuild.py` reads pre-assembled `tick.bin/keys.bin/tooltip.bin` that are git-ignored; nothing assembles them [obs: I had to run vasm by hand]. A clean checkout cannot build. |
| Gates "PASS" in a clean checkout | **Cannot run**: `PMWW.at_gate()` needs `work/ref/name_gate.png`, `opt_gate.png` (git-ignored, absent); snapshots, `extracted/`, `disks/` absent. I bypassed with sleeps. Navigation "flaky" (HANDOVER3 4.7). |

### 1.3 Landmines (what the branch's own notes and my checks show)
1. **Contradictory documentation.** `README.md` still says base = PP106 and "a byte search of the original's game image finds no match" (false: 40 % of windows match); the top banner says Cobra; it says "read HANDOVER2 first" while HANDOVER3 says read HANDOVER3 first; PLAN.md says patches go to `$b8800` etc. Do not read these as plans.
2. **Wrong beliefs it recorded and later corrected (do not re-derive, but re-check once)**: patch-site file offsets = text offset - `$110` (runtime `$13da0` = text `$13eb0`); font is `$8406` not `$8976`; `$e4ca` is the physical screen base, not a font; screen is 4 bpp, 160 bytes/line, **byte column = x/2**; "composer `$82c8` = terrain combine" was the trap that cost the tooltip hunt three searches; STE TOS is 1.06/1.62 (an earlier run used TOS 1.04 on an STE and its failure meant nothing).
3. **Hatari/harness traps** (valid, keep): breakpoints need `:trace` to log; `b (addr).b ! (addr).b` fires on reads; `$2edb2/$2edb4` pointer words are rewritten by the IKBD handler every VBL (use `goto_st`); a debugger `w` to a variable that the pass re-derives is overwritten; short dumps are silently repeated (check `len`); `vasm equ` does not advance the location counter (use `org`); `poke_click` is needed because Hatari only delivers absolute-mouse buttons with movement.
4. **Payload address `$72000`** (UPDATED, stage 1): the branch claims `$72000-$c1cff` is free. At the map view only **`$71b84-$77fff` (25724 B) is a free zero run** and `$78000-$7ffff` holds a 32000-byte picture buffer (the territory chart, non-zero from the chart on), the resource-cache bump allocator starts at `$80000` (`lea $80000,a0; move.l a0,$2cfda` at `$5e8`) and grows upwards, `$9fc58-$f7fff` is zero at the map view [obs]. The branch's `$72000-$c1cff` therefore runs over the chart buffer and into the cache: **do not copy it**. Stage 1 places the payload in `$72000-$77fff` only (22.5 KB for patch blobs), which the cache can never reach; evidence in `work/notes/placement.md`.
5. **Disk dependence**: the game's data loads come through the raw WD1772 driver in master's engine (hd_* patches exist for HD). Cobra's "loads via TOS GEMDOS from A:" is a *crack* behaviour; the EA original differs at `$d41f-$dd01` [obs] - expect original raw loading. The branch's save/load story (no disk in A:) is moot for the EA.
6. **Soft stop conditions** in `soak.py` ("battle view is not a failure") and `keygate` pixel tolerance: tighten.
7. **Bad base name hygiene**: "Cobra #27" in `originals/` is *not* a WW1 disk (its root has `A.PRG ... DICE.PRG LEANDER.PRG TORNADO.PRG`, no WW1 files) [obs]; Fuzion #156 == Cobra #26 for WW1. Only 4 distinct WW1 releases exist among the 6 files (EA, Pompey, Fuzion/Cobra26, Flame/Superior).

---------------------------------------------------------------------------------------------------------------------------

## 2. The game releases, packers, and the base

### 2.1 What is in `games/queue/powermonger-ww1/originals/` (expected-original md5s; read-only, user's copies)
| file (md5 of the zip) | content | game program |
|---|---|---|
| `powermonger_-_world_war_i_edition_electronic_arts.zip` `934d176f1781b22bb03b276aa067c130` | Pasti `powermonger_..._electronic_arts.stx` (889658 B, 84 track records; tracks 0-79 = 10 normal sectors each, single side; tracks 80-83 raw images, 0 sectors). **Converted `.st` (800 sectors) md5 `95354c89884a4cb82b62fe63400bf750`, 409600 B** (`/tmp/pmww1/stx2st.py`). FAT12, 2 sectors/cluster, 1 side. | `AUTO\WW1.PRG` 76336 B md5 `dc93b917458125398a072c95f452f4b0`; data: CAPGRAPH, FX, LOSE, MAP, QAZ, SPRITE16/24/32/8, TEXTURES, WIN `.PAK` + `MAPDATA.DAT` (291 KB). No boot code (sector 0 not executable; TOS runs AUTO). |
| `Cobra #26.zip` `46eab0d1a3b5df3b5a9d986434f9631b` | `COBRA26.MSA` (Pompey-variant `$0E0F` header) -> `.st` md5 `c1b82d148f5b1a639296672a571982b6` (829440 B, converted with the branch's `msa2st.py`) | `WW1.PRG` 61650 B md5 `9b66a99ea8303a6b3fa0305f6ccd4b3d` (ATOMIK v3.5 Altair linkfile, per the branch) + `WW1_FUZI.LFB` 217708 B md5 `98ee2595b3f2d66f19fdcf5455e8e9ef` + cracktro files; `INDY.PRG` is another game |
| `Fuzion #156.zip` `73dd799f4176ee914ea183d595974564` | `FUZ156.MSA`: root `1`(4032), `2`(61650), `3`(15432), `SHADOW.LNK`(454072), `WW1_FUZI.LFB`, `CHECK_CD.PRG` | file `2` **md5 identical to Cobra #26 `WW1.PRG`**; `WW1_FUZI.LFB` identical too [obs] |
| `Cobra #27.zip` `de732dddd3f3fb39006340ebaf2b0254` | a *different* Cobra compilation (DICE, LEANDER, TECHNO, TORNADO...) | **no WW1 program found** in the root listing [obs, top of listing only] |
| `Flame Of Finland_Superior #109A.zip` `0c1833a0abbd18969c246b6e63fd5f60` | `SUPE109A.MSA`; FAT with media byte ff/f9 (mtools needs `MTOOLS_SKIP_CHECK=1`); Medway Boys protector; files `WW1.SPR`(57822) `BIGRUN.SPR` `BIGRUNSU.PER`(426522) `*.PAK` `MAPDATA.DAT` `AUTO\MENU109A.PRG` | not examined; layout (PAK files + `.SPR`) is a different crack structure |
| `Pompey Pirates #106.zip` `fd564266c72da2065c01c84759816d44` | PP menu disk | `WWIEDITN.PRG` 283902 B (Alien "single-part": 12-chunk POPI archive per the branch) + original-1987-dated `TYANKEEG.EXE` etc. Not examined by me. |

All the crack builds are the same game with the protection check left in (user: accepts `0000`).

### 2.2 The EA program: stage structure (what I verified)
* `AUTO\WW1.PRG` = GEMDOS header `601a 0001 2a10` text 76304 B, no relocs, text offset 0 = Super(0) (`42a7 3f3c0020 4e41`) as in master's WAR.PRG [obs].
* Text `$2cc..$304` = the eight `move.l #imm,-(a7)` + `jmp (a7)` (offset 792 in file = `4ed7`): identical push constants to master (`2f3c005c4e75 2f3c00204fef 2f3c4cef7fff 2f3c538166fa 2f3c66fa4219 2f3c12d85380 2f3c2549005c 2f3c45fafffe 4ed7`) [obs]. The `rts` at the end of that routine is where master puts `jmp hook1/2`.
* Immediately after `4ed7`: `RNC\x01  0002368c  00012705  601a  0c34  42  a3`, then the stream (unpacked size 145036 = the nested TOS program, packed length 75525, data from text `$30a` = 12 bytes after the tag). UPDATED: this IS an RNC method-1 decoder, but a variant: no CRC/leeway fields (12-byte header), bits are read from the END of the stream and the output is written backwards. My earlier "CRC mismatch" was this layout difference. Decoder, tables and the nested-PRG relocation (base `$576`) are in `tools/wwdepack.py`; `work/notes/delivery.md`.
* The nested image's hand-over is at `$576` as in master's stage 1/2 (RAM at that breakpoint = the file-derived image, byte for byte) [obs]. **Unlike master, there is no second SPRITE40-style stage**: the whole game + intro is the one nested program, so the delivery has ONE hook (master's `hook2` shape, entered from the stack routine's `jmp`, leaving to `$576`). It is a DATA DISK: the game asks for the original Powermonger floppy (`work/notes/intake.md`).

### 2.3 Packer risk and how the plan avoids it ("packers were causing problems")
What went wrong in the branch (from its notes): (i) wrong depack constants and file-offset-vs-runtime confusion (`HANDOVER.md`: "the previous table used the runtime addresses as file offsets; that was wrong", the `$110` shift, "two details the earlier notes had wrong"); (ii) the first carrier appended the payload after the reloc table, which TOS never loads, so the game "ran into empty memory" (`HANDOVER2.md`); (iii) the Pompey base (POPI archive, runtime-expanded code) needed an unfinished chunk depacker, wasting the first day; (iv) an unnoticed "load base vs `$576` copy" two-constant mapping.
Controls for the new port:
* **R1 - nothing is analysed or built on a depacked/extracted file until (a) its md5 is recorded and (b) a cold boot in Hatari reaches the WW1 title.** For the EA this is already satisfied for the *original* (md5 above, title reached) - there is nothing to depack at build time.
* **R2 - verify against RAM, not against a transcribed depacker**: master's `pmpatch` already verifies the original bytes of every site against the resident image at run time (all-or-nothing, marker `PMPO/PMPF`). Take a hand-over dump with the debugger (master's `pmpatch.py dumps` approach: breakpoint at the stack-routine `rts`, `savebin`) as the build-time reference, and record its md5. No packer reverse-engineering is on the critical path.
* **R3 - the payload rides in the PRG data segment** (TOS loads `28 + text + data`) and a front stub copies it; never append past the file's reloc table.
* **R4 (optional, later)** - identify the EA packer from the stub (text `$8..$2c8`: ~700 bytes of 68k) if a file-derived resident image is wanted for static analysis. Estimate 0.5 day Sonnet; not needed for the port.

### 2.4 Which base? -> EA original (decided), with the following checks first
* It is unmodified code, no cracktro, no GEMDOS-loader crack, and it is what master did (`disks/protected.st`, the original floppy).
* How master chose: master's README keeps a table of 7 variants with md5s and picks `protected.st` because `AUTO\WAR.PRG` is the unmodified original, byte-identical to the one inside the cracks; the others are comparison.
* The cracks differ from EA only in 13 clusters of the resident image (loader/protection/intro edits) [obs]; useful to see how Fuzion bypassed the loader (`$d41f-$dd01`, `$763c-$793d`, `$763c` = a 774-byte stretch likely their loader/hook).
* Floppy size: 409600 B single-sided: the master floppy builder assumed 819200 B double-sided; `pmpatch.py`'s FAT-chain extension must be taught the 1-side geometry (sectors/track 10, heads 1) - small.

---------------------------------------------------------------------------------------------------------------------------

## 3. Tooltips: master vs WW1

### 3.1 Master's (good) tooltips [obs: `/tmp/pmww1/pm_bar.png`, from `games/done/powermonger/work/shots/pmtt_2sword_id4.png`; source `patches/pm_tooltip.s`, notes `work/notes/tooltip.md`]
* One line of **52 characters, cream text on a black bar** (top bar rows 0..5, free from x=112 right), e.g. "Get Men: recruit more men"; the text depends on the captain's posture (1/2/3 swords, from the posture word), with optional key labels "(K)" when the keys patch is on.
* Covers **32 ids**: the 20 command/posture cells of the perspective grid, the 4 map-mode icons (x 0-63), rotate L/R, zoom in/out, compass.
* Drawing: its **own composer (~700 B)** reads the game's 4x6 font in place (blocks of 48 B at `$8976 + 48*(ch>>2)`, column `ch&3`) and **maps the glyph background colour 1 to colour 0** (`P0 &= P1|P2|P3`), so text sits on the black bar. Composed once per change of (target, level, keys), then 6 x 104 B copied each pass.
* Erase: draws into the **back buffer after the 32 K frame-picture copy**, which restores the bar next pass: no cleanup code. Hook = `jsr $178ae` after the window copy `$12ce0`.
* Hit test: the game's own two line tables (`$12e6a`, `$12ee4`) + cell table, run only when the pointer moved; wording in one table, 52-char limit checked by `tools/pmtt_check.py`; gates `pmtt_ab` (frame A/B with pointer held), `pmtt_state` (full-RAM per-tick), `pmtt_check`, screenshots.

### 3.2 The branch's WW1 tooltip [obs: `/tmp/pmww1/ww1_tooltip_bar.png`, `ww1_tooltip_getmen.png` (hover on "Get Men", Cobra-based patched PRG, STE 1 MB TOS 1.62)]
What shows: a **solid light-khaki/beige box ~100 px wide x 6 rows** stuck into the black top bar, starting at x=104 (right next to the small status icon), with the words "Get Men" in **low-contrast grey inside it, partly squeezed to the right**, and **stray multicoloured pixels in the first 4 character cells**. Names only, 24 chars max.
Why (from `work/ttproto/tooltip.s` and the picture):
1. **It reuses the game's own window-text composer `$82c8`** (a 4-glyph x 6-row strip per call, `d7` loop x 6, clip variable `$82c4` saved/overwritten/restored). That routine was written for window panels: it paints the glyph **cell background colour 1 (khaki) as pixels**; the branch never maps it to the transparent/black colour as master does -> **the box**. [obs for the box; cause = code reading, INFERENCE that mapping is absent/needed].
2. The strip start / phase/mask logic of `$82c8` expects the window machinery state (rotate counts from the 8 bytes before the font, `a5` advance of 8 bytes, 4-phase mask); the hook runs it from outside that context and it merges with whatever the destination holds -> **junk pixels in the first cells and shifted text** [obs of the junk; precise mechanism INFERENCE - needs a trace].
3. **Content is a stub**: only the 20 names (no effect text, no 1/2/3-sword levels, no key labels, no map-mode/rotate/zoom/compass ids), 24 chars vs 52.
4. **Colour**: the glyph shades 2-5 are rendered against the khaki (grey on beige), not cream on black.
5. **Gate is blind**: `tooltipgate.py` compares the 24-byte `LINE` buffer and "top-bar pixels changed > 0", so it passes on the ugly picture. No screenshot review, no A/B frame check.
So: *the data (hit test, grid, font location, back-buffer trick) is right; the rendering is the part to redo, by transposing master's `pm_tooltip.s` composer (own composer, bg->0) with `FONT equ $8406`, and the wording table.*

### 3.3 Open details to settle in the port
* WW1 palette/glyph colour indices vs master (is bg still colour 1? master: glyph pixels 1..5, 1 = window bg) - read the font bytes at `$8406` in the EA RAM, 20 minutes.
* The WW1 equivalents of master's other hit zones: rect table `$13250` (rotate/zoom), compass test, map-mode `x>>4` zone, window-open flag `$7a36`, posture word `[$51538 + [$57fd2] + $3c]` -> new addresses (**[INFERENCE] they exist: engine identical**; locate by signature).
* Wording: WW1 commands may differ in meaning (WW1 manual) - lead/user review.

---------------------------------------------------------------------------------------------------------------------------

## 4. Master's Powermonger patch set vs WW1: applicability
(Master default set: README of `games/done/powermonger`. "Branch" = what the branch already has.)

| master patch(es) | WW1 status | action |
|---|---|---|
| `tick_head/pass/men/rain/click1-3` fixed-rate world tick | Branch has 7-site version, equivalent design; sites hold claimed originals in EA RAM (`$13da0`, `$13e24`...) [obs for `$13da0`; others branch claim] | re-site into `patches/`, assemble in-build, re-gate (state equality, rates, 50/60 Hz, soak). |
| `p3b_interp/p3b_delta` men interpolation | not done; needs the entity-table addresses (branch says men records at `$51af7..`, 50 B stride) | port after tick (default yes in master). |
| `pm_noprot`, `pm_noprot_box` | Branch has both, sites confirmed [obs] | port, re-gate. |
| `qol_keys`, `qol_keys2`, `qol_hover`, `qol_hover2` | Keys: branch has A-Y,1-3 (no labels, no `keys2` = the `$199c` IKBD overrun/second-site?, no village hover) | port keys properly + hover. |
| `pm_tooltip` | **redo** (section 3) | port from master. |
| `pm_credit` (version line on the menu screen), `pm_intro_*` (real-time intro), `pm_mste` (Mega STE 16 MHz+cache `init`) | not done. `pm_mste` is game-independent (`init` only) -> reusable nearly verbatim; credit/intro need WW1's menu/intro loop sites (WW1 title is a different screen) | credit: user requirement for every release (master convention). intro: ask user. |
| `pm_cachecap` (Retire/Win/Lose crash) | **not done, high risk** (cursor `$2cfda`, start `$80000`; payload location decides) | analog needed + `pmretire`-style gate. |
| `p4_clamp` (IKBD overrun), `p4_ptr_a/b`, `tt_ptr` (TT/Falcon pointer) | `p4_ptr_b` signature matched at `$9b8` [obs]; others unknown | port; user reported TT stutter/audio on the branch (unconfirmed) - decide scope. |
| `p4_spr`, `p6_cpy`, `p6_tri`, `p6_slope` (performance) | signatures match: `$124a8->$1325e`, `$12ce0->$13a94`, `$ef62->$f342` [obs]; but WW1's hotspot is the `$82c8` pattern combiner (40 %) which master has no counterpart for | fresh profile first; the three matched ones are cheap ports, the combiner is a design task. |
| `p7_triple_*` triple buffering | not done (flip routine `$e0e`, buffers `$2ed98/$2ed9c` per branch) | after tick; needs gate parity. |
| `snd_*` DMA sound, `fal_ym` | WW1's sound = timer-C player at `$1bc92` per branch, not master's timer-A sample IRQ | separate study; may be out of scope. |
| `hd_*` HD loader (`hd_load` `$d574`, `hd_sector` `$d9fc`, `hd_s1`, `hd_kbd`) | EA game must be re-checked for the same raw-FDC stack (resident bytes at those sites differ in Cobra only in the crack ranges). Master shipped floppy+HD; the branch has neither | ask the user whether HD is wanted; if yes, port after floppy. |

---------------------------------------------------------------------------------------------------------------------------

## 5. Salvage list

### 5.1 Facts / addresses reusable after a spot-check (not behavioural claims)
(spot-check = a short Hatari/debugger look at the EA RAM; those I already confirmed in the EA dump are marked **V**)
* Runtime layout: text offset = runtime + `$110` in the Cobra/branch's nested PRG; **EA runtime addresses = Cobra's** (**V**, 95.6 % of windows). Pass head `$13da0` **V**; font `$8406` **V**; composer `$82c8` **V**; window copy `$13a94` **V**; noprot flag `$15998` and box `$bbd2` **V**; key sites `$f30`, `$13e6a` **V**; tooltip site `$13e0a` **V**; resource-cache cursor `$2cfda`, start `$80000` **V**.
* Variables: world counter `$2ed90`, pass counter `$50fd8`, pause `$5a856`, speed countdown `$5a854`/period `$5a852`, buffers `$2ed98/$2ed9c`, pointer `$2edb2/$2edb4` (click `$2edae/$2edb0`), click latch `$2edb6`, VBL counter `$71b7c`, IKBD packet words `$1d2a0-$1d2c0`, mouse-enabled `$5a84e` (branch; spot-check).
* The command grid: `tools/pwwgrid.py` (20 cell centres, names, oracle-checked vs the game's hit test per the branch; **I saw 5 hovers return the right names**) and the line/cell tables `$13bde/$13c58/$1a89a`.
* `frameloop.md` 1990->WW1 site map, `input.md` (IKBD/latch/click path, icon grid), `protection.md`, the TOS table correction, the harness traps (1.3.3), the stack-leak rule, the "4 bpp: byte col = x/2" rule.
* Tools reusable as-is or with small edits: `stx` conversion (mine, `/tmp/pmww1/stx2st.py`), `pwwgrid.py`, the harness `pmww.py` (after replacing refs/gates), `soak.py` idea, `crash_trace.py`, `rate_check.py`, `pmtick_series.py` (state-equality by series at a fixed PC, aligned by counter) - **method is good**.

### 5.2 Behavioural claims that must be re-verified by a fresh gate (each = a line in section 7's gate budget)
tick rate 4.00/s at 8 and 16 MHz; 50/60 Hz (real boot); 12-tick state equality; release gate; soak (20 min, with a hard "world advancing" criterion); noprot (no question, Save/Format enabled); keys == click words; phantom-click fix; "tooltips 6/6" (visual); "confirmed on real Mega STE"; stack-leak fixed; "Cobra stock won't run on MSTE" (irrelevant).

### 5.3 Must be redone
* Folder layout and patch sources: `patches/*.s` with `; name/; default/; site/; orig/; note` headers; payload assembled by the build; `pmpatch.py`-style builder for the EA floppy (front stub, hook, runtime verify, FAT-chain extension, `.st` writer for a 1-side disk). Replace `wwbuild.py`/`atomik.py`/`carrier*`.
* Tooltips (section 3). Keys wording/labels. Credit line. Cache cap. Delivery address decision.
* Gates: runnable on a clean checkout (refs generated by a tool, snapshots reproducible), hard criteria, screenshot gates.
* README/REPORT/PLAN in master's shape; one handover, not three.

### 5.4 Delete
`work/eq/*.cmds` (36), `HANDOVER.md`, `HANDOVER2.md` (history; keep the facts in the rewritten notes), `carrier.md`/`carrier*.s`/`delivery.md` (Pompey/ATOMIK delivery stories), `atomik.py`, `wwdepack.py`, `msa2st.py` (keep a copy only if the Cobra/Fuzion crack is studied), `pmww_exit/loop/menu.py` scratch, `profile16.txt` (33 KB; keep a summary), `tick26.s/tick_intext.s` variants, `ttprobe.s`, `play.sh` as written (rewrite after master's `play.sh`).

---------------------------------------------------------------------------------------------------------------------------

## 6. Staged plan (master's project recipe)

Folder: `games/in_progress/powermonger-ww1/` -> `games/done/powermonger-ww1/` on completion (as master did). Layout (copy master): `README.md`, `REPORT.md`, `PLAN.md`, `patches/` (core.s + `*.s`, README_FLOPPY.TXT), `tools/` (`pmww.py` harness, `wwpatch.py` = pmpatch clone, `play.sh`, `package.sh`, `packcheck.sh`, gates), `work/notes/*.md` (one topic each), `disks/` (git-ignored: `ea.st` md5 `95354c89...`), `extracted/ea/`, `dist/`. Never commit game files (`.gitignore` already covers `*.PRG`, `*.PAK`).

Each stage has: scope, owner model, gates (a stage is "done" only when its gates are green on a fresh run and logged under `work/notes/`), and an estimate. Estimates are agent time for one Sonnet-class worker unless stated; add ~30-50 % for the lead's review turns. Total for the **core** set (stages 0-5): about 9-11 working days of agent time; the optional performance/sound/HD tails extra.

**Rules for every stage** (from master's practice and the branch's failures): R1/R2/R3 (section 2.3); every patch hook entered by `jsr` and left by `jmp` pops the return address; one patch = one file; no claim in a note without the command that produced it; tick-state and pixel gates run against *real built disks*, not debugger-applied patches; the lead commits.

### Stage 0 - Intake, base, harness (0.5-1 day, Sonnet) - **DONE 2026-11-23** (`work/notes/RESULTS_stage01.md`, `intake.md`, `addrmap.md`)
* `tools/stx2st.py` (from `/tmp/pmww1/stx2st.py`) -> `disks/ea.st`, md5 recorded; extracted tree md5s; intake note `work/notes/intake.md` (versions table of section 2, packers, which cracks are comparison).
* Harness `pmww.py` for a floppy folder-less run (copy master's `pm.py`); regenerate reference crops (title/name/options) with a tool instead of git-ignored hand crops; navigation to the map view with a **hard** "world counter advances" check.
* Hand-over dump(s): breakpoint at the stack routine's `rts` (text `$304`+), `savebin` 1 MB -> `work/dumps/entry576.bin`, md5; compare to a title dump to prove nothing moves after the hand-over.
* **Gate G0**: unmodified `ea.st` cold boot -> title -> name -> options -> map view in Hatari STE TOS 1.62 and Mega STE 2.06 (first 4 steps already done [obs]); screenshot per stage; the protection question appears (baseline).
* Open item to resolve here: does the EA game load more code later (grep resident RAM change at the map view, as master did: 98.7 % identical)?

### Stage 1 - Delivery core and floppy writer (1-1.5 days, Sonnet; lead reviews payload placement) - **DONE 2026-11-23** (`delivery.md`, `placement.md`, `RESULTS_stage01.md`)
**Facts that changed the plan (stage 0/1):** (1) **[stage 2 correction: the request is a key-disk check, part of the copy protection, removed by `pm_nokeydisk`; the shipped disk needs only the WW1 floppy, see work/notes/RESULTS_stage02.md section 2]** the unpatched game asks for the original Powermonger floppy on the first START NEW CONQUEST (harness swaps disks; gates of the UNPATCHED / core-only / credit-only builds need `games/done/powermonger/disks/protected.st`); (2) the stub's packer is an RNC1 variant, decoded by `tools/wwdepack.py` (file-derived resident image = hand-over RAM, byte-identical); (3) the payload is `$72000-$77FFF` (22.5 KB for blobs), NOT `$72000-$c1cff`: `$78000-$7ffff` is the chart picture and `$80000+` the resource cache; large optional blocks of master (sprite cache, triple buffers, sample bank) need another placement; (4) master's `tick_head` site (`lea $14e20,a2`) does not exist in WW1 (loop head = `$13da0 tst.w $5a856`), the other 30+ default sites map 1:1 (`addrmap.md`); (5) the protection question is asked on the first land and after a lost game, not on a second land right after a correct answer; (6) the harness types with XTEST keys (the harness's `--window` keys are dropped by the name prompt); (7) master's Hatari win-forcing trick works at `$d6c8` / `$5a830`.
* Port master's `core.s` front stub + `hook1/hook2/apply` + site table to the EA stub (hook replaces the final `rts`; check the `4e75` position in the pushes, `2f3c005c4e75`), payload in the PRG data segment, marker `PMPO/PMPF`, original bytes verified at run time.
* `.st` writer for a 1-sided 80x10 disk: replace `WW1.PRG` (extend the FAT chain into free clusters, 36 KB free; payload ~6-10 KB), leave all else bit-identical.
* **Payload address decision (design review by lead / Fable if unclear)**: `$72000-$7ffff` (below the cache cursor start `$80000`) vs master's `$B8000`+ with an analog of `pm_cachecap`. Prove by the master's pattern-fill method (fill, play, check) *and* by the Retire/Win/Lose/new-territory gates (stage 4). Default proposal: `$72000` for the code, plus the cache cap analog regardless.
* **Gate G1**: no-patch build boots identically to original (RAM diff vs original at the title limited to the hook + payload); a deliberately corrupted site -> `PMPF` and the game still runs; `packcheck`-style verification of the built disk (FAT intact, only `WW1.PRG` + free clusters changed).

### Stage 2 - Tick, noprot, keys (core QoL) (2-3 days, Sonnet)
* Re-site `tick_*` (branch `tick.s` is the starting source; re-derive the 7 sites from master's `tick_*.s` and compare), `noprot` + `noprot_box`, `qol_keys`/`keys2`, `pm_cachecap` analog.
* **Gates (fresh, master's tools as templates)**: `pmtick`-style 12-tick state equality + negative control on built floppies; rate matrix 8/16 MHz (ST, STE, MSTE; 50 and a *real* 60 Hz boot); soak 20 min with hard criteria (world advancing, no exception, payload intact, stack margin); protection: no question, Save/Format work; keys: key == real-click words (exact, fix the 1-px harness tolerance by synthesizing the click at the cell centre); phantom-click gate; Retire/Win/Lose gate (analog of `pmretire.py`); save/load round trip via a save disk.
* Budget for re-gating the branch's PASS claims is inside this stage: ~1 day.

### Stage 3 - Tooltips (1-1.5 days, Sonnet; wording/visual review by lead and user)
* Port `pm_tooltip.s` structure: own composer + bg-colour mapping + 52-char wording table + posture levels + key labels + 32 ids; WW1 sites/tables from section 3.3; keep the back-buffer-after-copy trick (site `jsr $13a94` at `$13e0a`, validated).
* **Gates**: `pmtt_ab` frame A/B with pointer held; `pmtt_state` full-RAM tick-state with tooltips on (world untouched); `pmtt_check` (52 chars); **side-by-side screenshot sheet vs master's (`pmtt_*.png`) reviewed by the user** - the missing gate in the branch. No box, no junk, cream on black.
* Risk: WW1 font/palette differs; contained by the first task (read font bytes) and the sheet.

### Stage 4 - Remaining master defaults, in priority order (3-4 days, Sonnet each; ask the user to scope)
1. `pm_mste` (nearly verbatim; gate: MSTE register read after boot, TOS 2.06, `_MCH` cookie rules) - 0.5 d.
2. `pm_credit` version line (user requirement for every game: `v<VERSION> enhanced by dad_prg`) - 0.5 d (needs the WW1 menu loop site).
3. `p4_clamp`/`p4_ptr_*`/`tt_ptr`, `p3b_interp/delta` men interpolation, `qol_hover` village hover - 1.5 d.
4. `pm_intro_*` real-time intro (ask: WW1 intro differs) - 0.5 d.
5. `p6_cpy`, `p4_spr` (signature-matched) - 0.5-1 d after profile.
* Gates per patch: master's A/B frame gate (pixel-identical unless stated) + state gate + machine matrix.

### Stage 5 - Profile and decision on performance, sound, triple buffer, HD (1 day study, Sonnet; **design model for the decisions**)
* Fresh profile on EA (Hatari `--profile` start-up flag; the branch's "no profiling data" was missing `--profile`). Questions: what is `$82c8` doing for 40 % (terrain patterns?) and is there an exact speed-up (pre-shifted patterns, blitter)? is the sound the timer-C sequencer (cost 14 % per branch)? flip/buffer layout for `p7_triple`.
* Needs the design model for: (a) any exact-equivalence speed-up of the combiner; (b) the sound redesign (DMA) if wanted; (c) HD loader if wanted. Otherwise Sonnet.

### Stage 6 - Regression, packaging, report (1.5-2 days, Sonnet; lead commits)
* Machine matrix (ST TOS 1.04, STE 1.06/1.62, Mega STE 2.05/2.06 at 8/16 MHz, TT, Falcon) per master's `regression.md`; `package.sh` -> `dist/Powermonger_WW1_v<ver>_patched_floppy_<date>.zip` + `README_FLOPPY.TXT` + md5 table (determinism: two builds identical) in README; `REPORT.md` in plain English; move to `games/done/`; update the top-level README/queue.
* Release recipe = master's: verify -> build floppy (deterministic md5) -> gates on the *built artefact* (not a debugger patch) -> md5 table -> zip -> commit.

### Estimates and routing summary
| stage | agent-days | model |
|---|---:|---|
| 0 intake/harness | 0.5-1 | Sonnet |
| 1 delivery + floppy writer | 1-1.5 | Sonnet (+ lead review of RAM placement) |
| 2 tick/noprot/keys/cachecap + re-gating | 2-3 | Sonnet |
| 3 tooltips | 1-1.5 | Sonnet; user visual acceptance |
| 4 other defaults | 3-4 | Sonnet |
| 5 profile + decisions | 1 (+ design 0.5-1 if combiner/sound) | Sonnet; **design model only for combiner speed-up, sound, HD** |
| 6 regression/package | 1.5-2 | Sonnet |
Parallelism (per game-delegation): stage 3 (tooltips) and stage 2's keys can run in parallel once stage 1 lands; stages 0 and the EA-packer curiosity (R4) are independent. Each subagent gets its own Hatari workdir; never two Hatari on one workdir; results-file insurance.
Nothing needs the design model **on the critical path**, except the payload-placement/cache-cap decision (a short review) - which the evidence above already largely settles (`$72000` is below the allocator).

### Risks
1. **Payload vs resource cache/Retire/Win/Lose/new-territory** (master's v1.1 bug): mitigated by placement below `$80000`, cache-cap analog, dedicated gate.
2. **Packer unknown**: mitigated by R1-R3; if a build-time image is ever needed, 0.5 day to identify (R4).
3. **Raw loader vs data disk**: the game reads sectors raw; the patched disk's FAT must stay valid; floppy-only first (HD optional).
4. **Protection**: EA's check = same structure (flag `$15998`); verify no second check (disk-based, tracks 80-83 raw data exist: a Pasti-protected disk may read them) - unproven; test by running the *converted `.st`* through the whole flow (it runs, so the tracks are not needed, [obs to title only]; test to the map and a save).
5. **Hatari/real-hardware gap**: the real-machine claims (Mega STE ok / TT stutter) are unverified; TT/Falcon not gated by the branch.
6. **WW1 wording/design choices** need user input (tooltip text, keys for WW1-specific commands).
7. **STX conversion fidelity**: the 4 raw tracks were dropped; a Hatari boot proves the game does not need them for the title only.
8. **Branch notes can mislead**; treat only section 5.1 items as reusable, after spot-check.

---------------------------------------------------------------------------------------------------------------------------

## 7. Gate budget (re-verification of branch claims is built in)
| gate | stage | time | tool basis |
|---|---|---|---|
| cold boot to map view (hard criteria) | 0,every | 2 min/run | harness |
| tick state-equality 12 ticks + negative control | 2 | 1.5 h build + 20 min run | pmtick_series idea |
| rate 8/16 MHz x 50/60 Hz x machines | 2,6 | 2 h | rate_check, master `pm_measure` |
| soak 20 min, hard criteria | 2,6 | 30 min per config x 3 | soak idea |
| noprot, keys==clicks, phantom | 2 | 1 h | keygate/phantomgate fixed |
| Retire/Win/Lose/territory/save-load | 2 | 2 h | `pmretire` analog |
| tooltips A/B + state + sheet | 3 | 2 h + user | pmtt_* |
| final matrix + package determinism | 6 | 0.5 day | master regression |
Re-gating of the branch's PASS table ~1 day total, inside stages 2-3.

---------------------------------------------------------------------------------------------------------------------------

## 8. Open questions for the lead/user (answered by the user 2026-11-23, via the lead)
1. HD version: **yes**, like the other releases (adds the hd_* port and the raw-loader checks; after the floppy).
2. Master extras in scope: **all** (performance, DMA sound, triple buffering, rain, men interpolation, real-time intro, TT/Falcon pointer). Performance is scoped by the separate profiling study (`work/notes/profile_ww1.md`, not this file's owner). The release has the budget "to be done right".
3. Version credit text and number: `v1.0 enhanced by dad_prg` (stage 1, user default).
4. Tooltip wording: **master's style adapted to WW1 names**.
5. Cobra/Fuzion cracks: comparison only (the Fuzion crack runs standalone, it never asks for the Powermonger disk: see the key-disk finding in stage 2).

## 9. Evidence files (`/tmp/pmww1/`)
`stx2st.py` (STX->ST), `ea_check.st` (the converted EA disk, md5 `95354c89884a4cb82b62fe63400bf750`), `orig/ea/f2/AUTO/WW1.PRG` + `f2/*.PAK`, `ea_title_ram.bin` (1 MB RAM at the EA name prompt), `ww1_depack.bin` (branch atomik depack of Cobra, 153665 B), `montage1.png` (Cobra boot), `montage3.png` (**EA cold boot to the title**), `ww1_tooltip_getmen.png` / `ww1_tooltip_bar.png` (WW1 branch tooltip), `pm_bar.png` (master's tooltip), `run5.log` (hover LINE results, tick counter), `rnc/rnc1.py` (failed RNC header probe), `b/games/in_progress/powermonger-ww1/` (scratch copy of the branch with payloads assembled by vasm; `build/tt/` = branch patched PRG), run scripts `run1-5.py`.
Nothing under the repo or the user's checkouts was modified. Hatari instances were launched with private HOME in `/tmp/pmww1/run*` and terminated by the harness.
