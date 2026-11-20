# v1.6: the real-floppy fix and its gates (2026-11-19)

Follow-up of `realfloppy.md` (the investigation of the downloader's v1.4/v1.5 report: STe and Mega STe, real floppies written with DOS and makedisk,
"module music starts playing, but no disc activity anymore, even with the graphics disk. It doesn't freeze"). Everything here ran in Hatari
2.6.1-devel (`~/Code/AtariST/hattari/build/src/hatari`), private HOME `/tmp/mw2f/home`, `--fastfdc no --trace fdc`, one instance at a time. **Nothing ran on a real
drive, a real STE or a real Mega STE.** Labels: **[MEASURED]** raw lines under `work/floppy16/out/` (the scratch traces in `/tmp/mw2f/` are RAM and gone after a reboot),
**[SOURCE]** read in the disassembly, **[INFERENCE]** not proven.

Note on the report: "module music" exists only in v1.5 (the Amiga `asn_*` patches); v1.4 plays the YM tune. If the downloader's disks were v1.4, "music" was
the YM title tune. Either way the failure mechanism below hits v1.5 as well (section 2).

## 1. What changed

| # | Change | Where | Bytes |
|---|---|---|---|
| 1 | **Head parking**: stage 1 ends with the stub's own FDC restore (`bsr.w $4DCB8`: `$ff8606 = $80`, cmd `$05` = restore, h=0 V=1 r=12 ms, waited by the stub's `sub_04ddea`) after loading the payload; the game's first `restore` then starts at TR 0 / track 0 (v1.4: track 79, v1.5: 46, original: 71) | `STAGE1_SRC` in `tools/mw2patch.py`, FFA `$4DDAA` (36 of 64 dead bytes) | +4 |
| 2 | **FDC time-out x2 on 68000/68010**: `cpufix` (floppy only) writes `$000A0000` over `$27CB0` (`move.l #$50000,d0` of `sub_027caa`) = 4.4 s at 8 MHz, 2.2 s at 16 MHz. 68020+ keeps its x16 `fdctab` value (`$800000`) | `patches/core.s` `fdctab68` | 10 |
| 3 | **One drive (`_nflops` = `$4A6.w` = 1)**: `eori.w #6,$27D34` (`$28B44`, the drive A/B toggle of the identity check `sub_028B20`) -> `eori.w #0`, and `moveq #1,d0` (`$28B24`: two attempts) -> `moveq #0,d0`: a failed check shows the black prompt after ONE read of drive A; no drive-B probe. Two drives: no byte changed | `patches/core.s` `nodrb` | 20 |
| 4 | `.msa` copies of all four disks (uncompressed MSA), `WRITING_DISKS.TXT`, README text, deterministic zips (fixed member order/times), deterministic HD zip too | `tools/mw2patch.py` (`st_to_msa`/`msa_to_st`), `tools/package.sh`, `patches/*.TXT` | |

`cpufix` is now 256 of 256 bytes ([SOURCE] `core_segments`). FFB/FFC sector 0 and everything else on FFB..FFD are byte-identical to v1.5.

