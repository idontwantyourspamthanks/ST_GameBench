# Midwinter 2: the Amiga MUSIC (study for a DMA-sound port to the STE)

Read-only study phase (nothing in the patch tree / tools was changed, nothing committed). Evidence tags: **[obs]** observed in Copperline (headless A1200, KS 3.1, PAL) with MMIO/memory watches; **[disasm]** read from `mwii_flat.bin` (the relocated `MWII`, see `amiga_sound.md` §2.0; **operand address = flat offset + `$270d0`**, all addresses below are operand addresses like the ones in the disassembly, e.g. tick `$57720` = flat `$30650`); **[model]** computed by `work/music_study/amiga/sim.py` / `render.py`; **[INFERENCE]** not verified.
All scratch work is in `work/music_study/amiga/` (scripts, `extract/`, `wav/`); `*.bin`, `*.png`, `*.wav`, `*.raw` there are git-ignored (the `.gitignore` of the repo covers them); emulator save states live in the Amiga repo (`games/in_progress/Midwinter-2/work/states/music/`, `*.clstate` ignored).

## 0. Verdict
1. **The user-heard "intro/title music" is MWII's own player, tune 1 of 17** (not the cracktro, not a loader). It plays from the moment the game starts its intro sequence (logo + credits crawl) until the hall appears, and tune 1 is ALSO the music of the raid map, the personnel / training / control screens, the F5 "map table", the waypoint map and the jeep "accelerated time" screen. It is a **4-voice sample-instrument sequencer** (Paula, one voice = one 8-bit sample played at a note period, a volume envelope, optional slide/vibrato), driven once per VBL.
2. The player is small and fully understood: **I re-implemented it in Python (`sim.py`) and it reproduces the emulator's Paula write stream (AUDxLC/LEN/PER/VOL/DMACON) tick for tick: tune 1 over its whole 3620-tick intro run from power-on, and all 17 tunes for 1599 ticks each: 0 mismatches** (§6).
3. Data is tiny: **score data 16 154 B for all 17 tunes (tune 1: 4 342 B), 15 instruments, 56 640 B of samples (tune 1 needs 49 150 B of them)**, all in `MWII` (code hunk tables + the tail of the chip hunk after the 81 544-byte sfx pool).
4. STE port feasibility: **good for tune 1** (tick = VBL; a 4-voice mixer already exists in `patches/asn/blob.s`): RAM ~66 KB for tune 1, CPU 14 % / 29 % / 57 % of a frame for 4 voices at 6258 / 12517 / 25033 Hz mono (§7). The Amiga turns its 3.3 kHz LED filter ON in every tune, so 6258 Hz loses almost nothing audible (≤2 % of the energy is above 3.1 kHz after the filter, §7.3).
5. Music and sfx share the 4 Paula channels and are **mutually exclusive in time**: the VBL tick pointer is either the sfx driver or the music driver (§4.1). On the ST the intro/title/front end has no sfx running, so no conflict.

## 1. What plays when (screen / music timeline)

### 1.1 Method [obs]
Copperline sessions (floppy set `[cr SPL]` in df0-df2 = the original; HD image `Amiga_enhanced_games_2026-11-15.hdf`, volumes `Midwinter2Orig` = unpatched, `Midwinter2` = patched direct-controls build): MMIO write watches on `$dff0a0-$dff0df` + `$dff096` (value, PC, frame), write watches on the driver variables `$60a8e` (current tune), `$57340` (tune request), `$57344` (pause), `$5e296` (VBL tick pointer), `$609da` (scene id), screenshots. `tools/` of the study: `trace.py`, `explore.py`, `walk*.py`, `scenes.py`, `verify_tunes.py`. Frame rate measured: 3621 VBL in 72.5359 s = **49.92 Hz** (PAL, 313 lines x 227 CCK).

### 1.2 Timeline from power-on (original floppy set, A1200) [obs]
| time (emulated) | what is on screen | Paula writer | notes |
|---|---|---|---|
| 0 - 13.4 s | Kickstart, startup-sequence text ("Loading") | none (only ROM `DMACON` setup) | silent |
| 13.4 - 20 s | Sepultura cracktro (`INTRO`, ProTracker module, code at `$18bxx-$19700`) | INTRO's own replayer, 4 voices, period 428... | **out of scope** (identified in one line: `INTRO` + `M.K.` module at `INTRO+$3834`; it exits on left mouse button; the unpatched HD volume does not run it at all) |
| after INTRO: game loads | black / "insert disk" etc. | none | silent |
| **53.485 s** (frame 2670) | MWII starts its intro sequence: the MIDWINTER II logo builds, then a beach "credits crawl" | **MWII music player, tune 1** | `DMACON=$000f` hardware reset (`$5750a`), first note one VBL later at 53.505 s |
| **126.021 s** (frame 6291) | hall (WAR ROOM / PERSONNEL / RAIDS / CONTROL / TRAINING) appears | stop: `$4cc2e` (`$57344:=1`, `$5750a` reset) | **tune 1 was playing for 3621 ticks = 72.5 s and is cut off mid-loop (its loop is 6592 ticks = 132 s)** |
| 126 s onward | hall | none | **silent** |
HD, unpatched `Midwinter2Orig` (no INTRO, shorter loads): tune 1 starts at **8.634 s**, stops at **72.636 s** (3195 ticks = 64.0 s) when the hall appears [obs, `walk2_mw2orig`/`walk5`]. The length of the intro music = length of the intro animation = disk-load dependent; the music is not what ends it.

