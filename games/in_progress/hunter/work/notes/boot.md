# Hunter boot, screens and `boot_to_game()` (HunterBench)

Machine: 1 MB STE, TOS 1.62, 8 MHz, Hatari 2.6.1. `tools/hunter.py`: `Hunter().boot_to_game()` (43 s, ran twice in a row from a cold start:
both runs ended with player words `$ab2..` = `9e26 0000 2415`, i.e. HUD X158 Y36, VBL 2269 / 2272, `in_game()` True).

## 1. Why a GEMDOS-HD (Hatari `--harddrive`) does not work, and what does
Evidence chain (all from this session):
1. With `--harddrive`, START.TOS shows the HW-detect screen and the title picture, then returns to the desktop. `--trace gemdos`: `Dgetpath(0xc0760)` -> `'\FILES'`, a bus error probe at `$fff00039`, then `Pterm0()` at `$f814`.
2. Disassembly of START.TOS (`$f4bc`): `cmpi.l #'PPHD',-8(a1)` with `a1 = ($472)` (hdv_bpb): looks for PP's own HD driver. Without it: TOS<2 -> `bsr $f9be` = direct ACSI read of **physical sector 0** into `$1742a` and `cmp.w #$1234` on the word sum (`$f9a8`), TOS>=2 -> XBIOS DMAread (`trap #14 / $2a`); otherwise IDE probe at `$fff00000` (`$fab8`) and exit with `d7=$ffdf` (the Pterm).
3. After the check passes, the loader **runs the root sector** (`jsr (a0)` at `$f706`, `a0 = $1742a`, `d7 = dev<<5`, `d5 = $80`) to install the HD driver privately, then copies hooks into the live vectors ($472/$476/$47e/$4b2/$4b6/$516/$5a0, `$4c2` = 3) and hooks trap #1 for Malloc/Mshrink (`$f966`).
4. The game's own mini-OS (`$84 = $c84a0`, GEMDOS emulation `$c899e`, trap #13 handler `$c0bee`) opens `\FILES\<hexdigit>` through the **live hdv vectors**. With a fake bootable root sector (`rts`, sum `$1234`) the game's floppy-only `hdv_bpb` (`$c19be`: `cmpi.w #2,8(a6)` -> returns NULL for dev>=2) gives `Getbpb(2)=NULL`, `Fopen` returns -33, nothing is loaded and the game executes unloaded data (history trace: `jsr 4(a0)` at `$c9ae` into `$11676`, `eor.l d2,-(a6)` with `a6=$ff8000` -> bus error, reset).
5. So the disk needs a real driver in the boot sector chain: HDDRIVER boot code (`gamebench/hd/hddriver_root.bin`, sector 0 of an HDDRIVER-formatted disk: finds the bootable partition, reads its boot sector with DMAread `$2a`, checks `$1234`, jumps; partition boot sector: searches `HDDRIVER SYS` in the root directory and runs it).

`build_hd()` builds that: 16 MB FAT16 image (`mkfs.fat -F 16 -s 2 -r 512 --offset 2`), root sector = HDDRIVER boot code `$0..$1b5` + our partition table (flag `$81`, `BGM`, start LBA 2) + checksum word so the sum is `$1234`; partition boot sector = HDDRIVER partition loader (`hd/hddriver_pboot.bin`, `$34..$1fd`) + our BPB (`$3..$33`), sum `$1234`; `HDDRIVER.SYS` (V10.15, from `gamebench/hd/`), all game files, `DESKTOP.INF` with `#Z 01 C:\START.TOS@ @`. Hatari is started with `--gemdos-drive skip --acsi 0=<scratch>/hd.img`; boot log: `HDDRIVER V10.15 ... Atari ACSI (ICD) 0.0: Hatari EmulatedHarddisk, Drives: C`, then the desktop autoruns `C:\START.TOS`.
Not tested: TOS 2.06 / Mega STE (the first attempt with a plain `rts` root sector ended in `Pterm(-1)` before AUTO; the HDDRIVER-based image was never tried with TOS 2.06). 16 MHz numbers therefore use `--cpuclock 16` on the STE.

