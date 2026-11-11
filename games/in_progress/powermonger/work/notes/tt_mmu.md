# Powermonger on the TT with the PMMU on (`dist/run_tt.sh --mmu true`): "double bus error" at once (TTMMU, 2026-11-10)

Tags: **[obs]** raw tool output (Hatari 2.6.1; scratch drivers `/tmp/ttmmu/*.py`, not kept; harness `tools/pmtt.py` for the HD image), **[disasm]** read from disassembly, **[INFERENCE]** not run.

## 1. Cause [obs]
* User report: HD image, TT TOS 3.06, `--mmu true`, P at PMBOOT: "Detected double bus/address error => CPU halted" at once; the same without `--mmu` works (confirmed by the user, and by PMTT's runs in tt.md).
* Reproduced with `pmtt.TT(extra=["--mmu","true","--trace","cpu_exception"])` on the shipped image: the first bus error is `Bus error reading at address $1cf90000 PC=$50e` (`$50e` = the stage-0 stub's copy loop `move.b (a2)+,(a1)+` at `$508..$512`, text `$66..$71` in loading.md section 1.1), then TOS's own handler dies at `$e012b8` and Hatari halts.
* Why the *read* from the program text (`a2` = `$17558` + n, plain low RAM) goes to `$1cf90000`: with the MMU on, TOS 3.06 translates every access through tables **in low RAM**. Hatari's debugger `r` shows the MMU registers; at `pc = $508` (breakpoint `pc = $508 && ($508).w = $203c`):
  `CRP: 8000000200000700  SRP: 0  TT0: 017E8107  TT1: 807E8507  TC: 80F04445`
  = root table at **`$700`** (short format, 16 entries), TC.E = 1, page size 32 KB (PS = $F), TIA/TIB/TIC/TID = 4/4/4/5. TT0 = `$01-$7F` transparent, TT1 = `$80-$FF` transparent + cache inhibit (the I/O at `$FFFFxxxx`).
* The tables (`m $700 256`) [obs]: root `$700..$73F`, B tables `$740` / `$780`, C table `$7C0..$7FF`. `$00000000-$00FFFFFF` is the **identity** map (C table `$7C0`: 1 MB pages `$000000..$d00000`, `$e00000` ROM, `$f00000` I/O with the CI bit `$59`); `$F0000000-$FEFFFFFF` alias to `$00000000..`, the rest is 16 MB / 256 MB identity pages. TOS keeps them in `$700..$7FF`.
* The game's stage 0 copies its 286 KB image down to `$514`, which runs over `$700..$7FF` after 0x1EC bytes; the source pointer reaches the next 32 KB page at `$18000` a few hundred bytes later, the ATC misses, the table walk reads the overwritten root/B/C tables and returns a garbage physical address (`$1cf90000`). Nothing in the game, in `core.s` or in `hd_core.s` is "wrong" in itself: TOS 3.x's PMMU tables are simply inside the region the game takes over (it also overwrites the vector table at `$0..$7FF` with its `rte` stubs, which is why TOS cannot be resumed anyway; the HD build's TOS-region swap R/S keeps TOS's *code state*, it does not need the tables).
* Falcon TOS 4.04 has the same layout [obs, read after the fix, so TC.E is already 0 there]: `CRP 8000000200000700`, `TT0 017E8107`, `TT1 807E8507`, `TC 00F04445` (the same values as the TT), and the build **without** the fix (`build/dist_build/floppy/powermonger.st`, 15:32) on a Falcon with `--mmu true` never gets to stage 2 (`$10a6` = garbage `$10b2`, no screenshot afterwards).

## 2. Fix (`patches/core.s`, `cacroff`, 68020/030 branch only)
After the CACR = `$0808` write (caches off, section 9 of loading.md) the 020/030 path now also switches the PMMU translation off:
```
        moveq   #2,d1                   ; a line F from here on ends the routine
        subq.l  #4,a7
        dc.w    $f017,$4200             ; pmove tc,(a7)
        bclr    #7,(a7)                 ; TC.E = 0
        dc.w    $f017,$4000             ; pmove (a7),tc
        addq.l  #4,a7
        dc.w    $f000,$2400             ; pflusha
```
* Why switching off is right: TOS's map of `$0..$FFFFFF` is the identity (section 1), everything above is TT0/TT1 transparent (the `$FFFFxxxx` I/O of `move.w x,$8240.w` etc.), so with TC.E = 0 the game sees exactly the address space it used with the PMMU on (and the one it always saw with `--mmu false`). The cache-inhibit bit TOS puts on the I/O page only matters with the data cache, which is already off for the whole run (`cacroff`; DMA is not snooped anyway). TT0/TT1/CRP are left alone.
* Done in `init` (supervisor, before WAR.PRG ran an instruction of its own, after `uinit`'s GEMDOS calls, which use TOS with the MMU still on). The HD build's `tos_in`/`tos_out` exchange of TOS's low RAM then runs with translation off, which is the no-MMU configuration of tt.md; GEMDOS/HDDRIVER need nothing from the tables (observed: HD loads, SPRITE40.DAT, saves via `hd_sector` as before).
* Gating: the code sits in `cacroff`'s `.ctrap` branch, which a 68000/68010 never reaches (they take `.cdone` straight from the `movec` illegal instruction: unchanged path, ST/STE/Mega STE identical). A 68040/060 does not reach it either (`cpusha` works there; its MMU is a different one and untouched). The `pmove` itself runs under the existing temporary line-F handler: on a 68020 without a 68851 and on a Hatari 030 without `--mmu true` a line F ends the routine (`d1 = 2` -> `.cdone`, stack reset by `a2`); `cmpi.w #2,d1` in `.ctrap` is the guard against looping. The entry segment grew 282 -> 310 B (no addresses moved; `HOOK1 = $B8140`).
* Not done / not needed: relocating the tables (TOS 3.x would have to be told), PP's HAGA approach (Midwinter's `tt.md`: it *uses* the PMMU to swap low RAM; we do not need to).

## 3. Gates [obs] (`/tmp/ttmmu/gate.py` over `pmtt.TT` / `pmpatch.make_pm`; WAV via the `recsound` shortcut over the whole run; mouse moved at the end)
Builds: `pmpatch.py build --out build/mmu` of the working tree (with the other agents' defaults), image = copy of the dist VHD with `POWERMON\WAR.PRG`, `PMLATE.DAT`, `DATA\SPRITE40.DAT` replaced (`mcopy -i ...@@1024`; `make_hd_image.py` not run).
| machine | build | result |
|---|---|---|
| TT 3.06 4 MB 32 MHz VGA **`--mmu true`** (status bar `32MHz/030(CED)/68882/MMU`) | HD image, PMBOOT -> P | map view, `PMPO`, `FLAGS 3`, arrow visible and follows the mouse, `CACR = 0`, **`TC: 00F04445` (E = 0)**, WAV rms 2065 / peak 17309 |
| same | floppy | map view, `PMPO`, arrow, `TC 00F04445`, WAV rms 1588 / peak 17325 |
| TT `--mmu false` | HD / floppy | map view, `PMPO`, WAV rms 2056 / 1592 |
| Falcon 4.04 4 MB 16 MHz `--mmu true` | floppy | map view (driven by RAM markers, the gate screenshots are TT/ST geometry), `PMPO`, arrow, `TC 00F04445`, WAV rms 171 / peak 13801 |
| ST 1.04 1 MB | floppy | map view, `PMPO`, `FLAGS 6`, WAV rms 1021 |
| STE 1.62 1 MB | floppy | map view, `PMPO`, `FLAGS 3`, WAV rms 1356 |
| Mega STE 2.06 4 MB | floppy | map view, `PMPO`, `FLAGS 3`, WAV rms 1348 |
Before the fix, the same HD image with `--mmu true` crashed as in section 1 (first run of this note).

## 4. Hunter
Hunter needs no change: HD (ACSI + HDDRIVER) and floppy builds reach the 3D view on a TT with `--mmu true` (details in `games/in_progress/hunter/work/notes/ttfalcon.md`).

## 5. Not done
Real hardware; Falcon HD (not testable, see Hunter's ttfalcon.md); 68040/060 (their MMU is not handled; not reachable in Hatari here); the dist `.img`/`.vhd` is NOT rebuilt (`make_hd_image.py` is the lead's); `tools/package.sh` for Powermonger left to PMIntegrate so the md5s are taken once, after this change.
