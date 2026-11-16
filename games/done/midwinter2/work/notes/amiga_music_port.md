# Midwinter 2: the Amiga MUSIC on the STE's DMA sound (`asn_mus*`, part of the `asn_*` group) - HANDOFF

Status: **built, unit-verified, and working in Hatari on STE 1 MB HD (one full cold boot); NOT finished.** Work was stopped on request; this file is the
handoff. Nothing is committed. Read with `amiga_music.md` (format), `st_music.md` (ST interface), `amiga_sound.md` (the sfx part of the same blob).
Evidence tags: **[obs]** seen in a tool run of this session (raw output below), **[model]** computed, **[INFERENCE]** not verified.

## 0. One-paragraph state
The blob (`patches/asn/blob.s`) now contains a 68000 port of the Amiga music player plus a reworked shared mixer; the bank (`tools/asn_build.py`) carries the
score + instruments of the 13 tunes the ST can request. Two longs of the YM driver's vector table (`$806` tick, `$80a` start) point into the blob (`asn_mus`).
Unicorn: the real entry points play all 13 tunes for 1700 VBL bit-identical to `sim.py` + an integer mixer model (voices AND the DMA ring), negative control fails.
Hatari STE 1 MB HD cold boot: tune 1 is on the DMA from the game's logo screen (`$ff8901 = 03`, `$ff8921 = 81`), survives every screen to the 3D view, the sfx
take the DMA over at 6258 Hz, F5 brings tune 1 back, the bank is byte-identical in RAM at 7 checkpoints. **Open: the HD load mute does not work as designed
(§6.1), the hall is silent in my run (cause not established, §6.2), no cold boot yet on floppy / Mega STE / ST / TT, accelerated time not tested, pixel gate
not re-run, user docs not updated.** Ordered checklist: §7.

## 1. Settled design
### 1.1 RAM map (1 MB HD, measured) [obs]
`work/asn_mus/ramsurvey.py` booted an HD build whose `ASNBANK.BIN` was padded with a pattern (`word = address ^ $A55A`) from the old bank end up to `$E83E0`
(so the RUNME splice itself wrote it), and dumped `$B0000-$FFFFF` at every screen (`work/asn_mus/survey1.txt`):
```
[logo] VBL 1508   bank/pattern bytes changed: 0      above the pattern ($e83e0..): first non-zero $f7fad
[mjk] [hall] [personnel] [hall2] [map] [island] [objectives] [boss]   bank/pattern bytes changed: 0 ; first non-zero above: $e83e6, last $fb613
[3d] VBL 14313  changed: 1045 = only ('0xbbe00'..'0xbbebf') state and ('0xbc000','0xbc3ff') ring (the old blob's own)
[f5map] [f5map2]  the same; "non-zero in any dump above the pattern: lowest $e83e6"
```
=> **free RAM `$BB000-$E83E5` (185 317 B) on every screen walked** (logo, M/J/K, hall, personnel, control map, island, objectives, boss, 3D view, F5 map).
The game/PP use RAM from `$E83E6` up from the M/J/K screen on. NOT walked: War Room, Raids, Training, mission end, accelerated time, 2/4 MB, floppy
(floppy has no HAGA: `$BB000-$FFFFF` was all zero in an older in-game dump [INFERENCE that it stays so]).
The builder's limit is `LIMIT = $E8000`; the bank ends at **`$E61B2`** (176 562 B, 7 758 B to spare).

### 1.2 Bank layout (`tools/asn_build.py` docstring is authoritative; equates at the top of `patches/asn/blob.s` must match) - CHANGED from the sfx-only bank
| offset (RAM) | what |
|---|---|
| `+$0000` (`$BB000`) | header `'ASN2'`, version 2, nrows, bank address, total length. `+$40..$FF` zeros = `B_SIL` (silence of the one-shot instruments / what a finished voice reads) |
| `+$0100/$0300/$0700` | sfx ROWS / SEQ / REC (unchanged) |
| `+$0E00` `SV` | blob state 256 B (new variables from `+$12` and `+$C0`, see blob.s) |
| `+$0F00` `MS` | 4 music channel records x `$40` |
| `+$1000` `RING` | DMA ring, now **2048 B** (was 1024) |
| `+$1800` `B_VT` | 3 gain sets x 16 levels x 256 B: 0.5 (sfx <= 2 voices), 0.25 (sfx 3-4 voices and peaky tunes), 0.35 (other tunes) |
| `+$4800` (`$BF800`) | the blob. **7 fixed 6-byte entries `jmp abs.l`** (was 8 until `asn_mload` was removed, section 10): +0 asn_tick, +6 asn_wd, +$c asn_lvc, +$12 asn_lv1, +$18 asn_lv2, +$1e asn_mtick, +$24 asn_mstart. 3 614 B, room to `$C1000` |
| `+$6000` (`$C1000`) | music section (`asn_music.build_music`): tune table 18 x 16 B (4 list pointers, first = 0 -> tune not in the bank), `+$120` flags per tune (rate.b, gain set.b), `+$144` null list, `+$148` idle stream, `+$150` silence envelope, `+$162` fixed envelope (0, 32, `$ff`), then lists, patterns (the Amiga bytes, pointers rewritten to RAM addresses), envelopes, instrument descriptors (flag.w LC1.l LEN1.w LC2.l LEN2.w), samples |
| after it | the 16 sfx sample regions |
Every sample region is followed by `PAD = 48` bytes (loops: the region repeated; one-shots: zeros) because the mixer tests the end of a buffer once per 8 outputs.
The sfx pads shrank from 800 B to 48 B (that is what made room). Music: 69 674 B (score 14 210 B, 13 instruments 55 464 B), sfx samples 82 312 B.
The score format is the Amiga's (`amiga_music.md` section 5) byte for byte, only the three pointer kinds (pattern in a list, INSTR, ENV) are RAM addresses.
The instruments are low-passed at build time (the Amiga's LED filter, on in every tune: two one-poles at 3.3 kHz at the instrument's duration-weighted
median playing rate; `--no-led` switches it off) [model; not judged by ear].

### 1.3 Tunes per delivery
One bank for HD and floppy: tunes **1, 5, 2, 4, 6, 7, 10, 15, 16, 17, 8, 9, 12** = every tune the ST game has a call site for (`st_music.md` 2.4).
3, 11, 13, 14 have no ST call site and are not in the bank (they would fall back to the YM driver). `--tunes N ...` builds a smaller bank.
`asn_build.py stats` [obs]:
```
tune  1: loop  6593 ticks, 33 patterns, 10 instruments, peak  312 -> gain set 2 (0.35), rate 12517 Hz
tune  5: loop  1601 ticks, 21 patterns, 6 instruments, peak  332 -> gain set 1 (0.25), rate 12517 Hz
tune  2: 144 -> set 2 | tune 4: 417 -> set 1 | tune 6: 312 -> 2 | tune 7: 199 -> 2 | tune 10: 224 -> 2 | tune 15: 257 -> 2 | tune 16: 224 -> 2
tune 17: 272 -> 2 | tune 8: 379 -> set 1 | tune 9: 270 -> 2 | tune 12: 271 -> 2          (all 12517 Hz)
```
(peak = largest |sum| of the voices with one full-scale voice = 127; the gain set must keep `peak * gain * 1.1 + 2 <= 127`; `asn_mus_test.py clip`
checks the exact integer mix over each whole loop - written, NOT run yet.)