### 1.3 Front end and 3D view (HD unpatched/patched, `walk5/6/7/12/13` + `scenes.py`) [obs]
| screen | music | how it starts / stops (observed variable writes, pc = runtime) |
|---|---|---|
| intro: logo, credits crawl | **tune 1** | request at game start: `$60a8e`:=-1, `$60a8e`:=1 (`$4cbba`), `$57344` 0->1->0 inside the start routine `$5760c` |
| M / J / K control prompt ("Press 'M' for Mouse...") - **only in the patched HD build `Midwinter2`, not in the unpatched game** | tune 1 keeps playing (no events between the end of the credits and the key press) | key `M`: `$57344`:=1 via `$4cc2e` -> hall silent |
| hall | **none** (paused, hardware reset) | `$4cc2e` called from the hall code (flat `$1f1c6`); [obs] 5 s in the hall: 0 Paula writes |
| WAR ROOM (campaign menu: start/load/save campaign) | none (still paused from the hall) | - |
| RAIDS -> "select level of play" | none (paused) | - |
| raid map (islands AGORA/DHAFRA/LOBOS/CAMARGO...) | **tune 1, restarted from tick 0** | map init `$4d9f8`: `$60a8e`:=-1, stub `$4cb32` (tune 1) |
| PERSONNEL, CONTROL, TRAINING (clicked in the hall) | **tune 1, restarted** | each screen init does `$60a8e`:=-1 + stub `$4cb32` |
| island zoom, mission briefing (objective page), equipment | **tune 1 keeps playing** (no new request: no write to `$60a8e`/`$57344` from the map at 106.6 s to the mission start at 179.5 s; [obs] at the equipment screen 249 music ticks (1583 Paula writes from the music code) in 5 s). The briefing page is `scene 7`, whose entry `$4a0a0` requests **tune 6** only when `$637ae`==0 (called directly from the hall state: tune 6, objective page) - in the normal path no request was seen | - |
| mission start | **music stops** and the sfx driver takes over the VBL: `$60a8e`:=-1 at `$25cd8`, sfx request `$56820`:=`$100` | `$4cd88` (flat `$25cb8`): `$4e638:=$56482` (sfx tick), `jsr $4e616` |
| 3D world (normal play) | **none, only sfx** (`$5e296` = `$56482`); [obs] 5 s in the cockpit: 0 writes from the music code, 2292 from the sfx driver | - |
| F5 in the 3D view (the "map table" animation, then the island map with the key icon) | **tune 1, restarted** (193.648 s: `$60a8e` -1 -> 1, `$609da`:=6 at `$25f518`) | F5 handler -> scene 6 |
| hover the key (icon row: person, ...), click the waypoint icon -> waypoint map | tune 1 continues; clicking the key/icon again restarts tune 1 (225.876 s) | each click re-requests tune 1 |
| click the far-left icon -> jeep "travel" screen = **accelerated time** | **tune 1 restarted at 243.484 s, plays 717 ticks (14.35 s)**, then `$60a8e`:=-1 at 257.831 s (pc `$26fd48`), sfx driver restored, world resumes | start: request via `$4cb32`; stop: `$4cd88` as at mission start. The length is the length of the time jump |
| character / interface sub-screens of the 3D game (`scenes.py` calls their entry routines directly) | own tunes: **scene 1 governor/person page: tune 10; scene `$a` "stop and rest": tune 2; scene 3 field-agent skills: tune 7; scene 5 diary: tune 15; scene 7 mission objective: tune 6; scene 4 secret weapons: tune 16; "MISSION SUCCESSFUL" (fireworks): tune 4 or 17** | entry routines `$4a008/$4a02e/$4a054/$4a07a/$4a0a0/$4a17c/$4a1de/$4a22c/$4a270` (all: `$60a8e`:=-1, stub, `$609da`:=scene, `jsr $4c9b0`) |
Raw watch output (from `walk6` patched build, `mw2` volume): `(8.634 tune 0000->FFFF pc $26e63e) (8.634 tune FFFF->0001 pc $26fb64) (8.634 pause 0000->0001 $27a5c2) (8.634 pause 0001->0000 $27a6aa) ... (88.522 pause 0000->0001 pc $26fbce) ... (106.59 tune 0001->FFFF pc $26936c; ->0001 $26fb64) ... (179.546 tune 0001->FFFF pc $26fd48) (179.55 sfxreq FFFF->0100)`; F5 / accelerated: `(193.648 tune FFFF->0001 ...; scene 0000->0006 pc $25f518)`, `(243.484 tune 0001->FFFF pc $270998; ->0001) ... (257.831 tune 0001->FFFF pc $26fd48) (257.854 sfxreq FFFF->0100)`.

### 1.4 Tune -> trigger map (static, all 17 stubs; "ref" = flat offset of the `jsr` operand) [disasm]
Stub `$4cb32` = tune 1, `$4cb3a` = 2, `$4cb42` = 4, `$4cb4a` = 5, `$4cb52` = 6, `$4cb5a` = 7, `$4cb62` = 8, `$4cb6a` = 9, `$4cb72` = 11, `$4cb7a` = 12, `$4cb82` = 10, `$4cb8a` = 3, `$4cb92` = 13, `$4cb9a` = 14, `$4cba2` = 15, `$4cbaa` = 16, `$4cbb2` = 17; each is `moveq #n,d0 / bsr $4cbba / rts`.
| tune | loop | call sites (flat) | what it is |
|---|---|---|---|
| 1 | 132.1 s | `$997a` (intro `$30a30`), `$d0ec`, `$154a4`, `$1f306`, `$230fa`, `$23140`, `$23186`, `$245d8`, `$24b32`, `$26932` | title/intro, raid map, personnel/training/control, F5/travel screens [obs: several] |
| 2 | 23.1 s | `$c216`, `$22f68` | scene `$a` "stop and rest" [obs] |
| 3 | 192 s (ch1 reads low memory) | none | **never requested** |
| 4 | 25.6 s | `$231ce` (also via `$4a294`, scene 7) | victory / "mission successful" variant [obs: entry `$4a1de`/`$4a286`] |
| 5 | 32.1 s | `$242c8`, `$2b2bc`, `$2b85c` | mode toggle `$5d3a8` / `$52926` (map-style mode) [disasm only] |
| 6 | 26.9 s | `$21bf0`, `$22fe2` and the per-island table (below) | mission briefing (scene 7) [obs] / the "room" music default |
| 7 | 25.6 s | `$22f8e` | scene 3 field-agent skills [obs] |
| 8 | 16.7 s | `$27018` (`$4e0e6`) | [disasm only, context not identified] |
| 9 | 19.2 s | `$20fc`, `$233e` (`$291ca`/`$293fe`: counter `$2762e`:=2) | [disasm only] |
| 10 | 30.8 s | `$5dc`, `$10ece`, `$22f42` | scene 1 governor/person page [obs] |
| 11 | 915 s (ch1 reads low memory) | none | **never requested** |
| 12 | 23.1 s | `$2a5a4` | [disasm only] |
| 13 | 192 s (ch1 reads low memory) | table slot only | per-island table index 3 (below) |
| 14 | 23.1 s | none | **never requested** |
| 15 | 65.4 s | `$22fb4` | scene 5 diary [obs] |
| 16 | 76.9 s | `$230b6` | scene 4 secret weapons [obs] |
| 17 | 121.8 s | stub `$4cbb2` (`$4a270`/`$4a22c`) | "mission successful" [obs] |
Per-island/"room" table: `sub_28340` (flat) takes the first word of `$27632` (a screen/room index 0..15) and calls the stub in the 16-entry long table at `$27690`: **index 3 -> tune 13, index 7 -> tune 10, all others -> tune 6**; skipped when `$5d3a8` != 0. [disasm]
So for the ST intro/title/map/F5/accelerated-time requirement only **tune 1** is needed; tunes 2,4,6,7,10,15,16,17 serve the 3D game's character/interface screens.

