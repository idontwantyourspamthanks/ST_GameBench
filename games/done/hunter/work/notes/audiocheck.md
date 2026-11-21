# Hunter v1.2.1 audio check: sample-bank integrity (HunterBank)

Tags: [obs] observed (raw lines in `work/audiocheck/out/<cell>.txt`), [src] read in source/disassembly, [INFERENCE] reasoning only.
Scope after the lead's narrowing: bank integrity on the SHIPPED v1.2.1 zips (unzipped to `/tmp/huntbank/rel`), sound ON (`--sound 50066`), Hatari 2.6.1-devel (`hattari/build/src/hatari`), private HOME, workdirs `/tmp/huntbank/<cell>`. No tracked file edited.
Method (`work/audiocheck/cell.py`): cold boot; `savebin $8BA00 $23600` and compare with the source bytes (`FILES/P` of the HD zip: payload at `$8BA00`, bank at `$90000` = `P[$4600:]`, header length `$1E4DE`, bank end `$AE4DE`, panel block to `$AEF11`), state areas masked (`DYN` in `ac.py`). Checkpoints: load (marker `HNPO` first seen), title, 3D view (full RAM dump), every 30 s of walking, after Save, after Load, final (full RAM dump). Effect pass: all 21 effect ids injected on channel 0 at volume 12 with the WAV capture running, features per effect (`fx.py`, `fxcmp.py`). Ring pass: write-cursor lead before each top-up over 800 VBL with 2 loops + explosions.

## 1. Result

