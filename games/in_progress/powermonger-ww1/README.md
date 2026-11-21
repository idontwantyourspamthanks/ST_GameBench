# Powermonger: World War I Edition (1991, Electronic Arts / Bullfrog)

Status: **in progress** (started 2026-11-21). Porting the original Powermonger enhancements
(`../../done/powermonger/`) to the WW1 edition: the fixed-rate world tick, the tooltips, the
keyboard shortcuts, and the performance work where the engine still matches.

Base: the cracked **Pompey Pirates #106** release (`disks/pp106.st`, converted from the
`originals/Pompey Pirates #106.zip` MSA by `tools/msa2st.py`). Chosen by the user ("The Pompey
Pirates version is probably the best bet"): plain files, no Pasti protection, and the crack's
own notes explain its changes. Other menu-disk conversions of the same game are in `originals/`
(Cobra #26/#27, Flame Of Finland Superior #109A, Fuzion #156) and the Pasti image of the
original Electronic Arts disk (`powermonger_-_world_war_i_edition_electronic_arts.zip`, .stx,
not used).

## The disk (PP106, 80 tracks, 819200 B, FAT12)

| File | Bytes | Date | Role |
|---|---:|---|---|
| `AUTO\MENU106.PRG` | 97598 | 1992-05-29 | the PP menu: runs the virus check, `READ_ME.PP`, then the game |
| `WWIEDITN.PRG` | 283902 | 1992-05-29 | **the game, "single parted" by The Alien**: GEMDOS PRG, text 62050 B + a 221820 B packed payload; it reads its own trailing bytes at file offset 62082 into `$c1d84` at boot |
| `READ_ME.PP` | 60794 | 1992-05-29 | the Alien's doc displayer ("HL Displayer v0.9") + the typed reference card (Pompey Packer V2.6) |
| `CHEKFILE.PP` | 899 | 1992-05-29 | file checksum checker ("This disk is a perfect copy") |
| `PP6091FX.PRG` | 8018 | 1992-05-29 | the Toxic crack intro (same stub start as the original's `WAR.PRG` stage 0: Super(0)) |
| `TYANKEEG.EXE` | 131718 | **1987-04-22** | the original EA file: the game proper, self-depacking (a different LZ+variable-length scheme, not the original Powermonger's pure Huffman) |
| `TYANKEEI.EXE` | 118762 | **1987-04-22** | the original intro/title program (repacked, has the Pompey Packer string) |
| `TMYANKEE.DAT` | 73577 | **1987-04-22** | data (not a PRG) |
| `TMYANKEE.TOS` | 2310 | **1987-04-22** | a small launcher (BIOS probe + same depacker) |
| `YANKFILE.DAT` / `.BAK` | 1028 | **1987-04-22** | the resource/ramdisk table (starts `05 08 01 00`) |
| `DESKTOP.INF`, `HIDDEN.DOC`, `TOXIC\*` | | | desktop setup, the Alien's hidden doc, the Toxic intro's files |

"Yankee" is Bullfrog's internal name for the Powermonger engine (the original 1990 game's
`DATA\SPRITE40.DAT` — the packed game proper — is dated 1987 too).

## Boot chains

From the floppy (as shipped): TOS boot sector ("WWI_PP+%" signature) → `AUTO\MENU106.PRG` →
`READ_ME.PP` (docs) → the game.

From a folder (the way the harness runs it): TOS → `C:\WWIEDITN.PRG` (the packer) → reads its
own trailing payload → the Toxic intro → the doc displayer → the game title ("Powermonger WW1
Data Disk" credits, name prompt) → the options screen (Start New Conquest / Continue Conquest /
Play Random Land) → the territory chart → the 3D map view.

The game's data loads (e.g. the territory for a new conquest) go through **TOS's own GEMDOS/FDC
and read the files from drive A:**, so test runs keep the real disk in A: — with its boot
sector's checksum broken (`BS[0:2] = 0`), so TOS still boots from C: and the harness's
`--auto` wins. The Alien's "ramdisk" (his note in the docs: the game only checks that one
file exists) does not cover the territory loads.

## Harness

`tools/pmww.py` (`PMWW`, a `stharness.Hatari` subclass):
- `PMWW()` — the PP menu floppy. `PMWW(disk=None)` — the folder run with the single-part game
  (C: = `extracted/pp106/` minus the AUTO folder) and a de-booted copy of `disks/pp106.st` in
  A: (needed only by the save-disk path). `no_floppy=True` — the same without any disk.
- Cold boots: `boot_to_options()` = intro/docs (a burst of 8 spaces, then silence — the docs
  exit on their own timer; a disk present at boot makes the displayer HANG) -> name prompt ->
  options screen. Takes a snapshot at the options (`work/snapshots/options.sav`), then
  `boot_to_map()` = select Start New Conquest: click (112,72), activate (130,88) -> the chart
  (a dim live-rendered map) -> click the island (60,20) -> the 3D map view
  (`work/snapshots/mapview.sav`). `in_game()` checks the render loop runs.
- The **UI is an icon grid on a skewed panel** (`$6cac` the hit test, cells 4x6 px): the
  option rows have a select spot and a separate activate spot (+18,+16 px); "Continue
  Conquest" at (130,106) opens the dim "DISK STATUS REQUESTER / SAVE GAME DOES NOT EXIST"
  (the save-disk path — this one does drive the FDC through TOS, needing a disk in A:).
- **Mouse clicks need `poke_click(x, y)`**: the game re-programs the IKBD's absolute mouse
  position every VBL and Hatari only delivers absolute-mouse button packets together with
  movement, so a stationary host click never reaches the game. `poke_click` moves the host
  pointer to the target (the game's own position-forcing feedback keeps its tracked words
  there), then writes the packet parser's buttons byte: `$1d2af = 4` (left down), re-armed
  until the game's down-seen word `$2edbc` proves its latch code ran (`$81e`: latch
  `$2edb6`, click position `$2edae/$2edb0`), then `10` (release), `0` (idle).


## Input findings (options/title screen, the engine in RAM)

- IKBD ACIA handler `$e52`: keyboard scancodes `$f6..` split; the absolute-mouse packet
  (`$f7` + 5 bytes) is stored at `$1d2b1..` (buttons, x, y), and at packet end
  `$1d2af = buttons`, `$2edb2/$2edb4 = x/y` (the title program's tracked words).
- VBL handler `$75e` (vector `$70`): `$71b7c` = the VBL counter; `$2edac` = the VBL flag the
  loops wait on; **`$1d2af` (the buttons byte) is the VBL dispatch index** (table at `$79a`):
  4 = left-down → the latch code at `$81e` (latch `$2edb6`, click position `$2edae/$2edb0`,
  down-seen `$2edbc`), 8/10 = release paths, 0 = the idle path `$866` (which also re-programs
  the IKBD mouse position every frame).
- The item hit test `$12ee0` requires `$5a84e` (mouse-enabled) — 0 at boot, toggled by the
  game's own "mouse icon" region action (region 195, dispatch entry 22 at `$14446`).
  The harness pokes it on (`w $5a84e 0 1`).
- Clicks on the options screen: the "exit back to the crack chain" item is around
  (140..148, 84..88) — clicking there quits the game to the Alien's doc displayer.
  The real option-item boxes are still being mapped (pointer-hover sweep).

## Method

As `../../done/powermonger/` (`REPORT.md`, `work/notes/`): every claim cited by a disassembly
line or raw emulator output; the engine here is a **different build** from the 1990 game (a
byte search of the original's game image finds no match — the patch sites must be re-derived),
but the same codebase family, so the original's notes are the map.
