Powermonger: World War One Edition (Bullfrog / Electronic Arts 1992) - patched floppy v@VER@
===========================================================================================

PowermongerWW1_patched.st is the original single-disk Powermonger WW1 Edition with a
small loader added and a set of fixes. It boots like the original: put it in drive A
and reset (the game starts from the AUTO folder). Nothing else on the disk is changed.
The game still saves to a separate SAVE GAME disk, as in the original.

What is different
-----------------
- The copy protection is gone. The game does not ask a manual question, and it does
  not ask for the original Powermonger disk when you start a new conquest: the WW1
  disk is the only one you need (apart from your save disk).
- The world runs at the same speed on every machine: a fixed 4 world ticks per
  second (the original ties the game clock to the frame rate), also on a 60 Hz
  screen.
- Faster drawing, the picture identical to the original frame by frame: the mouse
  pointer is redrawn only when needed, sprites and the 3D-window copy use the blitter
  on STE-class machines (a pre-shifted cache on a plain ST), the landscape triangle
  fill was rewritten, and the game draws into a third screen buffer instead of
  waiting for the next refresh. What was measured in Hatari (frames per second
  before / after the last round of speed patches, 8 MHz STE): map view 5.08 -> 6.58,
  zoomed view with men moving 2.97 -> 4.58, a random land 4.00 -> 4.95, the STE battle
  4.44 -> 5.71; at 16 MHz STE 10.1 -> 14.1, 6.4 -> 9.6, 8.4 -> 11.0, battle 9.3 -> 12.7.
  Plain ST 8 MHz: 3.47 -> 4.48, 2.48 -> 3.53, 2.80 -> 3.66; Mega STE as shipped
  (16 MHz + cache): 8.42 -> 11.71, 5.10 -> 7.97, 3.20 -> 4.17. No battle was measured
  on the ST or the Mega STE; real hardware was not measured.
- STE, Mega STE, TT and Falcon: the sound effects play through the DMA sound chip
  instead of the sample interrupt that ate part of the CPU. A plain ST / Mega ST
  keeps the original YM sound. (On a Falcon the game's own YM sample player is also
  changed to use addresses the Falcon has.)
- Men walk smoothly between world ticks on machines fast enough to draw more than
  4 frames a second (16 MHz and up). Rain and snow are drawn on every frame, not
  only when the world takes a step.
- Hover help: point at a command icon (or the map, rotate, zoom and compass symbols)
  and its meaning appears in the black bar at the top of the screen, with the key
  that does the same. Rest the pointer on a town for a moment and the bar shows what
  its workshop is making and how far along it is; with Build selected it says what
  the town would make.
- Keys: the command icons have keys (1 2 3 postures, A Attack, D Drop Food, E Equip,
  F Get Food, G Send Captain, H Go Home, I Invent / Build, L Alliance, M Get Men,
  N Drop Items, O Option, Q Query, R Derank, S Supply Food, T Trade, X Transfer Men,
  Y Spy; F1-F4 the map icons; [ ] rotate, = and - zoom, Shift gives the fine rotation
  and the closest / farthest zoom; F5 (or Alt+D) cycles the 3D detail level between High,
  Medium (no rain/snow, 50% trees) and Low (no rain/snow, no trees, flat-shaded
  terrain) with a brief top-bar message). A key does exactly what the click on the icon
  does; the cursor keys still scroll. Keys are ignored while you type or while a
  window is open.
- TT and Falcon: the game starts from the normal desktop mode (the loader sets the
  ST-compatible 320 x 200 mode itself; on a Falcon with a VGA monitor too), and the
  mouse pointer is drawn into the new picture before it is shown, so it does not
  vanish or flicker.
- Mega STE: 16 MHz with the CPU cache on. A Mega STE starts at 8 MHz and neither TOS
  nor the game switches it up; the loader writes 3 (16 MHz, cache on) to the speed
  register ($FF8E21) before the game runs. If the register is already non-zero when
  the game starts, your value is kept. A 0 is the power-on state and cannot be told
  from an explicit 8 MHz without cache, so it is raised as well. Going back to 8 MHz
  while the game runs is not possible. The cache is not proven on real hardware: the
  game unpacks code and rewrites its own instructions, which a cache can get wrong.
  It ran without a difference in Hatari; if your Mega STE misbehaves, set 16 MHz
  WITHOUT cache before starting the game (your value is kept).
- Retire and the win / lose pictures: the game keeps every picture it loads in a RAM
  cache that grows without a limit; the cache now stops below the patch code, and a
  picture that does not fit is read from the disk again the next time. (Without this
  the picture after Options -> Game -> Retire could land on the patch code.)
- Victory button: when you reach a full winning position, the balance gauge above the
  compass is replaced by a golden VICTORY button; clicking it retires straight to the
  victory screen.
- Keyboard / mouse: a position that the mouse packet parser would take from outside
  the screen is ignored (it could crash the game after a lost byte), the blitter copy
  is done in short pieces so that the keyboard chip is not starved, and typing in the
  name / save boxes is buffered in a 32-key FIFO and drawn immediately so fast typing
  never drops letters.
- The main menu shows the version and credit line (v@VER@ enhanced by dad_prg) at the
  bottom of the screen.
- Every change checks the original bytes first. If anything is not as expected
  nothing is changed and the game starts as the original.
See PATCHES.TXT for the list.

Machines
--------
Tested in the Hatari emulator, not on real hardware: ST (TOS 1.04) 1 MB, STE (TOS 1.62)
1 MB, Mega STE (TOS 2.06) 4 MB (starts at 8 MHz, the loader sets 16 MHz), TT (TOS 3.06)
4 MB from the default TT-medium desktop, Falcon (TOS 4.04) 4 MB with an RGB or a VGA
monitor. Needs 1 MB of RAM.

TT and Falcon: the original game does not start on a 68030 (it runs code it has just
unpacked over the unpacker, and the instruction cache still holds the old bytes). The
loader switches the CPU caches off on a 68020 or better. The TT and Falcon builds
were also played by hand in Hatari (TT, Falcon floppy and Falcon hard disk).

Saving
------
Use the game's own Option -> File menu. The game asks for a SAVE GAME disk in drive A;
swap the disks when asked. The game disk has only 14 KB free, so the save disk must be
a second disk, exactly as in the original. A blank disk image with the game's own
SAVED GAME DISC boot sector is what the game expects; the game cannot format a disk
under Hatari.

Not tested on real hardware: the DMA sound set-up, the patches that probe the STE
hardware, the Mega STE speed register and cache.

Build: v@VER@, git @GIT@ (tools/package.sh)
