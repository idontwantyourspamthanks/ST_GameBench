# Nebulus: "no input at all, per run" (NebInputStall)

Tags: **[obs]** raw tool output of this session (scripts and raw rows in `work/ikbd/`), **[disasm]** read from `work/train/dis_33000_40000.txt` / unpacked START, **[INFERENCE]** not proven.
User report (MiSTer, STE mode, patched HD build from the all-games image): some runs take no input at all (keys, joystick), others are fine; F10 works on a real machine; the unpatched NEBORIG
was never seen failing (few runs); under Hatari with the exact `run_ste.sh` options F9/F10 "did nothing" once.

## 0. Result
**Root cause (reproduced, STOCK bug, present in PP's NEBORIG):** between START's `move.w #$2700,sr` (`S+$35c`) and the game's own `move.w #$2300,sr` (`$38486`, in `sub_0383f6`) the CPU runs with interrupts
masked for ~1.3 s (the depack of NEBEXE.FIC plus the game's init) and then REPLACES the keyboard handler. A single byte the IKBD sends in that window (a key make/break, a joystick packet, a mouse
packet) stays unread in the ACIA data register (RDRF set, IRQ line low). `sub_0383f6` then clears IERB/IPRB (`clr.b $fa09`...) and re-enables GPIP4: the MFP detects that interrupt by an EDGE and the line
never goes high again, so the game handler is **never entered again for the rest of the run**: keys, joystick, F9, F10, D, everything. It is a per-RUN failure (what the user's input did in those 1.3 s),
exactly as described.
Fix: `patches/ni_ikbd.nep` + `.s` (default yes, 2 sites + 90-byte blob at `$7726c`): `drain` at `$38486` (read the ACIA while RDRF/OVRN, then the original SR change) and a watchdog `wd` at the poll's entry `$3853a`
(if the ACIA status shows RDRF/OVRN in main context, run the real handler through a fake exception frame: self-heals any stall, also a lost edge or a stuck in-service bit, within one poll = 40 ms).
Numbers: sections 3 (stall rate), 7 (sites + gates), 8 (window timing), 9 (editor), 12 (open items).

## 1. The game's whole input chain (state machine) [disasm]
There is NO packet parser in the game. The chain is:
```
IKBD -> ACIA $fffc00/02 -> MFP GPIP4 (edge, IERB/IMRB bit 6, vector $118) -> $384fc:
  $384fc move.w d0,-(a7)
  $384fe btst #0,$fc00.w            ; RDRF?            (status read)
  $38504 beq.w $38524               ;   no -> $38524: btst #5 (OVRN) -> read $fc02 once -> $3851a
  $38508 move.b $fc02.w,d0          ; data read (clears RDRF; OVRN only if status was read first)
  $3850c jmp $200                   ; START/Gamex patched these 5 bytes: cmp.b #$c3,d0 (F9 break -> save state, jmp $ffd20)
                                    ;   cmpi.b #$f6,d0 / bcc -> $3851a (HEADER bytes $f6..$ff are DROPPED, nothing is stored)
                                    ;   else jmp $38514
  $38514 move.b d0,$38498.l         ; the ONE "last byte" cell (ours: ni_latch stub1 here, fire latch)
  $3851a move.w (a7)+,d0            ; (ours: ed_overlay hook -> ed_key: F10/key latches RS+42/44, then the same two instructions)
  $3851c bclr #6,$fa11.w            ; MFP in-service bit of GPIP4 (software-EOI mode)
  $38522 rte
```
Readers of the cell: only `sub_03853a` ("poll": `$3853e move.b $38498(pc),d0`; bits 4-6 set = menu/scancode path -> `$3849a`; else bit 7 = fire `$338f0`, bits 0-3 = direction tables), called once per
title/game loop (every 2 VBL) from `$3d6c4/$3d6ae/$3dacc/$3dcf4/$38298/$38604/$38614`, and from the editor's own loops. The trainers' key hook (`$3dcf4`) and the editor's title hook read the same cell.
Consequences for the "parser" questions: (1) a joystick packet `$fe/$ff + data` -> header dropped, data stored (no state); a mouse packet (`$f8-$fb` + dx,dy; in absolute mode `$f7` + 5 bytes) -> header dropped, EVERY
data byte is stored into the cell, so mouse/status bytes can look like joystick/fire (stock behaviour); a dropped byte cannot desynchronise anything: there is no multi-byte state variable to get stuck.
(2) The cell is overwritten by any byte; the poll samples it once per 2 VBL (the reason for ni_latch).
IKBD set-up: `sub_0384ba` (called first by `sub_0383f6`, `$383f6`): `$09 00 00 00 00` (absolute mouse positioning, max 0,0), `$14` (joystick EVENT reporting), then writes `$15` to the **MIDI** ACIA control
`$fffc04` (receive interrupt off, so MIDI can no longer hold the shared GPIP4 line); no `$12` (mouse disable) / `$1a` (joystick disable) / reset (`$80 01`) is sent; the keyboard ACIA control `$fffc00` is never written
(it keeps TOS's `$96`: RIE on). Then `$383fa..`: `clr.b` IMRA/IMRB/IERA/IERB/ACR-timer regs (`$fa13,$fa15,$fa07,$fa09,$fa19,$fa1b,$fa1d`), timer B `$fa21=2`, vectors `$120/$118/$70/$134`, `bset` IERA0/IMRA0/IERB6/IMRB6,
`move.w #$2300,sr` (`$38486`), `bsr.w $33e84`. The game never touches the ACIA again (no IMRA/IERA writes, no `move #$2700` in the game code; grep of the whole `$33000-$40000` dump: the only SR write is `$38486`).
Hazards in the stock handler [disasm]:
1. **The hand-over (this bug).** Nothing drains the ACIA before the handler is installed.
2. The handler reads the data register ONCE per interrupt. On a real 6850 an overrun (two bytes before the first is read) leaves OVRN (and RDRF) set after the single read and the IRQ line stays low: no new
   edge, dead until something reads status+data again. Hatari's ACIA drops the IRQ after one RDR read (`src/acia.c ACIA_Read_RDR`: OVRN is only a status bit there), so Hatari cannot show this one;
   [INFERENCE] it can happen on hardware/FPGA cores when the ISR latency exceeds one byte time (1.28 ms), e.g. under a long masked section. In the game nothing masks interrupts for that long after init
   (the only SR write is `$38486`; level-6 interrupts preempt the level-4 VBL), so this is a weaker hazard than 1.
3. `bclr #6,$fa11` is the only EOI: a path that skips it (none found) would block GPIP4 for good.

## 2. Our patch layer vs the stock chain [disasm + obs]
`ni_latch` (`$38514` -> stub1 `$76d04`: the same store, then `andi.b #$f0,d0 / cmpi.b #$80,d0 / move.w #1,$76d00` and `jmp $3851a`), `ed_overlay` `$3851a` -> `ed_key` (`$7785c`: reads the cell, latches F10 `$44` in RS+42 and
make scancodes in RS+44, then `move.w (a7)+,d0 / bclr #6,$fa11 / rte`), `ni_latch` stub2 in the poll, trainers' hook at `$3dcf4`: none of them touches the ACIA, the MFP or SR, none can skip the `bclr`/`rte`, none
loops. They add ~100 cycles to the ISR path. The editor's disk excursion drains the ACIA itself (editor.md section 2: it had found the same `$fffc00 = $83` dead state there).
The loader adds nothing to the masked window: `NEPATCH` stub at `S+$34c` runs BEFORE the 128-Vsync wait with interrupts on (TOS handler active); core1/core2 run inside the window (measured: window 66 VBL patched vs 65 orig).

## 3. Reproduction in Hatari [obs]
Harness: `work/ikbd/` (`lib.py`, `mksnap.py`, `r2.py` snapshot trials, `r5.py` random trials, `r1/r3/r4/r6/r7/r8.py`, `t1.py`, `j1.py`, `e1.py`, `e_eq.py`, `t30.py`; raw rows `sweep_*.jsonl`, `rand_*.jsonl`, `*.out`).
Builds: `orig` = `originals/NEBULGX` (PP's unpatched = NEBORIG), `patched` = default set + ed_overlay without ni_ikbd, `fixed` = the same + ni_ikbd (`tools/nepatch.py build --only ...`), STE 1 MB TOS 1.62, 8 MHz, ACSI/HDDRIVER image of `tools/nebulus.py`.
Method: a pre-window snapshot of a cold boot (START still in its 128-Vsync wait, VBL ~2480) is restored; a breakpoint at `pc=$1b172` (= `S+$35c`, the `move.w #$2700,sr`) gives time 0; one xdotool key tap (80 ms) is injected at +DT s;
after the title is up a key (`a`) is pressed and the entries of the game's handler (`b pc=$384fc :trace`) are counted: 2 = alive (make + break), 0 = dead.
**Do NOT read the ACIA status with the debugger (`m $fffc00`): Hatari shows the last value a CPU read stored in IoMem (my first probe showed `$83` "stuck" on a healthy game), not the live register. Count handler entries instead.**
Control (no input): alive on all three builds.
```
single space tap at +DT after the SR=$2700 start (DT<=0 = "right at the start"); ISR alive?
DT     orig   patched  fixed
none   alive  alive    alive
<=0    DEAD   DEAD     alive      (0.0 and the <0 rows are the same moment)
0.2    DEAD   DEAD     alive
0.4    DEAD   DEAD     alive
0.6    DEAD   DEAD     alive
0.8    DEAD   DEAD     alive
1.0    DEAD   DEAD     alive
1.2    DEAD   DEAD     alive
1.3    alive  DEAD     alive
1.4    alive  alive    alive
1.5..2.2 alive alive    -
```
= the vulnerable interval is the masked window: orig `$1b172` VBL 2549 -> `$38486` VBL 2614 = **65 VBL = 1.30 s** (`t1_orig.out`), patched 2546 -> 2612 = **66 VBL = 1.32 s** (core1/core2 + blocks add ~1 VBL).
Exact `dist/run_ste.sh` options (no `--fast-boot`, no `--joy1 keys`; `r7.py`, tap at +0.5 s): `orig`: **dead** (0 handler entries for the later key), `fixed`: alive (2 entries).
Mechanism trace (`r6.py`, `--trace acia`, patched, tap at +0.4 s; `r6_patched.out`, log `/tmp/strun-ikbd/log.txt`):
```
acia ikbd clock_rx received rdr=0x39 VBL=2567 HBL=99      make byte arrives, SR=$2700
acia ikbd update irq irq_new=1  VBL=2567 HBL=99           IRQ line goes low (MFP edge recorded, interrupt masked)
acia ikbd clock_rx overrun rsr=0xb9 unread rdr=0x39 VBL=2572   the break byte is lost
(no "read rdr" and no "mfp iack ... new_vec=0x118" in the next 4 s; at VBL 2612 the game's own TX-wait loop `$384e8` reads the status as 0x81/0x83 = RDRF + IRQ set, 1024 times, and never reads the data register)
```
Random trials (`r5.py`, seed 7, the same 24 schedules for every build: 1-3 events of space/a/Return/Right Ctrl (joystick fire through `--joy1 keys`)/Right/mouse moves at uniform random times 0..3 s after the window start):
```
build    trials  dead  with >=1 event in the window (t<=1.3 s)  dead&in-window  alive&in-window  dead&outside
orig       24     11            11                                11                0                0
patched    24     11            11                                11                0                0
fixed      24      0            11                                 0               11                0
```
Stall rate: 11/24 for both stock and patched = the fraction of runs in which the user's input touched the 1.3 s window (here by construction ~46%); 0/24 with ni_ikbd. **The bug is stock: the patch layer neither adds nor removes it.** Recovery: none (the stall lasted to the end of every dead run, 3-4 s observed plus the later key probe; no self-recovery path exists in the code).

## 4. Where our loader's file reads sit relative to the window (wall time, slow media) [disasm + obs]
`NEPATCH.BIN` (Fopen/Fread/Fclose to `$B0000`) and `NEBLEVEL.OVL` (zero-fill + Fread to `$BC000`) are read by the stub that replaces `move.w #$7f,d7` at `S+$34c`, i.e. BEFORE the 128-Vsync wait and BEFORE `S+$35c` (`move.w #$2700,sr`),
with interrupts on and the TOS keyboard handler active (`tools/nepatch.py stub_code`, `START_unpacked` `S+$34c..$35c`). So **none of our file I/O is inside the masked window**; the window contains only CPU work
(LZ depack of NEBEXE.FIC, core1, the game's relocation, core2 = site check + writes + the editor blocks, `sub_03dfe0` init), which is the same speed on a MiSTer (8 MHz FX68K core) as on Hatari. Slow SD/IDE media therefore lengthen the time
before the window (more time for the user to press keys, none of which is lost: the TOS handler is alive), not the window itself. A byte that arrives during those reads is queued by the still-armed MFP and is fine.
The window is ~1.30 s stock, ~1.32 s patched (`r8.py` with the exact `run_ste.sh` options, `r8_*.out`: see section 8). `drain` (`$38486`) runs after ALL loads and after the game's own IKBD command exchange, so it covers everything.
Caveat [INFERENCE]: HDDRIVER's HD driver may mask interrupts during sector transfers on real media; an unread byte then waits for the unmasked moment with the MFP IPR bit kept (IERB stays enabled), so TOS still gets it; only the game's `clr.b $fa09`/`$fa0d` can drop it.

## 5. MiSTer (AtariST_MiSTer RTL, read from github) [obs of the source]
- `rtl/acia.v`: a simple 6850: `irq = cr[7] && rx_data_available || tx...`, a read of the data register clears RDRF **and** OVRN together (so an overrun cannot latch the line by itself, unlike a real 6850 [INFERENCE for real chips]); status reads have no side effect. An unread byte keeps the line low, same as Hatari.
- `rtl/mfp/mfp_srff16.v` + `mfp.v`: "IPR bits are always set on the rising edge of their input", `set & ~setD & mask` with `mask = ier`; a write to IERA/IERB clears the pending bits (`ipr_reset |= ~din`). **Exactly the edge/mask behaviour that makes the hand-over stall: it WILL happen on the core**, the same as Hatari. README: "Some MFP imperfections".
- IKBD = the real firmware on an HD6301 core (`rtl/ikbd/rom/IKBD.ASM`), so the byte stream is the real one; joystick/mouse/keyboard events are fed from the HPS: a USB pad with analog drift or a mouse touched during the load produces exactly the packets that hit the window.
  [INFERENCE: not checked whether the firmware reports the joystick state on `$14`; with the game's own command exchange happening at SR=$2700 before the handler install, such a reply would arrive after `$38486` and be handled.]

## 6. Junk RAM (MiSTer does not clear RAM on a reset) [obs, `j1.py`]
Our assumptions of zero: every blob (`$76c00`, `$76d00`, `$77a00`, and now `$7726c`) is a nepatch "site" whose original (zero) bytes are checked in pass 1: junk -> `NEPF`, nothing applied, STOCK game (fail-safe); the editor blocks are plain copies (junk overwritten);
the editor's state block RS `$77c80..$77cbf` and V are NOT verified and not cleared at boot (V is cleared at each editor entry; the title hook clears rsCamp/rsLvl every poll).
```
j1.py patched all 1 (random bytes over $76b10..$77ec0 before the depack):  marker NEPF, sites 0000, handler entries for a key = 2 (alive), $70 = $382d8: the stock game runs
j1.py patched rs  2 (random bytes over RS+V only):                         marker NEPO, sites 0x15, handler entries = 2 (alive), $70 = $75a32 (= the editor's own VBL: the editor/manager OPENED BY ITSELF at the first title poll, RS+42 junk != 0)
```
So junk RAM never kills the input (the ACIA path is untouched), but (a) a relaunch / warm reset after a patched run finds the previous blobs in RAM -> `NEPF` -> the next run is silently the STOCK game (no credit line on the frog page, no F10/D, no trainers; the credit line is the visible
indicator that the layer applied), and (b) [needs the lead] junk only in RS with zero blobs (practically impossible: it needs random junk that happens to be zero over 4 KB of blobs) would open the editor at boot. Cheap hardening for the editor owner: add RS `$77c80..$77cbf` as a 64-byte zero-verified
site in `ed_overlay.nep` (gen_ed.py) so junk -> NEPF. Not done by me (editor sources are not mine).

## 7. The fix: `patches/ni_ikbd.nep` + `patches/ni_ikbd.s` (default yes) [obs]
Generator `work/ikbd/gen_ikbd.py` (vasm; refuses to write if the blob overlaps a site or block of any other patch). 24 sites in the default set (was 21), blob 90 bytes at `$7726c..$772c6` (the 148-byte gap between the editor's DATA block (ends `$7726c`) and CODE2 (`$77300`);
free ranges of the zone in the default set: `$7726c..$77300` (148), `$779e8..$77a00` (24), small 2-6 byte slivers; nepatch checks site-site overlaps only, blocks are checked among themselves, so the generator checks site-vs-block).
`nefloppy.py` already consumes `ni_ikbd.s` (blob at `$77f00` there; it finds `wd` by the label `\nwd:`: keep the label layout).
| site | original | new | role |
|---|---|---|---|
| `$38486` (8 B) | `46fc2300 6100b9f8` = `move.w #$2300,sr / bsr.w $33e84` | `4ef9 0007726c 4e71` | `drain`: `move.l d0,-(a7)`, up to 16x { RDRF or OVRN set -> read `$fffc02` }, restore d0, the original `move.w #$2300,sr`, `jmp $33e84` (= bsr + rts). Runs once per run (`sub_03dfe0` is called only from `$3db62`), at SR $2700, after the MFP is armed, after ALL loads. |
| `$3853a` (8 B) | `48e7c080 103aff58` = `movem.l d0-d1/a0,-(a7) / move.b $38498(pc),d0` | `4ef9 00077294 4e71` | `wd`: the movem; if `($fffc00 & $21) != 0` (RDRF or OVRN in MAIN context) `heal`: save SR, `ori #$700,sr`, push a fake exception frame (`pea .r(pc)` + `move.w sr,-(a7)`), `jmp $384fc` = the REAL handler (reads the byte, Gamex hook, ni_latch stub, ed_key, `bclr #6,$fa11` = clears a stuck in-service bit, `rte` back to `.r`), restore SR; then `move.b $38498.l,d0`, `jmp $38542`. |
In normal play the status bits are clear and the cost is one status read + `andi` + `beq` per poll (once per 2 VBL). A byte that arrives just before the poll sees the interrupt masked for ~100 cycles and is handled inline; the interrupt that was pending then finds RDRF=0/OVRN=0 and exits through `$38524/$3851a` (harmless).
Isolation (`iso_fwd.jsonl`, `iso_fdr.jsonl`, taps at +0.4 and +1.0 s): the watchdog alone (blob + `$3853a` site, no drain site) heals both, the drain alone prevents both: each half is sufficient, both are shipped.
Gates (all on the `fixed` build = default set + ed_overlay + ni_ikbd):
- stall reproduction: sweep DT 0.0..1.4 s alive at every point (orig dead 0..1.2, patched dead 0..1.3); exact `run_ste.sh` options: alive; random trials 0/24 dead (stock/patched 11/24) - section 3.
- `nepatch.py verify` (default set): `271849 game bytes compared, 0 differ`, 24 sites, every site `dump-orig OK` (`$38486 orig 46fc23006100b9f8`, `$3853a orig 48e7c080103aff58`, `$7726c` zeros).
- cold boots (`work/input/gate_boot.py work/ikbd/build/fixed ste|megaste`, `gate_ste.out`, `gate_megaste.out`): STE 1 MB / TOS 1.62: **NEPO, site count 00 18 (24)**, in tower after 23 s; Mega STE 4 MB / TOS 2.06: **NEPO, 00 18**, in tower after 49 s; hook bytes as before; at runtime (`e1_fixed.out`): `$38486 = 4ef90007726c4e71`, `$3853a = 4ef9000772944e71`, blob `2f00700f0838...`.
- in-tower equivalence (`work/ikbd/e_eq.py ni_ikbd` = e97-style: stock snapshot `own_tower.sav`, the patch applied live at the loop-top poll, scripted input as a function of the level timer through `scripted2.py` + `cmp_sc.py`, enemies on; raw `eq_ikbd.out`):
```
== iq_hook vs iq_stock: 1119 / 1120 loops after timer start (compare first 1117)
loops where the non-player block (creatures, timer, flags, energy, ...) differs at the SAME index: [] (0)
loops where the player vars differ at the same index: [] (0)
creature/timer/energy simulation state differs at the same loop index in 0 of 1117 loops []
framebuffer event 1 differing bytes, rows: (0, None)
```
  (The watchdog's slow path is not taken in normal play, so this is the "no behaviour change" gate; the slow path is exercised by the stall gates. The gate's sensitivity is the one established by NebInput2 for `cmp_sc` (a deliberately different run differs by thousands of bytes, input.md section 8.2); I did not re-run a negative control for this particular patch.)

## 8. What the fix means for the two review questions [obs]
- **Wall-time window, slow media** (lead's question 1): our only file I/O (`NEPATCH.BIN` -> `$B0000`, `NEBLEVEL.OVL` -> `$BC000`, both by the stub at `S+$34c`) happens BEFORE `S+$35c`, with the TOS handler alive (section 4). Measured with the exact `dist/run_ste.sh`
  options (no `--fast-boot`, no `--joy1 keys`; `r8.py patched`): stub call at VBL 2442, window start (`$1b172`) at VBL 2572 = **130 VBL (2.6 s) after the stub call** (the reads + the 128-Vsync settle), then the masked window 2572 -> 2638 (`$38486`) =
  **66 VBL = 1.32 s**. Stock `r8_orig` was not re-timed (parser bug, `r8_orig.out` empty) but the stock window is 65 VBL in the same harness (`t1_orig.out`, VBL 2549 -> 2614). A slower SD/IDE therefore moves this whole block later in time; it cannot lengthen the
  masked window, because the window contains no I/O. `drain` runs at the very end of it (`$38486`), after all loads and after the game's IKBD command exchange, so it covers the whole window on any media; the watchdog then covers anything that arrives later.
- **The editor path** (lead's question 2): covered and gated - section 9.

## 9. The editor path [disasm + obs]
The editor's own loop calls the game's poll: `ed_run` (`patches/ed_editor.s`): `.loop: bsr redraw; .w: cmp.w vFrame(a5),d0 / beq .w ; jsr $3853a.l ; ...` once per editor frame (its VBL `ed_vbl` at `$70`; `$118` is still `$384fc`), and `ed_title` calls `jsr $3853a` on the title; the manager, the edit view and the playtest all run inside that loop
(a playtest returns into the game's loop whose poll is `$3dcf4 -> $3853a`). So the watchdog at the poll entry is executed in every state of the editor; `heal` runs the real handler `$384fc`, which goes through the `$3851a` hook = `ed_key` (F10/shortcut latches), so a healed byte is latched exactly like an interrupt-delivered one.
The editor's own masked sections: `ed_run` entry/exit (a few instructions with `ori #$700`), and the disk excursion `disk_op` (SR $2500/$2700 for 0.5-1 s, MFP block swapped; it re-arms the game MFP with `mfp_set` and then drains the ACIA (`.dr`) before restoring SR: the same bug found and fixed there earlier, editor.md section 2). After that drain a byte can still
arrive before `move.w d1,sr`; its pending bit is kept (IER enabled by `mfp_set`), so it is delivered.
Gate (wedged ACIA while the editor is active): `work/ikbd/e1b.py BUILD` opens the editor with F10, loads `work/ikbd/wedge.bin` (`wedge.s`: mask interrupts, `clr.b $fa09` = IERB 0 so the pending bit is dropped, wait for a byte in the ACIA, `move.b #$40,$fa09`, SR back, `jmp $3853a`) at `$b8000`,
hijacks the editor's next poll call with `r pc=$b8000`, taps a key, then counts entries of `$384fc` and probes a later key:
```
e1b.py patched (control, no ni_ikbd): poll entry $3853a: 48e7c080103aff58 | editor active ($70 = $75a32) | sanity 1 | hijack fired: True
                                     game ISR entries since the wedge: 6 | later key: ISR entries 0 | again: 0 | editor still active: $75a32   <- WEDGED, no recovery
e1b.py fixed:                        poll entry $3853a: 4ef9000772944e71 | editor active ($70 = $75a32) | sanity 2 | hijack fired: True
                                     game ISR entries since the wedge: 4 | later key: ISR entries 2 | again: 2 | editor still active: $75a32   <- HEALED, editor still usable
```
Answer to the lead's review question: **the editor's own loop calls the game's poll `$3853a` once per editor frame (`ed_run`), so the watchdog covers the manager, the edit view and the playtest without touching the editor sources; the wedge test above shows it heals there (and that without ni_ikbd the editor stays dead).**
The editor's `disk_op` excursion already drains the ACIA itself (unchanged).

## 10. Floppy build sites (for NebRelease3) [obs]
`ni_ikbd`'s two hooks are at addresses the floppy's shifted text keeps identical: in `work/floppy/ex/TOPPLER.JMP` (NEBEXE equivalent, relocated) `$38486` = `46fc2300 6100b9f8`, `$3853a` = `48e7c080 103aff58`, the whole handler `$384fc..$3853c`,
`sub_0384ba` (`$384ba`) and `sub_0383f6`'s head are **byte-identical to the PP image** (compare `work/floppy/res/sites_orig_compare.txt` convention; raw check of this session: PP vs floppy at those six ranges all `SAME`).
`tools/nefloppy.py` already generates ni_ikbd for the floppy (blob at `$77f00` because `$7726c..$772d6` holds the TOS-state capture there), remaps the two site targets with its `symmap`, and finds `wd` via the `\nwd:` label: do not reorder/split those labels in `patches/ni_ikbd.s`.
The floppy's masked window has the same shape (START's `$35c..`; the floppy's own START is the same code path) `[INFERENCE: the floppy starter in `nefloppy.py` was not re-measured]`.

## 11. What to ask the user to test on the MiSTer
1. **NEBORIG, forced**: start `NEBORIG\START.TOS`, and from the box-art picture on, keep tapping SPACE (or wiggle the joystick) until the game's title appears, then try Right + fire. Expected with this analysis: the same dead input (the bug is PP's; the credit line is absent, so NEBORIG cannot be confused). If NEBORIG refuses to fail this way, the MiSTer-only factor is elsewhere.
2. **Patched build, same forced test** (tap SPACE all the way through the loader): should now always work. The credit line `v<version> enhanced by dad_prg` on the frog page shows the patch layer applied at all (a relaunch after a previous run on the same MiSTer may show **no** credit line: the blob check fails on the old RAM and the release falls back to the stock game by design - a power cycle / core reload clears it, see section 6).
3. Ask: when it fails, does the title still animate/cycle (game alive), is F9/F10/D dead too (yes, expected), does a key or joystick release ever bring it back (expected: never), which joystick/mouse is connected, and is it a fresh start or a relaunch of the game after another game/run on the same core session?

## 12. Open items
- Title-tap gate (30 F10 taps on each of the three title pages) not finished: the page sampler works (`t30b.out`: pages `$3d5b6` = 0/1/2 cycle, seen in the order 1,2,0), the tally run was starved by host load (title took 124 s to appear, one tap on a page whose word read 0 hit a manager that was still fading). F10 correctness is otherwise covered by the 2 ISR-entry probes, the 24/24-alive random runs and the editor gates above.
- `r8.py` timeline with the exact `run_ste.sh` options: patched `$1b162` VBL 2442 -> `$1b172` (window start) 2572 -> `$38624` 2629 -> `$38486` 2638: window 66 VBL = 1.32 s, and our stub's I/O + the 128-Vsync wait = 130 VBL (2.6 s) BEFORE the window. Orig build not re-timed after the parser fix (`r8_orig.out` empty).
- Equivalence negative control (`ni_ikbd_neg`: poll reads a constant 0) not run: the temporary patch file was removed; `eq_ikbd.out` has no differences at all (0/1117 loops, 0 framebuffer bytes), which is the strongest form of the same result.
- `e1.py` (first editor-wedge attempt, debugger write to `$fffa09`) was inconclusive (control also healed): the Hatari debugger `w` to the MFP did not create the stall; `e1b.py` (snippet with a real `clr.b`) is the valid gate.
- Real 6850 overrun semantics (IRQ stays low after one RDR read) is [INFERENCE]; Hatari does not model it, the MiSTer core clears RDRF+OVRN on one read. The watchdog heals a wedged line either way.
