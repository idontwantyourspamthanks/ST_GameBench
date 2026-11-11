# Midwinter 1 and 2 on the Hatari TT (TOS 3.06, 68030 @ 32 MHz) — floppy and HD image (MWTT, 2026-11-10)

Tags: **[obs]** observed (Hatari 2.6.1, `run_tt.sh` settings: TOS 3.06, 4 MB, `--cpuclock 32`, VGA), **[disasm]** read from disassembly, **[INFERENCE]** not verified.
Covers both games (MW2: same causes, its own addresses in the section "MW2"). Shared code: `patches/cpulib.s` (MW1 and MW2 keep identical copies), `patches/floppy_cpu.s`, `patches/core.s` segment `cpufix` at $B9F00.

## 1. Verdict
| game | medium | before | after |
|---|---|---|---|
| MW1 | floppy (MWA in A, MWB swapped in; with or without the ACSI image) | **black screen**: TOS reset loop (see 2.1) | 3D view, `MWPO`, caches off (`CACR=0`) [obs] |
| MW2 | floppy | stub loads garbage, address error at `$4de10` | Lobos 3D view, `MWPO` [obs] |
| MW1 | HD image (ACSI) | TOS state trashed, bus error (see 3) | 3D view, `MWPO` with **`--mmu true`** [obs] |
| MW2 | HD image | same | Lobos 3D view, `MWPO` with `--mmu true` [obs] |

HD without `--mmu true` **cannot work** (section 3): not our bug; `dist/run_tt.sh` and `midwinter2/tools/play-tt.sh` now pass `--mmu true`.

