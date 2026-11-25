# Stage 4b results (PMWW1Stage04b, 2026-11-23/24): booting and gating the stage-4 patches one at a time on top of the committed default set (c1ae155)

Evidence contract: **[obs]** = raw lines from a file named here; **[INFERENCE]** = reasoning only; failures are listed as failures.
Hatari 2.6.1 (`~/Code/AtariST/hattari/build/src/hatari`), private HOME per run (`<workdir>/home`), work dirs `/tmp/pmww1s4b/*`, one Hatari at a time. Gate logs: `work/runs/s4b_*.txt`.
Method: builds `build/s4b_<name>` = the committed set (`pm_cachecap pm_credit pm_nokeydisk pm_noprot pm_noprot_box pm_tooltip qol_keys qol_keys2 tick_click* tick_head tick_men tick_pass tick_wx`, `/tmp/pmww1s4b/base.txt`)
plus ONE new patch at a time (cumulative). Each patch: cold-boot smoke (title -> map, site bytes, payload / HIGH-fill / cursor checks), its own gate, then `tools/stage04b_regress.sh NAME BUILD`
(STE 1 MB cell `--fill-hi --trace --steps boot,map,rate,saveload,lose,win,round3`, `tools/wwkeys.py`, `tools/wwtt.py gate --quick`).

## 0. Harness changes made in this run
* The prepared edits `/tmp/pmww1s4/patch_wwgate.py` / `patch_wwgate2.py` were still there (not wiped) and are applied to `tools/wwgate.py`: `--psg` (sound ON + strict Hatari + psgcheck at the end of the cell), step `hw`
  (register / flag checks per patch present in the manifest), `--hd DIR [--acsi] [--hd-rlen HEX]` (HD build folder via `tools/wwhd.py`).
* New: `--img` (resident image `$576-$1d2ad` against the hand-over dump at every checkpoint), `--mste-want`, `tools/wwclamp.py`, `tools/wwsnd.py`, `tools/stage04b_regress.sh`, `pmww.PMW(ymwav=...)` (WAV capture path).

## 1. p4_clamp (site `$ed6`, blob `$75c00`)
Smoke (`s4b_smoke_clamp.txt`): `CELL DONE clamp/ste-1.62-1024K: OK (130s)`, sites PASS, `payload@map`, `hi@map PASS pattern / constants: 0 of 290816 bytes changed`.
Own gate `tools/wwclamp.py` (`s4b_clamp_gate.txt`, `s4b_clamp_control.txt`):
```
GATE clamp/ste site $ed6 PASS 4eb900075c004e714e71
GATE clamp/ste normal use: the drop path is never taken PASS 0 hit(s) of $75c1e in 20 s of pointer motion
GATE clamp/ste clamp: the garbage position is dropped, $2edb2 / $2edb4 keep the last good position PASS after the poke ('0x78', '0x46'), before ('0x78', '0x46')
GATE clamp/ste the game runs on: no CPU exception, counter ticking PASS errors [], ticking True
control (build WITHOUT p4_clamp):
GATE base/ste control: the garbage position reaches $2edb2 / $2edb4 (the gate can fail) PASS ('0x500', '0xadfd')
GATE base/ste control: the unclamped garbage hurts the game (bus error, or it stops) PASS errors ['Bus Error', 'Bus Error'], ticking False
```
(the debugger writes `$1d2b2 = $0500, $1d2b4 = $adfd` at the packet-complete branch `$ed6` = what a lost IKBD byte produces).
Regression (`regress_clamp`): `CELL DONE clamp/ste-1.62-1024K: OK (475s)` (59 PASS, 0 FAIL; `world rate = 4.00/s PASS 4.057`; loader trace as stage 4: no skip), `CELL DONE clamp_keys: OK`, `TOOLTIP GATE clamp_tt: 116 lines PASS, 0 FAIL`.

## 2. tt_ptr (site `$e20`, blobs `$75a00` init + `$75a40` hook with the 314-byte pointer block; `LIVE` = `$75bf0`)
Static [obs]: the 314 `dc.w` bytes of the block equal the resident image `$87e-$9b7` byte for byte (python compare of `patches/tt_ptr.s` against `work/dumps/entry576.bin`), the block's end is followed by the original `$9b8` (`btst #1,$fc00.w`), so the appended `rts` replaces it.
The flip routine `$e0e` swaps `[$2ed98]`/`[$2ed9c]` and writes `$ff8201/03`; `$e20` is `move.l d0,$2ed98.l`.  In the TT map view (8 s, probe) the debugger counted `$e0e` 206x, `$e20` 204x, `$e28` 202x, loop top 200x, VBL pointer block `$87e` 587x: the hook runs once per flip.
**Harness findings (not game faults, recorded so nobody repeats them):**
1. `tools/pmww.py goto_st` assumed 2 host px per ST px; on the TT window it is 1:1 and the island click never landed (pointer words alternated `(0,0)` / `(120,40)`). `goto_st` now measures the gain and keeps it.
2. TOS 3.06 on the harness TT boots in **TT medium** (`$ff8262 = $04` at the hand-over, read in `/tmp/pmww1s4b/ttres5`), the game never writes the shifter mode (no reference to `$ff8260/62` in the image) and the picture is tiled 2 x 2 with garbage below
   (`ptrshots_0.png`, seen in two TT screenshots, with `--monitor rgb` and `--monitor vga`, `--fast-boot no`, nvram copied: all the same). Master's TT runs came from an HD image whose boot starts in low resolution. So on the harness TT the pointer gate is meaningless until the
   machine is in ST low: a TEST-ONLY patch (`/tmp/pmww1s4b/patches_low/test_ttlow.s`: `move.w #0,$ffff8262.w` in an init, a `WW_PATCHDIR` copy, never in the tree) puts the TT into low resolution (screenshots 640 x 436, correct picture). **[INFERENCE, release note candidate]** on a real TT the
   game, like the original, runs in whatever resolution the desktop is in; it has to be ST low (320 x 200).
