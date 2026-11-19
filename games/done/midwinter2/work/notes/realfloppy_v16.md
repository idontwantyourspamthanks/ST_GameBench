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

RESULTS_A

## 3. Gate (c): disk swaps, one and two drives (`swapgate.py`)

RESULTS_C

## 4. Gate (b): full floppy cells (`cell16.py`)

RESULTS_B

## 5. Gate (d): the shipped zips

RESULTS_D

## 6. Not proven / limits

* No real drive, STE or Mega STE. Hatari's FDC answers an EMPTY drive at once (scenario C: 1.6 s, no time-outs), a real 1772 without index pulses probably waits for the game's time-out ([INFERENCE]: five of 4.4 s at 8 MHz = about 22 s of dark before the black prompt on a 68000 machine with the drive empty and one drive; v1.5 spent the same 22 s on drive A + drive B).
* The restore timing on real drives (index pulse phase, spin-up 1.0-1.2 s, step 12 ms) was taken from Hatari's FDC model. The v1.6 margins are large (first restore 25 % of the time-out at 8 MHz, 0.02-0.06 s when the motor is still running), but real behaviour is untested.
* Falcon: MW2 does not run on the Hatari Falcon (`PLAN.md`), not tested. TT: see section 4. Campaign creation on floppy: not re-run (Hatari discards the writes, as before).
* The downloader's disks may have been v1.4 or v1.5; the mechanism was reproduced in Hatari for v1.5 at 16 MHz (section 2), v1.4 only as a 98 % margin on the STE and a cut second restore at 16 MHz.