All other waits of the game's FDC driver (**checked, nothing else changed**) [SOURCE, `tools/m68dis.py work/dumps/ram_boot_fl1mb.bin 27a4e..27d38`]: every command (restore `$27A38`, seek `$27A4E`, step in `$27A86`, read `$27B12` ... write `$27AC4`) ends in
`sub_027caa`, the one wait with a time-out (`btst #5,$fffa01` loop of `$50000` rounds; on expiry `sub_027bd6` + force interrupt `$D4` `sub_027ab2`). The other loops are
`sub_027C6A` (read: a `dbra` settle, then GPIP poll ended by the DMA address reaching the end: no time-out), `sub_027cd2` (motor-off poll before a deselect, `$2710` status reads: it ends early on a fast CPU and then the deselect just goes ahead), and three `dbra` settle delays between FDC register accesses (`$27CF0`, `$27ABA`, `$27C6A`; 120 us / 160 us / 190 us at 8 MHz, still above the 1772's register-access gap at 16 MHz). Only `sub_027caa` is shorter than a legitimate command at 16 MHz. The stub's own copy of the wait (`$4DDEE`) is
left alone on 68000: its longest command in all traces (the restore from track 71, 0.87 s with the motor running) is inside 1.08 s, and a cut stub command only repeats the file (the loader retries forever on a checksum mismatch).

## 2. Gate (a): the game's first restore (Hatari `--fastfdc no --trace fdc`, `work/floppy16/bootgate.py`, parser `fdctrace.py`)

The parser reads `fdc type I restore ... tr= head_track= VBL= video_cyc= pc=27c4e` (the game's FDC command write), the next `complete command` or `type IV force int`, and converts VBL/video_cyc to seconds with the frame length taken from the index pulses (50.1 Hz STE, 60.0 Hz Mega STE; the CPU clock multiplier from the index spacing). Verified against the realfloppy numbers: original 2.000 s (2.006), v1.5 STE 1.667 s (1.671), v1.4 STE cut 2.176 s (2.182), Mega STE 16 MHz v1.4 0.971 s (0.97).
Gate PASS = the first game restore starts parked (TR 0, head 0) and completes within 75 % of the time-out in effect (2.18 s stock, 4.35 s v1.6, both / CPU multiplier), and NO game type I command in the whole boot-to-prompt trace is cut by the game's force interrupt.

```
=== g_ste8_v16 (expected PASS)
frame 313 lines = 50.1 Hz
first game restore starts at tr=0x0 head_track=0x0 (PARKED); ends complete after 1.109 s = 25 % of the 4.35 s time-out in effect (v1.6 wait, CPU x1)
game type I commands cut by the force interrupt, whole run: 0 of 15
GATE first-restore g_ste8_v16: PASS (parked=True completed=True margin<=75%=True cuts=0)
RESULT g_ste8_v16: PASS (as expected)
=== g_mste8_v16 (expected PASS)
frame 261 lines = 60.0 Hz
first game restore starts at tr=0x0 head_track=0x0 (PARKED); ends complete after 0.022 s = 1 % of the 4.35 s time-out in effect (v1.6 wait, CPU x1)
game type I commands cut by the force interrupt, whole run: 0 of 15
GATE first-restore g_mste8_v16: PASS (parked=True completed=True margin<=75%=True cuts=0)
RESULT g_mste8_v16: PASS (as expected)
=== g_mste16_v16 (expected PASS)
frame 261 lines = 60.0 Hz
first game restore starts at tr=0x0 head_track=0x0 (PARKED); ends complete after 0.058 s = 3 % of the 2.18 s time-out in effect (v1.6 wait, CPU x2)
game type I commands cut by the force interrupt, whole run: 0 of 15
GATE first-restore g_mste16_v16: PASS (parked=True completed=True margin<=75%=True cuts=0)
RESULT g_mste16_v16: PASS (as expected)
=== g_ste8_v14 (expected FAIL)
frame 313 lines = 50.1 Hz
first game restore starts at tr=0x4f head_track=0x4f (not parked); ends complete after 2.133 s = 98 % of the 2.18 s time-out in effect (stock wait, CPU x1)
game type I commands cut by the force interrupt, whole run: 0 of 15
GATE first-restore g_ste8_v14: FAIL (parked=False completed=True margin<=75%=False cuts=0)
RESULT g_ste8_v14: FAIL (as expected)
=== g_mste16_v14 (expected FAIL)
frame 261 lines = 60.0 Hz
first game restore starts at tr=0x4f head_track=0x4f (not parked); ends complete after 0.980 s = 90 % of the 1.09 s time-out in effect (stock wait, CPU x2)
game type I commands cut by the force interrupt, whole run: 1 of 15
  CUT: fdc type I restore spinup=on verify=on steprate_ms=12 drive=0 tr=0x8 head_track=0x8 | ends: FORCE-INT after 1.078 s (VBL 3021 -> 3085, x2 CPU)
GATE first-restore g_mste16_v14: FAIL (parked=False completed=True margin<=75%=False cuts=1)
RESULT g_mste16_v14: FAIL (as expected)
=== g_mste16_nowait (expected FAIL)
frame 261 lines = 60.0 Hz
first game restore starts at tr=0x0 head_track=0x0 (PARKED); ends complete after 0.059 s = 5 % of the 1.09 s time-out in effect (stock wait, CPU x2)
game type I commands cut by the force interrupt, whole run: 1 of 15
  CUT: fdc type I restore spinup=on verify=on steprate_ms=12 drive=0 tr=0x8 head_track=0x8 | ends: FORCE-INT after 1.296 s (VBL 3887 -> 3965, x2 CPU)
GATE first-restore g_mste16_nowait: FAIL (parked=True completed=True margin<=75%=True cuts=1)
RESULT g_mste16_nowait: FAIL (as expected)
=== g_ste8_v15 (expected info)
frame 313 lines = 50.1 Hz
first game restore starts at tr=0x2e head_track=0x2e (not parked); ends complete after 1.635 s = 75 % of the 2.18 s time-out in effect (stock wait, CPU x1)
game type I commands cut by the force interrupt, whole run: 0 of 15
GATE first-restore g_ste8_v15: FAIL (parked=False completed=True margin<=75%=False cuts=0)
RESULT g_ste8_v15: FAIL
=== g_mste16_v15 (expected info)
frame 261 lines = 60.0 Hz
first game restore starts at tr=0x2e head_track=0x2e (not parked); ends FORCE-INT after 1.119 s = 103 % of the 1.09 s time-out in effect (stock wait, CPU x2)
game type I commands cut by the force interrupt, whole run: 3 of 4
  CUT: fdc type I restore spinup=on verify=on steprate_ms=12 drive=0 tr=0x2e head_track=0x2e | ends: FORCE-INT after 1.119 s (VBL 3690 -> 3757, x2 CPU)
  CUT: fdc type I restore spinup=on verify=on steprate_ms=12 drive=1 tr=0x0 head_track=0x0 | ends: FORCE-INT after 1.292 s (VBL 3793 -> 3871, x2 CPU)
  CUT: fdc type I seek dest_track=0x1 spinup=on verify=on steprate_ms=12 drive=1 tr=0x93 head_track=0x0 | ends: FORCE-INT after 1.288 s (VBL 3871 -> 3948, x2 CPU)
GATE first-restore g_mste16_v15: FAIL (parked=False completed=False margin<=75%=False cuts=3)
RESULT g_mste16_v15: FAIL
=== g_mste16_nopark (expected info)
frame 261 lines = 60.0 Hz
first game restore starts at tr=0x2e head_track=0x2e (not parked); ends complete after 1.773 s = 81 % of the 2.18 s time-out in effect (v1.6 wait, CPU x2)
game type I commands cut by the force interrupt, whole run: 0 of 15
GATE first-restore g_mste16_nopark: FAIL (parked=False completed=True margin<=75%=False cuts=0)
RESULT g_mste16_nopark: FAIL
=== sg_ste8_v16 (expected PASS)
frame 313 lines = 50.1 Hz
first game restore starts at tr=0x0 head_track=0x0 (PARKED); ends complete after 1.042 s = 24 % of the 4.35 s time-out in effect (v1.6 wait, CPU x1)
game type I commands cut by the force interrupt, whole run: 0 of 15
GATE first-restore sg_ste8_v16: PASS (parked=True completed=True margin<=75%=True cuts=0)
RESULT sg_ste8_v16: PASS (as expected)
=== sg_mste8_v16 (expected PASS)
frame 261 lines = 60.0 Hz
first game restore starts at tr=0x0 head_track=0x0 (PARKED); ends complete after 0.031 s = 1 % of the 4.35 s time-out in effect (v1.6 wait, CPU x1)
game type I commands cut by the force interrupt, whole run: 0 of 15
GATE first-restore sg_mste8_v16: PASS (parked=True completed=True margin<=75%=True cuts=0)
RESULT sg_mste8_v16: PASS (as expected)
=== sg_mste16_v16 (expected PASS)
frame 261 lines = 60.0 Hz
first game restore starts at tr=0x0 head_track=0x0 (PARKED); ends complete after 0.054 s = 2 % of the 2.18 s time-out in effect (v1.6 wait, CPU x2)
game type I commands cut by the force interrupt, whole run: 0 of 15
GATE first-restore sg_mste16_v16: PASS (parked=True completed=True margin<=75%=True cuts=0)
RESULT sg_mste16_v16: PASS (as expected)
```
Reading: v1.6 passes on STE 8 MHz, Mega STE 8 and 16 MHz (dev build and shipped zip: same FFA md5 25ce70a8...); the first restore from track 0 takes 0.02-0.06 s when the motor still runs, 1.0-1.1 s from cold (STE: spin-up). The negative controls fail as they should: v1.4 STE 8 MHz ends at 98 % of the 2.18 s time-out from track 79 (not parked); v1.4 on a 16 MHz Mega STE has the second restore (track 8) cut by the force interrupt; v1.5 on a 16 MHz Mega STE reproduces the reported symptom (first restore cut after 1.119 s, then the drive-B probe, and no orange prompt: the trace idles at the black screen); `nowait` (v1.6 without the longer wait) at 16 MHz has the second restore cut (1.296 s). `nopark` (v1.6 without the head parking) completes at 16 MHz (81 %) because the longer wait alone absorbs it, but the first restore starts at track 46, so the gate's parked condition fails. [MEASURED, Hatari FDC model]


## 3. Gate (c): disk swaps, one and two drives (`swapgate.py`)

```
=== s_ste_d1_nonflops.log
SWAP A s_ste_d1_nonflops: black prompt UP (wall 32.3 s since the key); FDC burst 1.95 s emulated (first cmd to last event), 6 cmds, 0 force-ints (VBL 5417, 50 Hz)
SWAP B s_ste_d1_nonflops: FFB inserted at the prompt, key -> M/J/K screen REACHED (wall 41 s); FDC burst 10.05 s emulated, 0 force-ints
=== s_ste_d1_v15.log
SWAP A s_ste_d1_v15: black prompt NOT up (wall - s since the key); FDC burst -1.00 s emulated (first cmd to last event), -1 cmds, -1 force-ints (VBL 5205, 0 Hz)
SWAP B s_ste_d1_v15: FFB inserted at the prompt, key -> M/J/K screen REACHED (wall 26 s); FDC burst 9.78 s emulated, 0 force-ints
=== s_ste_d1_v16.log
SWAP A s_ste_d1_v16: black prompt UP (wall 3.0 s since the key); FDC burst 1.96 s emulated (first cmd to last event), 5 cmds, 0 force-ints (VBL 5001, 50 Hz)
SWAP B s_ste_d1_v16: FFB inserted at the prompt, key -> M/J/K screen REACHED (wall 31 s); FDC burst 10.83 s emulated, 0 force-ints
=== s_ste_d1_v16c.log
SWAP C s_ste_d1_v16c: black prompt UP (wall 2.4 s since the key); FDC burst 1.49 s emulated (first cmd to last event), 5 cmds, 0 force-ints (VBL 5359, 50 Hz)
SWAP CB s_ste_d1_v16c: FFB inserted at the prompt, key -> M/J/K screen REACHED (wall 36 s); FDC burst 11.61 s emulated, 0 force-ints
=== s_ste_d2_v15.log
SWAP A s_ste_d2_v15: black prompt UP (wall 3.1 s since the key); FDC burst 2.22 s emulated (first cmd to last event), 10 cmds, 0 force-ints (VBL 5002, 50 Hz)
SWAP B s_ste_d2_v15: FFB inserted at the prompt, key -> M/J/K screen REACHED (wall 31 s); FDC burst 13.67 s emulated, 0 force-ints
=== s_ste_d2_v16.log
SWAP A s_ste_d2_v16: black prompt UP (wall 2.5 s since the key); FDC burst 1.73 s emulated (first cmd to last event), 10 cmds, 0 force-ints (VBL 5422, 50 Hz)
SWAP B s_ste_d2_v16: FFB inserted at the prompt, key -> M/J/K screen REACHED (wall 31 s); FDC burst 13.13 s emulated, 0 force-ints
=== s_ste_d2f_v15.log
SWAP D s_ste_d2f_v15: M/J/K screen REACHED after 36 s (wall)
=== s_ste_d2f_v16.log
SWAP D s_ste_d2f_v16: M/J/K screen REACHED after 31 s (wall)

(shipped zip, sc_*; the r runs repeat a scenario whose first key press was lost by the harness: no FDC activity at all; swapgate.py now re-presses and logs it)
=== sc_ste_d1_v16.log
SWAP A sc_ste_d1_v16: black prompt UP (wall 2.4 s since the key); FDC burst 1.58 s emulated (first cmd to last event), 5 cmds, 0 force-ints (VBL 5616, 50 Hz)
SWAP B sc_ste_d1_v16: FFB inserted at the prompt, key -> M/J/K screen REACHED (wall 31 s); FDC burst 8.49 s emulated, 0 force-ints
=== sc_ste_d1_v16c.log
SWAP C sc_ste_d1_v16c: black prompt NOT up (wall - s since the key); FDC burst -1.00 s emulated (first cmd to last event), -1 cmds, -1 force-ints (VBL 5563, 0 Hz)
SWAP CB sc_ste_d1_v16c: FFB inserted at the prompt, key -> M/J/K screen REACHED (wall 31 s); FDC burst 10.00 s emulated, 0 force-ints
=== sc_ste_d1_v16cr.log
SWAP C sc_ste_d1_v16cr: black prompt UP (wall 1.2 s since the key); FDC burst 1.65 s emulated (first cmd to last event), 5 cmds, 0 force-ints (VBL 5577, 50 Hz)
SWAP CB sc_ste_d1_v16cr: FFB inserted at the prompt, key -> M/J/K screen REACHED (wall 31 s); FDC burst 13.94 s emulated, 0 force-ints
=== sc_ste_d1_v16r.log
SWAP A sc_ste_d1_v16r: black prompt UP (wall 1.2 s since the key); FDC burst 1.98 s emulated (first cmd to last event), 5 cmds, 0 force-ints (VBL 5223, 50 Hz)
SWAP B sc_ste_d1_v16r: FFB inserted at the prompt, key -> M/J/K screen REACHED (wall 31 s); FDC burst 9.05 s emulated, 0 force-ints
=== sc_ste_d2_v16.log
SWAP A sc_ste_d2_v16: black prompt UP (wall 3.0 s since the key); FDC burst 2.20 s emulated (first cmd to last event), 10 cmds, 0 force-ints (VBL 5419, 50 Hz)
SWAP B sc_ste_d2_v16: FFB inserted at the prompt, key -> M/J/K screen REACHED (wall 36 s); FDC burst 8.42 s emulated, 0 force-ints
=== sc_ste_d2f_v16.log
SWAP D sc_ste_d2f_v16: M/J/K screen REACHED after 36 s (wall)
```
Reading: single drive v1.6: with FFA still in drive A (A) or with the drive empty (C) the black "Insert Graphics Disk / press any key" is up after one 1.5-2.0 s FDC burst (5 commands, 0 force interrupts); v1.5 / the `nonflops` control (v1.6 without the one-drive patch) spend about 11 s on the drive-B probe (realfloppy.md 3.1; the v1.5 A run here missed its key, the `nonflops` run shows 6 commands / 32 s wall because the probe runs). Inserting FFB there then reaches the M/J/K screen in every 1-drive run (B, CB), also after the empty-drive case. Two drives (campaign disk in drive B): behaviour equal to v1.5 (10 commands = drive A then B, black prompt after 1.7-2.2 s emulated; B passes; FFB in drive B with FFA in A is found without a prompt: D). [MEASURED]


## 4. Gate (b): full floppy cells (`cell16.py`)

cell16.py cold-boots FFA, swaps to FFB at the orange prompt, presses M, goes HQ hall -> personnel -> control door -> map -> Lobos -> boss screen -> 3D view (the game's security check is skipped by the shipped trampoline, `$2c574 = $6002`, read back in every cell), turns the mouse; some cells soak 2-3 min (alive, fps 5-25 depending on scene). With one drive the helper service() puts in the disk the game's black prompt asks for (name string at [$93ca]: graf = FFB, camp = the created campaign disk, mission = FFC). Dev build, /tmp/mw2f/b16:
```
=== c_mste206_16_d1.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 79, 'fps': 7.9, 'vbls_per_frame': 6.329113924050633, 'units_per_sec': 22.23816355810617}
heading series ['0x300', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6']
first game restore: tr=0x0 head_track=0x0 -> complete after 0.054 s
game type I commands: 222, cut by the game's force interrupt: 0
CELL c_mste206_16_d1: PASS
=== c_mste206_16_d2.log
EXC RuntimeError('never reached the boss screen')
first game restore: tr=0x0 head_track=0x0 -> complete after 0.047 s
game type I commands: 122, cut by the game's force interrupt: 0
CELL c_mste206_16_d2: FAIL
=== c_mste206_16_d2r.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 79, 'fps': 7.9, 'vbls_per_frame': 6.329113924050633, 'units_per_sec': 22.16642754662841}
heading series ['0x300', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4']
first game restore: tr=0x0 head_track=0x0 -> complete after 0.047 s
game type I commands: 212, cut by the game's force interrupt: 0
CELL c_mste206_16_d2r: PASS
=== c_mste206_8_d1.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 0, 'fps': 0.0, 'vbls_per_frame': None, 'units_per_sec': 0.0}
heading series ['0x0', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6']
first game restore: tr=0x0 head_track=0x0 -> complete after 0.024 s
game type I commands: 218, cut by the game's force interrupt: 0
CELL c_mste206_8_d1: PASS
=== c_st104_8_d1.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 48, 'fps': 4.8, 'vbls_per_frame': 10.416666666666666, 'units_per_sec': 27.74390243902439}
heading series ['0x300', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4']
first game restore: tr=0x0 head_track=0x0 -> complete after 1.191 s
game type I commands: 218, cut by the game's force interrupt: 0
CELL c_st104_8_d1: PASS
=== c_ste162_8_d1.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 42, 'fps': 4.2, 'vbls_per_frame': 11.904761904761905, 'units_per_sec': 19.96951219512195}
heading series ['0x300', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6']
first game restore: tr=0x0 head_track=0x0 -> complete after 1.099 s
game type I commands: 218, cut by the game's force interrupt: 0
CELL c_ste162_8_d1: PASS
=== c_ste162_8_d2.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 25, 'fps': 2.5, 'vbls_per_frame': 20.0, 'units_per_sec': -84.22256097560975}
heading series ['0x300', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6']
first game restore: tr=0x0 head_track=0x0 -> complete after 1.023 s
game type I commands: 216, cut by the game's force interrupt: 0
CELL c_ste162_8_d2: PASS
=== c_tt306_d1.log
EXC RuntimeError('never reached the boss screen')
game type I commands: 0, cut by the game's force interrupt: 0
CELL c_tt306_d1: FAIL
```
Failures in this block (harness flow, none of the disk logic [INFERENCE]): the first 1-drive cells (c_ste162_8_d1, c_mste206_8_d1) stopped at the 'Insert Campaign Disk' prompt because the first version of the cell had no disk service (reruns after adding it: PASS, out/rerun_cells.log); c_mste206_16_d2 stalled on a blank map (122 FDC commands then idle; rerun c_mste206_16_d2r PASS); c_tt306_d1 found no game commands because Hatari reports pc=27c54 on a 68030 (parser fixed; the trace re-parsed: first restore from track 0 in 0.033 s, 0 of 124 commands cut) and ran out of patience on the slow TT (waits x3; the shipped-zip TT cell PASSES).


## 5. Gate (d): the shipped zips

Zips built by tools/package.sh from the clean tree of commit 5ac5b2c, twice: identical md5 (section 7). Unzipped to /tmp/mw2f/ship; the four .msa equal the four .st through an independent MSA reader (msa_to_st), FFA md5 equals the dev build. Gates (a), (c), (b) run on the shipped images; the .msa copies of FFA/FFB are booted in sb_ste162_8_d1_msa:
```
=== sg_mste16_v16.log
first game restore starts at tr=0x0 head_track=0x0 (PARKED); ends complete after 0.054 s = 2 % of the 2.18 s time-out in effect (v1.6 wait, CPU x2)
game type I commands cut by the force interrupt, whole run: 0 of 15
=== sg_mste8_v16.log
first game restore starts at tr=0x0 head_track=0x0 (PARKED); ends complete after 0.031 s = 1 % of the 4.35 s time-out in effect (v1.6 wait, CPU x1)
game type I commands cut by the force interrupt, whole run: 0 of 15
=== sg_ste8_v16.log
first game restore starts at tr=0x0 head_track=0x0 (PARKED); ends complete after 1.042 s = 24 % of the 4.35 s time-out in effect (v1.6 wait, CPU x1)
game type I commands cut by the force interrupt, whole run: 0 of 15
=== sc_ste_d1_v16.log
=== sc_ste_d1_v16c.log
=== sc_ste_d1_v16cr.log
=== sc_ste_d1_v16r.log
=== sc_ste_d2_v16.log
=== sc_ste_d2f_v16.log
=== sb_mste206_16_d1.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 78, 'fps': 7.8, 'vbls_per_frame': 6.410256410256411, 'units_per_sec': 22.30989956958393}
heading series ['0x300', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4']
first game restore: tr=0x0 head_track=0x0 -> complete after 0.016 s
game type I commands: 222, cut by the game's force interrupt: 0
CELL sb_mste206_16_d1: PASS
=== sb_mste206_16_d2.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 77, 'fps': 7.7, 'vbls_per_frame': 6.4935064935064934, 'units_per_sec': 21.233859397417504}
heading series ['0x300', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4']
first game restore: tr=0x0 head_track=0x0 -> complete after 0.053 s
game type I commands: 212, cut by the game's force interrupt: 0
CELL sb_mste206_16_d2: PASS
=== sb_mste206_8_d1.log
EXC RuntimeError('never reached the boss screen')
first game restore: tr=0x0 head_track=0x0 -> complete after 0.037 s
game type I commands: 124, cut by the game's force interrupt: 0
CELL sb_mste206_8_d1: FAIL
=== sb_mste206_8_d1r.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 0, 'fps': 0.0, 'vbls_per_frame': None, 'units_per_sec': 0.0}
heading series ['0x0', '0x2c8', '0x2c8', '0x2c8', '0x2c8', '0x2c8', '0x2c8', '0x2c8', '0x2c8']
first game restore: tr=0x0 head_track=0x0 -> complete after 0.023 s
game type I commands: 218, cut by the game's force interrupt: 0
CELL sb_mste206_8_d1r: PASS
=== sb_st104_8_d1.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 48, 'fps': 4.8, 'vbls_per_frame': 10.416666666666666, 'units_per_sec': 27.286585365853657}
heading series ['0x300', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6']
first game restore: tr=0x0 head_track=0x0 -> complete after 1.157 s
game type I commands: 218, cut by the game's force interrupt: 0
CELL sb_st104_8_d1: PASS
=== sb_ste162_8_d1.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 45, 'fps': 4.5, 'vbls_per_frame': 11.11111111111111, 'units_per_sec': 27.36280487804878}
heading series ['0x300', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6']
first game restore: tr=0x0 head_track=0x0 -> complete after 1.205 s
game type I commands: 218, cut by the game's force interrupt: 0
CELL sb_ste162_8_d1: PASS
=== sb_ste162_8_d1_msa.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 40, 'fps': 4.0, 'vbls_per_frame': 12.5, 'units_per_sec': -77.51524390243902}
heading series ['0x300', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6']
first game restore: tr=0x0 head_track=0x0 -> complete after 1.071 s
game type I commands: 218, cut by the game's force interrupt: 0
CELL sb_ste162_8_d1_msa: PASS
=== sb_ste162_8_d2.log
EXC RuntimeError('never reached the boss screen')
first game restore: tr=0x0 head_track=0x0 -> complete after 1.074 s
game type I commands: 122, cut by the game's force interrupt: 0
CELL sb_ste162_8_d2: FAIL
=== sb_ste162_8_d2r.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 0, 'fps': 0.0, 'vbls_per_frame': None, 'units_per_sec': 0.0}
heading series ['0x300', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6']
first game restore: tr=0x0 head_track=0x0 -> complete after 1.058 s
game type I commands: 212, cut by the game's force interrupt: 0
CELL sb_ste162_8_d2r: PASS
=== sb_tt306_d1.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 181, 'fps': 18.1, 'vbls_per_frame': 2.7624309392265194, 'units_per_sec': 22.270114942528735}
heading series ['0x300', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4', '0x2c4']
first game restore: tr=0x0 head_track=0x0 -> complete after 0.028 s
game type I commands: 218, cut by the game's force interrupt: 0
CELL sb_tt306_d1: PASS
=== ctl_v15_ste162_8_d2a.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 30, 'fps': 3.0, 'vbls_per_frame': 16.666666666666668, 'units_per_sec': -82.6219512195122}
heading series ['0x300', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6']
first game restore: tr=0x2e head_track=0x2e -> complete after 1.733 s
game type I commands: 212, cut by the game's force interrupt: 0
CELL ctl_v15_ste162_8_d2a: PASS
=== ctl_v15_ste162_8_d2b.log
$6220=d $700a=2 MWPO 000B2FF8: 4d 57 50 4f                                      MWPO
world_rate {'vbls': 500, 'flips': 0, 'fps': 0.0, 'vbls_per_frame': None, 'units_per_sec': 0.0}
heading series ['0x300', '0x2c8', '0x2c8', '0x2c8', '0x2c8', '0x2c8', '0x2c8', '0x2c8', '0x2c8']
first game restore: tr=0x2e head_track=0x2e -> complete after 1.785 s
game type I commands: 212, cut by the game's force interrupt: 0
CELL ctl_v15_ste162_8_d2b: PASS
```
Failures in this block, with their reruns: sb_ste162_8_d2 and sb_mste206_8_d1 stalled at the blank-map screen with 122-124 FDC commands and nothing cut (the same stall as c_mste206_16_d2); the reruns sb_ste162_8_d2r and sb_mste206_8_d1r PASS with 212 / 218 commands. Three stalls in about 14 full cells, all in the map step; the v1.5 control ctl_v15_ste162_8_d2a/b (same cell, two drives) passed twice, so the stall is not shown to be new, but it is also NOT shown to be harness-only: not investigated [INFERENCE: the cell presses space and clicks while the map is still loading]. sc_ste_d1_v16c: the first key press was lost (no FDC activity); sc_ste_d1_v16cr repeats it: PASS.


## 6. Not proven / limits

* No real drive, STE or Mega STE. Hatari's FDC answers an EMPTY drive at once (scenario C: 1.6 s, no time-outs), a real 1772 without index pulses probably waits for the game's time-out ([INFERENCE]: five of 4.4 s at 8 MHz = about 22 s of dark before the black prompt on a 68000 machine with the drive empty and one drive; v1.5 spent the same 22 s on drive A + drive B).
* The restore timing on real drives (index pulse phase, spin-up 1.0-1.2 s, step 12 ms) was taken from Hatari's FDC model. The v1.6 margins are large (first restore 25 % of the time-out at 8 MHz, 0.02-0.06 s when the motor is still running), but real behaviour is untested.
* Falcon: MW2 does not run on the Hatari Falcon (`PLAN.md`), not tested. TT: sections 4/5 (shipped-zip cell PASS on TOS 3.06, 4 MB, MMU). Campaign creation on floppy: not re-run (Hatari discards the writes, as before).
* The downloader's disks may have been v1.4 or v1.5; the mechanism was reproduced in Hatari for v1.5 at 16 MHz (section 2), v1.4 only as a 98 % margin on the STE and a cut second restore at 16 MHz.

## 7. Release md5s (tools/package.sh, 2026-11-19, built twice from commit 5ac5b2c, identical)
```
672f6f463b4e98728352f9f38c151214  dist/Midwinter2_v1.6_patched_floppies_2026-11-19.zip
2b2f153b83879f822dd7a3e426c03523  dist/Midwinter2_v1.6_patched_2026-11-19.zip
25ce70a8b5be671b15818395ecf89c57  FFA_boot.st       ec8adc69186454a002e2865eebd5b882  FFA_boot.msa
9d4ea2ddfcfe5fa7fdf7b54f26168ed3  FFB_graphics.st   c96a86572136cca4bdf71174a89bed4b  FFB_graphics.msa
252d0ad0674db02ba5d104891db12e29  FFC_missions.st   ec235f89ad4d7ae4d6c8a85994fce037  FFC_missions.msa
5e034299f50432eb6fe5e7048a5d2ccc  FFD_campaign_blank.st  6c5917ae319c3906012eb6bd44bf0c83  FFD_campaign_blank.msa
```
FFB/FFC/FFD are byte-identical to v1.5 and to FILES/FFB..FFD; the HD zip's RUNME.TOS differs from v1.5 only in the version string and the (HD-inert) cpufix bytes.