3. The Falcon cannot be judged before `snd_*`: the original sample player (`$1bcb8 movep.l d1,-$720f(a0)` = four YM writes `$ff8800/02/04/06`) bus-errors on a Falcon (`WARN : Bus Error writing at address $ffff8804, PC=$1bcb8`, repeated 32768 times, the map view never comes: probe `/tmp/pmww1s4b/falshots`).
   Master avoids it on the Falcon with the DMA path of `snd_*` (its `fal_ym` only covers the stage-1 intro player, which WW1 does not have). The Falcon pointer cell is therefore run on the snd build (section 9).
Gate `tools/wwptr.py` (boot to the map view, 10 spots, 6 screenshots each; a pointer-sized area compared with the same area with the pointer elsewhere; TT, `--mmu true --cpuclock 32 --monitor vga`, test patch `test_ttlow` in BOTH builds):
```
build/s4c_ttptr_low (clamp + tt_ptr + test_ttlow)  s4b_ptr_tt_stlow.txt:          PTR ttptr_tt_stlow tt TOS 3.06: visible in 60 of 60 screenshots (LIVE $ff)
build/s4c_ctl_low   (clamp + test_ttlow, control)  s4b_ptr_tt_stlow_control.txt:  PTR control_tt_stlow tt TOS 3.06: visible in 46 of 60 screenshots (LIVE $00)
```
(master: 20 of 20 with the patch, fewer without.)  `LIVE` is `$00` on an STE.

## 3. Build tooltip wording (assignment b) [static; gate re-run pending]
WW1's build order `$505a` (called from `$5200`, the Build icon's target click, and `$1629a`) sets the settlement's item word to the table word `$510c + 2 * d1`, `d1 = [posture word + $3c] - 2` (`$259e`): `$10` tank, `$e` plane, `$6` rifle for 3 / 2 / 1 swords (item indexes of the table `$9cd0`: tank 8, plane 7, rifle 3); no wood / iron rules (disassembly `tools/m68dis.py work/dumps/entry576.bin 505a`). The stage-3 text `ploughs, boats; iron: swords` / `pikes; iron: swords` / `rifles, planes; iron: swords, tanks` was master's rule and WRONG here.
`patches/pm_tooltip.s` entry e7 is now `Build (I): a town workshop makes rifles | planes | tanks` (1 / 2 / 3 swords). `wwtt.py check`: `WORDING 29 ids, 203 checks ... 0 problems` (longest still 51). The tooltip gate `wwtt.py gate --quick` runs inside `tools/stage04b_regress.sh` on the `build/s4c_*` builds (they contain the new text).

## 4. STATE AT THE END OF THIS RUN (budget reached) - what is gated, what is not
GATED on the committed set (`c1ae155`): **p4_clamp** (section 1: smoke, own gate + negative control, STE regress cell 59 PASS / 0 FAIL, keys, tooltip 116 PASS). **tt_ptr**: TT pointer 60 / 60 vs control 46 / 60 (section 2, in ST low); STE regress cell `CELL DONE ttptr/ste-1.62-1024K: OK (527s)`, 60 PASS, 0 FAIL (`work/runs/s4b_ttptr_ste.txt`); its keys / tooltip steps were still running when I stopped (`work/runs/s4b_ttptr_keys.txt`, `s4b_ttptr_tt.txt`: read them, they are not yet judged).
NOT booted / not gated: pm_mste, tick_rain, qol_hover(2), p3b_interp / p3b_delta, snd_*, Falcon pointer, hd_*, campaign end (wwend), resident-image check.
Queued unattended chains (started by me, logs when they finish): `/tmp/pmww1s4b/chain3.sh` (regress ttptr, then `chain_mste.sh` = pm_mste cells Mega STE 4 MB `--fill-hi` + `hw` + `rate`, pre-set `$02` control build `build/s4c_mste_pre`, no-pm_mste control, STE / ST / TT `hw`; then regress mste, logs `work/runs/s4b_mste_*.txt`, `s4b_mste_{ste,keys,tt}.txt`) and `/tmp/pmww1s4b/chain4.sh` (`wwend.py final` / `orphan` on `build/s4c_mste` with the image check: `work/runs/s4b_end_*.txt`). They run one Hatari at a time; kill them with `pkill -f chain3.sh; pkill -f chain4.sh` if not wanted.
Builds ready for the next patches (assembled, not run): `build/s4c_{rain,hover,interp,snd}` (cumulative), `build/s4c_hd` (`--hd`, floppy + `hd/` folder); gate tools written, never run: `wwrain.py wwhover.py wwinterp.py wwsnd.py wwhd.py`, `wwgate.py --psg --hd --img` (applied from /tmp, still present).