## 2. Floppy
### 2.1 Cause: the loaders' FDC time-out is a loop count (8 MHz 68000)
- [obs] MW1 MWA on the TT: at the stub's `jmp $3df44` (`$d05e`) RAM `$3DF28` holds sector 138, not stage 2 (sector 558): the seek was aborted. [disasm] stub `sub_d3c0`: `move.l #$40000,d0 / btst.b #5,$fffa01 / beq / subq.l #1,d0 / bne`, on time-out it writes the FDC force-interrupt command `$d0` (`sub_d1f8`) and returns as if all were well. ~1.4 s at 8 MHz, ~0.1-0.3 s on a 68030: shorter than a 55-track seek. The wrong data then crashes the machine; the game resets, TOS's start-up logo loop never ends (VBL vector left at the game's `rte`) = black screen.
- The same driver exists three times (stub, MW1 stage-2, the game), each with four loop-count constants (time-out + `dbra` delays `$180,$100,$20`). Proof [obs]: poking only the stub's time-out (`w $d3c2 $01 0 0 0`) at `pc=$d000` gets MW1 through the stub; poking stage-2's (`$3ef4a`) too reaches the credits.
- MW2: same driver (`$50000` at `$4ddf0`, `dbra` `$60`/`$100`); poking `$4ddf0` alone lets the game start [obs].
### 2.2 Video: TT boots in TT-medium
[obs] The game never sets a resolution (an ST boots in low). TOS 3.06 on VGA leaves `$ff8262 = $04` (TT medium 640x480x4): pictures come out tiled twice. Fix: on a TT (`_MCH` cookie `$0002xxxx`) `clr.b $ffff8262.w` (TOS's own Setscreen byte; Hatari also mirrors `$ff8260` writes to it). Falcon (`_MCH $0003xxxx`) is not touched (not examined).
### 2.3 What was added (all gated on CPU >= 68020; a 68000/68010 only runs `cl_detect`)
- `cl_detect`: 020+ via the index-register scale (a 68000 ignores scale bits; two `lea (0,pc,d0.w*2)` / `(0,pc,d0.w)`, difference 4 = 68000, 3 = 020+), 040/060 via the `_CPU` cookie; no exceptions. `cl_cacheoff`: 020/030 `CACR=$0808`, 040/060 `cpusha bc` + `CACR=0`. Caches stay off for the whole run (as Powermonger/Hunter: DMA is not snooped, loaders overwrite code). `cl_patch`: `{addr.l,size.w,value.l}` table writer.
- Widened: time-out `$40000`/`$50000` -> `$800000`, `dbra` delays x4 (`$0600,$0400,$0080` / MW2 `$0180,$0400`, game `$0600`).
- **MW1**: block at stub `$D7E0` (1147 zero bytes; NOT `$D488..`: that zero zone is the stub's stack, `$d618` downwards, my first version was overwritten), reached by two 6-byte splices: `$D000 lea $d618.l,a7 -> jmp st_entry` and `$D05E jmp $3df44.l -> jmp st_s2` (patches stage-2's four constants, then runs it). The game's four constants (`$11304,$112c4,$110a6,$1133a`) by `cpufix` (`FDCTAB`, floppy only) when the trampoline starts. `CPUFLAG` = `$B2FF4`.
- **MW2**: the stub has 18 free bytes, so the block sits in the **boot sector's** 308 zero bytes (`$CA..`), reached by replacing the boot sector's final `jmp $4d9a6.l` (`$B4`) with `bra.w` + nop; sector word sum restored through the word at `$1FE`. The game's constants (`$27cb0,$27cf2,$27abc,$27c6c`) by `cpufix`.
- HD builds: `cpufix` is just `rts` (`ifnd FLOPPY`). First version read the cookie jar and switched caches off on HD and broke MW2 HD on the TT: HAGA remaps low RAM ($5a0 is not TOS's jar there) and owns CACR.
- STE/ST: MW1 floppy cold boots with `MWPO` on STE TOS 1.62 1 MB (Options + THE TEAM) and ST TOS 1.04 1 MB (Options) with the final zip [obs]. **Not re-run**: Mega STE 4 MB, STE HD, MW2 on ST/STE/Mega STE (the 68000 path is the same few instructions, by construction [INFERENCE]).

## 3. HD image on the TT: PP's HAGA needs the 68030 MMU
- [obs] Without the MMU: after RUNME's stack-phase copy, RAM `$4a2` (BIOS `savptr`) holds PP's code bytes (`60ea4e75`); HAGA's first `Fopen` (`$3f9022`) -> TOS `trap #13` -> `move.w d0,-(a1)` with `a1 = $60ea4e73` = bus error, bombs. PP's block overwrites `$200-$5E7` (text `$498`..) including TOS's variables; `savptr` poked back to `$93a` gets further and then fails elsewhere.
- [disasm] HAGA's hardware detect (`$3f8100`): TOS major 3 -> class 5 (TT), 4 -> Falcon. The service entry (`$3f8fc4`, swap routines `$3f9166`/`$3f9372`) on class 4/5 switches game/TOS low RAM by rewriting a PMMU page descriptor (`$3f8850`/`$3f885c`, `pflusha` = `dc.w $f000,$2400`) and sets CACR from RUNME's parameter (`movec d7,cacr`); other classes copy the low-RAM words. So on a TT the game's `$0-$7FFF` lives at physical `$100000/$200000`, TOS's stays at 0. Hatari's TT runs without MMU emulation by default -> no remap -> TOS trashed. The user's GEMDOS-folder boot works because Hatari's GEMDOS emulation bypasses TOS's trap #13.
- [obs] `--mmu true`: MW1 HD reaches the options screen and the 3D view with the shipped PP original-style flow, with our patches `MWPO` (20 fps at 32 MHz, `CACR=0` set by HAGA). MW2 HD likewise reaches the Lobos 3D view.
- Not done: a HAGA patch that makes the no-MMU Hatari work (would replace PP's class-5 path, unverified on real TT). Real TT hardware has the MMU [INFERENCE: PP's path untested by me on hardware].

## 4. Tools / repro
`mw1patch.py build --floppy`, `mw2patch.py build --floppy`, `package.sh`, `tools/make_hd_image.py`. Test drivers were throwaway (`/tmp/mwtt`): Hatari TT `--monitor vga --cpuclock 32 [--mmu true] [--acsi IMG --gemdos-drive skip] --disk-a ...`; HD image autorun via a `DESKTOP.INF` line `#Z 01 C:\MIDWINTR\RUNME.TOS@` (do not use mw2harness's `--auto` with ACSI: the harness GEMDOS drive takes C:); TT mouse home = ST-screenshot (107,67).
## 5. Not done
Falcon; Mega STE 4 MB and STE HD regression re-runs; real hardware; a no-MMU HD fix; MW2 on ST/STE/Mega STE after the change; PM/Hunter behaviour under `--mmu true` (run_tt.sh now sets it for the whole image) not checked.