## 2. How a tune is started, stopped, switched (interface) [disasm + obs]
Variables (operand addresses; the same code runs from the floppy and HD loads):
| var | meaning |
|---|---|
| `$60a8e` w | current tune, -1 = none. **A request for the tune that is already current is ignored** (`$4cbba: cmp.w $60a8e,d0 / beq out`), so every caller first writes `-1` |
| `$57340` l | tune number handed to the start routine `$5760c` |
| `$57344` w | **pause flag** (1 = no music: the tick returns without playing, DMA stays off) |
| `$60aa2` w | music enabled (nonzero = on); toggled by a keyboard key (`$3e336 not.w $60aa2`; when turned off the tick pointer is restored; key-state byte `$60b02`) |
| `$5e296` l | **VBL tick pointer**: VBL handler (`$3dfc8` = flat `$16ef8`, level-3 autovector `$6c`) -> `$3e030` -> `jsr ([$5e296])` once per VBL |
| `$4e638` l | tick pointer to restore when music stops: `$4e558` (just `rts`, front end) or `$56482` (the sfx driver tick, set at `$4bcb4` / `$4cd98` when the 3D game starts) |
| `$609da` w | scene/screen id of the character-interface screens (scene routines in §1.3) |
Start: `$4cbba(d0=tune)` (`$4cbba: ... move.w d0,$60a8e / $57340:=d0 / $57344:=0 / jsr $5760c`); then **if `$60aa2` != 0: `$5e296:=$57720`** (the music tick replaces whatever the tick pointer was, i.e. the sfx driver), else (music disabled) the pointer is restored to `$4e558` and `$5750a` is run.
`$5760c` start routine: lock `$57374`:=1, remember `$57344`, `$57344`:=1, `jsr $5750a` (hardware reset: `DMACON:=$000f` (clear AUD0-3), `AUDxLC`:=*mem[$5c292] (= 0: the source operand is an address, not an immediate: an original assembler slip), `AUDxLEN:=$10`, `AUDxVOL:=0`, `AUDxPER:=1`), clear the 8 channel records (`$57f98.. $44` each) with a 205-word loop, copy the tune's 4 list pointers (`$57e78 + 16*tune`) into the records' `$1e`, point every record's event pointer at the **idle stream `$58304`** (`2c 18 1c 08` = LED filter on, slide off, vibrato off, next pattern) and its list pointer at `$582fc` (a null list => reloads the tune's list on the first tick), set the ids 1..4 (music) and 5..8 (the second set, §4.4), restore `$57344`, unlock.
Stop / pause (callers): `$4cc2e` (`$57344`:=1 + `$5750a`: the hall; flat `$1f1c6`), `$4cc1e` (`$57344`:=1, `jsr $4e616`: flat `$24304`, `$2b980`), `$4e616` (init `$4e55a`, `$5e296:=[$4e638]`, `$70:=$56740`, `DMACON:=$000f`; used at mission start `$25cd2`, `$172a0`, `$26342`, `$26b3a`, `$2b396`, `$2b8a2`, `$1318`, `$2ac2`). The disk-load code also pauses.
**Switching**: `$60a8e:=-1` then a stub => `$5760c` resets everything (tick 0, all 4 channels), i.e. a new request always restarts the tune from its beginning; tune 1 re-requested on each front-end screen is therefore restarted each time.
Tempo/tick: **one `$57720` call per VBL; no CIA timer; no tempo variable**; all durations are in VBL ticks. PAL 49.92 Hz [obs]; on NTSC (60 Hz) the game would run 20 % faster [INFERENCE: no compensation in the code].

## 3. Where the data is [disasm]
Operand addresses (flat = operand - `$270d0`), all inside `MWII`:
| item | address | size |
|---|---|---|
| tick `$57720`, start `$5760c`, requests `$57378`, hw reset `$5750a`, per-channel tick `$57a8a`, command table `$57ce6` | `$57378-$57e70` (code hunk, flat `$302a8-$30da0`) | ~3 KB code |
| tune table | `$57e78 + 16*n`, n = 1..17: 4 longs = pointer to the pattern LIST of ch0..ch3 | 272 B |
| channel records (RAM) | `$57f98`, stride `$44` (music ch0..3 ids 1-4), `$580a8..` (second set ids 8,7,5,6), dummy hw block `$581b8` | 8 x 68 B |
| lists, patterns, envelopes | `$58304 - $5b..` / `$5c34e-$5c3f4` (code hunk data) | 2 816 + 12 736 + 120 B |
| **instrument table** | `$5c1c0`, 15 x 14 B | 210 B |
| silence loop `$5c292` (16 B zeros), waveform `$5c32a` (tune 13 only) | code hunk | 16 / 18 B |
| **samples** | chip data hunk 3, `$89478 + 81544 ... + 138191` (the tail after the sfx pool of `amiga_sound.md`) | **56 640 B** in 14 regions |
`work/music_study/amiga/extract/tunes.json` = every tune, channel list, pattern (events), envelope, instrument; `extract/instruments/inst_<addr>.raw` = the 14 sample regions (signed 8 bit, native); `lowmem_a1200_ks31_hd.bin` = the 1 KB of Amiga low memory the driver reads by accident (§5.6).

