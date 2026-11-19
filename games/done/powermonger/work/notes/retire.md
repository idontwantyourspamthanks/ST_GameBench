# Powermonger: Options -> Game -> Retire = black screen, hang (PMRetire, 2026-11-18/19)

Tags: **[obs]** raw tool output (kept in `work/retire/`, `work/retire/runs/*.txt`); **[INFERENCE]** not run.
Everything in Hatari 2.6.1; real hardware not run.

## 0. Result
* **Cause: our payload ($B8000..), not the original and not any single patch.** The game's resource loader (`$df52`) caches every resource it loads in RAM with a bump allocator (cursor `[$2c1ba]`, starts at `$80000`, **no upper bound**). At the map view the cursor is `$b74f4`; Retire loads the LOSE picture (resource 14, `$7d00` B) and caches it at `$b74f4..$bf1f4`, **over core, `tick_*`, `p3b_*`, `tt_ptr` and the start of `p4_*`** (payload `$B8000-$DC117`). The next VBL / loop pass runs trampled code, bus errors at `$fffff23e` follow and the CPU parks in `stop #$ffff`. The win picture (resource 15) goes the same way.
* **Fix: new default patch `pm_cachecap`** (`patches/pm_cachecap.s`, site `$e000`, 6 B -> `jsr $dc100`, 24 B blob): a resource that would end above `$b8000` is not cached (the game's own "no cache" path, as on a 512 KB machine). The picture is already in its destination buffer; the next use reads it from disk again.
* Gate: `tools/pmretire.py` (cold boot -> level -> Option -> GAME -> RETIRE -> picture stable and non-black -> payload blobs intact -> click -> option screen -> START NEW CONQUEST -> map view, twice; `--win`, `--final`, `--img`, `--hd [--acsi]`). Fixed build passes on Mega STE (floppy, HD ACSI), STE, ST; the unfixed build fails everywhere it was run.

## 1. Repro recipe [obs]
`python3 tools/pmpatch.py build --floppy --hd --out build/retire/v_def --only <default set minus pm_cachecap>` (or an older build), then
`python3 tools/pmretire.py --disk build/retire/v_def/floppy/powermonger.st --manifest build/retire/v_def/floppy.json --machine megaste --tos 2.06 --mem 4096`
(`CELL DONE ... FAIL`; cold boot 148 s). By hand: cold boot, `boot_to_game()`, click the Option symbol (ST px 70,137; it is the first icon of the command panel; key `O` also), the GAME button, RETIRE (the panel slides in; `find_btn` refs `work/ref/pm_btn_game.png`, `pm_btn_retire.png`, git-ignored like all refs: crops of the 832x588 screenshot, 32x14 and 50x14 px, text only). `--snap OUT.sav` saves a memstate with the Retire menu open (restore with `PM(snapshot=...)`; snapshots hold the code of the build that made them). First repro: patched floppy, Mega STE TOS 2.06 4 MB, black on the first click, same from the snapshot every time.
Stuck machine [obs, `r` after 25 s]: `0000112a 4e72 ffff stop #$ffff`, `SR=A71F` (T1, S, IM=7, STP=1), `A7=ISP=$112a`, `D0=$0000DF92`, vector `$8` = `$112a`, screen black. In the clean RAM `$112a` is `42b9 0002c1ba 4e73` (`clr.l $2c1ba; rte`, the game's RAM-probe bus error handler, `$110e-$1128`); at the stuck state it holds `4e72 ffff f23e 4e73 0612 0000 1132` = a bus-error frame written over it. Hatari log: `WARN : Bus Error reading at address $fffff23e, PC=$fffff23e addr_e3=12aa op_e3=4efb` then `4096 repeats of: ... PC=$fffff23e`. `4efb` = `jmp $12ac(pc,d0.w)`, the VBL handler's jump table (`$12a8`); `$12ac + $FFFFDF92 = $FFFFF23E`, i.e. the table index byte `[$1c48f]` and other game data were already garbage. Seconds earlier (4-6 s after the click) the CPU sat in TOS's `vsync` wait `$e00d28 cmp.l $466,d0 / beq` [obs, not explained further]. Hatari halts with the "double bus error" dialog on ST / TT (the harness then gets no screenshot).
Other machines: ST TOS 1.04 and TT TOS 3.06: "CPU halted" (cells report `no screenshot`), STE TOS 1.62: FAIL as Mega STE.

## 2. Original or patch? [obs, Mega STE TOS 2.06 4 MB cold boot of the floppy build unless noted]
Variants = default set minus the named patches, **without** `pm_cachecap` (`work/retire/runs/megaste_floppy_*.txt`; "blobs differ" = how many patch blobs' first 16 B no longer equal the build after the picture).
| build | result | blobs differ after Retire |
|---|---|---|
| original `disks/protected.st` | **OK** (defeated picture, back to options, 2nd level) | - |
| default set (v1.0) | **FAIL** (black, `stop` at `$112a`) | 12: tick_head/pass/men/rain, p3b_interp/delta, p4_clamp, p4_ptr_a/b, p4_spr, tt_ptr x2 |
| minus `tick_*` | FAIL | 8 (p3b, p4, tt_ptr) |
| minus `p4_*` | FAIL | 8 (tick, p3b, tt_ptr) |
| minus `p7_triple_*` | FAIL | (cell run; log in `megaste_floppy_v_nop72.txt`) 12 |
| minus `qol_*` | FAIL | 13 |
| minus `snd_*` | FAIL | 12 |
| minus all patches whose blobs lie in `$b74f4..$bf1f3` (`tick_*`, `p3b_*`, `p4_*`, `tt_ptr`) | **OK** (17 blobs intact, 2 rounds) | 0 |
| default **plus `pm_cachecap`** | **OK** (2 rounds, 31 blobs intact) | 0 |
Reading: dropping any ONE group does not help, dropping exactly the groups whose code sits in the overwritten range does, and the set of blobs that differ is exactly the static overlap list. `p7_triple_*` (the first suspect: C = `$70000` is where the picture is decompressed because `[$2df78]` = C) is not the cause: its blobs are above `$bf1f4` and stay intact; `tick_*`, `tick_rain`, `qol_*`, `pm_intro_*`, `snd_*` (win/lose music), pointer patches, `p4_clamp`, credit are all innocent individually.
Other machines: STE TOS 1.62 1 MB: original OK, default FAIL, with cap OK. ST TOS 1.04 1 MB: with cap OK (unfixed: halted dialog). HD `--acsi` Mega STE: with cap OK.

## 3. Root cause, evidence [obs]
* `$110e-$1128` (stage 2 start): `lea $80000,a0; move.l a0,$2c1ba; move.w #$3039,(a0)`; `$1132 cmpi.w #$3039,(a0)` else `clr.l $2c1ba` (512 KB: no RAM there -> cursor 0 -> no cache).
* `$df52` (resource loader): after a disk load + decompress `$dfe8-$e032`: `tst.w $e03e` (cache on) / `movea.l $2c1ba,a1` (`$e000`) / `cmpa.l #0,a1` / `beq` / copy `d2` bytes (`$e02c`, size = `$e084[res]`) / `e040[res] = a1` / `move.l a1,$2c1ba` (`$e032`). Only two accesses to the cursor exist (`m68dis --xref 2c1ba`). No bound check.
* Retire: `$d2c8`: `cmpi.w #4,$57fce` (4 = won): lose -> `$1a5b2` (`df52(14)`), won -> `$1a4da` (`df52(15)`; last island `$2df6e = 4 & $580a4 = $c2` -> `$1a486` -> `df52(12)`, `df52(13)`, 73 KB).
* Cache table (`work/retire/cache_tables.txt`): at the Retire menu, original: cursor `$b74f4`, cached 10 `$80000`, 11 `$97c00`, 1 `$a7af4`, 8 `$af7f4`; 8 s after Retire: cursor `$bf1f4`, resource 14 at `$b74f4` size `$7d00`. A change watch on `$b8002` in the ORIGINAL hits in `$e02c move.b (a0)+,(a1)+` with `A1=$b8004, A0=$1d210, A2=$24400` (the original also writes there, it just has nothing there). In the patched run the copy loop is live at `A0=$7575B A1=$BCC4F` (source = C `$70000`) when the payload is overwritten.
* RAM diff after Retire (pmretire, first 16 B of each blob) gives exactly the 12 blobs above (table, section 2).
* The earlier free-RAM proofs (`triple.md` s.2, `loading.md`) covered boot, map view, get_men, battle, save, load only: none loads a first-time resource, so the cache cursor never moved.

## 4. Fix [obs live + cold boots]
`patches/pm_cachecap.s`: `$e000 movea.l $2c1ba.l,a1` -> `jsr $dc100.l`; hook: load cursor, `move.l a1,d0; beq.s ret; add.l d2,d0; cmp.l #$b8000,d0; bls.s ret; suba.l a1,a1; ret: rts` (d2 = resource size, d0 is reloaded at `$e00e`, a1 = 0 makes the existing `cmpa.l #0,a1 / beq $e038` skip the copy). Blob range `$DC100-$DC1FF` added to `EXTRA_RANGES` in `pmpatch.py` (inside p6_'s range, HD overlay window, restored from PMLATE.DAT: +32 B). Live test first: the 24 bytes poked into the unfixed Mega STE snapshot -> defeated picture, cursor stays `$b74f4`, click -> option screen. Cost: the win / lose / end pictures are loaded from disk every time (not cached, as on 512 KB machines); resources 10/11/1/8 are cached as before.
`pmpatch.py` / `play.sh`: the HD ACSI path pointed at `games/hunter/tools` (moved to `games/done/hunter`): fixed.

## 5. Gates / results with the fix [obs, `work/retire/runs/`]
| cell | result |
|---|---|
| Mega STE floppy, LOSE, 2 rounds (retire -> picture -> click -> options -> new conquest -> map view -> retire again) | OK x2 (`megaste_floppy_v_fix*.txt`), cursor stays `$b74f4`, 31 blobs intact |
| STE 1 MB floppy | OK; ST 1 MB floppy OK; HD `--acsi` Mega STE OK |
| WIN on Mega STE (balance forced at `$d2d8`) | the victory picture ("After a glorious victory you must go on to conquer the whole world", 14 colours) shows and is stable with the fix, payload intact; on the original too. The first script version then clicked START NEW CONQUEST into the game's "delete all conquered lands" dialog and stopped; the script now answers YES (re-runs below) |
| unfixed builds | FAIL: Mega STE x3, STE; ST / TT halted dialog |
Cold-boot gates of `combined.md` (pointer / keys / hover / fps / pixel / state) are unaffected by construction (one hook in the resource loader that none of their paths reaches); `pmcombined.py` SITES now includes `cachecap`. Not re-run in full [INFERENCE: unchanged].

## 6. Open / not done
* Queued but not finished when this was written (see `work/retire/runs/*.txt`, `CELL DONE` lines): all-games image run (`--img`; needs `--fast-boot no` and no GEMDOS dir, else HDDRIVER halts the Mega STE: a harness trap), WIN re-runs with the new script (Mega STE, STE, HD), TT / Falcon cells, `--final` (ending pictures, never executed; same loader, so the cap applies [INFERENCE]).
* The user's drive image must be rebuilt for the fix (lead). `work/ref/pm_btn_game.png`, `pm_btn_retire.png` are git-ignored (regenerate from a screenshot of the Option panel).
* Real hardware / MiSTer: not run. A win on the MiSTer is the same path (section 3).

## 7. Release gates (PMRelease, 2026-11-19): all of section 6's open items closed
TT / Falcon cells OK (v_fix), win and the last island's ending pictures run through (`pmload.py --seq lose,win,lose,lose`, `--seq final`), the all-games image cell is part of the final gate, full cold-boot gates / fps, load times, free-RAM pattern: `work/notes/release.md`. `pmretire.py`'s win round 2 failure on Mega STE / HD was a harness effect (the click on the picture pressed START NEW CONQUEST of the next screen), `release.md` section 7. Released as v1.1.
