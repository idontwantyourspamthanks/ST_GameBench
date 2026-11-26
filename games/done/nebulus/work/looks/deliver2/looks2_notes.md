# Nebulus v1.2 round 2: colour/enemy list pickers, editor recolouring, crumble ledge (NebLooksUI)

Tags: **[obs]** observed in Hatari (raw lines in `logs/`), **[disasm]** read from `work/train/dis_33000_40000.txt`, **[INFERENCE]** not proven.
Built and gated in a COPY (`/tmp/nlui`, RAM disk); the real tree is untouched except this directory; `PATCH.diff` is against HEAD a30cc67 (`git apply --check` passes in the game dir).
Scripts here carry `/tmp/neblooksui/...` scratch paths (the gate fixtures `lg/ne`, `lg/r/base8_ste` are produced by `work/looks/mk_looks2.py` + `run_look.py`).

## 0. What the user saw (repro on his image) [obs]
`dist/AtariST_enhanced_games_2026-11-19_pm1.2.img` (NEBULUS\NEPATCH.BIN md5 6007941c.. = a fresh HEAD build), Mega STE TOS 2.06 4 MB, fast-boot no, `--auto C:\NEBULUS\START.TOS`, real keys:
F10 -> Levels -> <new level> -> Tower > Colours: next x3 -> `flags $30` (panel `S3 E0`; **the editor view does not change: the editor palette was a fixed 16-word table**) -> Playtest: `$351ac` == stock tower-3 palette, TREC `01003030`, screenshot green bricks (`shots/repro_user_image/04_playtest.png`).
So the playtest recoloured in Hatari on that image; **not reproduced: "playtest shows nothing"** (MiSTer/real hardware, or another flow, is possible: [INFERENCE]).  Real defects found: the editor never showed the choice and the menu never said which colour "next" was.  Fixed by the redesign below.

## 1. Menu inventory (before) and the consolidation (after)
| item (old `Tower >`) | changed in the record | in play |
|---|---|---|
| Look: next tower | tower byte (0..7) | palette, raster, skyline, texture, eye design `tower&3`, default time (only if record time 0), title (record name overrides), the grid of Copy original grid |
| Look: other mission | mission byte (1/2) | nothing visual in play; title Options page "Mission #n", name table, which original grid set Copy uses [disasm `$3d826`, `$377b8`, `$3d0f8`] |
| Colours: next | flags high nibble 0..8 | palette+raster+skyline+texture of tower n-1 (via ed_lvl cache) |
| Enemies: next | flags low nibble 0..4 | eye-disc design n-1 |
| Time +50/-50, Name | time word, name | start time, level title |
After: `Level >` = **Colours >** (list), **Enemies >** (list), **Copy tower >** (list of the 16 shipped towers), Blank grid, Time +50/-50, Name..., < back.  *Tower: next* and *Mission: next* are gone.
* **Colours pick writes the TOWER byte** (v1.1.1 recolours from it, so a new file is backward compatible) and clears the flags colour nibble; an old nibble is still honoured by the game and by the lists (cursor shows the effective choice = nibble if set, else tower byte; there is no ambiguous "as tower").
* **Enemies pick = flags low nibble 1..4**; with nibble 0 the eye design follows the tower byte (`tower&3`), the list shows that effective design.
* **Copy tower pick** = mission, tower, grid (decoded by the game), flags cleared.  New level: mission 1, tower 0, flags 0.  Mission is invisible in play (only the title Options page prints it).
* Panel line 0 is now `S<colour 1..8> E<design 1..4>` (effective values = the list numbers); the old `T M` line is gone.

## 2. The picker (as built)
* Lists are built at run time in the menu buffer (`pk`, action 14 `a_pick`): Colours = `n <tower name>` from the game's own name table `$3d14e` (8 mission-1 names, 0 bytes of strings), Enemies = `Eyelid / Studded / Four orbs / Split plate`, Copy tower = the 16 names (`$3d14e`..`$3d16e`).  Cursor starts on the current choice.
* **Live preview**: every cursor move in a pick list calls `set_theme`: the 16-word editor palette `EPAL` ($A8980, non-game RAM) is rebuilt from the game palette table `$35250+32k` through a 16-byte map (`tmap`: text gradient = palette 8..15, background = palette[2], tiles from the two ramps) and the editor VBL copies it.  `< back` (Left) restores the current look; the map screen re-themes itself at every full redraw.
* Editor view: grid, tiles, panel, status text and background take the look's colours at once (8 looks: `shots/editor_colours/`).  Skyline and tower texture are **not** drawn in the flat editor (they exist only in the game's renderer: playtest).
* Floppy build: the `$35250` / `$3d14e` literals are remapped by `nefloppy.remap_source` (checked: palette table equal at the same address, name table pointers valid at `$3d146`).