## 4. Driver architecture [disasm]
### 4.1 Sharing Paula with the sfx driver
The sfx driver (`amiga_sound.md` §2.1, tick `$56482`) and the music driver both write AUD0-3. They never run together: `$5e296` holds one of `$4e558` (rts), `$56482` (sfx), `$57720` (music). Starting a tune overwrites the pointer with `$57720` (`$4cbba`); stopping restores `[$4e638]`. In the 3D world (sfx tick) no tune runs; every music screen (intro, map, F5, travel) is a non-3D screen. [obs: at 179.55 s the sfx request `$56820` is written right after the tune stop]. The sfx request word is NOT cleared by music: requests made while music plays are consumed later.
### 4.2 Tick `$57720` (per VBL)
For channel c = 0..3 in order: if `$57346` (never written) or a sfx record is active, the music record would run against a dummy register block (`$581b8`) so it keeps its timing; otherwise **run record `c` against the real Paula channel** (`$57a8a`: a0 = record, a2 = `$dff0a0+16c`, d5 = DMA bit, d1 = `$8200|bit`). When `$57344` != 0 nothing runs (the whole tick returns early, `$57720` returns if lock `$57374` set).
### 4.3 Channel record `$44` bytes
`$00 w id` (0 = off) | `$02 w cnt` (ticks left in the event, loaded with duration-1) | `$04 w state` (0 simple instrument; 1 instrument with 2nd part; 3 = "just started") | `$06 w per` | `$08 w slide mode` (0 off, 1 up, else down) | `$0a w step` | `$0c w target` | `$0e w slide delay` | `$10 w vibrato phase` (0 off, 1..4) | `$12 l env ptr` | `$16 l event ptr` | `$1a l list ptr` | `$1e l list start` | `$22 l env start` | `$26 l LC1` `$2a w LEN1` `$2c l LC2` `$30 w LEN2` | `$32 w vib counter` `$34 w vib reload` `$36 w vib up amount` `$38 w vib down amount` `$3a w vib delay` `$3c w vib delay reload` | `$3e w vol subtract` (only used with `$5736c/$5736e`, never set) | `$40 w vol add` | `$42 w vol-add flag`.
### 4.4 The second record set (ids 5-8, `$580a8..`) is not used by the game
`$57378` (sfx-style request `$57338` -> first free channel) and the records `$580a8/$580ec/$58130/$58174` form a per-channel "interrupt" mechanism (a request would play an event stream from table `$582f4` over the music on that channel). **No code ever writes `$57338`/`$5733c` outside this routine** (raw search of the load file, [disasm]); it is dead code in the shipped game. The tick, however, still checks `$57348-$57354` (all zero).