### 1.4 Hooks and exact fallback rules
- `patches/asn_mus.s`: site `$806`, orig `00000d0e 00000c6c` -> `000bf81e 000bf824` (boot phase, applied by the `$B3000` trampoline on HD and floppy, i.e. AFTER the
  boot stub's own YM title tune and BEFORE the game's first `$321fe`). `$80e` (silence `$c4c`) is deliberately NOT patched: nothing to do for a DMA tune.
- `asn_mstart` (`$80a`): mode != 2 (ST, Mega ST, 68020+, no/old bank) -> `jmp $c6c` untouched. Mode 2: tune in `$b96.l`; 0, > 17 or table entry 0 -> stop a running
  DMA tune (`mus_off`) and `jmp $c6c` (YM plays it). Else: `$b96 := 0; jsr $c6c` (parks the YM driver on its silent tune 0 and silences the chip), `$b96 := tune`,
  `mus_setup` (the Amiga's `$5760c`). A `v_lock` byte makes the tick a no-op while a start is in progress (the start runs in main context).
- `asn_mtick` (`$806`, copied by the game into `$5138`): `v_mus == 0` -> `jmp $d0e` (YM tick). Else `mus_run`: heartbeat for `asn_wd`, `mus_enter` if the session
  is not music (stops the DMA, sets rate/target/gain of the tune, Paula reset), 50 Hz tick (60 Hz: 5 of 6 VBL), `mus_vols` (`$b9a` attenuation read EVERY VBL:
  table `256,256,256,181,128,91,64,45,32,23,16,11,8,6,4,0` / 256, i.e. 2 = normal, 3 dB per step, `$f` = mute), then the shared `asn_mixer`.
- Once flag `$ba2`: when a channel's list wraps and `$ba2 != 0` the DMA tune stops, `$b96 := 0`, `jsr $c6c` (what the YM driver does at `$e72`).
- Music <-> sfx: exclusive. `v_act` 0 none / 1 sfx / 2 music; each tick enters its own session (`asn_enter` / `mus_enter`) which stops the DMA, resets the ring
  cursor and loads its parameter block (`par_sfx`: 6258 Hz, target 192, K 9285653 << 2; `par_m12`: 12517 Hz, target 640, thr 656, max 64 groups, K 4642826 << 2;
  `par_m6`: 6258 Hz music, K 4642826 << 3). The rate is written by `asn_dmastart` (`$ff8921 = $80 | rate`) only while the DMA is stopped: glitch-safe.
- `asn_wd` (unchanged site `$262c2`) stops the ring within 2 VBL when the game parks the tick. `mw2patch.py` now REFUSES an `asn_*` build without `asn_wd`,
  without `MW2_BANK`, or with a bank whose magic is not `ASN2` (the sites jump to `$BF800`).
- Mixer (rewritten, serves both): per voice a buffer (pointer, length in words), 16.16 phase, `cmp.w end / bhs` once per 8 outputs; at the end: sfx loop
  (`idx -= len`), music = Paula's reload from the pending `AUDxLC/LEN` (`V_NSMP/V_NLEN`), and a voice that lands in `B_SIL` is dead (`V_DEAD`) until the next DMA
  start. Music voices at volume 0 still advance (`mus_skip`). 4 voices: 40 + 3 x 48 cycles per output.

## 2. Files: exact state
| file | state |
|---|---|
| `patches/asn/blob.s` | REWRITTEN (sfx driver unchanged, mixer/session code changed, music added). Assembles; unit tests pass; cold boots in section 10. `asn_mload` and its entry REMOVED (section 10) |
| `patches/asn_core.s`, `asn_wd.s`, `asn_lvc.s`, `asn_lv1.s`, `asn_lv2.s` | targets changed to the entry table (`$bf800`, `$bf806`, `$bf80c`, `$bf812`, `$bf818`), notes updated. Verified by `verify` + the cold boot (sfx at the 3D view) |
| `patches/asn_mus.s` | NEW, done (site `$806`, 8 B) |
| `patches/asn_mus_ld.s` | DELETED (section 10; the loader stall of 6.1 stays open) |
| `tools/asn_music.py` | NEW, done: Amiga image from the ADF, `Music` (= sim.py), `Paula`, `build_music`, `led_filter`, integer `mix`, `BlobModel`, `render` |
| `tools/asn_build.py` | REWRITTEN for the layout above; `build_bank()` now returns `(bank, info)`; new `muswav DIR`, `--tunes`, `--no-led`, `--rate6`. `stats` works. `muswav` untested |
| `tools/asn_mus_test.py` | NEW: `unit` (spec / player / mixer / iface) passes; `clip` written, NOT run |
| `tools/asn_test.py` | adapted (new `build_bank` API; its mixer check now calls `asn_mus_test.unit_mixer`); passes |
| `tools/asn_mus_cold.py` | NEW: `run` (HD path used once, works; floppy / ST / TT paths written but NEVER run) and `compare` (works, see 3.3) |
| `tools/asn_cold.py`, `asn_live.py` | constants adapted to the new layout (bank length, dyn range `$BBE00-$BC7FF`, blob `$BF800-$C0FFF`); NOT re-run |
| `tools/asn_abtest.py` | one emulator at a time, own base cache `build/ab/asn_base`; NOT re-run |
| `tools/mw2patch.py` | +3 refusals in `main()` (no bank / not `ASN2` / no `asn_wd`), docstring line. Nothing else changed; the bigger bank needs no change (HD: file length; floppy: 46 of the 79 blank track-sides) |
| `tools/play.sh` | `--asn` now rebuilds the bank when `alt/amiga/disk1.adf` exists, adds `asn_mus asn_mus_ld`, and refreshes `FILES/ASNBANK.BIN` in `build/play-asn` on every run (an old v1 bank there would crash the new RUNME). Syntax-checked, the build command was run by hand; the script itself was NOT launched |
| `work/asn_mus/` | scratch: `ramsurvey.py`, `survey1.txt`, `build.sh` (bank + `build/mus/hd` + `build/mus/fl`), `mus3d.sav` (snapshot of the music build at the Lobos 3D view, STE 1 MB: patched RAM incl. the bank) |
| `work/asn_cold/mus_hd_ste162_1mb.*` | the cold boot log / json / screenshots / WAV (441 s from power-on) |
| `build/mus/asn_bank_v1_backup.bin` | the old sfx-only bank (not needed) |
| `patches/README.md`, `PATCHES.TXT`, `FLOPPY.TXT`, `.omp/skills/mw2-patching/SKILL.md` | **NOT updated**: they still describe the sfx-only bank (`$D5600` blob, 110 KB, ring 1024). Checklist item 9 |
`work/notes/amiga_sound.md` is now out of date in the same points (blob address, ring size, pad size, bank size); its sfx logic and evidence still hold.

## 3. Verified (raw output)
### 3.1 Tree gates, run last [obs]
```
$ python3 tools/mw2patch.py verify            -> verify: ALL OK      (asn_mus site $00806 and asn_mus_ld site $27848: image match, ramdump match)
$ python3 tools/asn_test.py unit --ticks 300
driver: 123 sound/level runs x 300 ticks, mismatches 0
mixer : 300 random trials (half sound-effect mode, half music mode), ring + cursor + voice state, mismatches 0
amiga : the original Amiga driver vs the blob, 41 sounds x 3 levels x 300 ticks, mismatches 0        (ASN_NEG=1: mismatches 57)
$ MW2_BANK=build/asn_bank.bin python3 tools/mw2patch.py build --out build/mus/hd --only <defaults incl. pp_bigram_cache pp_nofade> asn_core asn_wd asn_lvc asn_lv1 asn_lv2 asn_mus asn_mus_ld
built .../build/mus/hd with 46 patch(es) + 2 file patch(es)      (HAGA+$3228 pp_bigram_cache, HAGA+$0ffc.. pp_nofade applied)
... the same without asn_mus asn_mus_ld: built .../build/mus/hd_sfxonly with 44 patch(es) + 2 file patch(es)
floppy: built floppy set in build/mus/fl ... 47 patch(es)   (payload + bank = 209 330 B = 46 track-sides from 81)
```
### 3.2 Unicorn, music [obs] (`python3 tools/asn_mus_test.py unit --ticks 1700`)
```
spec  : asn_music.Music vs the study's sim.py, 17 tunes x 1700 ticks of Paula writes, mismatching tunes 0
player: asn_mstart + asn_mtick per VBL vs sim.py + mixer model, 1700 VBL each, voices + ring + cursor; (tune, mismatching VBLs): [(1, 0), (5, 0), (2, 0), (4, 0), (6, 0), (7, 0), (10, 0), (15, 0), (16, 0), (17, 0), (8, 0), (9, 0), (12, 0)]
player: tune 1 at 60 Hz (5 ticks / 6 VBL) 0 mismatches; with DMA underruns 0; with a $b9a fade 2..15, mute, back to 2: 0
mixer : 300 random trials (half sound-effect mode, half music mode), ring + cursor + voice state, mismatches 0
iface : vector-table behaviour, 22 checks, failed: none
RESULT: ALL OK
```
What `player` is: FFA file 8 (the real YM driver) and the bank are loaded, the blob is entered through its fixed entries exactly as the patched vector table
does, the DMA position register is fed like the hardware; after EVERY VBL the four voices' period / Amiga volume / LC / LEN / DMA bit / latched buffer / phase /
dead flag / mixer volume, the whole 2048-byte ring, the write cursor and the DMA state must equal the reference (the study's `sim.py` driving the integer mixer
model). Negative control (`ASN_NEG=1`, reference channel 2 one period unit off): `PLAYER MISMATCH tune 1 VBL 64 ... RESULT: FAILED (spec 0, player 20, ...)`.
`iface` covers: YM machine -> `$c6c`/`$d0e` really run; tune missing -> YM; DMA tune parks the YM on tune 0; `$b9a = $f` mutes and the DMA stops after 12 VBL
while the tune goes on; back to 2; the start lock; restart; sfx take-over at 6258 Hz and back; tune 0; once flag (tune 8 ends after 833 ticks, `$b96 = 0`);
the loader hook.

### 3.3 Hatari cold boot, STE TOS 1.62, 1 MB, HD (`tools/asn_mus_cold.py run hd_ste162_1mb ste 162 1024 hd build/mus/hd --snap work/asn_mus/mus3d.sav`) [obs]
`work/asn_cold/mus_hd_ste162_1mb.txt` (t = emulated seconds since power-on):
```
[logo       ] t=  62.23s mode 2 session 2 dma 255 tune  1 rate 1 tick   148 $b96=00000001 $b9a= 2 $7626=0001 $5138=000bf81e $ff8901=03 $ff8921=81
MWPO ; vector table $806: 000bf81e000bf82400000c4c
[intro1..6  ] t= 71.44 .. 110.06s  tick 609, 962, 1353, 1739, 2124, 2510   (same state)
[intro      ] profile 250 VBL: blob 48678 cycles/VBL = 30.4 % of a 50 Hz frame; YM driver 0/VBL
[mjk        ] t= 129.16s ... tick  3450 ; profile: blob 47173 cycles/VBL = 29.4 %
[M-key      ] t= 146.82s ... $b9a= 2 ;  [fade0] t= 155.83s dma 0 tick 4769 $b9a=15 $7626=0000 $ff8901=00
[hall       ] t= 175.55s dma 0 tune 1 tick 5756 $b9a=15 $7626=0000 $ff8901=00 ; profile: blob 4716 cycles/VBL = 2.9 %   <- muted, see 6.2
[personnel  ] t= 206.06s dma 255 tick   698 $b9a= 2 $7626=0001 $ff8901=03     (restart)
[hall2      ] t= 223.32s dma 0 tick 1547 $b9a=15 $7626=0000 $ff8901=00
[map        ] t= 253.57s dma 255 tick 1210 $b9a= 2 $7626=0001 ; profile: blob 47534 cycles/VBL = 29.7 %
[island] [objectives] [boss]  tick 2851, 3865, 4519: tune 1 keeps playing
[3d         ] t= 386.33s mode 2 session 1 dma 255 rate 0 $5138=00018f92 $ff8901=03 $ff8921=80     (sfx tick, 6258 Hz, the helicopter engine: voice 3 vol 63 per 540)
   requests of effects 2 and 4: voice 0 period 520 then 888 (they ran; the reads were too slow to catch them playing)
[3d         ] profile: blob 8150 cycles/VBL = 5.1 %
[f5         ] t= 420.29s mode 2 session 2 dma 255 tune 1 rate 1 tick 380 $5138=000bf81e $ff8901=03 $ff8921=81 ; profile: blob 47356 cycles/VBL = 29.6 %
wav: 441.5 s; rms before the game's tune (boot stub, YM) 4581, first 30 s of the tune 2421
DMA machine: mode 2 at every stage True; music stages with a DMA tune 17/17, session 2 17/17, $5138 = music tick 17/17
bank checks: {'intro': 0, 'mjk': 0, 'hall': 0, 'map': 0, 'boss': 0, '3d': 0, 'f5': 0}     (bytes of $BB000-$E61B2 differing from build/asn_bank.bin outside state/records/ring)
```
WAV facts (20 ms RMS): boot stub's YM tune 53.2-56.9 s, silence 57.0-58.3 s, DMA tune from 58.35 s.
`python3 tools/asn_mus_cold.py compare work/asn_cold/mus_hd_ste162_1mb.wav 58.4 --secs 40` (spectrogram correlation with the model render, 5 s segments):
```
coarse onset of the tune in the capture: 59.38 s
segment   rho(model tune 1)   lag ms   rho(model tune 5)   rho(capture shifted 1.5 s)
  0.0 s  0.162 | 5.0 s -0.012 | 10.0 s 0.112 | 15.0 s 0.417 | 20.0 s 0.810 | 25.0 s 0.796 | 30.0 s 0.822 | 35.0 s 0.755     (other tune: 0.002, shifted: -0.054)
```
i.e. from 20 s on the capture IS the model's tune 1 (0.76-0.82 against 0.00 for tune 5 and for a 1.5 s shift); the first 15-20 s do not line up with a
single offset because the game stalls the VBL there (6.1): 32 ticks are missing between t = 71.4 and 79.1 s (tick 609 -> 962 in 7.70 s instead of 385), and
the fitted onset (59.38 s) is 1.0 s later than the real one (58.35 s). **So "tune 1 correlates with the model" is shown only for 20-40 s; the compare tool
needs a per-segment lag search wide enough to follow the stalls before the first 20 s can be claimed.**
CPU: music **47.2-48.7 k cycles per VBL = 29.4-30.4 %** of a 50 Hz frame (4 voices, 12517 Hz); muted 4.7 k (2.9 %); sfx in the 3D view 8.15 k (5.1 %, as before).

## 4. NOT verified
- Floppy build (boots? tune 1 on the logo?), Mega STE TOS 2.06 4 MB HD, plain ST TOS 1.04 and TT TOS 3.06 (YM passthrough + YM audible). The code paths exist
  in `asn_mus_cold.py run` but were never executed. The sfx-only group passed those cells before this rework (`amiga_sound.md`), with the OLD blob layout.
- Accelerated time (tune 5): not run. What the code says [disasm]: the autopilot `$37626` calls `$32156` (= `$321fe(5)`) every frame while `$40b6 != 0` and
  `jsr $502c` (back to the sfx tick) when bit 4 of `$40e0` is set; the ST study saw tune 5 play only ~2.1 s (stopped by a `$502c`, and never restarted because
  `$7626` stays 5). So the ST asks for **tune 5** (the Amiga's travel screen plays tune 1), and by the original game's own logic it may only sound for the first
  seconds of a route [INFERENCE until run on a long route]. Tune 5 is in the bank (gain 0.25, 12517 Hz).
- The pixel A/B gate (`tools/asn_abtest.py`) with the new blob; `asn_live.py` / `asn_cold.py` with the new layout.
- `asn_mus_test.py clip`, `asn_build.py muswav`, `tools/play.sh --asn` end to end.
- Tunes other than 1 in the game (2, 4, 5, 6, 7, 8, 9, 10, 12, 15, 16, 17 are only proven in Unicorn), the once tune 8 in the game, 60 Hz in Hatari.
- Sound quality by ear: nothing was listened to. Real hardware: nothing.
- The requested "first ~40 s of the intro" WAV was not cut; the whole capture is `work/asn_cold/mus_hd_ste162_1mb.wav` (tune from 58.35 s).

## 5. For the user: what to listen for (once the checklist is done)
- STE / Mega STE: the boot stub's title tune is still the YM (HD ~4 s, floppy ~28 s); from the "Flames of Freedom" / logo screen on it is the Amiga tune 1,
  mono, 12517 Hz, low-passed like the Amiga with its LED filter on, a little quieter than the stub's YM tune. Short drop-outs where the game loads (6.1).
- The game's own fades (key M at the M/J/K screen, door clicks) fade the DMA tune in 3 dB steps every 0.4 s, like the YM.
- 3D view: the Amiga sound effects as before; F5 map: tune 1 again.
- Title/hall/map screens run with ~30 % of the CPU taken by the mixer (pointer and animations slower).

## 6. Known problems
### 6.1 Music stalls during loads; `asn_mus_ld` does not mute them (design error)
The hook at `$27848` stops the DMA at the START of the game's loader `sub_2783E`, but the loader then sets `move.w #$2300,sr` (`$2784e`), the next VBL's
tick restarts the ring, and only later PP's HAGA service masks the interrupts (`HB+$fe0: move #$2700,sr`, restored at `HB+$1164`, `load_fade.md`). So the
ring loops (164 ms) for the masked time anyway. [obs] in the cold boot: silences of only 0.14 / 0.16 s at t = 72.16 / 74.6 s while 0.64 s of ticks were lost.
`$62f2` cannot be used as "loading" flag (it is a general busy flag, `$ffff` in many other places). The loader's exit `$2789a` is taken by the delivery's
`<load-hook>` (and `hookexit` never returns to `$278a0`), so a second hook there is not possible.
Options, best first: (a) a HAGA file patch (like `pp_nofade`) at the service's mask/unmask points (`HB+$fe0` / `HB+$112a`) that calls a mute/unmute entry of
the blob - must be position independent, must not touch `$ff8901` on machines without DMA (call the blob only if `SV+0 == 2`; the blob address is fixed);
(b) in the blob: at `$27848` set a hold flag AND extend core.s `hookexit` (`$B3070`) to clear it (the load hook then has to be installed whenever `asn_mus_ld`
is in the set: `build_image` only adds it when a deferred site exists); the tick neither mixes nor restarts the DMA while the flag is set (music pauses for
the whole file load on HD; leave floppy alone, its VBL keeps running). Until then `asn_mus_ld` can simply be left out of the set (nothing depends on it).
Note the tune also loses time during these stalls (as the YM tune does): that is the original behaviour, not a port bug.

### 6.2 Hall silent in my run - cause open
`st_music.md` (original game) saw the hall restart tune 1 about 3 s after the M-key fade ended. In the cold boot above the hall stayed at `$b9a = $f`,
`$7626 = 0` for at least 20 s (and again after leaving the personnel screen), while personnel, map and F5 restarted the tune. The game's tune logic does not
read the driver, so the port is not an obvious cause; candidates: the default patch set, or my harness timing (e.g. a key press landing on the music on/off
toggle `$26358`/`$763a`). NOT investigated. Check: the same walk on `build/game` (default set, no asn) and on the unpatched game, reading `$7626`, `$b9a`,
`$763a` in the hall.

### 6.3 Smaller
- The first HD title tune (boot stub) stays YM. To change it: `mw2patch.py`'s copy routine (RUNME text `$3A8` is already ITS staging jump) would have to
  plant `jsr hook` over the stub's `$4da4a` (`61000106 7000`), the hook = `jsr $4db52` + the two table longs + `moveq #0,d0`; core.s must then accept an
  already-patched `$806` (boot sites fail on any mismatch today), the ring must be stopped at `$3104` (no `asn_wd` in the stub phase) and muted during the
  stub's own file-9 load. Floppy: stage 1 (the file-10 read) would have to move before `$4da50`, +8-10 s before the title tune starts.
- A missing `FILES\ASNBANK.BIN` still crashes an asn build (the sites jump into zeros) - as before this work.
- `asn_mus_cold.py`'s effect check at the 3D view reads the voices too late (shows only the changed period).
- Two gain levels among the tunes (0.35 / 0.25): tunes 4, 5, 8 play 2.9 dB quieter than the others.

## 7. Remaining work, in order (each step small; do not skip the checks)
1. **DONE (quick path, section 10): `asn_mus_ld` removed**; 6.1 stays open. (Original text: remove `asn_mus_ld` from `tools/play.sh` and `work/asn_mus/build.sh`, delete `patches/asn_mus_ld.s`, the `asn_mload` routine
   and its entry.) Check: `asn_mus_test.py unit` ALL OK, `verify` ALL OK.
   Proper path: option (a) or (b) of 6.1, then a cold boot must show no ring repeat at t ~ 72 s (autocorrelate the WAV at 8192 capture samples).
2. **DONE (section 10)**: `python3 tools/asn_mus_test.py clip` -> every tune "overflowing samples 0"; no gain change.
3. **DONE (section 10)**: hall (6.2): the default build and the unpatched game are silent there too; not the port.
4. Cold boots, ONE AT A TIME, all with `tools/asn_mus_cold.py run` (build first with `work/asn_mus/build.sh`):
   `fl_ste162_1mb ste 162 1024 floppy build/mus/fl`; `hd_mste206_4mb megaste 206 4096 hd build/mus/hd`; `hd_st104_1mb st 104 1024 hd build/mus/hd`;
   `hd_tt306_4mb tt 306 4096 hd build/mus/hd`. Acceptance: STE/Mega STE lines like 3.3 and all bank checks 0; ST/TT: "YM machine: mode 1 ... True" on all four
   flags and a non-zero WAV rms during the tune. The floppy/YM branches of the tool are untested: expect to fix small things.
5. Accelerated time: restore `work/asn_mus/mus3d.sav` (`Hatari(snapshot=...)`, STE 1 MB; it already holds the patched RAM), F5, key icon (bottom left) ->
   waypoint icon -> click a far spot -> key -> far-left icon; poll `$5138`, `$7626`, `SV+$12` (DMA tune), `SV+$d0` (ticks) once a second for the whole route.
   Report: tune requested (5), how long it plays, what plays after. Acceptance: no stuck ring, `$ff8901 = 0` or sfx after the `$502c`.
6. Pixel gate: `python3 tools/asn_abtest.py --only asn_core asn_wd asn_lvc asn_lv1 asn_lv2 asn_mus asn_mus_ld --flips 10` and `--flips 40` -> IDENTICAL on both
   snapshots; negative control: the same + `test_sky` -> DIFFER.
7. `compare`: make the lag search per segment +-1.5 s (it is +-120 ms around a global onset now) so the stalls are followed; acceptance: rho > 0.7 in every
   5 s segment of the first 40 s, other tune ~ 0. Then cut the 40 s WAV for the user from `work/asn_cold/mus_hd_ste162_1mb.wav` (58.35 s .. 98.35 s) into
   `work/asn_cold/mus_intro_40s.wav`.
8. `tools/play.sh --asn --machine ste --ram 1024` once (it launches a visible Hatari: only with the user's consent).
9. Docs, same style as the existing asn entries: `patches/README.md` (section "Amiga sound effects ..." -> add music, new bank layout `$BF800` blob / ring
   2048 / 176 KB / ends `$E61B2`), `patches/PATCHES.TXT` and `FLOPPY.TXT` (optional feature line: music too, patch names, floppy track-sides 81-126),
   `.omp/skills/mw2-patching/SKILL.md` (owner table row `$BB000-$E61B2`, the `asn_wd`/`ASN2` refusals), `work/notes/amiga_sound.md` (layout numbers).
10. Leave everything `default: no`. Do not commit (the lead does).

## 8. Traps hit (each cost time)
- **vasm shortens `jmp label` to `bra.s`/`bra.w`.** The first entry table was 2-4 bytes per entry; every site jumped into the middle of it and the game hung
  on the "Flames of Freedom" screen (the palette fade `$27228` behind `asn_wd` never ran, main loop waits on `$541c`). The table is now `dc.w $4ef9 / dc.l`
  (macro `JENT`), `asn_build.py` checks the 8 entries, and the Unicorn tests call through the table addresses (`asn_mus_test.ENTRY`), not the labels.
- A global label in the middle of a routine ends vasm's local-label scope (`mw_rts` broke `asn_microwire`'s `.out`).
- `build/play-asn/FILES/ASNBANK.BIN` is copied only on the first run of play.sh: an old bank + new RUNME = crash. Fixed in play.sh; any other copied game dir
  with an old `ASNBANK.BIN` has the same problem (the magic `ASN2` only protects the blob's own gate, not the jumps).
- Patterns share tails (4 overlaps): copy address ranges, not parsed patterns, and rewrite each pointer once.
- An envelope with no steps is `volsub, voladd, $00ff`: the hold reads the word BEFORE the terminator = the voladd word. Copy envelopes verbatim.
- `$62f2` is not a loader flag. The loader re-enables the VBL (`$2300`) right after its entry; the masking is PP's, later.
- The capture's coarse alignment by envelope dot product locks on the louder YM stub tune: use a normalised correlation and pass the onset.
- `Hatari.profile` reports ~141 k cycles per VBL in total; percentages here are of 160 256.
- `/tmp/hatari.sav` is the shared default memstate path of every cold-boot harness instance (`savemem`): do not snapshot while another agent's run may.

## 9. MusicDocs: `compare` with a followed lag, the 40 s WAV, user docs
Evidence tags as above. Checklist steps 7 and 9 done (step 7's acceptance is met only with 2.5 s segments, see below).
- New command `python3 tools/asn_live.py mcompare WAV T0 [--secs 40] [--tune 1] [--other 5] [--seg 5] [--win 1.5]` (`asn_live.cmd_mcompare`, uses `asn_mus_cold.spectro/scorr/model_pcm`; the old
  `asn_mus_cold.py compare` and `asn_live.py compare` (sfx) are unchanged). Per segment the lag is searched +-1.5 s around the PREVIOUS segment's lag (the first: around T0), coarse 20 ms steps,
  then 32-sample steps; "offset" = where the tune starts in the capture, relative to T0.
```
$ python3 tools/asn_live.py mcompare work/asn_cold/mus_hd_ste162_1mb.wav 58.35 --secs 40            [obs]
segment   rho(model tune 1)   offset ms vs T0   rho(model tune 5)   rho(capture shifted 1.5 s)
  0.0 s         0.870          +379.2         0.014                0.057
  5.0 s         0.798          +380.0        -0.018               -0.023
 10.0 s         0.290          +700.4        -0.041                0.050
 15.0 s         0.406         +1020.7         0.036               -0.019
 20.0 s         0.829         +1019.0        -0.027               -0.032
 25.0 s         0.836         +1019.8        -0.022               -0.045
 30.0 s         0.827         +1020.6        -0.088                0.018
 35.0 s         0.792         +1018.8        -0.021               -0.086
mean rho 0.706 (min 0.290); other tune -0.021; shifted -0.010
$ ... --seg 2.5
  0.0 s 0.855 +379.2 | 2.5 s 0.856 +380.0 | 5.0 s 0.785 +380.8 | 7.5 s 0.800 +381.6 | 10.0 s 0.851 +379.8 | 12.5 s 0.358 +700.2 | 15.0 s 0.313 +1020.6 | 17.5 s 0.768 +1018.8
 20.0 s 0.839 | 22.5 s 0.819 | 25.0 s 0.777 | 27.5 s 0.856 | 30.0 s 0.852 | 32.5 s 0.788 | 35.0 s 0.756 | 37.5 s 0.840        (mean 0.757, min 0.313; tune 5: -0.022; shifted -0.014)
$ ... --tune 5 --other 1   (control: tune 5 as the model)   rho 0.055 0.048 0.071 0.063 0.041 0.051 0.136 0.055 ; mean 0.065
```
Reading: the capture IS the model's tune 1 over the whole 40 s (0.76-0.87 in every 2.5 s segment except the two that hold a stall; 0.00 +-0.1 for tune 5 and for a 1.5 s shift). The tune starts 380 ms after
58.35 s (the first segment's own offset), then the capture falls 640 ms behind the model in two steps of 320 ms in the segments at 12.5 s and 15.0 s (t = 70.9-75.9 s of the capture, the
loader stalls of 6.1: the game's VBL stops, the tune loses time). A single lag per segment cannot describe a stall INSIDE the segment, so with 5 s segments the two that contain one score 0.29 / 0.41:
the "rho > 0.7 in every 5 s segment" criterion is not reachable by a lag search alone; it holds for every segment without a stall, and for all 2.5 s segments but those two.
- `work/asn_cold/mus_intro_40s.wav` cut from `mus_hd_ste162_1mb.wav`, 58.35 s .. 98.35 s, 40.00 s, 50066 Hz stereo 16 bit (8.0 MB; git-ignored `*.wav`). No Hatari run.
- Docs updated for the state after `asn_mus_ld` was removed (7 blob entries `+$00..+$24`, blob 3 614 B, bank 176 562 B to `$E61B2`, ring 2048, patches `asn_core asn_wd asn_lvc asn_lv1 asn_lv2 asn_mus`,
  floppy track-sides 81-126): `patches/README.md` (section "Amiga sound effects and music ..."), `patches/PATCHES.TXT`, `patches/FLOPPY.TXT`, `.omp/skills/mw2-patching/SKILL.md` (owner row `$BB000-$E61B2`),
  `work/notes/amiga_sound.md` (superseded-layout note). The loader-stall problem (6.1) is listed as a known issue there. Note: sections 1.2/2/6.1 above still mention `asn_mload` / `asn_mus_ld`
  (history; MusicCold removed them).

## 10. MusicCold: `asn_mus_ld` removed, clip, hall, the four remaining cold boots
Evidence tags as above. Checklist steps 1-4 done; the cold-boot matrix is complete (STE HD, STE floppy, Mega STE HD, ST HD, TT HD).
### 10.1 Step 1: `asn_mus_ld` / `asn_mload` removed (quick path; 6.1 is NOT fixed, the loader stall stays open) [obs]
- Deleted `patches/asn_mus_ld.s` and `asn_mload` from `patches/asn/blob.s`; the blob now has **7** entries (`+$00..+$24`, first code at `+$2a`), not 8: the 8th had no use,
  a dummy entry would be dead weight. `tools/asn_build.py`: entry check `range(7)`, target `>= CODE + 42`; `asn_mus_test.ENTRY` 7 names, the two `mload` checks of `unit_iface` deleted (20 checks left);
  `tools/play.sh` and `work/asn_mus/build.sh` build `asn_core asn_wd asn_lvc asn_lv1 asn_lv2 asn_mus`; stale mentions in `patches/asn_core.s` / `asn_mus.s` notes fixed.
- Blob 3 614 B (was 3 658), the bank is unchanged in size (176 562 B, ends `$E61B2`; the blob lies in a zero-padded window). `asn_tick` is now `$bf82a`.
```
$ python3 tools/mw2patch.py verify                     -> verify: ALL OK
$ python3 tools/asn_test.py unit --ticks 300           -> driver 123 runs 0 mismatches; mixer 300 trials 0; amiga 41x3x300 0
$ python3 tools/asn_mus_test.py unit --ticks 1700      -> spec 0, player 13 tunes x 1700 VBL all 0, 60 Hz 0, underruns 0, fade 0, mixer 0, iface 20 checks failed: none, RESULT: ALL OK
```
The 6.1 problem is unchanged: the HD loader's masked time (PP's HAGA service, `$2700`) still repeats the 164 ms ring; the options (a)/(b) of 6.1 remain the way to fix it.
### 10.2 Step 2: `clip` [obs] (`python3 tools/asn_mus_test.py clip`, 5.6 s; exact integer mix over each whole loop, normal volume): no tune overflows, gains unchanged
```
tune  1: gain set 2 (0.35), 6593 ticks, largest |sum| 110 of 127, overflowing samples 0 | tune  5: set 1 (0.25) 1601 ticks 83 | tune 2: set 2 51 | tune 4: set 1 104 | tune 6: set 2 110
tune  7: 70 | tune 10: 79 | tune 15: 91 | tune 16: 79 | tune 17: 96 | tune 8: set 1 95 | tune 9: 95 | tune 12: 96        (every tune "overflowing samples 0")
```
### 10.3 Step 3: hall silent (6.2): NOT caused by the port [obs]
The same walk (`tools/asn_mus_cold.py run X ste 162 1024 hd BUILD --intro 8 --to hall`, STE TOS 1.62, HD, 1 MB) on `build/mus/def` (the DEFAULT patch set, no `asn_*`, built from `mw2patch.py list`'s defaults)
and on `build/none` (no patches of ours): identical game state to the port's run.
```
default build (mode 0 = no blob, YM driver ticking 2045 cycles/VBL, $5138 = 00000d0e):
[logo] t=62.23 $b9a= 2 $7626=0001 | [M-key] t=108.15 $b9a= 2 $7626=0001 | [fade0..2] t=117.18..127.98 $b9a=15 $7626=0000 | [hall] t=136.89 $b9a=15 $7626=0000
[personnel] t=167.44 $b9a= 2 $7626=0001 (the personnel screen restarts the tune) | [hall2] t=184.70 $b9a=15 $7626=0000 | [map] 214.97 $b9a=2 $7626=0001 | island/objectives $b9a=2 $7626=0001
build/none: the same: [fade0] 124.07 $b9a=15 $7626=0 ... [hall] 143.81 $b9a=15 $7626=0 | [personnel] 174.34 $7626=1 | [hall2] 191.60 $b9a=15 $7626=0
WAV (20 ms rms in 5 s windows from the hall state on): default 0, 0, 417, 3173, 3616, 3613 ; none 0, 0, 34, 2427, 3831, 3611  (silent in the hall, the YM tune comes back at the personnel click)
```
So the unpatched/default game also leaves `$7626 = 0`, `$b9a = 15` in the hall for >= 13 s (the YM is silenced by the game's own fade end `$322d6`); the port reproduces exactly that
(STE HD/floppy, Mega STE: hall `$b9a=15 $7626=0`, tick installed and running, DMA off, resumed at personnel). The hall start of `st_music.md` table row 7 (`$321fe` from the hall area `$1cee8`)
did NOT occur in any of my walks (8 s of hall without input, then the click on the personnel door); what triggers it in the study's walk is not established [INFERENCE: some input or hall state the harness does not produce].
It is not an issue of the port and not related to the vtable start/silence path (`$7626` is the game's own variable; the port's `asn_mstart` was never asked).
### 10.4 Step 4: cold boots [obs] (`tools/asn_mus_cold.py run`, raw logs `work/asn_cold/mus_<cell>.txt/.json/.wav`; blob/bank from the `work/asn_mus/build.sh` build)
| cell | result | key numbers |
|---|---|---|
| `fl_ste162_1mb ste 162 1024 floppy build/mus/fl` | PASS | tune 1 at the logo (`$5138 = 000bf81e`, `$ff8901 = 03`, `$ff8921 = 81`) 62-68 s after power-on, the whole floppy swap-prompt, M/J/K, hall (`$b9a=15`, DMA off, like HD), personnel/map/island/objectives/boss: music tick + DMA tune 11/11, session 2 11/11; 3D view: session 1, `$5138 = 00018f92`, `$ff8921 = 80`, effects 2 and 4 requested (voice 3 vol 63 period 540 = helicopter engine; periods 520 / 888 in voice 0); F5: tune 1 again (`$5138 = 000bf81e`); bank 0 differing bytes at mjk/map/boss/3d/f5; blob 29.1 % of a frame (music) / 5.1 % (3D sfx) |
| `hd_mste206_4mb megaste 206 4096 hd build/mus/hd --no-profile` | PASS | "mode 2 at every stage True; music stages with a DMA tune 16/16, session 2 16/16, `$5138` = music tick 16/16"; bank checks all 0 (intro, mjk, hall, map, boss, 3d, f5); 3D: session 1 6258 Hz, effects 2/4 ran; F5 tune 1 again. WAV 383 s, rms 2428 for the first 30 s of the tune |
| `hd_st104_1mb st 104 1024 hd build/mus/hd --no-profile` | PASS | "YM machine: mode 1 at every stage True; DMA tune never set True; blob DMA flag never set True"; `$ff8901` reads `ff` at every stage (no DMA hardware: the debugger sees the open bus, `$ff8921 = 00`), so the tool's old `$ff8901 == 00` check printed False (fixed, see below), DMA never started; bank checks 0; YM audible: WAV rms 3590 in the first 30 s of the tune (boot stub 4935), 304 of 348 one-second windows rms > 100, max 7517; the silent intervals (140-173 s, 200-211 s) are the hall (`$b9a=15`) |
| `hd_tt306_4mb tt 306 4096 hd build/mus/hd --no-profile` | PASS | "mode 1 at every stage True; DMA tune never set True; `$ff8901` never started True; blob DMA flag never set True"; bank checks 0; WAV rms 3672 in the first 30 s (stub 3652), 281 of 329 windows > 100, max 6642; silent intervals 117-152 s and 176-189 s = the hall |
Floppy and the three new machines match the STE HD cell of 3.3 (tune 1 from the logo on, `$b9a` fade by the game's M key, restart at personnel/map/F5, sfx at the 3D view, bank intact); the floppy cell has no
bank check at the intro and hall stages (the tool only does them on HD; mjk/map/boss/3d/f5 were checked, all 0).
Problems found while running (harness, not port) and fixed in `tools/asn_mus_cold.py`:
- **Floppy "3D view" came too early**: the first floppy run (`work/asn_cold/mus_fl_ste162_1mb_run1_early3d.txt`) took `$6220 == 0xD and $700a == 2` for the 3D view while the mission was still loading (the helicopter preview), so the
  "3d" state still showed the music tick and the F5 was pressed too early. The stage now also waits for `$5138 == 00018f92` (up to 200 s) and then 15 s; the rerun is the table row above.
- **Mega STE profiler**: `h.profile(250)` hangs for 300 s ("VBL breakpoint never fired") on the Mega STE (a 20-VBL profile returned no data, a second one never returned and Hatari died; cause not looked into).
  New option `--no-profile` (used for Mega STE, ST and TT); the music CPU cost is therefore only measured on STE (HD 29.4-30.4 %, floppy 28.8-29.7 % of a frame, 3D sfx 5.1 %).
- **ST: `$ff8901` reads `ff`** (no DMA registers): the YM verdict accepts `00`/`ff` on the plain ST, `00` on the TT (the TT has the DMA registers and reads `00`).
- **YM audibility**: the per-state "WAV rms before each state" line (first version) is not meaningful: the capture is shorter than the emulated time (383 s vs ~450 s on Mega STE/TT; Hatari drops sample
  time around the debugger pauses), so a state's `t` does not index the WAV. Replaced by `wav_silences()`: seconds with rms > 100 and the silent intervals >= 2 s; the stale TT output line in `mus_hd_tt306_4mb.txt`
  (`mjk=0 M-key=0 3d=0 ...`) is that old, misaligned output: the same WAV analysed with the new function gives the silent intervals above (117-152 s, 176-189 s = hall), and rms > 100 elsewhere.
  `asn_live.py` WAV helpers were not touched.
### 10.5 Final gates (after all edits) [obs]
```
verify: ALL OK | asn_test unit --ticks 300: mismatches 0 (driver, mixer, amiga) | asn_mus_test unit --ticks 1700: RESULT: ALL OK | clip: 13 of 13 tunes "overflowing samples 0"
```
### 10.6 Still open after this section
Loader stall 6.1 (HD loads: the tune loses 0.4-0.6 s, ring repeats ~0.15 s), accelerated time (step 5), pixel gate (step 6; its `--only` list must drop `asn_mus_ld`), `tools/play.sh --asn` visible run (step 8), listening by ear, real hardware.

## 11. MusicAccel: pixel gate (step 6) and accelerated time (step 5)
Evidence tags as above. **Step 6 DONE (passes, negative control differs). Step 5 DONE (no failure; the answer is "tune 5 plays ~2.2 s, then the 3D sfx path"; the original YM does the same for ~2.1 s).** No tree file was changed (only new scratch scripts, below).
### 11.1 Step 6: pixel gate [obs] (`python3 tools/asn_abtest.py --only asn_core asn_wd asn_lvc asn_lv1 asn_lv2 asn_mus --flips N`; `mw2patch.py list` names the patch `asn_mus`, the list has no `asn_mus_ld`)
```
--flips 10: 1mb_ingame_walking: pixels IDENTICAL; fps base 3.1 (63 flips) -> patched 3.2 (64 flips) | 1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (85 flips) -> patched 4.0 (80 flips)
--flips 40: 1mb_ingame_walking: pixels IDENTICAL; fps base 2.8 (56 flips) -> patched 2.5 (49 flips)  | 1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (84) -> patched 4.0 (81)      (exit 0)
negative control, the same list + test_sky, --flips 10: walking: pixels DIFFER (36640 bytes) | foot: pixels DIFFER (34888 bytes)    (exit 1)
```
(The fps lines are reported, not gated; the 40-flip walking run was 2.8 -> 2.5 under host load, the others within 5 %.)
### 11.2 What the code does (so the numbers below are expected) [disasm, `tools/m68dis.py work/dumps/ram_ingame_lobos.bin`]
- The F5 map's icon row (hover the key bottom left at screenshot (140,415), WAIT ~2.5 s for the row): icon 6 (plane + dots, x ~ 527) = waypoint mode (`$40b6 := $ffff`, `$25864`). **In waypoint mode a left click ZOOMS the map (each click, no waypoint)**;
  **SPACE adds a waypoint** to the list at `$10d5e` (words x,y; first entry = the helicopter, terminator `$ffff`; `$24e90`). The far-left icon (`$31116`) refuses an empty list ("message", `$12e37`), else `$37922` sets `$40b8 := $ffff`,
  `$311ea`, `jmp $370ee` = world reload. (The old study's "click a far spot" is a SPACE press, not a click; a mouse click only zooms and leaves no route: two of my first runs returned to the 3D view with no "Auto Route".)
- **Tune 5 is requested from the F5 screen, not from the flight**: `$310c8..$310d4` (`not.w $40b6; jsr $37a0a; jsr $32156` = `$321fe(5)`) runs when the route is started in the map; the world is then reloaded (silent loading screen), and the 3D start
  `$32488: jsr $502c` (`$338c2`: park, then `$5138 := $513c = $18f92`) ends the music. So tune 5 sounds for the loading time of the world reload, and that is all. The autopilot `$37626` calls `$32156` every frame but `$7626 == 5` dedupes it; it calls
  `$502c` again only when the route follower flags the end (`btst #4,$1a(a0)`, `$37666`) or when `$12(a5)` ends it (`$376e8`).
### 11.3 Step 5: the run [obs] (scripts `work/asn_mus/accel_route.py SNAP TAG [--wp x,y ...] [--exact]` and `accel_an.py TAG`; output `work/asn_mus/accel/<tag>/` = `samples.log`, `run.txt`, screenshots, `*_start_mid_end.png`)
Route (identical in both games): F5, key, waypoint icon, SPACE at four spots (listing `04800b48 08b00d60 07200a90 090008d8 05b808d8 ffff`, = Lobos -> the NE island -> E -> SE -> S, far over the sea), key, far-left icon.
Sampler: breakpoint `b pc = $262c2 :25 :trace :file samp.txt` (the game's VBL handler, every 25th hit = 2 samples per emulated second): `e VBL`, `$5138`, `$7626`, `$b96`, `$b9a`, `$ba2`, SV (`$BBE00`, 24 B), SV+`$d0` (ticks), `$ff8901`, `$ff8909` (ring position), `$ff8921`, `$6220`, `$700a`, `$40b6`, YM shadow `$bc0`, `$6888`.
Port (`work/asn_mus/mus3d.sav`, run `port2`): **1726 samples over 866.7 s emulated (VBL 20907..64286), median spacing 25 VBL, largest gap 89 VBL (island reloads)**. Click on the far-left icon at VBL 25064; route end (`$6220 = 17` parachute, the helicopter ditched over the sea) at VBL 62736 = **752 emulated seconds, 12:05 -> 14:05 game time**.
```
VBL 20907 t=0     $5138=000bf81e (music tick) $7626=1 act=2 (music) dma on tune 1 rate 1 $ff8901=03 $ff8921=81    (F5 map: tune 1; DMA off 25 VBL once at 21073 = the F5 load)
VBL 25064 (click) tune 1 restarted by the world-return `$32f20` (asn_mstart at VBL 25226 in run port3), DMA off ~25 VBL at 25296 (reload), tune 1 again
VBL 26312 $7626=5 $b96=5 tune=5 act=2 dma on rate 1 $ff8921=81  <- TUNE 5 on the DMA (12517 Hz)
VBL 26412 $5138=00018f92 act=1 (sfx) rate 0 $ff8921=80 $ff8901=03  <- sfx tick took over; tune 5 never comes back ($7626 stays 5)
VBL 26412..62736 (725 s): the same state in all 1450 samples: $5138=00018f92, act 1, sfx 6258 Hz, $ff8901=03 (1500 of 1507 sfx samples have the DMA on; the 7 with DMA off are at VBL 63161-64086, after the ditching: no engine voice -> the sfx session stops the DMA when idle)
```
Exact numbers (run `port3` / `orig2`, `--exact`: breakpoints on `$321fe`, `$33870`, `$338c2`, `$c6c`, `$bf824`, `$3225c`, route cut 6 s after the tune ended; both from the same F5/route script):
```
                      PORT (mus3d.sav)                                   ORIGINAL (work/snapshots/1mb_ingame_foot.sav, unpatched YM)
tune 1 (F5)           VBL 21007 req + asn_mstart (b96=1, $c6c with $b96=0 = the YM parked)   VBL 17821 req + $c6c
tune 1 (world return) VBL 25226                                          VBL 26876
tune 5 request        VBL 26416: $321fe d0=5 -> asn_mstart ($b96=5, $c6c b96=0, $3225c)   VBL 27734: $321fe d0=5 -> $c6c ($b96=5), $3225c
autopilot's call      VBL 26501 $321fe d0=5 (deduped, no start)         VBL 27818
3D start              VBL 26528 $338c2 (park + $5138 := $18f92)          VBL 27838
=> tune 5 plays       112 VBL = 2.24 s                                   104 VBL = 2.08 s          (the earlier ST study: 106 VBL)
after the park        $321fe(5) every 10 VBL (autopilot frame), never reaches asn_mstart; no $c6c/$bf824 hit again     the same (every 5-7 VBL, never $c6c again)
```
What plays (WAV, `--sound 50066`, 100 ms RMS; the WAV starts ~1 s before the click, so VBL times are +0.7..0.9 s there):
- **PORT**: tune 1 rms ~2400; tune 5 2.4-2.5 s at rms 1300-2000 (WAV 25.2-27.7 s); from 27.8 s to the end of the flight a CONSTANT rms 2325-2326 (the 3D game's helicopter engine on the DMA, sfx path, 6258 Hz), 781 of 783 one-second windows have rms > 100; after the ditching (WAV 753 s) low sfx 66-430.
- **ORIGINAL**: tune 1 rms ~3600; tune 5 rms 4600-5100 for 2.05 s (WAV 18.8-20.85 s); from 20.9 s on a CONSTANT rms 1840-1890 (the YM engine drone of the original 3D sfx driver) to the end; 612 of 612 one-second windows have rms > 100; the same ditching/parachute at VBL 55877 (route end).
  `run orig1`: click at VBL 26723, route end (`$40b6 = 0`, `$6220 = 17`) VBL 55877 = 582 s; samples 1546, `$5138` `00000d0e` until VBL 27726 then `00018f92`, `$7626 = 5` from VBL 27626.
So the behaviour to match IS what the port does: tune 5 for the world reload only (~2.1-2.2 s), then the game's own engine sound (YM drone / DMA engine) for the whole route, nothing else. Ring/DMA: at the tune-5 -> sfx hand-over `$ff8901` is 03 in every sample before and after
(samples are 25 VBL apart, so a shorter gap would not show), `$ff8921` goes 81 -> 80 (12517 -> 6258 Hz). **No stuck ring**: in the sfx session the blob's ring cursor (SV+4) differs between EVERY pair of consecutive samples (0 equal pairs of 1500, 256 distinct values), `$ff8909` mid byte took all of `$c0-$c7`, `$ff8901 = 03` throughout (except the 7 idle samples after the ditching).
Island changes of the route (the world reloads, `$6220 = 0` for ~2-3 s: screens "Brokem Hollow / Fortune Bay / Forte Fields / Lion Island / Wildgrass / Atlantic Ocean") do NOT request a tune (`$7626` stays 5) and do not disturb the sfx tick.
Anomalies (not accelerated-time specific) [obs]: music ticks per VBL while the F5 map scrolls in / the world reloads: 25 ticks per 33 VBL (VBL 20957-21164 and 25189-25387; the game's VBL handler site `$262c2` was reached only 25 times in 33 VBL) = the tune runs 24 % slow for ~3-4 s there
[INFERENCE: the HD loader's masked time, 6.1], and the DMA is off for ~25 VBL once per map entry / world return (VBL 21073, 25296) [INFERENCE: the game's own tune-1 restart, `asn_mstart` hit at VBL 21007 / 25226]. The original loses VBLs too (largest sample gaps 356 / 290 / 256 VBL at island changes).
Screenshots at start / mid / end (`work/asn_mus/accel/port2/port2_start_mid_end.png`, `.../orig1/orig1_start_mid_end.png`): start = Lobos 3D cockpit 12:05, mid (WAV-time ~392 s) = Atlantic Ocean message at 12:45 / then 13:25 open sea (N, 308 kt), end = the parachute/dinghy view 14:05.
### 11.4 Not done / notes
- Both the route and the original comparison used the same F5 script, but different snapshots (port: `mus3d.sav`, own cold boot; original: `1mb_ingame_foot.sav`); the Lobos start state and the route list are identical (`$10d5e` list above), the route end differs in length only through frame rate (752 s vs 582 s).
- Tune 5 on the DMA is 4-6 dB (rms 1300-2000 vs 4600-5100) quieter than the YM's tune 5 (gain set 1 = 0.25, low-pass); not judged by ear.
- `tools/mw2harness.py` `Hatari.rel/goto` in the F5 map: the pointer only follows after the map has finished scrolling in (wait >= 25 s after F5 with the music mixer running) and the icon row needs ~2.5 s of hover before a click lands on it (a click earlier = "return to world" loading screen without a route).
- Scratch left in the tree: `work/asn_mus/accel_route.py`, `accel_an.py`, `work/asn_mus/accel/{port2,port3,orig1,orig2}/` (samples, screenshots, the two 40 s WAVs `port3.wav` / `orig2.wav`; the long-run WAVs were deleted after analysis).