## 3. Crumble ledge
* Cell `$91` (the game's `sub_03ab50`, called every frame of the walking state `$39d0e`: cell under the frog `(v&3)==1 && (v&$30)==$10` is cleared, then the ground check lets the frog fall) [disasm].  Menu item **Crumble ledge** (cell menu, after Ledge); editor draws it as a dotted ledge, status line "Crumble ledge".  The game draws `$91` **exactly like `$81`**: start screenshot crops (sky, skyline, tower, ring, frog) of a ring with `$91` at cols 3,4 and of the plain ring are pixel-identical (`logs/e201*`: crop diff `None`).  The variants are **not** needed for the crumble.
* [obs] STE: before `row1 cols2..5 = [129,145,145,129]`, frog (x,y,state) (4,8,0); t+0.2 s `[129,0,145,129]`, frog (29,0,8): the cell was cleared and the frog fell into the sea; then state 10 (death), respawn with the grid restored.  (Lower-platform variant: see e201 log.)
* **Conveyors `$a1/$b1` are not in the menu**: the same code paths exist in the game (`sub_03ab84`), [obs] a frog standing on `$b1` cells without input is pushed right (x 4 -> 24 = the end of the run), on `$a1` cells left (x 4 -> 111 = wrapped to the end of the run); the game draws them like plain ledges.  A menu entry plus arrow tile/name needs ~95 B against 76 B total free after this round; they still load, save, copy and play (the editor draws them as plain ledges).
* No format change: `ov_check` does not look at cell codes, `version` stays 1, the packing is unchanged.  The dadprg parser/Compose accept every code (tests with `crumble.ovl`).  `ovl.py`: `tiles()` was already broken at HEAD (tile pad byte removed by the looks build) and is fixed; `classify` returns tile 3 only for `$91`.

## 4. Budget (`gen_ed.py`)
| segment | before (HEAD) | after | free after |
|---|---|---|---|
| CODE1 $75740 | 5306 | 5298 | 14 |
| DATA $76d40 | 1314 | 1294 | 30 |
| CODE2 $77300 | 1786 | 1776 | 16 |
| CODE3 $77a40 | 570 | 570 | 6 |
| CODE4 $77dc0 | 252 | 252 | 4 |
| CODE5 $76c76 | 136 | 136 | 2 |
| CODE6 $772da | 28 | 34 | 4 |
| total | 9392 | 9360 | 76 |
Start addresses unchanged.  Sources of room: the 7x6-byte hook jump table at $75740 is gone (sites jump straight to `ed_dec`... : -42 B); 108 explicit `bsr.w/bra.w/bcc.w` became unsized so vasm picks short forms (-108 B; `nefloppy` uses the same assembler path); shared tails `dec2` (inside `dec3`), `ld_dec`, `mb_new/mb_lst`, `c_nav/c_bt` (-90 B); removed `c_look`, `c_mis`, `c_col/c_eye` cyclers, 5 menu items, the `T M` panel line, the fixed `pal` table (-250 B).  New: picker `pk` 178 B, `preview` 32, `a_pick` 70, `set_theme`+`theme_cur` 42, `eff_col/eff_eye` 34, `tmap` 16, enemy names 37, tile/menu/name for the crumble ledge.  No code outside game RAM.  New non-game RAM use: `EPAL` $A8980 (32 B).
`nepatch verify`: 33 verified sites, 3 clear ranges, 11 blocks; `nefloppy selftest`: 5/5 `== patches/*.nep blocks: yes`; floppy release builds (`Nebulus_game_disk.st 419840 B`).

## 5. Gates (raw: `logs/`)
Passed **[obs]** (first run of `e200.py` on the STE title snapshot of this build, `logs/e200_first_run_ste.out`): F10 opens manager; new level tower 0/mission 1/flags 0 and the map palette == theme(1); root menu has Crumble ledge + Level >, no Tower >; Level > items; Colours list = 8 numbered tower names + back, cursor on the current; **EPAL == theme(k) at all 8 highlights (preview)**; back restores; pick 5 -> tower 4 flags 0, map EPAL == theme(5); Enemies list + effective cursor; pick 3 -> flags 3; lists reopen on the current choice; Copy tower list 17 items, M2 T5 pick -> mission 2 tower 4 flags 0 and grid == the original decode; Crumble ledge item writes `$91`; colours 6 + enemies 2 -> playtest: palette, raster, skyline buffer == stock tower 6 (RAM), eye frames == stock design 2, `$3390c` = 5; back in the editor with the pick intact and theme 6; committed record `(2,5,rows,2)` validates.  One FAIL in that run = a wrong expected cursor in my script (fixed in the delivered script); the Save/Load/Edit/Copy tail did not run (missing helper, fixed).
`e201.py` first run (crumble, STE): crop equality NORMAL vs CRUMB, cell cleared + frog fell, conveyors as above; its lower-platform cell failed because the walk crossed the first crumble (script restructured: level CRUMBL).
**Not finished at the time of writing** (scripts delivered; a background chain `chain1` was still running): e200 tail (Save/Load/Edit/Copy/new-level), e201 rerun, `e202.py` (the user's flow on the all-games image: Level > Colours > Playtest AND campaign play, Mega STE), looks15/base8/stock run_look + `check_look.py` (8 schemes + as-tower equalities, RAM + screenshot crops), e180 (odd/12-level/flags), e150, e170 (adapted), floppy boot `fl_ui.py` (adapted), e98 equivalence, Mega STE and ST runs of e200/e201.  **None of these has a result yet; do not read them as passed.**  [INFERENCE] the game-side hooks (`ed_lvl` and the 5 retargeted sites) are byte-identical to the v1.2 candidate, so the earlier look gates still describe them; every editor block changed, so re-gating is required.

## 6. dadprg (`~/Code/dadprg`, edited in place, not committed)
`Level#colour_scheme` / `eye_design` (model + parser struct) and the JSON/cart fields; `Legend` (tile 3 = dotted crumble glyph, kind `crumble`; conveyor labels; tile_for returns 3 only for `$91`); Vue `types/hub.ts`, `utils/nebulus.ts` (`COLOUR_SCHEMES`, `EYE_DESIGNS`, `lookText`); README; tests `ncmp_test` +2 (+legend lines), `compose_test` +1, `hub_browse_test` +1, fixture `crumble.ovl` (+generator).  `bin/rails test`: **217 runs, 1533 assertions, 0 failures, 0 errors**; `npx vue-tsc --build`: clean (exit 0).  `custom_look` facet unchanged (explicit nibbles only; colours picked by the v1.2 editor live in the tower byte).