## 5. Format specification (enough to implement a player) [disasm, verified by §6]
### 5.1 Time and structure
Tune = 4 independent channels. Channel = **list** (array of longs = pattern pointers, terminated by 0). The channel runs the patterns in order and wraps to the start of the list at the terminator (loops forever). Pattern = stream of 16-bit words: `w > $64` = **note**: `period, duration` (2 words); `w <= $64` = **command** (byte offset into the 15-entry jump table `$57ce6`, so values are multiples of 4). One tick = one VBL.
Event timing: on a note start `cnt := duration-1`; every following tick: `cnt==0` -> read next event; `cnt==1` -> (end-of-note tick, see below) then `cnt:=0`; else `cnt--`. So a note of duration D occupies exactly D ticks; a rest of D ticks likewise. Commands (and the NEXT/GOTO chains) execute in the **same tick** as the following note start (no tick consumed), so a pattern change costs no time.
### 5.2 Commands (word value, then arguments)
| cmd | name | args | action |
|---|---|---|---|
| `$00` | HALT | - | return (the event pointer is not advanced; repeats every tick) |
| `$04` | INSTR | long ptr -> instrument descriptor | descriptor word0 (flag) -> `state`; flag 0: `LC:=ptr+2` `LEN:=+6` written to Paula immediately; flag != 0: `LC1=l@+2, LEN1=w@+6, LC2=l@+8, LEN2=w@+12` kept in the record (all 15 instruments have flag 1) |
| `$08` | NEXT | - | `p:=list ptr`; if `*p==0` then `p:=list start` (wrap); `list ptr:=p+4`; continue reading at `**p` |
| `$0c` | ENV | long ptr | `vol sub:=w@0`, `vol add:=w@2`, envelope start `:= ptr+4` (words, terminated by `$00ff`) |
| `$10` | SLIDE | 4 words | `mode, step, target, delay` |
| `$14` | VIB | 6 words | `vib phase:=1; counter, reload, up, down, delay, delay reload` |
| `$18` | SLIDEOFF | - | `mode:=0` |
| `$1c` | VIBOFF | - | `phase:=0` |
| `$20` | REST | 1 word duration | `cnt:=dur-1`, envelope := the silence envelope `$5c3f4` (zeros), `AUDxVOL:=0`, then the usual envelope step; DMA untouched |
| `$24`,`$28` | END | - | DMA bit of this channel off, **`AUD0PER:=1` (always channel 0: original slip)**, `AUDxVOL:=0`, return (parked; repeats each tick) |
| `$2c` / `$30` | LED filter on / off | - | `bclr/bset #1,$bfe001` (A500/A1200 LED = audio low-pass) |
| `$34` | VOLADD | - | `vol-add flag := 1` for the next note (reset to the word at address 0 = 0 at every event fetch) |
| `$38` | GOTO | long | `a1 := *(long)a1` (jump to the pattern whose pointer follows) |
### 5.3 Note start (`$57c48` -> `$57c5e`)
`per := period; AUDxPER := period; cnt := dur-1; env ptr := env start; vib delay := reload; if vib phase != 0 then phase := 1;` then **(state 0) DMA on only** (the sample keeps playing from the loop) **or (state != 0) `state:=3; AUDxLC:=LC1; AUDxLEN:=LEN1; DMA on`**; then one envelope step (below). Next tick (`state==3`): `AUDxLC:=LC2; AUDxLEN:=LEN2; state:=1` (queues the loop part: Paula plays the whole first part once, then loops the second). At the end-of-note tick (`cnt==1`, `state != 0`): `DMACON` clear of this channel's bit (so the next note retriggers from sample start).
### 5.4 Per tick (no new event) in this order
1. **Slide**: if `mode != 0`: if `delay != 0` then `delay--` else `chg=1; per += step` (mode 1) / `per -= step` (else); if the target is passed (`target >= per` fails for up / `target < per` fails for down) then `per := target; mode := 0`.
2. **Vibrato**: if `phase != 0`: if `vib delay != 0` then `vib delay--` else if `counter != 0` then `counter--` else `{counter := reload; chg=1; if phase < 3: per -= down, phase++ else per += up, phase++; if phase == 5: phase := 1}`.
3. if `chg`: `rec.per := per; AUDxPER := per`.
4. **Envelope** (always path B; path A needs `$5736c/$5736e` which are never set): `p := env ptr; if *p == $00ff { p -= 2 }` (hold the last value) `; vol := *p++; if vol-add flag == 1 and the word was not the terminator: vol += vol add; AUDxVOL := vol; env ptr := p`. One envelope word per tick; the instruments' envelopes are short (<= 16 steps) and then hold the last value.
Writes happen in this order per tick per channel: `PER` (if changed), `LC`/`LEN`/`DMACON` (note start or state 3), `VOL`; channels in order 0,1,2,3 (this is what `sim.py` emits and what the emulator log shows, §6).
### 5.5 Instrument descriptor (14 bytes) and envelopes
`w flag(1), l LC1, w LEN1(words), l LC2, w LEN2` + for flag 0 only the first three fields are read. 14 instruments (`$5c1c0..$5c284`) have LC1 in chip hunk 3 (byte offset `LC1-$89478`), 1 (`$5c284`, tune 13 only) points at an 18-byte waveform in the code hunk. **LC1 is often ODD** (e.g. 82209, 97743): Paula ignores bit 0 of LC, so the real sample starts one byte earlier (the last byte of the previous region) [INFERENCE: standard Paula behaviour; the emulator log shows the odd value being written]. LC2/LEN2: 11 of 14 sample instruments use the 16-byte silence (`$5c292`), i.e. **one-shot**; 3 loop themselves for the whole note (LC2=LC1): `$5c222` 5 408 B, `$5c230` 6 236 B, `$5c268` 6 072 B (sustained "pad/string" voices).
Envelope = `w vol sub, w vol add, then words ..., $00ff` ; 10 distinct envelopes in all tunes (120 B): most are a single constant volume (20, 25, 35, 45, 54, 64) held, some short decays (e.g. `34,29,29,24,24,20,20,17,15,10,10,9,8,7,0`).
### 5.6 A data bug the driver tolerates (tunes 3, 11, 13 ch1)
Patterns of channel 1 in tunes 3/11/13 never execute an ENV command, so the envelope pointer is 0 and the driver reads the volume from **Amiga low memory** (`$12 := $22 = 0`, one word per tick from address 0: `0,0,$0020,$0810,$00f8,$0b0e,$00f8,...` on KS 3.1 / A1200 / HD: ExecBase and the exception vectors; Paula treats values > 64 as 64). The sound of that channel therefore depends on the machine/KS (`sim.py` embeds the captured words: `lowmem_a1200_ks31_hd.bin`). Tunes 3 and 11 are never requested; tune 13 is (per-room table). [obs: 0 mismatches only after embedding the captured low memory; with zeros 256/1185/1239 ticks of 1599 differ]. A port should give these channels a fixed envelope (decision for the port; suggested: 32).