| machine | build | bank vs file (all checkpoints) | Gamex TOS copy | other |
|---|---|---|---|---|
| STE TOS 1.62 1 MB | HD v1.2.1 | **0 differ** at all 12 checkpoints (180 s walk, Save, Load) | `[$d7008,$f2e98)` (`$ffd80`=`$d7008`, count `$94a`) | ring lead min/median/max 58/64/70 samples, 0 underruns; DMA `$ff8921`=`$80` after every request |
| STE 4 MB | HD v1.2.1 | **0 differ** (10 checkpoints) | `[$102008,$11de18)` | |
| Mega STE TOS 2.06 1 MB (Hatari runs it at 16 MHz; `--cpuclock 8` after start changes nothing: fps 8.67 standing, same as 16) | HD v1.2.1 | **0 differ** in the run `hd_ms1_8` (10 checkpoints, 120 s, Save, Load); the run `hd_ms1_16` was 0 differ until the game reset itself (section 3) | `[$d7008,$f9088)` (count `$b57`) | effects: identical to the STE to 4 digits (`fxcmp.py`, worst deviation 0.01); ring 58/64/70, 0 underruns |
| Mega STE 4 MB | HD v1.2.1 | **0 differ** until the game reset itself (section 3); `$AEF12..$C00FF` all zero | `[$102008,$124088)` | |
| Mega STE 1 MB (floppy cell runs at 8 MHz, `$ff8e21`=0, 4.67 fps) | floppy v1.2.1 | **0 differ** in the bank at all 9 checkpoints (90 s walk, Save, Load) | none (no Gamex on the floppy build: `$ffd80`=0) | effects identical to the STE (deviation 0.00) |
Not run (lead's narrowing): floppy 2-disk, ST, TT, Falcon, v1.2 and original controls, the broad underrun/rate sweep on other machines. The STE 1 MB floppy and the 2 MB cells were not run either.
Floppy "patch code 1283 B differ" is `$8BC02..`: the core's site table, consumed at boot (the floppy stage unpacks only the non-zero runs); not code that runs later.

## 2. Does anything overlap the bank or the patch code? No [obs + src]
* The Gamex/D15R TOS copy sits at `$ffd80.l` (HD only): `$d7008` on 1 MB (STE and Mega STE), `$102008` on 4 MB; length `(count+1)*48` = 114 192 B (STE 1.62) or 139 392 B (TOS 2.06). All of it is above `$AEF12` (payload end) and the bank (`$AE4DE`): the nearest is `$d7008`, 40 KB higher. Unlike HAGA in Midwinter 2 it is anchored at `$d7008`/`$102008`, not at `phystop - x - TOS size`, so a bigger TOS (2.06) only extends it upward (`$f9088` on 1 MB, still inside RAM).
* HDDRIVER's pool starts at `$af100` (first non-zero byte after the payload on 1 MB machines; `$AEF12..$C00FF` all zero on 4 MB); the payload file ends at `$AEF11`, 238 B below it, on every machine run.
* All game file loads go through a static table (`$7F3C..$7FD0`, 8-byte pointer/size pairs from `$10FB2`); the highest end is `$55504`; the other destinations seen (`$61514`, `$79714`+2 KB) end below `$7A000`. Nothing the game loads reaches `$8BA00` [src: dump `ram_foot_stand.bin`].
* Floppy: the loader's file cache starts at `$AF000` ([src] floppy.md); the panel block ends at `$AEF11`.
So the Midwinter 2 failure (a loader's live TOS swap buffer on top of the bank on a 1 MB Mega STE) does **not** occur in Hunter on any cell run. No damaged bytes, hence no writer to find and no affected sounds.

## 3. Incidental finding: the game reset itself on the Mega STE HD builds (not audio, not the bank)
* `hd_ms1_16` (Mega STE 1 MB, after the effect pass, ring pass and 60-90 s of walking): everything was cleared and START re-ran (HW screen, title). `hd_ms4` (Mega STE 4 MB): same, during the effect pass at effect 2. Hatari log line in both: `Address Error reading at address $3961 (resp. $3921), PC=$8c46e` = **`p4_poly` (`patches/p4_poly.s` line 66, `move.w 2(a3),d6`, `a3 = a4 + (byte<<4)` an edge record): the edge-record base is odd**. The game points the CPU exception vectors `$8..$2c` all at `$10f74` (clears `$804..$10f74`, `st $426`, jumps to the reset vector), so any exception is a full reset [src dump `ram_foot_stand.bin`, `m68dis --xref 10f74`].
* Not reproduced on the STE (5 HD runs incl. 180 s of walking), on `hd_ms1_8` (the same Mega STE configuration, 120 s) nor on the floppy Mega STE (8 MHz, 90 s): 2 of 4 Mega STE HD runs. My harness pokes the sound driver state (`$af0e`, `$11388`, `$11398`) during the effect pass, so a harness side effect is not excluded; the VBL handler saves `d0-d7/a0-a4` (`$c5f4`), so the mixer does not clobber `a4` [src]. The trap breakpoint at `$10f74` (armed only before the play phase, `cell.py` default) did not catch either reset, so no register dump exists. [INFERENCE] a timing-dependent state race in the Mega STE's different interrupt timing; needs the lead to decide whether to chase it (repro: `cell.py CELL --kind hd --machine ms1 --play 300`, 2 runs). A user-visible effect would be: the game suddenly restarts to the START screen, sound stops.

## 4. Audio facts measured on the way [obs]
* Mixer ring: the write cursor stays 58-70 samples (9-11 ms) ahead of the DMA position just before each top-up (TARGET 192, one VBL = 125 samples); 799 top-ups, **0 underrun resyncs**, identical on STE and Mega STE. The margin to an underrun is about one VBL minus 9 ms of interrupt latency.
* DMA rate register `$ff8921 = $80` (6258 Hz mono) on every cell, `$ff8901 = 03` while playing, back to `00` after the end of one-shots and after leaving the 3D view; no stuck DMA after any effect (`after=('00', 0)` for all 21 ids).
* Effect features (rms, spectral centroid, share above 1.5 kHz) agree between the STE, the Mega STE (HD and floppy) to < 1 %: the sound is the same on every machine Hatari can run; Hatari cannot show real-hardware differences (Microwire reset state, Mega STE cache vs DMA, real DMA position read timing: [INFERENCE] untested).

## 5. Proposed fix
None for the bank: nothing is damaged. If the lead wants a safety net like the Midwinter 2 canary anyway: an end canary in `tools/snd_build.py` (4 bytes after the bank) checked in `snd_init0` (`patches/snd_core.s`) would fall back to the YM driver on a machine where the bank was overwritten; not needed for any cell run. The reset in section 3 needs its own investigation (`p4_poly` `a4`/`a3` on the Mega STE).

## 6. Files
`work/notes/audiocheck.md` (this); `work/audiocheck/`: `ac.py` (helpers, source bytes, comparison, Gamex state), `cell.py` (cold-boot cell, checkpoints, play, Save/Load, `--fx`, `--ring`, `--voices`, `--trap`), `fx.py` (effect pass, ring-lead pass, voice-contention pass [written, not run]), `fxcmp.py`, `summ.py`, `run3.sh`, `out/` (raw cell logs `<cell>.txt`, per-effect features `<cell>_fx.json`, ring leads). Amiga WAV captures stay in `/tmp/huntbank/keep` (not in the repo).
Caveats: the "TRAP FIRED" line printed in `hd_ms4.txt` and `fl_ms1.txt` is a false positive of the log search (it matches the breakpoint's own `b pc = $10f74` echo); the overlap numbers in the older cell logs (`hd_ms1_8`, `hd_ste4`) were computed with a wrong bank length field and say "overlap with bank 139392/114192 B": the real overlap is 0 (addresses above); fixed in `ac.py` for later cells (`hd_ms4`, `fl_ms1`).
