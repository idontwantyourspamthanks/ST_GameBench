# Midwinter 2 (Atari ST): the YM music driver, its control interface and the hook points for a DMA music player

Study phase, read-only (nothing in `patches/`, `tools/` or the ST game was changed). Evidence tags: **[obs]** observed in a Hatari run of this session (original, unpatched game, 1 MB STE TOS 1.62 unless
stated); **[disasm]** read from disassembly (`work/dumps/ram_ingame_lobos.bin`, `ram_boot_hd1mb.bin`, `RUNME_unpacked.tos`; address = file offset, `tools/m68dis.py`); **[model]** computed; **[INFERENCE]** not verified.
Scratch/raw output: `work/music_study/st/` (`trace_hd.py`, `trace_full.py`, `trace_fl.py`, `parse.py`, `amiga_wrap.py`, logs `hd1/`, `fl1/`, `run1/`, screenshots). Context: `amiga_sound.md` (sfx port, blob `patches/asn/blob.s`).

## 0. Summary (what a replacement player has to know)
1. **The YM music driver is part of FFA file 8** (10494 B, track-side 16, checksum `$5857`, loaded by PP's / the original boot stub to `$806-$3104`; the file is byte-identical to RAM `$806-$3104` except 67 runtime-variable bytes) [obs: `FILES/FFA` dir
   entry + compare with the in-game dump; the loader's `d1 = $5857` seen at the `$c6c` breakpoint]. It is NOT in RUNME, HAGA or an FFB overlay. It holds the driver code (`$c4c-$123e`), its 9-long vector table (`$806-$829`), the note tables and all tune data
   (tune table `$142c`, sequences up to `$3104`). It is resident for the whole session (never overwritten).
2. **The whole external interface is one table at `$806` (vtable) plus 4 variables.** Every caller (boot stub, game) goes through `lea $806.w,a0 / movea.l N(a0),a1 / jsr (a1)`; nothing calls `$c4c/$c6c/$d0e` directly except the driver itself [disasm: raw scan]. So patching the three
   vtable longs `$806/$80a/$80e` redirects the tick, the start and the silence call of **every** screen, including the boot stub's own VBL handler and the title tune. Patch = 3 x 4 bytes, original `00000d0e 00000c6c 00000c4c`.
3. **Tick = VBL (50/60 Hz), no timer.** In the boot stub the stub's VBL handler (`$4decc`) calls `[$806]`; in the game `$5138` (called from `$262f0/$262f4` in VBL handler `$26298`) is set to the value of `[$806]` (`$d0e`) by the tune-start routine `$321fe`.
4. **The same tune ids exist on the Amiga with the same call-site structure** (17 wrappers, same ids, same caller order) so ST id n = Amiga id n [disasm both; §5].
5. **HD: the music can be DMA-driven from the very first note** (the bank is read by the RUNME splice before the boot stub runs). **Floppy: only from the game's first `$321fe` call after `jmp $3104`** (the bank is loaded after file 9), unless the stage-1 loader is moved before the stub's tune start (§4.3).

## 1. Timeline from power-on (screen -> owner of the tick -> PC)
Observed with `tools`-style breakpoints (`b pc = $X :trace :file`) on a cold boot of the unpatched HD build (`work/music_study/st/hd1/`, `run1/`) and of the unpatched floppy images (`fl1/`, FILES/FFA as drive A). VBL = Hatari's `e VBL` counter.

| # | VBL (HD / floppy) | event | PC / caller | tick installed |
|---|---|---|---|---|
| 0 | - | RUNME, HAGA menus, `FFF273.HST` title picture, boot stub read (FFA file 1) | RUNME text; HD only | none (YM silent) |
| 1 | 2016 / 655 | **Boot stub starts tune 1**: after loading FFA file 8 to `$806` the stub does `$4da50: moveq #0,d0 / bsr $4daa4` (attenuation `$b9a`=0), `$4da54: bsr $4dab0` -> `$4dac8` (`$b96`=1, `$ba0`=0, `$b9c`=0, `jsr [$80a]`=`$c6c`, `$b9a`=0, `$ba2`=0) | `$c6c` called from `$4dae4` (return) | stub VBL `$4decc` (vector `$70`): `$4df30: lea $806.w,a0 / movea.l (a0),a0 / jsr (a0)` = `$d0e`, each VBL once `$4e9d2` (set `$ffff` at `$4da58`) is non-zero; the same handler rotates 4 title-picture buffers every 6 VBL and reloads the palette |
| 2 | (HD 2016-2262 = 4.9 s, floppy 655-2071 = 28 s) | title picture animation while **FFA file 9 (240140 B) loads** to `$3104`; tune 1 plays throughout (HD: instant Fread; floppy: FDC, VBL kept running at 50/s) | stub | `$d0e` via stub VBL |
| 3 | 2262 / 2071 | stub ends `jmp $3104` (floppy bp `$4daa0`; HD `$4daa2` patched to `$4bc` = PP's patcher, then `jmp $3104`); game cold start `$26656: jsr $5032` = `$33870` | `$33870` called from `$2665a` | `$5138 = $3386e` (an `rts`): **music stops** (YM chip left as is; the driver state is not cleared) |
| 4 | 2345 / 2154 | game title: "Flames of Freedom" then MIDWINTER II logo. **Tune 1 restarted**: `$7626 = -1; jsr $32132` | `$321fe` d0=1, return `$32138` <- `$312c4` (call site `$312be`) | `$3225c: move.l (a0),$5138.w` -> `$d0e`; `$b9a`=2 |
| 5 | 3842 | M/J/K choice ("Press M ... Joystick ... Keyboard", the boss "Good morning Steel"); key M = `$2c5a0` handler: `jsr $3238e` = **fade-out start** (`$b9a` rises 2..15, one step per 20 VBL, driven from the VBL handler `$262fc`/`$32296`) | `$3238e` from `$2c5ba` | `$d0e` keeps ticking |
| 6 | 4122 | fade end: `$322d6`: `$b9a=$f`, `jsr [$808]` (silence = `$c4c`), `$7626 = 0`, `$6876 = -1` | `$322d6` from VBL handler (`$2633a`) | `$d0e` still installed but silent |
| 7 | 4276 | HQ hall/corridor (WAR ROOM, RAIDS, CONTROL, TRAINING, PERSONNEL doors): **tune 1 again** | `$321fe` d0=1, ret `$32138` <- `$1cee8` area (`$7626=ffff` first) | `$d0e`, `$b9a`=2 |
| 8 | 5271-5551 | click on a door (personnel): fade start `$3238e` (d0=0 = `$b9a` at that time) -> fade end `$322d6` | `$2c5ba`, `$26340` | |
| 9 | 5850 | Personnel screen (agent card): tune 1 restarted by `$2c6ce` (`$7626=-1; jsr $32132`) | ret `$2c6da` | `$d0e` |
| 10 | 5850-10756 | personnel -> hall -> CONTROL (world map "SELECT MISSION") -> mission text pages -> boss/thumbs screen: **tune 1 keeps playing** (every later `$321fe(1)` returns at once, `$7626 == 1`) [obs: no `$c6c` hit in 5850-11728] | `$321fe` from `$313ec` (`$313e6`) | `$d0e` |
| 11 | 10925 | thumbs-up: mission loads; sound init `$18e32`: `$513c = $18f92` (the 3D game's sfx tick, see `amiga_sound.md`) | `$18e32` from `$27ed8` | `$5138` still `$d0e` |
| 12 | 11728 | 3D view starts: `$32488: jsr $502c` = `$338c2`: `jsr $5032` (park tick `$3386e`, clear sfx voices, silence PSG `$338ce`) then `move.l $513c,$5138` | `$338c2` from `$3248c` | `$5138 = $18f92`: **music stops for good, sfx (asn_*) tick takes over** |

Other observations [obs]:
- **War Room** (door click in the hall after the first fade-out): no `$321fe`, no tick change; the screen is silent (`$b9a = $f`, `$7626 = 0` left by the earlier fade). Entering and leaving the War Room, and Training (no response), caused no tune start.
- **In the 3D view: F5 (tactical map)**: `$249d6: $7626=-1; jsr $32132` = tune 1, `$3225c` installs `$d0e` (VBL 17928, tick `$18f92` -> `$d0e`); map icons: key (bottom left, hover shows 7 icons).
  Key icon "return to the world" (far left): `$32f20` (`$7626=-1; jsr $32132` = tune 1 restarted, `$d0e` stays), world reload, `$18e32`, ..., `$32488: jsr $502c`: back to `$18f92`.
- **Accelerated time (the user's F5 -> waypoint icon -> pick spot -> key -> far-left icon)** [obs]: after the return to the world the autopilot ("Auto Route" in the cockpit message window) runs `sub_037626` once per frame (called from `$33bd6`); its first act is `jsr $32156` = `$321fe(5)`: **tune 5**
  (`$7626` 1 -> 5, `$c6c` with `$b96 = 5`, `$3225c` installs `$d0e`, `$b9a = 2`, `$ba2 = 0` = loops) at VBL 30181 (first run: 25300). Every later frame calls `$321fe(5)` again (no effect, `$7626 == 5`). It ends when `$37666`/`$32488` run
  `jsr $502c` (`$338c2` at VBL 30287 = 106 VBL = 2.1 s later in this run, route about 13 game minutes; first run 25300 -> 25404): `$5138` returns to `$18f92`, **the music stops, the route continues silently** (`$7626` stays 5 so it is not restarted). So tune 5 plays for the "preparation" phase of the accelerated
  time; how long it lasts on the user's screen depends on the route length [INFERENCE: the stop is the end of the auto-route's first phase, not of the whole flight; only two routes were run]. The cost of the 3D view during that time is the game's (no sfx tick is running: `$18f92` is NOT called while `$5138 = $d0e`), so a music mixer here does not add to the sfx cost.
- **HD vs floppy**: identical from #3 on (floppy run: `$33870` VBL 2071, `$321fe(1)` 2154, `$3225c` 2154). Differences are only #1-#2: the stub's tune is audible for 4.9 s on HD and for the whole file-9 load on floppy (28 s in Hatari; a real drive is slower) [obs]. Floppy additionally shows "Insert Graphics Disk" etc.; no music there (the `$5138` stays `$d0e` and the YM sits silent).
- **Other tunes** (2, 4, 5, 6, 7, 8, 9, $a, $c, $f, $10, $11): the call sites are known [disasm] but I did not walk those screens, except 5 (accelerated time, above) and 1. Table in §2.4 with the evidence that exists.
- Music on/off key: `$26358` (VBL handler) toggles `$763a` when key flag `$769a` is set and writes `$b9a = 2` (on) or `$f` (off) [disasm]; `$26342` (VBL) clamps `word($b9a)` to `>= 2` (no effect on the byte at `$b9a`).
- The VBL never stalled in the HD run (1.5 s sampling, no interval < 35 VBL/s) because Hatari's GEMDOS-HD loads take no emulated time; on a real HD the HAGA service runs `move #$2700,sr` around Fopen/Fread/Fclose (`$1f8fe2`) [disasm], so the VBL (and the music tick) is masked for the whole 200000-byte chunk read. The floppy loader (`sub_027840`) runs at `move #$2300,sr` (VBL allowed) [disasm]; floppy VBL was 50/s throughout [obs].

## 2. The control interface (what a replacement player must satisfy)

### 2.1 Vector table `$806` (FFA file 8 offset 0, 9 longs) [disasm]
| addr | value | meaning | callers |
|---|---|---|---|
| `$806` | `$00000d0e` | **tick** `jsr (a0)` once per VBL, saves nothing itself (callers `movem.l d0-d7/a0-a6`) | stub `$4df30`; game copies the LONG into `$5138` at `$3225c`, `$32288`, `$32322` |
| `$80a` | `$00000c6c` | **start**: starts the tune in `$b96`; the YM driver first does `$c44=1` (busy), `jsr $c4c`, clears its channel state `$123e-$1389`, loads 3 sequence pointers from `$142c + 12*tune` | stub `$4dae2`; `$3222c` (`$321fe`); `$3236a` (`$3232c`) |
| `$80e` | `$00000c4c` | **silence PSG** (regs 0-13 = 0, mixer `$ff`) | `$322ea` (`$322d6`, fade end) |
| `$812` | `$00000b96` | pointer to **tune id** (LONG, 0 = silent tune) | `move.l d0,(a1)` at `$32216`, `$4dad0`, `$32358` |
| `$816` | `$00000ba0` | pointer to `$ba0` (word, cleared at every start; YM-sfx mute flag) | cleared only |
| `$81a` | `$00000b9a` | pointer to **volume attenuation** (BYTE `$b9a`: 0 loud, 2 normal in game, `$f` = mute; subtracted from every YM volume `$100a: sub.b $b9a.w,d5`) | written by `$32296` (fade step), `$3224e/$3227a` (2 or $f), stub `$4daa8`/`$4daee`; read `$26342`, `$100a` |
| `$81e` | `$00000ba2` | pointer to **once flag** (WORD `$ba2`: 0 = loop, 1 = play once then tune 0) | written by `$322aa` (1), `$322c0` (0), `$4dabc` (0) AFTER the start call |
| `$822` | `$00000b9c` | pointer to `$b9c` (word, cleared at start; per-channel YM-sfx mask) | cleared only |
| `$826` | `$00000b9e` | pointer to the YM mixer shadow byte (`$b9e` = reg 7 image) | read by `$338b0` (copied into the 3D sfx state `$682c+..`) |
Plus one global value: the **volume level** is `$b9a` read each tick, and **the current tune** for the dedupe is the game's own word `$7626` (not the driver's).

### 2.2 The tune-request layer (game code, all in FFA file 9) [disasm]
`$321fe` `sub_0321fe(d0.w = tune)`: `cmp.w $7626.w,d0 / beq rts` (same tune already playing: nothing), `$7626 = d0`, `movem.l`, `$b96.l = d0` (via `[$812]`), `$ba0 = 0` (`[$816]`), `$b9c = 0` (`[$822]`), `jsr [$80a]`, `$6876 = 0`, `if $f92a != 1 then jsr $5032`
(= `$33870`: `$5138 = $3386e`, clear the 3D sfx state `$6869-$686b`, `$682c-$685f`, PSG silence `$338ce`), then
- music on (`$763a != 0`): `$b9a = 2`, `$763c = 2`, **`$5138 = [$806]`** (`$3225c`), `$762a = 0`, `$7630 = 0`;
- music off: `$762a = $7630 = 0`, `$b9a = $f`, and `$5138 = [$806]` only if `$f92a != 1`.
Then the wrappers set the once flag: `moveq #n,d0; bsr $321fe; bsr $322c0` (`$ba2 = 0`) or, for tune 8 only (`$3217a`), `bsr $322aa` (`$ba2 = 1`). Callers force a restart by writing `$7626 = -1` first (e.g. `$249d6`, `$2c6ce`, `$32f20`, `$2fedc..`).
Stop paths: `$5032 -> $33870` (park: `$5138 = $3386e`), `$502c -> $338c2` (`jsr $5032; $5138 = $513c`: back to the 3D sfx tick), fade: `$3238e` (init: `$7636 = $7634 = $14`, `$7638 = $b9a`, `$7630 = 1`) + VBL handler `$262fc` (every 20 VBL `$7638++`, `jsr $32296` = `$b9a = $7638`; at `$10`: `$7630 = 0; $7632 = -1; jsr $322d6`),
`$322d6` = `$b9a = $f; jsr [$808] ($c4c); $7626 = 0; $6876 = -1`. Timed tune: `$762a = 1, $762c = n` (e.g. `$31f50`: tune 7) -> `$3232c` (called from `sub_031500`, `$31530`): starts tune `$762c` via `[$80a]` directly, `$762a = -1`, `$7628 = $320` (800 VBL = 16 s), then `$3238e` = fade (`$3232c` -> `$32344..`).
Everything the player must honour: **start** (`$b96`), the **tick**, **`$b9a`** each tick (0..15 attenuation; 15 = silent), **`$ba2`** (once/loop; when a once tune ends the YM driver sets `$b96 = 0` and starts tune 0 = silence, `$e78`), and **silence** (`[$808]`). The game never reads `$b96`, `$c44`, `$ba0`, `$b9c`.

### 2.3 Tune ids and the YM data [disasm]
Tune table `$142c`, 12 bytes per tune = 3 channel sequence pointers; 18 tunes (0-17), tune 0 = three 3-byte stubs (`$1508/$150b/$150e`) = silence; tunes 1-17 -> `$291a, $1512, $218c, $15c2, $17da, $1a2a, $1a90, $1b1a, $1cd2, $2032, $1e14, $1ecc, $2226, $22f2, $23fa, $2770, $2872` (first channel). Sequence format = YM driver bytecode ($fe-escape opcodes via the jump table `$10ec`).
YM driver state: 3 channel records of `$50` bytes at `$123e` (+`$1240`..), `$c44` busy, `$c2c` channel bit, `$c2a`, `$c3e` (period offset), shadow regs `$bc0-$bd3`.

### 2.4 Which id on which screen (ST call sites; "parallel" = same id and same caller on the Amiga, §5)
| tune | wrapper | ST call sites (code address of the `jsr`) | `$757c` set there | screen / meaning | evidence |
|---|---|---|---|---|---|
| 1 | `$32132` | boot stub `$4dac8` (direct vtable), `$312be`, `$313e6`, `$32f26` (`$32f20`), `$249dc` (`$249d6`), `$2c6d4` (`$2c6ce`), `$30044`, `$30084`, `$300c2` (via `$30030/$3005a` with `$f92a=-1`), and a call from the hall (`$1cee8` area) | 2 at `$30090`, 6 at `$249e2`, else none | title, M/J/K, hall, personnel, map, briefing, F5 map, "return to world" | [obs] #1-#12, F5 run |
| 2 | `$3213e` | `$2fee2` | `$a` | ? | [disasm] only |
| 3 | `$321b6` | none | - | unused | [disasm] |
| 4 | `$3214a` | `$30106` | 7 | ? (`$3005a` branch `$5362 == 0`) | [disasm] |
| 5 | `$32156` | `$310d4`, `$3711c` (`$37100`: `$f92a=-1` around it, `$757c = 0` after), `$3762a` (`$37626` = **accelerated time**) | 0 | accelerated time / end of an episode | [obs] `$3762a`; others [disasm] |
| 6 | `$32162` | `$2ecd0` (`$757c=7`), `$2ff50` (`$2ff42`: `$757c = 7`, text "Destroy the Enemy Armada !!" / "This island is already free..." / "Press M for Mouse..." chosen by `$eb96/$eb9c`, 300 VBL wait, `jmp ($f92c)`) | 7 | mission briefing / mission-start text screen [INFERENCE from the strings at `$14adc/$14be9`] | [disasm] |
| 7 | `$3216e` | `$2ff04` | 3 | ? (also requested 16 s timed via `$762a/$762c` at `$31f50`) | [disasm] |
| 8 | `$3217a` (once flag 1) | `$334a6` | - | play-once jingle | [disasm] |
| 9 | `$32186` (jump table `$4f24`, once flag 0) | `$1ad86`, `$1af5a` (overlay `$18d96-$210b2`, near the weapon code) | - | in-game event jingle [INFERENCE] | [disasm] |
| `$a` | `$321aa` | `$2fec0` | 1 | ? | [disasm] |
| `$b` | `$32192` | none | - | unused | |
| `$c` | `$3219e` | `$3651a` (`$f92a=-1` around it) | 8 | ? | [disasm] |
| `$d`,`$e` | `$321c2`,`$321ce` | none | - | unused | |
| `$f` | `$321da` | `$2ff26` | 5 | ? | [disasm] |
| `$10` | `$321e6` | `$30014` | 4 | ? | [disasm] |
| `$11` | `$321f2` (loop, `$322c0`) | `$300e4` | - | ? | [disasm] |
`$757c` is the index of the screen's 16-colour palette (`$4d6a + 32*i`, `$32022`), not a tune. I could not name the screens of tunes 2, 4, 6, 7, `$a`, `$c`, `$f`, `$10`, `$11` from code alone (each `jsr` is the head of a screen-entry routine that ends with `lea screenhandler,a0 / jmp (a0)` via `$30128`); they
are the war-room / mission-end / death / training screens [INFERENCE]. The Amiga agent's per-screen list can name them since the ids are the same.

## 3. Who owns what (evidence for "which file")
- **FFA file 8** = `$806-$3104` = vtable + YM driver + note/instrument tables + all 17 tunes. Directory entry `[ck $5857][off $e88][start track-side 16][len 10494]`; extracted file == RAM `$806-$3104` except runtime variables (67 bytes: `$b9a-$b9e`, `$bc1`, `$c2d`, `$1000`, `$10d7`, `$123e-$1389` ...) [obs: Python compare, `work/music_study/st/ffa_file8.bin`]. `ram_boot_hd1mb.bin` and `ram_boot_fl1mb.bin` (boot dumps) already contain `$806: 0d0e 0c6c 0c4c 0b96` [obs].
- The **boot stub** (FFA file 1, 4096 B at FFA `$200`; HD: RUNME reads it with `Fread(4096)` from `FILES\FFA` and copies it to `$4d9a6` at its `$370` block; floppy: boot sector loads it) loads file 8 and file 9, starts tune 1 through the vtable and calls the vtable tick in its own VBL handler. It owns no music code itself [disasm `$4da3a-$4dae4`, `$4decc-$4df50`].
- **HAGA** (PP's resident file service, `$F8000`/`$1F8000`) and RUNME own no music code; HAGA's only relevance is the `move #$2700,sr` around file reads (§4.5).
- **FFB** overlays (`$18d96-$210b2` etc.) hold the 3D sfx driver (`$18f92`, `amiga_sound.md`) and the weapon code that requests tune 9; they never touch `$806-$3104`.

## 4. Hook design for a DMA music replacement

### 4.1 Sites (original bytes) [disasm]
Preferred: **the vtable** (FFA file 8, resident; a plain data patch, 3 sites):
| site | orig | new |
|---|---|---|
| `$806` (long) | `00000d0e` | `asn_mtick` (bank blob, e.g. `$D5xxx`) |
| `$80a` (long) | `00000c6c` | `asn_mstart` |
| `$80e` (long) | `00000c4c` | `asn_mstop` (silence) |
Each blob entry must, when the machine is not DMA-capable (`v_mode != 2`: ST, Mega ST, TT, Falcon, or no bank), `jmp $d0e.l` / `jmp $c6c.l` / `jmp $c4c.l` (as `asn_tick` does for the sfx path: the YM driver then runs unchanged; the cost is a `jmp`).
`asn_mstart` reads `$b96.l` (tune id), sets up the Amiga-derived tune, and when `$ba2`/`$b9a` are examined later by the tick (note: `$ba2` is written AFTER the start call). `asn_mtick`: apply `$b9a` (volume), run the player, run the (shared) mixer.
Alternative code sites (only needed if the vtable cannot be patched early enough): `$d0e` (`4a78 0c44 6700 0014`), `$c6c` (`31fc 0001 0c44 4eb8`), `$c4c` (`303c 000d 11c0`).
Where each variant takes effect: the table longs are read at call time (stub tick `$4df30`, start `$4dae0`) and **copied** into `$5138` at `$3225c/$32288/$32322`: any patch of `$806` made before the game's first `$321fe` is seen by all.

### 4.2 When the patch can be applied
- **Game phase (both HD and floppy)**: file 8 is in RAM when the existing boot trampoline (`$B3000`, applied right after PP's patcher `$4bc..$59C` on HD, from stage 1 on floppy) runs, so the three longs can be written there like any boot-phase site. Earliest music this covers: the game's tune 1 at the title logo (HD VBL 2345, floppy 2154); from this point the YM never has to sound.
- **HD stub phase (title tune, 4.9 s)**: the bank (`$BB000-$D5E9E`, loaded by the RUNME splice at text `$46` before anything) is already resident when the stub starts. Patch the stub's RAM after PP's own patches and before the jump: the final instruction of RUNME's stub-launch block is
  `$3c4 (file) / text $3a8: 4ef9 0004d9a6  jmp $4d9a6.l`; replace with `jmp hook.l` (a 6-byte same-size splice like the existing one at text `$46`; the block is copied to the stack region at `$370` so its size must not change) where the hook patches **file 8 after it is loaded**, i.e. it must act
  at `$4da4a: 6100 0106 (bsr.w $4db52, loads file 8) / 7000 (moveq #0,d0)`: replace those 6 bytes (`61000106 7000`) in the stub image in RAM by `jsr hook.l` (6 bytes) and let the hook do `bsr $4db52` (absolute `jsr`), write the 3 vtable longs, `moveq #0,d0`, `rts`. Nothing else in the stub changes: its tune start (`$4dae2 jsr (a1)`) and tick (`$4df30 jsr (a0)`) go through the vtable.
  Result: HD title tune on DMA from the first note (VBL 2016). The DMA hardware is then running in the stub phase (no game VBL handler, hence no `asn_wd`): see 4.4.
- **Floppy stub phase (28+ s of title tune)**: the bank is NOT in RAM until FFA file 10 (payload + bank) is read by stage 1 after file 9 (`mw2patch.py` `STAGE1`, final `jmp $4DAA0` -> stage 1). Options: (a) leave the YM for the stub phase; the game's tune 1 restart at the logo is DMA (cost: nothing, but the stub's 28 s title tune is YM);
  (b) move stage 1 (the file-10 read `sub_04db52` with `$16(a6)=10`, dest `$B3000`, 32 track-sides, about 8-10 s of FDC) before `$4da50` by editing the stub image in FFA at the same site (`$4da4a`, 6 bytes): the title tune then starts ~10 s later but is Amiga music; the dead-code window `$4DDAA-$4DDE9` (64 B) used by stage 1 is too small for both, so a second splice is needed [INFERENCE: sizes].
  [obs] the stub phase on floppy lasts VBL 655-2071 (28 s) and the title animation runs from `$4da58`.

### 4.3 Earliest moment, summary
| delivery | bank resident | earliest DMA-capable note | needs |
|---|---|---|---|
| HD | at RUNME text `$46` (before HAGA menus) | the stub's first tune start `$4dac8` (VBL 2016 here) | RUNME splice at the stub launch + `$4da4a` hook (§4.2) |
| HD, minimal | same | game logo tune 1 (`$321fe` VBL 2345) | the 3 vtable longs only (a normal boot-phase site set) |
| floppy | after FFA file 9, by stage 1 | game logo tune 1 (VBL 2154) | the 3 vtable longs |
| floppy, full | before file 9 | stub start | stage 1 moved before `$4da50` (+8-10 s boot) |

### 4.4 Sharing the sfx blob (single mixer, shared DMA)
Facts: the music tick (`$d0e` slot) and the sfx tick (`$18f92` -> `asn_core`) are never active together: `$5138` holds exactly one of them (`$d0e`, `$3386e`, `$18f92`); every transition goes through `$33870`/`$338c2` [obs timeline]. So one mixer/ring/DMA can serve both:
- `asn_mtick` (music) = player + `asn_mixer` with the music voices; `asn_tick` (sfx) = Amiga sfx driver + `asn_mixer` with the sfx voices; both set the heartbeat `SV+12` so the existing watchdog (`asn_wd`, game VBL handler `$262c2`) sees "a tick ran".
- Hand-over: when the sfx tick takes over from the music tick (`$502c`), `asn_enter` already clears the DMA and voices if `v_act == 0`: the music tick must set `v_act = 0` (and the sfx tick `v_mus = 0`) so that the other side re-runs its enter. Silence YM once at the first DMA start (already `asn_ymsilence`).
- The music stop path: `$33870` is run at every start and every stop (before `$5138` changes): hooking `$33870` is not needed if the music tick stops mixing as soon as it is no longer called; the watchdog stops the DMA within 2 VBL (a 40 ms repeat of the ring at the seam). A cleaner stop hook: `$33870`'s first instruction `48e7fffe` (movem) -> `jmp stub` that clears the music state then replays it.
- Microwire/mix init is shared (`asn_microwire`, done once at the first DMA start); in the stub phase that init happens in the vtable start routine.
- Cost: see `amiga_sound.md` §3.3: 125 samples per VBL, 40/48 cycles per voice and sample: 4 voices = 24.5 k cycles = 15 % of a frame. On the hall/map/briefing screens the CPU is idle, so a higher mix rate (more cycles per VBL) is affordable there; in accelerated time the user accepts frame loss (no player input), so higher quality is allowed there too. The DMA rate (`$ff8921`) is global: switching it between music (e.g. 12.5/25 kHz) and sfx (6258 Hz) needs both mixers to know the rate (`K4` constant, ring length) and the ring to be restarted at the switch.

### 4.5 Disk loads, ticks and rate
- **Interrupt masking**: HD: HAGA's service does `move #$2700,sr` around every `Fopen/Fread/Fclose` (`$1f8fe2`) [disasm]: the VBL (and so the music tick) can stall for the duration of a 200000-byte chunk read (real HD: unmeasured here; Hatari: 0 emulated time). The ring (1024 B at 6258 Hz = 164 ms) repeats during that stall -> a buzz of up to the stall length. Fix: mute the DMA (clear `$ff8901`) when a load starts and resume after: the game's loader entry `sub_027840` (`$27840: 48e7 fffe` ... `move #$2300,sr` at `$2784e`) and its return `$2794a`/`$2789a` (the existing load hook site) are known sites [disasm `loading.md`]. A larger ring (e.g. 8 KB = 1.3 s) only lengthens the repeat; muting is the right fix. Floppy: the game's loader keeps IPL 3 (VBL allowed), so the tick keeps running during loads (VBL 50/s observed) but the tick costs CPU while the FDC loop polls; the stub phase also keeps VBL running.
- **Rate**: the tick is the VBL: 50 Hz (`$ff820a` bit 1 set) or 60 Hz (bit clear). The YM tunes run per tick, so at 60 Hz the original plays 20 % fast; the Amiga tick is 50 Hz [INFERENCE: PAL VBL driver; the Amiga agent should confirm] -> use the `asn_run` accumulator (5 of 6 VBLs) for correct speed. The tick must not depend on the game frame rate: it is called from the VBL handler (`$262f4`) and the stub VBL.
- **STE-only gating**: reuse `asn_init0` (bank header `ASN1`, `BANK` address, 68000 probe, bus-error-guarded `tst.b $ffff8901.w`): on ST/Mega ST/TT/Falcon (and when the bank is missing) the three entry points `jmp` to the YM routines, so those machines keep the YM tune (also in the boot stub). The probe must run on the first `asn_mstart` (called in the stub on HD, before the game's VBL handler exists).
- **RAM free per screen**: the 1 MB HD layout has `$B2852-$E83E5` free during the game (the bank already uses `$BB000-$D5E9E`, 75063 B remain to `$E83E5`) and the bank was verified intact on the M/J/K screen, hall, map and 3D view (`amiga_sound.md` §8). The stub phase uses `$4D9A6-$4E9A5`, title pictures `$50000-$6FFFF`, stack `$783E8`, chunk cache `$81000-$B1D40` (HD, only while reading) [`loading.md`], none overlaps `$BB000+`. Floppy 1 MB in-game dump (`cr_fl_ste_ram.bin`): `$BB000-$FFFFF` all zero except the payload (`$B2FF8-$BA4A3`) [obs] (TOS's screen at `$F8000` is not used by the game), i.e. ~270 KB are free on floppy [INFERENCE: nothing else was running]. HD: PP's service sits at `$F7554`, the area `$E83E5-$F7554` was not examined.
- **The 3D view's CPU load**: the 3D game is CPU bound (5 fps); the music tick runs in the 3D view only during accelerated time (and the F5 map/loads), so it competes with the world update there only.

## 5. Mapping to the Amiga music (evidence)
- The Amiga MWII has the same wrapper family: `moveq #n,d0 / bsr.w $25aea / rts` at flat `$25a62..$25ae2` for **n = 1,2,4,5,6,7,8,9,$b,$c,$a,3,$d,$e,$f,$10,$11** (17 wrappers; ST: the same 17 at `$32132..$321f2`), and the dedupe core `$25aea` is the ST `$321fe` (`cmp.w $60a8e.l,d0` = `$7626`, `move.l d0,$57340.l` = `$b96`, `jsr $5760c` = `$c6c`) [disasm both; `work/music_study/st/amiga_wrap.py`].
- Same callers in the same order: ST `$2fec0 (id $a)`, `$2fee2 (2)`, `$2ff04 (7)`, `$2ff26 ($f)`, `$2ff50 (6)`, `$30014 ($10)`, `$30044/$30084/$300c2 (1)`, `$300e4 ($11)`, `$30106 (4)` <-> Amiga `$22f40 ($a)`, `$22f66 (2)`, `$22f8c (7)`, `$22fb2 ($f)`, `$22fe0 (6)`, `$230b4 ($10)`, `$230f8/$2313e/$23184 (1)`, `$231a8 ($11)`, `$231cc (4)`; unused ids on both sides: 3, `$b`, `$d`, `$e`; id 9 = a jump-table entry on both. ST id 12 caller `$3651a` <-> Amiga `$2a5a2`; id 8 `$334a6` <-> `$27016`; id 5 `$310d4/$3711c/$3762a` <-> `$242c6/$2b2ba/$2b85a`.
  Conclusion: **ids are parallel (ST tune n = Amiga tune n)** [disasm; the content of each tune was not compared].
- The Amiga tune table entry is 16 bytes = 4 track pointers (`$3057c-$305a4`: `id << 4` + `$57e78`), the ST entry 12 bytes = 3 channels. The Amiga flat `$57e78`/flat `$30da8` read in the flat dump did not look like a pointer table at the first entry (it starts mid-code); locating the table is the Amiga study's job.

## 6. Constraints and open risks
- **Seam/restarts**: the game restarts tune 1 on the title logo (`$7626 = -1`) 1.7 s after the stub's tune 1 was parked (HD VBL 2262 -> 2345); on floppy ~1.5 s too. The replacement must restart cleanly at `$80a` (and not skip because it is "already playing": the game's dedupe is `$7626`, not the player's).
- `$b9a` is changed asynchronously by the VBL handler (fade) and by the game (2 / `$f`), so the player must sample it every tick (not only at start). Tune 8 (once) and tunes ended by the fade rely on `$322d6` (`[$80e]`) + `$7626 = 0`.
- Music in accelerated time: tune 5 plays only until `$502c` (`$37666`/`$32488`), measured 2.1 s in one route; if the user hears music for longer, it is not `$d0e` (check with a longer route) [INFERENCE].
- Hatari measured only; real STE: nothing run on hardware (same caveat as `amiga_sound.md`).
- HD: the RUNME stub-launch splice (text `$3a8`) and the stub's `$4da4a` hook are new RUNME edits (the existing delivery asserts the shipped RUNME md5; the 6-byte same-size replacement keeps the copied block size).
- 2 MB/4 MB HD builds: the bank address is fixed (`$BB000`), the stub phase is the same; the chunk cache of >= 4 MB machines (`$81000-$135000`, `pp_bigram_cache`) already overlaps `$BB000` only when that patch is missing.
- TT/Falcon: `jmp` to the YM entries (unchanged music); the existing gate refuses a 68020+.
- Screens not walked live: War Room music (silent in the run), training, mission end/death, tunes 2/4/6/7/a/c/f/10/11 (§2.4).