## 6. Verification (raw output) [obs + model]
`render.py` = `sim.py` (interpreter) + Paula model + WAV; `compare.py` / `verify_tunes.py` compare the interpreter's per-tick write list with the emulator's MMIO log, requiring the **identical ordered sequence of (register, value) per VBL frame** (LC values mapped: hunk-0 operands + `$1f5670` (floppy) / hunk base, hunk-3 operands - `$89478` + chip base).
### 6.1 Intro tune 1 from power-on on the original floppy set (3 620 ticks = the whole 72.5 s the intro plays)
```
$ python3 compare.py full_trace_a.jsonl 1      # trace = MMIO writes of the music code (pc $24cb80-$24d980), frames 2670..6291
real rows 22755
first frame 2670 last 6291 nframes 3622
LC delta (operand-runtime) 461032 0x18b90
ticks compared 3621 mismatching ticks 1
first mismatch tick 3621 frame 6291
 sim  [('VOL0', 25), ('VOL1', 45), ('VOL2', 64), ('VOL3', 20)]
 real [('VOL0', 25), ('VOL1', 45), ('VOL2', 64), ('VOL3', 20), ('LC0', 0), ('LC1', 0), ('LC2', 0), ('LC3', 0), ('LEN0', 16), ..., ('PER3', 1)]
```
= identical for ticks 1..3620; tick 3621 is the game stopping the tune (hardware reset writes `$5750a`), not part of the tune.
First tick of tune 1 (emulator rows `frame time pc reg value`) vs `render.py regs 1 3`:
```
2671 53.5053 0x24d2d2 0xdff0a6 320        PER0 320            ('PER0', 320), ('LC0', 644505), ('LEN0', 2704),
2671 53.5053 0x24d28c 0xdff0a0 183473     LC0                  ('DMACON', 33281), ('VOL0', 25), ('VOL1', 0), ('VOL1', 0),
2671 53.5053 0x24d290 0xdff0a4 2704       LEN0                 ('VOL2', 0), ('VOL2', 0), ('VOL3', 0), ('VOL3', 0)
2671 53.5053 0x24d296 0xdff096 33281      DMACON $8201 (AUD0 + DMAEN)   [LC 644505-461032 = 183473: sim in operand space]
2671 53.5053 0x24d276 0xdff0a8 25         VOL0 ; then VOL1/2/3 = 0 written twice (idle ENV read + REST/ENV step)
2672 53.5253 ...  LC0 183473, LEN0 2704, VOL0 25, VOL1 0, VOL2 0, VOL3 0      (state 3: queued loop part)
```
### 6.2 All 17 tunes started by the game's own `$4cbba` (parked stub, d0 = tune, `$60a8e` := -1) on the HD unpatched build, 1 600 VBL each
```
$ python3 verify_tunes.py 1600 [1..17]            (work/music_study/amiga/verify_summary.txt)
tune  1: ticks compared 1599 mismatching 0     tune  2: ... 0     tune  4: ... 0     tune  5: ... 0    tune  6: ... 0
tune  7: 0   tune  8: 0   tune  9: 0   tune 10: 0   tune 12: 0   tune 14: 0   tune 15: 0   tune 16: 0   tune 17: 0
tune  3 / 11 / 13 with zero low memory: 256 / 1185 / 1239 mismatching ticks (first at tick 3: real VOL1=32, sim VOL1=0)
tune  3 / 11 / 13 with the captured low memory: ticks compared 1599 mismatching 0 (each)
```
Negative control: the same comparison with zero low memory produces the three failures above (the check is not vacuous).
### 6.3 Not verified
Audio itself (Copperline cannot record, `--noaudio`): the WAV renders are the model's Paula output; nothing was compared against a real recording. Paula DMA latency/restart details at the sub-tick level are modelled simply (LC/LEN re-latched at each end of cycle, DMA start = phase 0).

