# Moonshine Racers: the Amiga version (study of the four ADFs, audio, DMA-sound verdict)

Read-only study (nothing in `patches/`, `tools/`, the ADFs or the ST dumps was changed; nothing committed). Scratch, scripts and extracted data: `work/amiga/` (own `.gitignore`: only `*.py`, `race_bank.txt`, `inj_analysis.txt` are tracked-able; ADF-derived RAM images, traces, WAVs, modules, screenshots are ignored).
Evidence tags: **[obs]** seen in a tool run here (Copperline 1.1.0 headless, A500 profile, KS 1.3, 1 MB chip, PAL; Hatari 2.6.1 STE 1 MB for the ST side), **[disasm]** read from a disassembly (`tools/m68dis.py`, Amiga RAM image `work/amiga/ram_race_a.bin` = 1 MB dump of a running race), **[inf]** inference not proven. Raw outputs are pasted in the appendix and live in `work/amiga/`.

## 0. Verdict (one screen)
1. **Reference = `Moonshine Racers Disk 1.adf` + `Moonshine Racers Disk 2.adf`** (2002 dump, no trainer). The 1996 "PeakStar + Millennium" A/B set is the *same game data*: B and Disk 2 are byte-identical (same md5); A differs from Disk 1 only in 2 boot sectors, 1 byte of the core image (crack hook `$0c00` vs `$0d00`), the crack credit text, and 61 extra sectors holding a Punishers/Quartex **21-option trainer** intro. No language or version difference.
2. The Amiga game has **no music in the race**. Race audio = a 4-voice script-driven *sample* engine ("sound by Richard Joseph") with an **81 KB sample bank (28 bodies, native 5.5-16.6 kHz)**. The only music is four ProTracker modules for the front end (intro5, moon, sad5, bar: 61-88 KB each), not used in the race.
3. **The ST sound driver is the same script engine reduced to 3 YM voices** (`$8c00` start-script, `$8c38` interpreter, all requests via the wrapper `$7bb2` = the Amiga `$7b70`: `D0` = script id, `D1` = channel). So the trigger interface is one clean hook point (`$8c00`), the ST ids are renumbered (ST 1-82, Amiga 1-70) and Amiga ch3 requests are dropped on the ST.
4. **DMA-sound verdict**: replacing the YM player by a mixed Amiga-sound engine is **no** (a 2-voice 6 258 Hz mixer costs 7-12 k cycles/VBL = 1.9-3.3x the YM player's 3.6 k, 4 voices 23 k = 6.4x; RAM 49-65 KB (6 258 Hz) or 97-129 KB (12 517 Hz) against ~23 KB free on the 1 MB map). **Yes as an optional STE-only extra that costs less than the YM player**: *unmixed one-shot DMA* (the STE DMA plays one sample by itself; CPU only at the ~1 request per 90 VBL: ~150 cycles per start [inf], 0 per VBL), the engine loop and everything else stays on YM. One-shot subset that fits the 1 MB spare RAM: engine/gear note + crash = 13.6 KB, plus 3 more hit bodies = 19.9 KB at 6 258 Hz (§6).
5. Nothing in the Amiga renderer is a speed lead: it runs at **6-7 VBL per frame (~8 fps) on an A500**, with ~2.4 k small blits per second; its HUD sits in the sky band at the top (the layout the new ST top-bar HUD already has) and it has no clouds. Ideas in §7.

## 1. Image identification

| image | md5 | boot block | what it is |
|---|---|---|---|
| `Moonshine Racers (PeakStar + Millennium) A.adf` (1996) | `2cab2d11e0218578c849b13cc2d872e3` | `DOS\0`, checksum OK, **no AmigaDOS filesystem** (`adf.py info`: "Invalid Root Block"); custom trackloader | Disk 1 of the 1996 release: **Quartex crack** (credit text "BROKEN BY QUARTEX!" at ADF `$5b2e4`, sector 729) with a **Punishers "21 OPTION TRAINER" intro** (screen: "MOONSHINE RACERS - 21 OPTION TRAINER!!", a YES/NO list incl. "ALWAYS COME FIRST", "NEVER LOOSE POSITION", unlimited time / money / moonshine, "START GAME", "CRACKED BY QUARTEX! TRAINED BY ICE!", SPACE starts) [obs boot_015/045.png] |
| `Moonshine Racers (PeakStar + Millennium) B.adf` | `19f7f857beebb3110415f228f702b365` | non-DOS (`Ice!` packed data from byte 0) | Disk 2 (level data + sound/code overlays), same as Disk 2 |
| `Moonshine Racers Disk 1.adf` (2002 dump) | `6d192830382ad5ab0623ccaa56d9635f` | same trackloader, text "This is a CUSTOM bootstrap, do not remove, it is not a virus. PLEASE LEAVE ALONE." | Disk 1, **"BY BLITTER BROTHER"** crack text, **no trainer**: boots straight into the Millennium + Peak Star logo screen [obs d1_020.png], sheriff-car intro, credits ("GAME DESIGN BY PEAK STAR, PROGRAMMING BY PETE HICKINSON AND BILL CAUNT, GRAPHICS BY MARK EDWARDS, SOUND BY RICHARD JOSEPH", "PRESS A KEY" [obs d1_190.png]), manual-lookup protection ("type anything you want": any answer passes), then "Insert Disk 2 and press a key" |
| `Moonshine Racers Disk 2.adf` (2002) | `19f7f857beebb3110415f228f702b365` | = B | byte-identical to B |

A vs Disk 1, sector compare of all 1 760 sectors [obs, raw in the appendix]: 4 runs only: sectors 0-1 (boot block: `$6a: nop` vs `clr.l (a0)+`, other crack bytes, checksum), sector 60 byte `+$114` (`jmp $0c00.w` vs `jmp $0d00.w`, ADF `$7914`, RAM `$1d14` = the crack's hook), sector 729 (credit text), and **sectors 1681-1741 = 61 sectors only in A (the trainer/Punishers code; Disk 1 has zeros there)**. All other 1 698 sectors are identical: the game code, graphics, sound and level data are the same.
Hardware needs seen: OCS/ECS A500, 512 KB chip is enough [inf: the game image ends at `$67a00`, the race sound overlay at `$64470`; I ran with 1 MB].

## 2. Disk layout and loader (no filesystem; sector numbers = ADF 512-byte sector index)
[disasm of `work/amiga/stage2.bin`] Bootblock: copies itself to `$68000`, reads tracks 1-4 (raw MFM, `$77cc0`), jumps. Stage 2 installs a trackloader `$7822c` (`d0` drive, `d1` first sector, `d2` count, `a0` dest, `a1` MFM buffer) and loads **821 sectors from sector 54 (ADF `$6c00`) to `$1000`**: the unpacked game core (code, tables, front-end data, the `intro5` module). The remaining loads are table driven: pairs `(first sector, count)` at `$8a56-$8aa0` (race image) [disasm]; sound-relevant entries:

| overlay | sectors | RAM | content |
|---|---|---|---|
| **race sound overlay** | Disk 1 sector 1331, 173 sectors (88 576 B) | `$4ec70-$64470` | race engine code + instrument table + 81 KB sample bank. Proof: RAM `+$57990` = ADF address for the instrument table (`$6436a` -> `$bbcfa`) and for the 17 458 B sample (`$52d98` -> `$aa728`), code `$4ec70` -> ADF `$a6600` = sector 1331 [obs, byte compare in the appendix] |
| `moon` overlay | Disk 1 sector 1504, 177 sectors (pair at `$8a66`) | | PT replayer (`+0`) + module at `+$6f8` (ADF `$bc6f8`); loaded by `$a9ba`, called from the main loop `$7114` when `$d21 = 1` (front-end mode) [disasm] |
| `sad5` overlay | Disk 2 sector 175, 147 sectors (pair at `$8a82`; `Ice!`, 75 046 B packed -> 84 162) | | replayer + module at `+$6f8`; loaded by `$aa00`, called from `sub_007428` (`$74c2`; reached from the main loop `$7248` after `$8418`) [disasm] |
| `bar` overlay | Disk 2 sector 361, 95 sectors (pair at `$8a8a`; 48 204 -> 63 260) | | replayer + module at `+$6f8`; loaded by `$a9dc`, called from `sub_00755a` (`$75c8`; reached at `$7234` when the race counter `$d2c` reaches `$f`) [disasm] |
| level data | Disk 2, per track: `Ice!` chunks 32 128 B + 3.7-5.8 KB + 7 680 B + 22-25 KB | | road/scenery data, not audio |

Disk 2 is **64 sector-aligned `Ice!` (Pack-Ice 2.x) chunks**. The game's own depacker is at `$8824`; `work/amiga/iceunpack.py` runs that exact routine in `machine68k` (amitools) and `work/amiga/d2extract.py` unpacked all 64 chunks bit-exactly (`work/amiga/d2/sNNNN.bin`). Copperline: `media.floppy.eject` / `media.floppy.insert {drive:0,path}` swaps disks (a second drive is not detected by the game; the prompt waits for df0).
Names/purpose of `sad5` / `bar` / `moon` are [inf] (a lose/continue screen, an end/bar screen, the front-end tune); none of them played in my walk (front end after the disk swap -> first race used only the script engine, §3).

## 3. Audio architecture
Mode byte `$d21` (1 front end / 2 race / 3 other). Two kinds of sound code:
1. **Race engine** (overlay at `$4ec70`): jump table `$4ec70` init, `$4ec76` start script `d0` on channel `d1` (the game's only entry, via the wrapper `$7b70: cmpi.b #2,$d21 / jmp $4ec76`), `$4ec7c` start effect (4 scripts from a table), `$4ec82` per-VBL tick (`$4ed9e`), `$4ec9c` audio interrupt. Four channel records (`$4f602 + n*$92`), each a byte-code script (notes < `$80`, 22 commands `$80-$95` for instrument select (14-byte descriptor `{flags, loop offset, length words, sample ptr, period table}`), envelope, tempo, call/loop, wait, end), per-VBL tick writes period+volume of 4 channels (400 Paula writes/s) and DMA starts via the audio interrupt [disasm `$4ec82-$5330` intro layout, `$4ed2a`, `$4f122-$4f2a0` race layout]. Descriptor flag `$ffff` = looping instrument (the interrupt re-points LC to `sample + w26`, length `w28 - w26/2`), `1` = one-shot (re-arms the silent word `$505a0`, DMA off) [disasm `$4ed2a`]. The same engine (4 channels, same command set) runs the intro with another bank (descriptor table `$26632`, 30 instruments, `$636c-$26632`, 131 KB) at 25-75 s [obs trace].
2. **ProTracker replayer** (stock Noisetracker-style, `$59b00-$5a2ca` in the core; overlays for moon/sad5/bar): the intro module `intro5` plays from 75.4 s to 104.7 s [obs trace_nav1.jsonl: writers `$59c00-$5a0ff`], the front end after the disk swap and the whole race use only the script engine [obs trace_fe2.jsonl: 125 791 audio-register writes from 207.8 s to 516 s, writer pc pages only `$4e000/$4f000`].
**The race has no music**: all 17.6 k Paula events in 44 s of driving come from `$4edfc/$4ee00` (period/volume tick) and the script start path `$4f228-$4f2fa/$4ee10-$4ee28` [obs trace_race1.jsonl].

## 4. Audio assets
### 4.1 Race sample bank (race overlay, `work/amiga/race_bank.txt` = the 39-entry instrument table; WAVs `work/amiga/audio/race_*.wav` at their dominant playback rate)
All bodies are 8-bit signed. 28 distinct bodies (9 are 8-32 B waveform words); total **81 082 B** (without the tiny waves). Rate = 3 546 895 / period (PAL), periods from the Paula trace of each script:

| body (RAM) | bytes | flag | dominant period -> rate | script ids that use it (§4.3) |
|---|---|---|---|---|
| `$50648` | 8 488 | one-shot / loop (inst 9,10,11) | 320 -> 11.1 kHz (also 214, 428) | 23, 66, 67 |
| `$52770` | 1 576 | one-shot | 320 | 24 |
| **`$52d98`** | **17 458** | one-shot | 354 / 404 / 501 -> 10.0 / 8.8 / 7.1 kHz | 29, 30, 31 (ch3, engine/gear note) |
| `$571ca` | 2 930 | loop from 408 | 320 | 25 |
| `$57d3c` | 3 220 | loop | 320 | 26 |
| `$589d0` | 596 | loop | 288..160 sweep -> 12.3 kHz | 27 (countdown, `$f284`) |
| `$58c24 $58f6e $592ea $5960c $59934` | 842 892 802 808 816 | loop (chained) | 641 -> 5.5 kHz | 32 |
| `$59c64` | 1 442 | loop | 1281 -> 2.8 kHz | 33 |
| `$5a206` `$5a94e` | 1 864 / 1 432 | one-shot | 320 | 37 / 24, 36 |
| `$5aee6` | 6 244 | one-shot | 320, 226 | 34, 65 |
| **`$5c74a`** | **2 380** | one-shot | 641 / 539-659 / 719 / 906 / 1209 -> 5.5 .. 2.9 kHz | 35, 61, 62, 63, 64 |
| `$5d096` | 7 740 | loop from 5 638 | 641 -> 5.5 kHz | 38 (countdown, sustained), 18 |
| `$5eed2` | 12 860 | one-shot | 641 -> 5.5 kHz | 39, 18 |
| `$6210e` `$62e04` | 3 318 / 1 658 | one-shot | 214 (16.6 kHz) / 320 | 16, 68, 69 (jingle notes) |
| `$6347e` (3 variants), `$63740 $63a08 $63da8 $64060` | 706, 712, 928, 696, 674 | loop | 571..180 (12 semitone steps) | 3-14, 40-60 (beep scale) |
Size when resampled to the STE DMA rates (mono 8-bit): **all 64.3 KB @6 258 Hz / 128.6 KB @12 517 Hz**; without the two big bodies (`$52d98`, `$50648`) 48.6 / 97.2 KB. **Only the flag-`1` (one-shot) bodies map onto fixed-rate DMA without CPU work**: `$52d98` 10.9 KB, `$5c74a` 2.7, `$5aee6` 3.5, `$5a94e` 0.8, `$5a206` 1.05, `$52770` 0.9, `$5eed2` 14.5, `$62e04`/`$6210e` 2.2, `$50648` 4.8 (KB @6 258 Hz); the loop-type bodies (`$5d096` loop tail, `$589d0` period sweep, the five-body skid chain, beep tones) need loop offsets / period changes per VBL.
### 4.2 Front-end modules (ProTracker `M.K.`; files `work/amiga/audio/*.mod.bin`)
| module | location | songlen / patterns | sample bytes (samples) | size |
|---|---|---|---|---|
| intro5 | core image RAM `$5a2ca` = ADF `$43788` (copy at ADF `$962e0`) | 15 / 22 | 44 220 (12) | 67 832 B |
| moon | Disk 1 ADF `$bc6f8` | 30 / 19 | 67 880 (14: violins, bass) | 88 420 B |
| sad5 | Disk 2 chunk sector 175 + `$6f8` | 3 / 7 | 74 110 (6) | 82 362 B |
| bar | Disk 2 chunk sector 361 + `$6f8` | 4 / 4 | 56 280 (7: piano chords, crowd 26 874 B) | 61 460 B |
### 4.3 Script ids the race really requests (Amiga) [obs: 120 s driving log `calls_race2.json` (32 requests) + all 26 static call sites of `$7b70`; sample/pitch from the injection run `work/amiga/inject.py` -> `inj_analysis.txt`: each id 1-70 started in a running race and traced]
| id (ch) | plays | notes |
|---|---|---|
| 29 / 30 / 31 (ch3) | `$52d98` 17 458 B vol 53 at period 501 / 404 / 354 | **engine / gear sound**, requested from `$ef66` (vars `$d24,$dca`): 7 times in 120 s; one-shot 1.7-2.5 s |
| 61, 62, 63, 35 (ch2) + 65 (ch3, 0.09 s later) | `$5c74a` (vol 60) at 539-659 / 719 / 906 / 641 + `$5aee6` 6 244 B vol 26 | **bump/crash family** (pitch by severity [inf]): `$ec14 $ec74 $ed02 $eda0` + `$c618`; 10 ch2 requests in 120 s, 7 of them followed within 0.1 s by id 65 on ch3 |
| 23 (ch2) | `$50648` vol 63 | `$e976`, once at 521 s (steering left) |
| 24 (ch2) `$dd9e`, 25 (ch3) `$df4c` | `$52770` 1 576 B / `$571ca` 2 930 B vol 63 | pair near `bclr #7,$5da5` |
| 26 (ch2) `$e614`, 66 (ch2) `$e3da`, 32 (ch2) `$e46e`, 36/37 (ch2) `$f59c/$f5ae` | see §4.1 | 66 twice 0.3 s apart at 439.9 s |
| 38 / 39 / 40 / 27 | `$5d096` loop, `$5eed2`, `$6347e` beep, `$589d0` sweep | **start sequence** `$79b4-$7a22`: 40, [27 if `$26c5`], 38 at frame 10, 39 at a random frame 30-45, 40 at frame +22 (verified identical logic on the ST, §5) |
| 68 (ch0) + 69 (ch2) | `$62e04` + `$6210e` jingle notes (7-8 starts/4 s) | `$774e/$7758` at 469.94 s |
Engine pitch/volume modulation is not a script request: the engine tick adds per-channel words `$4ec94..9a` (volume scale) and `$48(a4)` (period offset) every VBL (`$4edf2-$4ee00`).

## 5. ST side: the sound interface and the Amiga counterpart
[disasm `work/dumps/ram_race_start.bin`] ST `$8bf2` (VBL hook from `$d486`: `tst.b $8bf0 / bne / bsr $8c38`), `$8c38` interpreter (jump table `$8c7e`, 17 handlers, YM writes `$8e30-$8e82`), **`$8c00` = start script**: `d0` = id (pointer table `$c974`, 82 scripts, ids 1-82), `d1` = channel 0-2: installs the script pointer in the channel record (`$9344/$937a/$93b0`), clears the 46-byte state. Wrapper `$7bb2` (`cmpi.b #2,$1021.w / tst.b d0 / bmi / cmpi.w #2,d1 / bhi / jsr $8c00`) = Amiga `$7b70` (variables are the Amiga's `$d00-$fff` block shifted by `+$300`: `$d21` -> `$1021`, `$d0e` -> `$100e`), `$7bba` the no-mode-check variant (jingles). 28 + 18 call sites + 4 direct (`$16920`: ids 64/65/66 on ch0/1/2 at race start). **Channel-3 requests never play on the ST.**
ST ids seen in 120 s of driving [obs `work/amiga/st_sndlog_raw.txt`, Hatari breakpoint on `$8c00` over the `ste1m_race_start` snapshot, joystick pattern via `$6105`; 65 requests in 6 000 VBL]: `47` ch2 x15 (each followed by `0` = stop), `63` ch2 x5, `54` ch2 x4, `73`+`74` (ch1+ch2) x4, `56` ch2 x3, `52`+`53` x2. = **about one request per 90 VBL**.
Call-site alignment (same source, same routine order; I matched sites by the variable operands near the call, `work/amiga/match_sites.py`; the first row I also verified line by line):
| game event | Amiga site (id/ch) | ST site (id/ch) | confidence |
|---|---|---|---|
| race start: beep, [flag], engine start (loop), rev (one-shot), beep | `$79b4 40/0`, `$79c4 27/1`, `$79de 38/0`, `$7a04 39/0`, `$7a22 40/0` | `$79ee 46/0`, `$79fe 60/1`, `$7a18 71/0`, `$7a3e 72/0`, `$7a5c 46/0` | **verified** (same code: `$29c7`<->`$26c5`, `$1030`<->`$d30`, frame counter `$100e`<->`$d0e`, random `$102e`<->`$d2e`) |
| 2-voice jingle | `$774e 68/0 + $7758 69/2` | `$776a 57/0 + $7774 58/2` (`$7bba`) | high (3 shared operands) |
| engine/gear note | `$ef66 29-31/3` (vars `$d24 $dca`) | `$118b6 47/2` (vars `$1024 $10ca`) | medium (2 operands); fits the frequency (ST 47 is the most frequent id) |
| the 4 bump/crash sites with variable id | `$ec14 $ec74 $ed02 $eda0` (ch2) + `$c618 65/3` | `$18cf4 $18d54 $18de2 $18e80` (ch2) + `$f652 54/2` | medium |
| `dd9e 24/2`, `df4c 25/3` | | `$10dd6 63/2`, `$10f84 50/1 + $10f8e 51/2` | low (1-2 operands) |
| `$f59c 36/2`, `$f5ae 37/2` | | `$11f16`, `$11f28` with `d0=d1=255` (rejected by the wrapper: **no sound on the ST**) | medium |
| ST `73/74`, `52/53`, `56` | none found | | ST-only or unmatched |

## 6. DMA-sound feasibility (STE / Mega STE; the ST has no DMA sound)
Baselines [from the repo notes]: 8 MHz STE = 160 256 cycles/VBL; **YM player `$8bf2` = 3.6 k cycles/VBL** (rendering.md §sound: 18.8 k/21.8 k per frame at 5-6 VBL); a driving pass today is ~3.06 VBL.
Mixer costs [from Hunter `snd.md` §7 (obs) and MW2 `amiga_music.md` §7.4 (model), same 68000 mixer family]:
| design | cycles per VBL | % of 160 k | vs YM 3.6 k |
|---|---|---|---|
| **A. unmixed one-shot DMA** (start/stop in the `$8c00` hook; one sample plays, DMA stops by itself; YM keeps everything else) | 0 per VBL; ~150 per start [inf: 6 DMA address bytes + mode + control, not measured]; ~1 start per 90 VBL => <2 cycles/VBL average | ~0 % | **far below** |
| B. mixed, 2 voices, 6 258 Hz mono (Hunter, obs) | 11.9 k with two voices at volume 15 (7.4 %), 6.9 k with one voice (4.3 %), 0.3 k idle; (mix loops 5.5 / 8.0 k + 2.0-2.9 k update) | 4.3-7.4 % | 1.9-3.3x |
| C. mixed, 4 voices, 6 258 Hz | 23.0 k (14.4 %) [model: 40 + 3 x 48 cycles x 125 samples] | 14 % | 6.4x |
| D. same at 12 517 Hz | 46 k (28.7 %) | | 12.8x |
| E. full Amiga engine port (script interpreter 4 ch + mixer) | ~26-50 k [inf: ~3 k interpreter + design C/D] | 16-31 % | 7-14x |
Per pass (3.06 VBL) design B costs ~+24-36 k cycles = +5-7 % of the 491 k-cycle pass (not "per frame": the mixer runs on every VBL, so two frames per tick do not dilute it). Mega STE 16 MHz halves the percentages (B: 2.2-3.7 %), not the cycles. **=> B..E break the "audio must not cost more than the YM player" rule; only A (and an optional B on request) satisfies it.**
RAM (STE DMA needs the sample in RAM; mono 8-bit signed, rate in `$ff8921`: 6 258 / 12 517 / 25 033 / 50 066 Hz; native 5.5 kHz material fits 6 258 Hz almost 1:1, the 10-16 kHz bodies lose bandwidth at 6 258 Hz):
- 1 MB map (integration.md §10.4): free runs of the default set `$DE000-$E2BFF` = 19 KB spare + `$BE000-$BEFFF` 4 KB (`ta_*`, free in the default set) => **~23 KB** (other agents are still changing it). One-shot subset for design A at 6 258 Hz: engine/gear `$52d98` 10.9 KB + bump/crash `$5c74a` 2.7 KB = **13.6 KB**; adding `$5aee6` 3.5 KB + `$5a94e/$5a206/$52770` 2.8 KB = **19.9 KB** still fits; the start-sequence rev `$5eed2` (14.5 KB) only fits instead of the engine body. [arith. from §4.1; resample sizes `work/amiga/` session, not built]
- 2 MB / 4 MB STE: everything fits (64 KB @6 258 Hz or 128 KB @12 517 Hz); 4 MB layouts also need the floppy/HD file placement worked out (open question).
Hooks (design A): (1) `$8c00` entry (6-byte `jmp` to the blob): `d0` = ST id, `d1` = channel: look the id up in a 82-entry table (flag, bank offset, length, rate); if present start the DMA (`$ff8901 = 0`, `$ff8903/05/07` start, `$ff890f/11/13` end, `$ff8921` mode, `$ff8901 = 1`) and, to avoid double sound, continue with the silent script (`d0 := 0`) so the YM channel stays quiet; `d0 = 0` for that channel stops the DMA; (2) STE detection + Microwire master/treble/bass once (`_MCH` cookie, as `asn_*`/Hunter); (3) nothing in the VBL hook. Blob ~0.5 KB + 82-entry table 0.5 KB + bank. Both machines use `$ff8900-$ff8925` (Mega STE has it).
Music: the four PT modules are front-end only, 61-88 KB each + a 4-voice mixer (23 k cycles @6 258 Hz, 46 k @12 517 Hz per VBL): affordable where the frame rate does not matter (title/intro: MW2 used the same reasoning), **but the front end's free RAM is not measured here** (open question 1).

## 7. Ideas from the Amiga version
1. **No rendering speed lead.** A500 race frame = 6-7 VBL (104 screen changes in 600 VBL while driving [obs fps.py]; histogram `{6: 72, 7: 17, 5: 5, 1: 4, 2: 3, 4: 2}`), so the original Amiga is not faster than the ST (5-6 VBL); our ST at ~3.06 VBL/pass is already ahead. Blitter use: ~2 400 BLTSIZE writes/s in the race (9 775 in 4 s; mostly 1-2 words wide x 1-15 high, `BLTCON0 $0ffe` copy 380 x, `$0dcf/$0fca/$0bfa` cookie-cut masks), i.e. hundreds of tiny blits per frame, not a better algorithm; the STE blitter has no advantage over the 68000 for such blits (blitter.md numbers in the repo notes).
2. **HUD in the sky band**: thermometer, track-profile graph, clock with seconds, speech text + character portrait are all at the top of the 320x200 view, speedometer + gear + position at the bottom corners [obs race_a/b/c.png]; the road area is never covered by HUD pixels. Same idea as the new ST top-bar HUD (use the Amiga as the layout reference).
3. **No cloud sprites** on the Amiga sky (HUD occupies it), consistent with the ST clouds removal.
4. **Sound script knowledge is portable**: the ST YM driver is the same engine; the Amiga ids/instruments tell what each ST id was meant to sound like (e.g. ST 47 = the engine/gear note: 17.5 KB sample at 3 pitches on the Amiga).
5. The trainer image (A) shows the cheats the game supports (always first, never lose position, unlimited time/money/moonshine, in-game extras): handy if the A disk is used to reach the later races for testing; Disk 1 has no such option.

## 8. Open questions for the user
1. **Scope**: is design A (optional, effects only, STE only, ~14 KB subset at 1 MB, whole set on 2/4 MB) what you want, or also the front-end music (needs the front-end RAM map; 61-88 KB per module)?
2. **Which sounds first?** Candidates by value (one-shot bodies only, §4.1/§6): the engine/gear note (ST id 47 [medium confidence], the most frequent ST request, 10.9 KB @6 258 Hz, 1.7-2.5 s), the bump/crash `$5c74a` family (2.7 KB) + `$5aee6` (3.5 KB), the start-sequence rev `$5eed2` (14.5 KB). Loop-type sounds (ignition `$5d096`, skid chain, sweeps, beeps) stay on the YM.
3. **Rate**: 6 258 Hz (smaller, noisy sub-bandwidth for the 10-16 kHz bodies) or 12 517 Hz (2x RAM)?
4. Is **a mixed 2-voice mode** acceptable as a non-default option (costs +5-7 % of a pass) for machines with spare time (Mega STE at 16 MHz)?
5. May I verify the medium-confidence ST<->Amiga id matches by playing/recording both (Hatari + Copperline) before a port is designed? (Everything marked "medium/low" in §5 is inference from operand matches.)

## 9. How it was done / files
`work/amiga/`: `cl.py` (Copperline session helpers: `Tracer` = MMIO write log of `$dff0a0-$dff0df` + DMACON, as in the MW2 study), `boot1/2.py`, `nav1-5.py` (boot -> credits -> manual check -> disk swap -> race; states `st_*.clstate`), `dump1.py`/`race1.py` (1 MB RAM dumps), `race2.py` (log every `$7b70` call: `break_pc` + `regs`), `inject.py` (start any script id in a running race via `regs.set` at the tick breakpoint `$4ec82`: `d0=id,d1=ch,pc=$4ec76`), `inj_analyze.py`, `fps.py`, `hw.py` (blitter/copper write histogram), `iceunpack.py` + `d2extract.py` (the game's own ICE depacker run in machine68k), `modinfo.py` (PT header parser), `match_sites.py`, `st_sndlog.py` (Hatari `$8c00` logger), `fe.py`/`fe2.py` (front-end audio writer timeline). Disassemblies kept locally: `snd_disasm.txt`, `sfx_disasm.txt`, `sfx_callsites.txt`, `race_eng*.txt` (ignored).

## Appendix: raw outputs
```
$ md5sum alt/amiga/*.adf
2cab2d11e0218578c849b13cc2d872e3  ...(PeakStar + Millennium) A.adf
19f7f857beebb3110415f228f702b365  ...(PeakStar + Millennium) B.adf
6d192830382ad5ab0623ccaa56d9635f  Moonshine Racers Disk 1.adf
19f7f857beebb3110415f228f702b365  Moonshine Racers Disk 2.adf
$ python3 tools/adf.py info A.adf   -> "OFS bootblock, flags=$00, root block 1, checksum OK ... (no AmigaDOS filesystem: Invalid Root Block)"
$ python3 tools/adf.py info B.adf   -> "non-DOS bootblock: magic=496365 (custom loader / trackloader)"
A vs Disk 1 sector diff runs (A=1996 trainer set, per 512 B sector): [0,1] [60,60] [729,729] [1681,1741]   (4 runs; 29 151 differing bytes in total)
sector 60 +$114: A `4ef8 0c00`  D1 `4ef8 0d00`;  sector 729: A "...BROKEN BY QUARTEX! ..."  D1 "...BY BLITTER BROTHER ..."
bootblock string (both): "This is a CUSTOM bootstrap, do not remove, it is not a virus. PLEASE LEAVE ALONE."
```
Loader (`work/amiga/stage2.bin`, base `$77cc0`): `0781fc: moveq #0,d0  0781fe: moveq #$36,d1  078202: move.w #$335,d2  078206: lea $1000.w,a0  07820a: lea $6b800.l,a1  078210: jsr $7822c.l ... 078228: jmp $1000.w` (sector `$36` = 54, count `$335` = 821).
Race overlay location proof (byte compare RAM vs Disk 1): `engine code $4ec70 -> ADF $a6600 (sector 1331)`; `instrument table $6436a -> ADF $bbcfa` (= RAM + $57990); `sample $52d98 -> ADF $aa728` (= RAM + $57990).
Instrument table (race, `$6436a`, 14 B entries `{flags,loop,len words,ptr,period tab}`): see `work/amiga/race_bank.txt`, e.g. `13 flags=0001,0000 len=17458 ptr=052d98`, `27 flags=0001,0000 len=2380 ptr=05c74a`, `28 flags=ffff,1606 len=7740 ptr=05d096`.
Calls of `$7b70` during 120 s of driving (`time, pattern, d0, d1, return`): `[413.444,upL,30,3,0xef6c] [414.687,upL,61,2,0xec1a] [414.782,upL,65,3,0xc61e] [420.601,upR,61,2,0xed08] [431.17,down,31,3,0xef6c] [439.02,upRF,35,2,0xec7a] [439.938,upRF,66,2,0xe3e0] [469.942,upLF,68,0,0x7754] [469.943,upLF,69,2,0x775e] [477.216,upRF,38,0,0x79e4] [480.021,up,39,0,0x7a0a] [482.224,up,40,0,0x7a28] [520.955,upL,29,3,0xef6c] [521.424,upL,23,2,0xe97c] ...` (32 rows).
ST `$8c00` request ids (Hatari, 65 events, masked words): `Counter({(0,2):21,(47,2):15,(63,2):5,(0,1):5,(54,2):4,(73,1):4,(74,2):4,(56,2):3,(52,1):2,(53,2):2})`.
Frame rate (Copperline, joystick up held, 600 VBL): `frames 600 changes 104 [(6, 72), (7, 17), (5, 5), (1, 4), (2, 3), (4, 2)]` (intervals in VBL between screen changes).
Blitter writes in 4 s of race: `BLTSIZE 9775, BLTCON0 6212, BLTCON1 5587, INTREQ 413, AUD0-3 period/volume 200 each`.

## 10. Verification: the engine/gear note (ids 29/30/31) and the continuous engine drone (Paula logs)
Method: Copperline, race state `st_n5`, 130 s of driving, MMIO write watch on `$dff0d0-$dff0df` (AUD3) + DMACON and a breakpoint on the game wrapper `$7b70` (`work/amiga/gear.py` -> `gear_trace.json`, raw 14 080 register writes + 33 requests). Analysis: per `LC=$52d98` start, every AUD3 write until the stop.
**Corrections to §4.3/§6 that this changes (read first):**
- (a) holds: **one request = exactly one start, plays once, stops by itself.** (b) **per-VBL writes DO occur, but with constant values**: the engine tick `$4edfc/$4ee00` rewrites AUD3PER and AUD3VOL every VBL (50 Hz, 86-99 writes per 1.74-1.99 s) with the SAME period and volume for the whole note: no pitch or volume envelope, no AUDxLEN reload. (c) The three ids differ only in the start period (and hence length): 29 -> 501 (`$1f5`), 30 -> 404 (`$194`), 31 -> 354 (`$162`); a new request while one plays **restarts the sample from byte 0** (cuts the old one).
- **My §0/§6 RAM figure for the engine note was too small**: three pitches of the same body = **three DMA variants**: 17 458 B at 354 / 404 / 501 plays 1.742 / 1.989 / 2.466 s = **10 904 / 12 447 / 15 432 B @6 258 Hz (38.8 KB for all three; 77.6 KB @12 517 Hz)**. One variant (354) = 10.9 KB; two (354 + 501) = 26.3 KB. At 1 MB (~23 KB free) only one or two variants fit alone.
- **The *continuous* engine drone is a different thing and DOES need per-VBL pitch** (§10.4).
### 10.1 What decides the id (disasm `$ef00-$ef66`)
`$ef12`: `d2 = ($29 + $d) >> 1 = $23`; `$ef14-$ef1e`: fires only when the speed word (`d0`) crosses `$23` between this frame and the next (`d3 xor d4`), `d1 = |speed change|`; `$ef4e-$ef62`: `d1 < 5 -> id 29 ($1d)`, `d1 < $a -> id 30 ($1e)`, else `id 31 ($1f)`; `moveq #3,d1` (ch3); `jsr $7b70` (`$ef66`). So it is a gear-shift whoosh triggered at the speed threshold crossing, soft/medium/hard by acceleration. Requests in the log (id on ch3, return address `$ef6c`): `413.4444 id30`, `431.1696 id31`, `431.8711 id31`, `449.8194 id30`, `500.0972 id31`, `517.4449 id30`, `520.9553 id29`, `535.2345 id31` (8 in 130 s; the other ch3 requests `$c61e` id 65 are the bump sample `$5aee6`, not the gear note).
### 10.2 Raw Paula lines, one clean request (id 30 at 449.8194; `pc` = Amiga code address, AUD3 = `$dff0d0..d8`, DMACON write value `$8008` = set ch3 DMA, `$0008` = clear)
```
449.8196 pc=0x4f158 DMACON=0x8        <- start routine $4f122: stop ch3 DMA
449.8196 pc=0x4f162 VOL=0x0
449.8196 pc=0x4f166 LCH=0x5   0x4f16e LEN=1   0x4f174 PER=0x1
449.8196 pc=0x4f17a DMACON=0x8008     <- parking buffer $505a0 (silence), LEN=8, PER=0x100
449.8325 pc=0x4f228 DMACON=0x8 ... 0x4f258 DMACON=0x8008  (script path re-arms silence)
449.8331 pc=0x4ee10 LCH=0x52d98       <- the real start (engine tick $4edf2): LC
449.8331 pc=0x4ee16 LEN=8729          <- 17 458 B
449.8331 pc=0x4ee28 DMACON=0x8008     <- DMA on
449.8333 pc=0x4ed7c LCH=0x5   0x4ed84 LEN=1    <- audio interrupt $4ed2a: loop pointer = silence (ONE-SHOT: no second LEN of the sample)
 ... 99 per-VBL writes pc=0x4edfc PER=0x194 and pc=0x4ee00 VOL=0x35 (all identical) ...
451.8216 pc=0x4ed74 DMACON=0x8        <- audio interrupt: DMA off by itself (1.988 s = 17458/(3546895/404))
```
Second window (id 30 at 517.4449): identical sequence, start `517.4608 LCH=0x52d98 LEN=8729 DMACON=0x8008`, 99 per-VBL writes all `PER=0x194 VOL=0x35`, stop `519.4493 pc=0x4ed74 DMACON=0x8` (1.989 s).
### 10.3 Retrigger and the three periods (all clean requests in the log)
| request (time, id) | start (LC, LEN words) | PER written per VBL (distinct) | VOL (distinct) | stop by itself |
|---|---|---|---|---|
| 431.1696 id 31 | 431.1834 `$52d98`, 8729 | `$162` | `$35` | **cut at 431.8714 by the next id 31** (0.70 s later): DMACON off `4f158`, silence, then a fresh start 431.8846 `LCH=$52d98 LEN=8729 DMACON=$8008` (restart from the beginning) |
| 431.8711 id 31 | 431.8846 | `$162` (86 writes) | `$35` | 433.627 `pc=0x4ed74` (1.742 s) |
| 449.8194 id 30 | 449.8331 | `$194` (99) | `$35` | 451.8216 (1.988 s) |
| 500.0972 id 31 | 500.1131 | `$162` (86) | `$35` | 501.8556 (1.743 s) |
| 517.4449 id 30 | 517.4608 | `$194` (99) | `$35` | 519.4493 (1.989 s) |
| 520.9553 id 29 | 520.9664 | `$1f5` | `$35` | (overlaps the id-65 bump on the same channel; the engine note itself is the same one-shot) |
| 535.2345 id 31 | 535.2491 | `$162` (86) | `$35` | 536.9915 (1.742 s) |
Exactly 15 ch3 starts for 15 ch3 requests in the log (8 gear + 7 id-65): the engine never re-triggers the note by itself. A bump (id 65, `$5aee6`, period `$e2`) on the same channel replaces a playing gear note (and vice versa): ch3 is one voice.
Id 65 (not the gear note) DOES have a per-VBL **volume** envelope: AUD3VOL steps `$10 $12 $14 $16 $18` (attack) and `$e $c $a` (decay) at constant `PER=$e2` (`431.0027 ... VOL=0xa`, `446.6481 ... VOL` set `0x10,0x12,...`); a baked-in envelope would be needed for it on the STE (same size, no period change).
### 10.4 The continuous engine drone (ch0) DOES write the period every VBL
From the 44 s race trace (`trace_race1.jsonl`): AUD0 plays the 706 B tone `$6347e` (loop) and is **restarted every 4.006 s** (`LC=$6347e` at 410.41, 414.417, 418.423, ... 450.494); `AUD0VOL = $b` constant; **AUD0PER changes every frame**: 2 196 writes, **44 distinct values, 387 (9.2 kHz) .. 571 (6.2 kHz)**, following the speed (571 standing, ~387 at speed; e.g. 3-s windows: 408 s 571, 414 s 455-571, 417 s 391-455, 420 s 387-391 ... 438 s 433, 441 s 433-571). Source: the game writes `-(speed)` into `$4ec94` once per frame (`$7a40: move.w d0,$4ec94.l`, after `subi.w #$50,d0` when `$ed9` is set) and the tick adds it to the channel-0 period (`$4edf6-$4edfc`).
STE consequence (the DMA rate is fixed at 6 258 / 12 517 Hz): a pitch change = a **different resampled loop**: the 706 B loop at period p is `706 * p * 0.001764` bytes at 6 258 Hz (711 B at p=571, 482 B at p=387); all 44 values = ~26 KB, 12 steps of ~0.5 semitone = ~7 KB [inf: needs the loop to be a whole number of cycles; one start/end re-arm per pitch step, 3 byte writes x2 per VBL at most (~100-150 cycles) = still below the YM's 3.6 k]. The ST's drone is most likely the three scripts started once at race start (`$16920`: ids 64/65/66 on ch0/1/2) and pitched by the game each frame [inf, not traced], not one of the discrete `$8c00` events of §5; design A (events) leaves it alone, replacing it is a separate, larger design.
### 10.5 Verdict for the "one-shot" plan
The gear note IS a pure one-shot (one start, constant period and volume, auto-stop), so design A can play it, but **three pitch variants = 38.8 KB @6 258 Hz** (or accept one variant, 10.9 KB). The per-VBL AUD3 writes are redundant refreshes of constants (CPU on the Amiga only). The continuous drone and the bump `$5aee6` volume envelope are the two places where "one-shot, fixed" does not hold; for the bump bake the envelope, for the drone keep the YM.
