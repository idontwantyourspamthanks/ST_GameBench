# Nebulus: what the "tower" byte controls (colour, backdrop, enemy sprites) and how to choose them per level (NebLooks)

Tags: **[obs]** observed in Hatari 2.6.1 (STE TOS 1.62, 1 MB, 8 MHz; raw output quoted or kept in the files named), **[disasm]** read from `work/train/dis_33000_40000.txt` / `tools/m68dis.py` on `work/dumps/tower_1mb.bin`, **[INFERENCE]** not proven.
Files: `work/looks/` = `mk_looks.py` (experiment OVL), `run_camp.py` (10-level campaign, RAM dump at every level start), `run_poke.py` (RAM-poke proof), `check_dumps.py` / `check_poke.py` (+ `.out`), `cmp_dumps.py` (+ `.out`), `sprites.py` (renders the sprite sources), `e_look.py` / `e_odd.py` (editor behaviour), `ed_look_proposal.s` (design sketch, assembled to measure bytes), screenshots `work/looks/shots/*.png`, `sprites_by_tower.png`, `towers_montage.png`, `body_split.png` (git-ignored).
Not changed: `patches/ed_*`, `gen_ed.py`, `tools/nebulus.py`, `tools/nepatch.py`, `originals/`.

## 1. Answers in four lines
1. A **campaign slot** (cart slot 1..8 on the site = a campaign record in the file) has **no graphics field**: it is a name + an ordered list of entries (custom level index, or original mission/tower). Nothing in the slot id picks a colour or an enemy set.
2. Everything visual comes from **one number per level: `tower.b` (0..7) of the level record** (the game's `$3390c`). `mission.b` (`$33910`) is **not** a graphics input: no visual site reads it [disasm] and M1T1 = M2T1, M1T4 = M2T4 byte for byte in RAM at level start [obs, section 4]. So there are **8 looks, not 16**.
3. The look is **not one data block**. The game reads `$3390c` at **six separate instructions** at level start (and per frame for the texture), each fetching a different table: palette (16 words), raster colours (4 words), skyline (512 B), tower texture (4 KB), **enemy "eye disc" sprites (4 designs, = tower & 3)**, time/title. The enemy designs are **not** bundled with palette or backdrop; they are a separate table indexed by `tower & 3`, so tower *n* and *n+4* share the eye design. The ball sprites (stone, red) are the same in every tower (only recoloured by the palette).
4. **Choosing colour and enemy set independently is proven by RAM pokes** (section 5) and costs ~190 bytes of code in the editor/hook blocks (section 7), which fits the ~236 B free budget. Everything is always resident (no per-tower loading). **Recommendation: build it** (small, low risk, backward compatible), after fixing the **odd-record crash found on the way (section 9, a real bug of the shipped editor)**.

## 2. What the base tower (`$3390c`) controls [disasm + obs]
`$3390c` is read by exactly these instructions in `$33000..$40000` (`grep 3390c`); every one is the 6-byte `move.w $3390c.l,d0` (`30 39 00 03 39 0c`) except the title one. All sites verified in RAM at a level start [obs `work/looks/run_poke.py` log: `363a4=30390003390c 3522e=30390003390c 3dc1e=30390003390c 36b68=30390003390c 366de=30390003390c`].

| site (RAM) | routine, runs | index | data read | resident at | what it is | verified by |
|---|---|---|---|---|---|---|
| `$3522e` | `sub_035228`, level start (`$3dc2a`) | `t&7` | `$35250 + t*$20` (16 STE words) -> `$351ac` | exe data | the 16-colour palette (a 0..7 ramp of one hue + a second ramp/accent) | A, B |
| `$3dc1e` -> `$351cc` | `sub_0351cc`, level start (`$3dc24`) | `t&7` | `$351e8 + t*8` (4 words) -> `$40398/$4039c` | exe data | the 4 raster colours (sky gradient ends) | B |
| `$366de` | `sub_0366d8` from `sub_03636e`, level start | `t&7` | `$3e382 + t*$200` (512 B) -> shifted copies at `$100e0..$110df` | exe data | the **skyline / horizon silhouette** (mountains, city, ...) | D1 |
| `$36b68` | tower draw `$36b50`, **every frame** | `t&7` | `$4b6ba + t*$1000` (+ phase/angle) | exe data | the **tower body texture** (bricks, bubbles, stucco ...) | C, D2 |
| **`$363a4`** | `sub_03636e`, level start | **`t&3`** | **`$54aba + (t&3)*$a00`** (8 frames of 16x16 mask+4 planes = 320 B each) -> pre-shifted sprite frames 12..19 (`$24be0..$2fadf`, 5600 B per frame) | exe data | **the enemy "eye disc" sprites (creature kinds 8 and 9, frame `$c..$13`)** | A, B, section 4 |
| `$3adae` / `$3d10a` | time init / title | `t` | `$3ad9e` (8 BCD words), name table `$3d14e`/`$3d16e` (mission picks the table) | exe data | default time, title text (the editor already overrides both from the record) | editor.md |
`$3390c` is also copied to the per-player tower words (`$3e274`, `$33a44`) and the progress mask `$33a34`; those are bookkeeping, not graphics [disasm `$3e27c..$3e37a`].
The sprite machinery [disasm]: `sub_03636e` (`$3dbf0`) calls `sub_0367e2/sub_03684a` which **pre-shift** every source sprite into 16 horizontal phases at level start: frames 0..11 from `$53bba` (balls, `$f00` B, **tower independent**) into `$14560..$24bdf`, frames 12..19 from `$54aba + (t&3)*$a00` into `$24be0..$2fadf`; the table `$316e0 + frame*$80` holds the buffer pointers; creatures are drawn by `sub_0394fe` (`$18(slot)` = frame). The frame numbers set by the AI (`sub_03b482`): kinds 8/9 use `$c + ((cnt>>2)&7)` = **frames 12..19 (the two eye discs)** [disasm `$3b5fc..$3b60e`]; frames 0..11 are the balls and the spawn/death animation [INFERENCE for the exact numbering; the sheet `sprites_by_tower.png` shows the pictures]. So "enemy set" is exactly the 4 eye-disc designs; shapes of stone/red/flyer are fixed, only their colours follow the palette.
Not tied to the tower: ledge/pillar/door/lift tiles (`$574ba`, `$536ba`, `$537fa`.. are fixed sources), the frog, the HUD, sea, the flyer sprite (`$456c2`), music (no read of `$3390c` anywhere else in `$33000..$40000`) [disasm: complete grep].

## 3. Table: tower -> look
Mission 1 and mission 2 use the same row (same RAM data at level start, section 4). Eye designs rendered from the real source blocks with each tower's own palette: `work/looks/sprites_by_tower.png` (rows = towers 1..8, frames 4..11 = balls, then eye frames 12/14/16/18); in-game look of the 8 towers: `towers_montage.png` (top T1..T4, bottom T5..T8).

| tower (`tower.b`) | palette `$35250+t*32` (colours 0..15) | raster 4 `$351e8` | eye design (`t&3`) | source md5 (6) eyes / skyline / texture |
|---|---|---|---|---|
| T1 (0) | `000 100 .. 700 710 .. 770 772` red ramp + yellow | `200 700 740 777` | **0 "eyelid eye"** | 359ab3 / d59804 / 2b03b0 |
| T2 (1) | `000 010 .. 070 071 .. 077 277` green ramp + cyan | `002 005 057 677` | **1 "studded disc"** | 68235f / e3a363 / 531996 |
| T3 (2) | `000 100 .. 700 701 .. 707 727` red ramp + magenta | `020 040 272 676` | **2 "four orbs"** | d66490 / 68557c / 626ac5 |
| T4 (3) | `000 010 .. 070 170 .. 770 772` green ramp + yellow | `202 606 747 767` | **3 "split plate"** | b23af6 / dd0516 / 7357f1 |
| T5 (4) | `000 001 .. 007 017 .. 077 277` blue ramp + cyan | `300 720 740 775` | 0 (same as T1) | 359ab3 / b85c45 / 5df33f |
| T6 (5) | `000 001 .. 007 107 .. 707 727` blue ramp + violet | `002 037 067 677` | 1 (same as T2) | 68235f / ed9d85 / 951612 |
| T7 (6) | `000 011 .. 077 167 .. 707 716` teal ramp | `400 730 760 777` | 2 (same as T3) | d66490 / 857f34 / b54583 |
| T8 (7) | `000 101 .. 707 716 .. 770 671` violet ramp | `411 533 655 777` | 3 (same as T4) | b23af6 / 4c42b9 / c09986 |
In game: T1 red bricks / orange sky; T2 blue bubble stone / green sky; T3 green bricks / pink sky; T4 pink stucco / yellow-green sky; T5 orange bricks / blue sky; T6 blue bubbles / violet sky; T7 gold stone / teal sky; T8 pale granite / magenta sky [obs `towers_montage.png`]. Skylines, textures, palettes are 8 distinct blocks each; the eye designs are 4 distinct blocks (md5 of the source and of the pre-shifted RAM buffer, section 4).
**The user's observation is the original game's behaviour**: tower 1 (red) uses eye design 0; tower 2 (green) design 1, etc.; every later tower looks different, and a custom level whose `tower.b` differs from the previous one does the same (section 8 checks the editor is not at fault).

## 4. Proof 1: two-record experiment (tower byte only), at level start [obs]
`work/looks/mk_looks.py` writes `NEBLEVEL.OVL` with 10 levels whose **grids are byte-identical** (ledge ring, exit, stone ball, red ball, two vertical eyes between pillars, one horizontal eye) and which differ **only in the record bytes mission/tower**: levels 0..7 = M1 T1..T8, level 8 = **M2** T1, level 9 = **M2** T4; one campaign plays them in order (`run_camp.py`: Hatari, F10 -> Campaigns -> Play, forced door entry between levels; E trainer on so the frog survives; RAM dump of 512 KB 2.5 s after every level start). `check_dumps.py` (raw, `work/looks/check_dumps.out`):
```
lvl  mission tower | $351ac==pal[t]  $40398==ras[t]  eye-buf md5(t&3)  body-buf $100e0 md5 (t)
  0  M1      T1    | True           True           9444978a (set 0)   8d08abed  mission-in-RAM 1 tower-in-RAM 0
  1  M1      T2    | True           True           e409205a (set 1)   ef576a50  mission-in-RAM 1 tower-in-RAM 1
  2  M1      T3    | True           True           3892848c (set 2)   7ad57eea  ...
  3  M1      T4    | True           True           d65f1a45 (set 3)   059f50db
  4  M1      T5    | True           True           9444978a (set 0)   342c8db9
  5  M1      T6    | True           True           e409205a (set 1)   d95fe99d
  6  M1      T7    | True           True           3892848c (set 2)   84d71716
  7  M1      T8    | True           True           d65f1a45 (set 3)   f64b2f22
  8  M2      T1    | True           True           9444978a (set 0)   8d08abed  mission-in-RAM 2 tower-in-RAM 0
  9  M2      T4    | True           True           d65f1a45 (set 3)   059f50db  mission-in-RAM 2 tower-in-RAM 3
eye buffer values per t&3 (must be one each): {0: 1, 1: 1, 2: 1, 3: 1}  body buffer values per tower (one each): {1..8: 1}
distinct eye buffers over 10 levels: 4  distinct body buffers: 8  ball/frame 0-11 buffers distinct: 1
```
and `cmp_dumps.out`: the grid region `$327f0` is identical in all 10 dumps (md5 3fb9497c), the sprite pointer table `$316e0` (2560 B) is identical, the ball frames `$14560..$24bdf` are identical, only palette/raster/skyline buffer differ per tower and the eye frames `$24be0..$2fadf` differ per `tower&3` (T1=T5, T2=T6, T3=T7, T4=T8). **Mission-only pair**: levels 0 vs 8 and 3 vs 9: palette, raster, eye frames, skyline buffer **equal** (md5 above), only `$33910` (1 vs 2) differs. So the tower byte drives palette + raster + skyline + texture + eyes; mission drives nothing visual (it picks the title name table, the original grid copy of "Copy original grid", and nothing else for a custom level).
(`cmp_dumps.out` also lists the whole region `$40390..$403df`: it differs between M1T1 and M2T1 because the lower part is runtime raster state; the 4 colours `$40398..$4039f` are what `check_dumps.py` compares, and they are equal.) (The pointer table equal means the table is rebuilt with the same buffer addresses each level; only the data behind it changes.)

## 5. Proof 2: independent choice by RAM poke [obs] (`run_poke.py`, logs `/tmp/looks/poke*.log`, checks `check_poke.out`)
Poke a site's `move.w $3390c.l,d0` (6 B) to `move.w #N,d0 / nop` (`30 3c 00 0N 4e 71`) while the game runs, then force the door (the same pokes as the campaign test) so that the NEXT level starts with that site changed; all other sites keep reading `$3390c`. Grid identical to the section 4 levels (the checks compare buffers, not the grid).
| step | pokes | next level (record = T2) | RAM result (`check_poke.out`) | screenshot (`work/looks/shots/`) |
|---|---|---|---|---|
| A | `$363a4` -> index 2 | **T2 colours, skyline, texture; T3 eye design** | palette == T2, raster == T2, skyline buffer == T2, **eye frames == T3 (= T7) natural** | `A_T2palette_body_with_T3eyes.png`: blue bubbles, green sky, city, the eyes are the 4-orb design |
| B | `$3522e`, `$3dc1e` -> index 4 | **T5 colours; T3 eyes, skyline, texture** | **palette == T5, raster == T5**, skyline buffer == T3, eye frames == T3 | `B_T5palette_with_T3body_eyes.png`: T3's brick body shape but T5's colours (orange bricks, blue sky) |
| C | `$36b68`, `$366de` -> index 6 | T2 colours, T2 eyes; **T7 skyline + texture** | palette/raster == T2, eye frames == T2 (=T6), **skyline buffer == T7** | `C_T2palette_eyes_with_T7body.png` |
| D1 | `$366de` only -> 6 | T2 texture/colours/eyes; **T7 skyline** | skyline buffer == T7 | `D1_T2_with_T7skyline_only.png`: bubbles + T2 sky but T7's spiky horizon |
| D2 | `$36b68` only -> 6 (acts per frame, mid-level) | T2 + **T7 texture** (bricks) on the same level | screenshot only (the texture is read per frame) | `D2_T2_with_T7texture_only.png`; `body_split.png` = natural T2 / D1 / D2 / C / natural T7 side by side |
Both directions of the user's question are therefore shown: **enemy designs of another tower with this tower's colours** (A) and **another tower's colours with this tower's enemy designs** (B). Raw excerpt:
```
pA: tower-in-RAM 1   palette == T2   raster4 == T2   eye buffers == T3,T7   body buffer == T2
pB: tower-in-RAM 2   palette == T5   raster4 == T5   eye buffers == T3,T7   body buffer == T3
pC2: tower-in-RAM 1  palette == T2   raster4 == T2   eye buffers == T2,T6   body buffer == T7
```
(On the grid line of `check_poke.out`: "none" only because the poke run used the near-frog grid and the natural dumps the first grid; the buffers are what is compared.)
**Residency / loading cost: none.** All 4 eye designs (4 x 2560 B at `$54aba..$572b9`), 8 textures (`$4b6ba..$536b9`, 32 KB), 8 skylines (`$3e382..$3f381`, 4 KB) and the palette tables are ordinary data of the game exe, always in RAM; the game already (re)builds the pre-shifted buffers from the source of the selected index at every level start (`sub_03636e`: that is the existing cost, ~unchanged when the index is another one). No loader, no extra RAM, no file access.

## 6. Mechanism and hook points for a per-level override
A patch replaces the 6-byte `move.w $3390c.l,d0` at a site by `jsr hook.l` (6 B, same length, `nepatch` derives the original bytes and verifies them). The hook must return the index in d0 and preserve everything the site's neighbours use. Registers at the sites [disasm]:
| site | live registers across the site | hook may clobber | order at level start |
|---|---|---|---|
| `$363a4` (eyes) | **a0 = `$54aba` (set just before)**, a1/a6 set before, d0 dead, d1 dead | d0, d1 | `sub_03636e` runs at `$3dbf0`, **before** the decode hook `$3dc12`: the hook must read the record itself (`cur_rec`, uses `rsLvl`, valid since `apply_entry`/Play/playtest), not a variable set by `ed_dec` |
| `$3522e` (palette) | a0 = `$35250` | d0, d1 | `$3dc2a` |
| `$3dc1e` (raster) | none | d0 | `$3dc1e..$3dc24` |
(`$366de`, `$36b68`: not hooked in the design, section 7; `$36b68` runs every frame so a hook there would cost ~100 cycles/frame unless the choice is cached in RS.)
Hook (`work/looks/ed_look_proposal.s`, assembled): `ed_eye` / `ed_col` entry points + common part: save a0, `bsr cur_rec`, if a record exists read `3(a0)` = flags, shift/mask the nibble, 0 = follow the base tower (`move.w $3390c.l,d0`), else d0 = nibble-1; return. Original towers (`rsLvl = 0`): `cur_rec` returns 0, so the base tower applies and **nothing needs clearing** when an original tower starts. Playtest: `rsLvl = $7fff` -> `TREC`, which `commit` has just encoded (including flags once `commit` writes them).

## 7. Design: format, editor UI, code and where it lives
**Format (no version change).** The level record's header byte 3 `flags.b` is reserved and 0 in every file written so far. Define (platform neutral, no addresses):
- bits 0..3 = **enemy set**: 0 = follow the base tower (old files), 1..4 = eye-disc design 0..3 (the four designs of the game; towers T1/T5 = 1, T2/T6 = 2, T3/T7 = 3, T4/T8 = 4);
- bits 4..7 = **colours**: 0 = follow the base tower, 1..8 = palette + raster colours of tower 1..8.
`mission.b`/`tower.b` keep their meaning (tower = skyline + texture + default time/title + the fallback for colours/enemies); the 4 eye designs and 8 colour sets are shown on the site as the 8-row table of section 3. Compatibility, checked in the code [obs/disasm]: the game's `ov_check` ignores byte 3 (it reads bytes 0..2 and the word at 4, `ed_editor.s` 2235..2290), `work/editor/ovl.py validate` ignores it, the site parser takes `_flags` and discards it and `Compose` copies the record bytes unchanged (`level.record == records[i]` is asserted) => **no validator rejects non-zero flags, old files = flags 0 = unchanged look, a v1.1 game opening a new file shows the base look (graceful)**. The only loss is an OLD editor re-saving such a level (`commit` does `clr.b 3(a2)`): the override is dropped when someone edits the level with the old editor, harmless.
**Editor UI.** `Tower >` menu (`m_tower`, 8 items now) gets two items next to `Look: next tower`: `Colours: next` (cycles 0 = "as tower" then 1..8) and `Enemies: next` (0 = "as tower", 1..4); the right-hand panel line `T3 M1` becomes `T3 M1 C5 E2` (or `C- E-` when following). The labels can name the set (e.g. "Enemies: 2 studded disc"), at ~16 B per string.
Editor-side code: `rsFlg` = RS word at +50 (free: `rsLast` = 48, `rsTosP` = 52 [editor equates]); `c_eye`/`c_col` (one shared routine, nibble cycle mod 5 / mod 9, ends in `c_ldone` like `c_look`); `commit`: replace `clr.b 3(a2)` by `move.w RSV+rsFlg(a5),d0 / move.b d0,3(a2)`; `lv_edit`: load `3(a0)` into `rsFlg`; `c_newlvl`: `clr.w rsFlg`; `c_copyorig` unchanged (it temporarily sets `rsLvl = 0`).
**Bytes** (`vasmm68k_mot -Fbin -no-opt` on `work/looks/ed_look_proposal.s`, 102 B including two 2-byte stubs, so hooks + cycle = 98 B):
| part | bytes |
|---|---|
| hooks `ed_eye`/`ed_col`/common (assembled, `$76d44..$76d6f`) | 44 |
| `c_eye`/`c_col`/cycle (assembled, ends with a 6 B `jmp c_ldone`; `bra.w` = 4) | 52 |
| menu items (2 x `action,param,text`) + `cmds` entries (2 words) [estimate from the existing strings] | ~38 |
| `commit` +4, `lv_edit` +8, `c_newlvl` +4 [estimate] | 16 |
| panel readout `C5 E2` [estimate] | ~30 |
| **total** | **~180** (+ ~12 spare for the three new sites in `ed_overlay.nep`, which are patch text, not RAM) |
Budget (current assembly of `ed_editor.s`, section sizes from vasm: CODE1 `$75740..$76bfa` free 6, DATA `$76d40..$7726c` free 148 (to `$77300`), CODE2 `$77300..$779e8` free 24 (to `$77a00`), CODE3 `$77a40..$77c7a` free 6 (to `RS $77c80`), CODE4 free 4, CODE5 free 2 [editor.md 13.5/13.7]) = 190 B in the blocks, plus the 24-byte dead strip `$75728..$7573f` before `CODE1` (= 214 B; the lead's ~236 B figure presumably counts more of the zero gap). It fits, tightly: put hooks + cycle (98 B) and the menu strings (the tail of DATA, 148 B free) in DATA; the panel code in CODE2/CODE3; if the panel readout is dropped (enemies/colours only visible in the menu text via the cycled value) the total is ~150 B and leaves ~58 B. If more room is needed: trim `m_levels`/`m_camps` (~70 B, editor.md 13.5) or share the cursor-column code (~50 B). All of it is game RAM (F9-safe); nothing can live in non-game RAM (`BUF`, `$BC000`) because the hooks execute during play and F9 overwrites that area.
**Loader / playtest path.** Nothing new at load time: the record is read from the store (`$BC000`) by `cur_rec` at each level start; a campaign entry sets `rsLvl` in `apply_entry` before the level; Play from the manager and Playtest set `rsLvl` (`$7fff` -> `TREC`, written by `commit` from `rsFlg`); for an original tower `rsLvl = 0` -> base look (override cleared automatically). The editor's own flat map does not show sprites or colours, so nothing there changes.
**Site / cart side** (`~/Code/dadprg/api/app/services/hub/ncmp/*`, read-only here): (1) `Parser.level_at` must stop discarding `_flags` and expose it (`Level#flags`; `campaign_writer.rb` stores `mission`, `base_tower`; add `look_colours`, `look_enemies` columns or derive them from `record` on read, because the record bytes are what is stored, `Compose` copies them untouched and dedupes by record bytes: two levels differing only in flags are correctly distinct records); (2) it should validate the nibbles (enemies 0..4, colours 0..8) as soft warnings (the game would accept any value: `and #15`, then a value above 4 / 8 reads `$54aba + (v&3)*$a00` / `table[v&7]`, still safe); (3) `hub_serializers.rb` (`mission`, `base_tower`) should add `colours`/`enemies` so the cart page can show "tower 3, colours 5, enemies 2"; (4) the preview legend draws enemy markers, not sprites, so it needs no change (a colour swatch row from the section 3 palette table would be a nice-to-have); (5) `Compose` is where the **odd-size crash (section 9)** must be prevented.

## 8. Is the user's observation an editor bug? [obs] (`work/looks/e_look.py`, `e_odd.py`, build = default `nepatch build` set with a zero `NEBLEVEL.OVL`)
`e_look.py` (menu-driven, `work/editor/ui.py` helpers): F10 -> Levels -> `<new level>` ... raw:
```
L1 new level opened                rsMis 1 rsTow 0 ... vDirty 1          <- defaults: mission 1, base tower 0 (T1), time $0450 (c_newlvl)
L1 after 2x look next              rsMis 1 rsTow 2
L1 after other mission             rsMis 2 rsTow 2
after leaving L1 | levels [('NEW LEVEL  ', 2, 2, 48)]                   <- Tower > wrote THIS level's record (mission 2, tower 2)
L2 new level opened                rsMis 1 rsTow 0                      <- level 2 does NOT inherit level 1's look
L2 after 3x look next              rsMis 1 rsTow 3
after leaving L2 | levels [('NEW LEVEL  ', 2, 2, 48), ('NEW LEVEL  ', 1, 3, 48)]
```
Code reading agrees (`c_newlvl`: `rsMis = 1`, `rsTow = 0`, `rsTime = $0450`; `c_look` changes only `RSV+rsTow`; `commit` writes `rsMis`/`rsTow` into byte 0/1 of THAT slot's record; `lv_edit` reloads them from the record; `apply_entry` sets `$33910`/`$3390c` from the entry's record at every campaign step) and the 10-level campaign of section 4 (`tower-in-RAM` follows each record: 0,1,2,..,7,0,3). **No editor bug in the look handling.** Consequences for users: every NEW level is `T1` (red, eye design 0) until someone presses `Look: next tower`; a campaign that mixes original towers and custom levels shows each level's own look, which is what the user saw. (A second subtle point: a new level's time is an explicit 450 s, not the base tower's 400 s.)

## 9. BUG FOUND: records of odd size crash the game (shipped editor v1.1 and the format) [obs]
The format puts level records back to back with `len` = `2*rows` + number of non-zero cells, **unpadded**. When a record has odd `len`, the next record starts at an odd address and the game reads its header words (`move.w 4(a1),d5` in `ov_check`, `lvl_ptr`, `store_end`, `lv_edit` `6(a0)`, `ed_time` `6(a0)`) at an odd address: a 68000 **Address Error** (Hatari log: `Address Error reading at address $bc1b3, PC=$77814`).
Evidence: (1) `work/looks/mk_looks.py` without `even`: 10 levels of 159 B (43 cells) -> F10 at the title: Address Error at `$bc1b3` (= `$bc000 + 272 + 159 + 4`), `$70` becomes the TOS vector `$e03380`, the manager never opens, TOS spin at `$e0339c` [obs]. With `even` (one more cell, 160 B records) the same file opens and the whole 10-level campaign plays (section 4). (2) **The editor itself produces the bad file**: `e_odd.py` = new level + one extra ledge cell (record 139 B = 23 cells) + a second new level, then Levels > level 2 > Edit: `Address Error reading at address $bc1a1, PC=$7662e` (`lv_edit`'s `move.w 6(a0),rsTime`), VBL vector `$e03380` (game gone) [obs, `/tmp/looks/eodd.log`]. A blank level has 22 cells (even); every odd-count level made by a user breaks any level after it. The site's `Compose` concatenates records the same way and the PC tools (`ovl.py`) accept such files.
Fix options (not done here: editor files are out of scope): (a) pad on write: commit/`ovl.py`/`Compose` make `len` even by adding a mask bit + stream byte `$00` for one empty cell (decoder writes 0, popcount rule still holds: no format change); (b) make every word access on a record byte-wise (many sites). (a) is a few bytes in `commit` and one line in the PC/site tools, and old odd files still need a repair pass on load. Until then **any test file must keep every record even** (`mk_looks.py ... even`).
(The earlier heads-up message to Main described the same bug.)

## 10. Risks, limits, recommendation
- **Worth building**: ~180 B, 3 hook sites + 2 menu items + 3 small editor edits, no loader, no new RAM, no format version bump, graceful on old games/editors. The user gets the 8 colour sets x 4 enemy designs (x 8 skyline/texture bodies via the base tower): "choose colour and enemy set" = two cyclers in `Tower >`.
- What it does NOT give: new enemy *shapes* (stone/red/flyer are common; only the two eye-disc kinds have 4 designs), custom colours (the 8 palettes are fixed tables; a free palette editor would need 32 B per level in the record: needs a format bump), colours independent of the skyline/texture shape is NOT split further than "base tower" (the two hook sites `$366de`/`$36b68` could take bits of a second reserved byte if wanted; `$36b68` per-frame hook is the only cost-relevant one).
- Risks: (1) the hook runs `cur_rec` -> `ov_ok` -> `ov_check` on first use (cached `rsOk`): at level start it executes the first time while still in the title/new-game path, fine (it already runs at `ed_time`/`ed_dec`); (2) `a0` is live at `$363a4`/`$3522e` (preserved in the sketch; a wrong register assumption would corrupt the sprite build: the poke proof used immediates and does not exercise the hook code, so the **hook itself still needs its own cold-boot gate** with equality of the `$24be0` and `$351ac` regions against the poke results above); (3) the odd-record crash (section 9) must be fixed first or the feature will be blamed for it; (4) 2-player mode, Mega STE and floppy builds were not run for this study (the hook sites are game code, same on every build; the editor's blocks are shared); (5) nothing was run on real hardware.
- Reproduce: `python3 work/looks/mk_looks.py /tmp/looks/near_even.ovl even`; `python3 tools/nepatch.py build --out /tmp/looks/build_near --ovl /tmp/looks/near_even.ovl`; `python3 work/looks/run_camp.py DIR OUT 10`, `python3 work/looks/run_poke.py DIR OUT [C|D]`, `python3 work/looks/check_dumps.py OUT`, `check_poke.py`.