## 7. Numbers for the STE port [model]
### 7.1 Tunes (`render.py loops`, `stats.py`, `analyze.py`)
loop = ticks until every channel's pattern list wrapped (LCM of the 4 channel periods); score bytes = tune table slice + the 4 lists + unique patterns + envelopes + descriptors; sample bytes = the distinct sample regions its instruments use; avg voices = mean number of channels with DMA on and volume > 0.
| tune | loop ticks | loop time | ch loop (ticks) | patterns | instruments | sample bytes | score bytes | avg voices (max) | note rate p50/p90/max (Hz) | use |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 6592 | 132.1 s | 6592 x4 | 33 | 10 | **49 150** | **4 342** | 3.49 (4) | 15625 / 20864 / 27928 | intro, map, F5, travel |
| 2 | 1152 | 23.1 s | 1152/576/576/384 | 7 | 2 | 11 480 | 384 | 2.93 (3) | 9309 / 13964 / 18668 | rest |
| 3 | 9600 | 192 s | 400/400/400/384 | 7 | 4 | 17 332 | 368 | 2.75 (3) | 10463 / 15625 / 19705 | unused |
| 4 | 1280 | 25.6 s | 640/640/640/1280 | 11 | 7 | 26 844 | 1 102 | 2.87 (4) | 12445 / 16574 / 23646 | victory |
| 5 | 1600 | 32.1 s | 1600 x4 | 21 | 6 | 21 886 | 1 704 | 3.11 (4) | 13185 / 17559 / 23646 | mode |
| 6 | 1344 | 26.9 s | 192/96/336/192 | 4 | 4 | 17 668 | 396 | 3.70 (4) | 16574 / 18668 / 24461 | briefing |
| 7 | 1280 | 25.6 s | 640/640/1280/640 | 5 | 2 | 12 308 | 452 | 2.92 (4) | 9309 / 13185 / 16574 | agent skills |
| 8 | 832 | 16.7 s | 832 x4 | 10 | 6 | 25 662 | 1 046 | 3.10 (4) | 15625 / 23646 / 27928 | ? |
| 9 | 960 | 19.2 s | 960/960/480/480 | 9 | 6 | 21 222 | 926 | 3.19 (4) | 15625 / 23646 / 27928 | ? |
| 10 | 1536 | 30.8 s | 1536x3/384 | 7 | 4 | 18 674 | 652 | 2.88 (3) | 12445 / 15625 / 19705 | governor |
| 11 | 45696 | 915 s | 476x3/384 | 7 | 4 | 17 332 | 540 | 1.51 (2) | 18668 / 24803 / 24803 | unused |
| 12 | 1152 | 23.1 s | 1152/1152/96/1152 | 5 | 5 | 22 268 | 1 270 | 3.15 (4) | 13185 / 16574 / 26273 | ? |
| 13 | 9600 | 192 s | 400x3/384 | 5 | 6 | 18 660 | 602 | 1.26 (2) | 16574 / 19926 / 23646 | room table |
| 14 | 1152 | 23.1 s | 1152x3/384 | 5 | 2 | 11 480 | 658 | 2.65 (3) | 16574 / 22168 / 27928 | unused |
| 15 | 3264 | 65.4 s | 3264 x4 | 16 | 7 | 25 252 | 2 048 | 2.75 (4) | 10463 / 15625 / 27928 | diary |
| 16 | 3840 | 76.9 s | 1280x3/384 | 4 | 4 | 21 768 | 450 | 2.86 (3) | 9852 / 15625 / 15625 | secret weapons |
| 17 | 6080 | 121.8 s | 3040x3/320 | 7 | 3 | 14 110 | 542 | 3.75 (4) | 8287 / 17559 / 19705 | mission successful |
(ch3 in tunes 3/11/13/14/16/17 is a loop of long rests, effectively silent.) Total over all 17: **score 16 154 B** (272 tune table + 2 816 lists + 12 736 patterns + 120 envelopes + 210 descriptors), 2 392 notes, **samples 56 640 B**. Tick rate 49.92 Hz (PAL VBL).
### 7.2 Instruments (all flag 1; rate = 3 546 895 / period; period range over every tune)
| descriptor | hunk-3 off | bytes | loop | period range | rate range (Hz) | tunes |
|---|---|---|---|---|---|---|
| `$5c1c0` | 81 544 | 664 | one-shot | 227 | 15 625 | 4,5,8,9,12,13,15 |
| `$5c1ce` | 100 373 | 354 | one-shot | 249-446 | 7 953-14 245 | 1,4,15 |
| `$5c1dc` | 100 728 | 1 632 | one-shot | 127-570 | 6 223-27 928 | 5,9 |
| `$5c1ea` | 102 360 | 1 800 | one-shot | 214-453 | 7 830-16 574 | 3,11,13 |
| `$5c1f8` | 87 617 | 3 800 | one-shot | 227 | 15 625 | 12 tunes |
| `$5c206` | 91 418 | 6 324 | one-shot | 150-892 | 3 976-23 646 | 11 tunes |
| `$5c214` | 97 743 | 2 630 | one-shot | 333-1338 | 2 651-10 651 | 1,6,15,17 |
| `$5c222` | 82 209 | 5 408 | **loops whole** | 127-808 | 4 390-27 928 | 13 tunes |
| `$5c230` | 131 955 | 6 236 | **loops whole** | 127-856 | 4 144-27 928 | 1,4,6,7,16 |
| `$5c23e` | 104 161 | 12 896 | one-shot | 127-906 | 3 915-27 928 | 1 |
| `$5c24c` | 126 524 | 3 394 | one-shot | 254-339 | 10 463-13 964 | 1 |
| `$5c25a` | 129 918 | 2 036 | one-shot | 254-339 | 10 463-13 964 | 1 |
| `$5c268` | 120 451 | 6 072 | **loops whole** | 127-1356 | 2 616-27 928 | 12 tunes |
| `$5c276` | 117 057 | 3 394 | one-shot | 143-762 | 4 655-24 803 | 4,5,6,8,9,10 |
| `$5c284` | code `$5c32a` | 18 | loops | 214 | 16 574 | 13 |
The samples are played at **9-18 kHz typically (p50 per tune 8.3-18.7 kHz, max 27.9 kHz at period 127)**: any STE rate below 25 kHz plays them with a phase step > 1 (decimation). Sample regions are contiguous: hunk 3 `[81544, 138191)`; Tune 1 uses 10 of the 15 instruments = 49 150 B; the other 4 regions (`$5c1c0`, `$5c1dc`, `$5c1ea`, `$5c276` = 7 490 B) serve only tunes 2-17.
### 7.3 Nyquist / what is lost at STE DMA rates (spectra of the rendered 44.1 kHz mix, first 1000 ticks)
Share of the energy above 3 129 / 6 258 / 12 517 Hz (= the Nyquist limits of 6 258 / 12 517 / 25 033 Hz):
* **Amiga as it sounds (LED filter ON: every tune executes `$2c` in its first tick; modelled as 2 one-poles at 3.3 kHz):** tune 1 **1.6 % / 0.2 % / 0.0 %**, tunes 2-17: 0.1-5.0 % (tune 13: 5.0 %) / <= 0.9 % / 0 %. **=> 6 258 Hz (Nyquist 3.1 kHz) already carries almost everything the Amiga lets through**, provided the mix is low-passed at ~3.3 kHz (or the instruments are pre-filtered) before the decimation.
* Unfiltered Paula output (what the chip generates before the filter): tune 1 18.6 % / 10.1 % / 2.4 %, tune 13 45.3 / 29.0 / 7.0, tune 6 1.3 / 0.6 / 0.3: dull at 6 258 Hz, bright content up to 12.5 kHz, little above 12.5 kHz.
* Share of voiced channel-ticks above each rate (tune 1): 98.9 % above 6 258 Hz, 67.3 % above 12 517 Hz, 1.3 % above 25 033 Hz: at 6 258 Hz nearly every note is decimated by 2-4x (needs band-limited instruments to avoid aliasing in the 3.1-3.3 kHz band; the LED-filter model leaves < 2 % there).
### 7.4 CPU (STE 8 MHz, 160 256 cycles per VBL; mixer costs from `amiga_sound.md` §3.3: 40 cycles first voice, 48 per added voice per output sample => 184 cycles per output sample for 4 voices)
| DMA rate | samples per VBL | 4 voices | % of VBL | tune 1 average (3.49 voices) |
|---|---|---|---|---|
| 6 258 Hz | 125 | 23.0 k | **14.4 %** | ~12.6 % |
| 12 517 Hz | 250 | 46.0 k | **28.7 %** | ~25 % |
| 25 033 Hz | 501 | 92.1 k | **57.5 %** | ~50 % |
| 50 066 Hz | 1002 | 184 k | 115 % (impossible) | - |
(compare the existing sfx mixer: 5 % one voice, 8.4 % 3 voices at 6 258 Hz, 15 % worst case.) The music driver itself (4 channel records, one envelope word each per tick, a few commands) is estimated at ~1.5-2.5 k cycles per VBL (1-1.5 %) [INFERENCE from the structure; the Amiga routine is ~120 instructions per channel tick]. Stereo (the Amiga pans ch0+ch3 left, ch1+ch2 right) costs the same number of voice-samples: two interleaved 2-voice mixes.
The intro/title screens and the jeep accelerated-time screen are not frame-rate critical (the user: frame loss acceptable in accelerated time), so **12 517 Hz (29 %) is affordable everywhere and 25 033 Hz (57 %) probably in the animation-light screens**; 6 258 Hz keeps the 3D/F5 screens cheap.
### 7.5 RAM
| item | tune 1 only | all 17 tunes |
|---|---|---|
| samples (native 8 bit) | 49 150 B | 56 640 B |
| score (Amiga format; a compact port format would be smaller: 2 392 notes) | 4 342 B | 16 154 B |
| volume tables (as in the sfx blob: 16 levels x 256 B x 2) | 8 KB | 8 KB |
| DMA ring | 1 KB | 1 KB |
| driver + mixer code (the sfx blob's mixer can be reused) | ~3 KB | ~3 KB |
| loop pad for whole-sample loops (800 B per looped instrument in the sfx mixer) | 2.4 KB | 2.4 KB |
| **total** | **~68 KB** | **~88 KB** |
The sfx bank leaves 75 079 B free in the 1 MB 3D layout (`amiga_sound.md` §3.1); the front-end RAM map differs (not studied here). Delivery would be the same kind of extra file as `ASNBANK.BIN` (build from the user's own Amiga disk; nothing from the disk is stored in git).
## 8. Feasibility / cost summary and open risks
* **Feasible**: format fully known, bit-exact interpreter verified against the emulator for all 17 tunes, only 4 voices/8-bit samples/VBL tick, a software mixer already exists. Work items: (1) bank builder (`asn_build.py`-style: read `alt/amiga/disk1.adf`, md5-check `MWII`, emit score + instruments), (2) a 68000 port of the tick (`sim.py` is the exact spec: ~15 small routines), (3) mixer changes (restart at phase 0 per note, one-shot + whole-loop voices, per-voice 7-bit volume) and the YM silence/handover at tune start/stop, (4) hooks on the ST: start on the intro (tune 1), restart on each map/F5/travel screen, stop at hall/mission start (the ST requirements are for the ST study).
* **Cost**: RAM ~68 KB (tune 1); CPU 14 / 29 / 57 % of a frame at 6 258 / 12 517 / 25 033 Hz; tick 50 Hz; no CIA timer.
* **Risks / open points**
  1. The WAVs and the 3.3 kHz filter model are not compared with a real Amiga recording; the LED filter on the A1200 vs A500 differs in detail [INFERENCE].
  2. Tunes 3/11/13 (ch1 reads low memory) - only 13 is reachable; choose a fixed volume.
  3. Odd LC addresses: a 1-byte-early start (the Amiga plays from `LC & ~1`); a port that starts at `LC` is 1 byte off (inaudible; keep `LC & ~1` to be faithful).
  4. `move.w d1,$dff096` with an uninitialised `d1` in the dummy-block path (only when a second-set sfx request is active, which never happens) - not reproduced, not needed.
  5. NTSC/60 Hz: the Amiga tick = VBL; on an ST at 60 Hz run the tick 5 of 6 VBL (as the sfx port does) to keep 50 Hz.
  6. The intro length is set by the intro animation/loading (64-72 s on the Amiga), not by the music; the ST intro length may differ, so the port should loop/cut tune 1 like the Amiga (loop 132 s, cut at the hall).
  7. The Amiga restarts tune 1 on every front-end screen change; replicate if the same behaviour is wanted (a restart is a full `$5760c`).
  8. The mission-start stop hands the VBL to the sfx driver (exclusive); on the ST the existing sfx blob must not be ticked while music is running (or the mixer must mix both: needs 4+ voices => the CPU numbers above add).
## 9. Hand-off data (for Main)
**Per-screen tune ids (Amiga, observed)**: intro/credits: 1 | M/J/K prompt (patched build only): 1 continues | hall: none | WAR ROOM / RAIDS level select: none | raid map: 1 (restart) | personnel / training / control: 1 (restart) | mission briefing page: 6 (only when `$637ae`==0; normally tune 1 continues) | mission start -> 3D: stop | F5 map table / island map / waypoint map: 1 (restart on F5, again on each key click) | accelerated time (jeep "travel" screen): 1 (restart; plays for the length of the time jump, 14.35 s in the test) | 3D world: none (sfx only) | person/skill/diary/rest/weapons/victory screens: 10 / 7 / 15 / 2 / 16 / 4 or 17.
**Format and bank size**: §5 (format), §7.1 (per-tune bytes), §7.2 (instruments), §7.5 (RAM): tune 1 = score 4 342 B + 10 instruments / 49 150 B of 8-bit signed samples at native pitch; all tunes 16 154 B + 56 640 B.
**Files** (`work/music_study/amiga/`): `sim.py` (exact interpreter), `render.py` (regs / wav / all / loops), `mwmusic.py` (parser), `extract.py` -> `extract/tunes.json`, `extract/instruments/*.raw`, `analyze.py`, `stats.py`, `spectra.py`, `compare.py`, `verify_tunes.py`, `trace.py`, `explore.py`, `walk*.py`, `scenes.py`, `music_dis.txt` / `music_dis2.txt` (disassembly of `$57370-$57f98`), `verify_summary.txt`, `compare_floppy_tune1.txt`, `full_trace_a.jsonl` (the emulator log of the intro run).
**WAV list** (`wav/`, 22 050 Hz stereo 16 bit, **LED filter applied**, git-ignored; 3000 ticks = 60 s cap for the long loops; all other tunes one full loop): `tune01.wav` (60.1 s of 132), `tune02.wav` (23.1), `tune03.wav` (60.1), `tune04.wav` (25.6), `tune05.wav` (32.1), `tune06.wav` (26.9), `tune07.wav` (25.6), `tune08.wav` (16.7), `tune09.wav` (19.2), `tune10.wav` (30.8), `tune11.wav` (60.1), `tune12.wav` (23.1), `tune13.wav` (60.1), `tune14.wav` (23.1), `tune15.wav` (60.1), `tune16.wav` (60.1), `tune17.wav` (60.1). Regenerate: `python3 render.py all wav --rate 22050 --filter`; whole tune: `python3 render.py wav 1 out.wav --rate 44100 --filter`.