## 2. Screens, keys, timings (cold boot, wall-clock seconds from launch)
| t | screen | action | gate (ref crop, box in 832x588 shot) |
|---|---|---|---|
| ~3 s | HDDRIVER banner | none | - |
| ~8 s | HW-detect text screen: "Press U for unlimited stamina", Machine STE, TOS 1.62, GAMEX: key F9 (`M` = machine settings for Mega STE/Falcon, `U` = unlimited stamina; not used) | counts down ~25 s without a key; **space (Hatari scancode 57 via `hatari-event`) skips it** | `hw.png` (96,52,600,82) |
| ~10-35 s | picture 1 (HUNTER / Activision photo): the loader reads HUNTER.PCH, D15R_H5.FIC, HUM.FIC | space (scancode 57, loader polls GEMDOS) | `title1.png` (320,405,505,445) |
| +15 s | game loads `FILES\6,4,3,7,8,9,1,2,E` (load map below), animated title (side icons animate, VBL ticks) | **xdotool `space` (0.3 s hold)**; `hatari-event keypress` here hangs the game's keyboard ISR (PC stuck at `$afe6`: `btst #4,$fa01(a6)` loop waiting for the ACIA IRQ line) | `title2.png` (200,85,640,170) |
| | MAIN OPTIONS: View soldier / Start new game / Disk Operation / Demo | click "Start new game" at (415,217) after `home()`; game pointer home = (100,66) | `main.png` (270,135,565,300) |
| | AVAILABLE GAMES: Hunter / Missions / Action / CANCEL | click **Action** at (415,249) | `games.png` |
| | "Please type in name-" | type a name (default `bench`) with xdotool keys, 0.15 s hold, 0.3 s gap; then click | `name.png` (90,52,320,82) |
| | MISSION 1 OBJECTIVE page | click again | `mission.png` (330,195,510,225) |
| ~43 s | 3D view, on foot at the HQ (X158 Y36-38), HUD visible | nothing pressed | `game.png` (470,340,740,418) + RAM marker |

Match tolerance: mean abs RGB diff < 1.5 (4.0 for the HUD crop). Do not touch the pointer after the last click: the game pointer sits in the HUD message area.

## 3. In-game marker (RAM)
`$899` (= `$93(a5)`, `a5 = $806`): bit 7 set while the 3D loop runs (in each of 3 samples it is `$80`; `$00` on every menu screen: dumps `work/dumps/boot/ram_{hw,title2,main,mission,game}.bin` give 0,0,0,0,128). The render briefly clears it (`$5f86 bclr #7`), so `in_game()` accepts 2 of 3 samples and also requires flips of `$ff8203` > 0.
Flip register: **`$ff8203`** (not `$ff8201`; `fps()` with `($ff8201).b` counted 0 flips). Set as the class default.

## 4. Gotchas found
- **Phantom joystick**: with Hatari's default joystick config the game moves the character/boat by itself (~100 world units/s, `Down`-like). `--joy1 keys` fixes it, and cursor keys then are the joystick. `Hunter()` always adds it. Restored snapshots also need it (the memstate does not carry the CLI option).
- A snapshot does not keep a held key: after restore the stick is released. Hold the key after the restore (`h.hold('Up')`).
- The first start (before any input) is not a vehicle: player on foot at the HQ; the car at X157 Y39 (object record `$b52`) is 1 unit left of the start. Walk `Up+Left` 1.7 s then `Left` 1.2 s to "You have boarded a car".
- `savemem` + restore of 1 MB and 4 MB states work (4 MB boot: same recipe with `memsize_kb=4096`, same game state and 4.5 fps).
- Load map of the game's file hook (`$150`, d0 = file digit, a0 = destination) to the 3D view: 6->$23000, 4->$10FB2, 3->$11656, 7->$79714, 8->$2AD00, 9->$2AD00, 1->$61514, 2->$48004, E->$23000. The two screen buffers are `$23000` and `$2AD00` (also the destinations of the picture files; they are overwritten by the 3D view).
- The game's trap#1 handler jumps to `$fa002a` (Hatari's GEMDOS cartridge trap address) only because START copies the vector it finds; harmless.
- Hatari's `profile on`: any fifo `hatari-debug` command resets the profiler; the helpers arm the end breakpoint first.

## 5. Snapshots (work/snapshots, 1 MB STE unless noted)
`1mb_foot_stand` (HQ, standing, X158 Y38), `1mb_foot_walk` (saved with Up held; after restore hold Up again), `1mb_car_stand` (just boarded the car), `1mb_car_drive` (saved while Up was held; the car sits against the shore, so it barely moves), `1mb_car_turn` (Up+Left held when saved), `1mb_hills_stand` (teleported by poking `$ab2/$ab6` to X151 Y50, terrain height 283), `4mb_foot_stand` (4 MB). All restore and run (fps 4.5-7.3). The "busy scene" is the standing HQ view itself (the heaviest measured: 1.76 M cycles/frame).
