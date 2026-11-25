Powermonger (Bullfrog 1990) - patched floppy v@VER@
===================================================

Powermonger_patched.st is the original single-disk Powermonger with a
small loader added and a handful of fixes. It boots like the original:
put it in drive A and reset. Nothing else on the disk is changed, and
the game still saves to a separate SAVE GAME disk as before.

What is different
-----------------
- The world runs at the same speed on every machine. The original ties
  the game clock to the frame rate (a 16 MHz Mega STE ran it 2-3 times
  too fast); now it runs at a fixed 4 world ticks per second, also on a
  60 Hz screen.
- Faster drawing, picture identical to the original: on an 8 MHz machine
  the map view runs at 4.7-4.9 frames per second instead of 2.3-2.8, and a
  marching army at 4.8-5.6 instead of 3.5 (measured in Hatari). The mouse
  pointer is only redrawn when it moved, sprites and the 3D-window copy
  use the blitter on STE-class machines (a pre-shifted cache on a plain
  ST), and the landscape fill was rewritten.
- STE, Mega STE, TT and Falcon: the sound effects play through the DMA
  sound chip instead of the 8 kHz timer interrupt that ate a quarter of
  the CPU. A plain ST / Mega ST keeps the YM sound.
- Men walk smoothly between world ticks on machines fast enough to draw
  more than 4 frames a second (16 MHz and up).
- The copy-protection question (manual page lookup) is gone: a new
  conquest goes straight to the map.
- Hover help: point at a command icon (or the map, rotate, zoom and
  compass symbols) and its meaning appears in the black bar at the top
  of the screen, with the key that does the same (see Keys below).
  Rest the pointer on a village for a moment and the bar shows what its
  workshop is making and how far along it is ("<name>: making swords
  (45%)", "workshop idle", "no workshop"); with Invent selected it says
  what the village would make.
- Keys: the command icons have keys (1 2 3 postures, A Attack, D Drop
  Food, E Equip, F Get Food, G Send Captain, H Go Home, I Invent,
  L Alliance, M Get Men, N Drop Items, O Option, Q Query, R Derank,
  S Supply Food, T Trade, X Transfer Men, Y Spy; F1-F4 the map icons;
  [ ] rotate, = and - zoom, Shift gives the fine rotation and the
  closest / farthest zoom; F5 (or Alt+D) cycles the 3D detail level between High,
  Medium (no rain/snow, 50% trees) and Low (no rain/snow, no trees,
  flat-shaded terrain) with a brief top-bar message). A key does exactly
  what the click on the icon does; the cursor keys still scroll.
- Triple buffering: the game draws into a third screen buffer and no
  longer waits for the next screen refresh before it starts a new
  picture, so the frame rate gains the half refresh it used to waste
  (2-4% at 8 MHz, 8-10% at 16 MHz), with no tearing and the same
  pictures.
- TT and Falcon: the mouse pointer is drawn into the new picture before
  it is shown, so it no longer vanishes in the menus or flickers on the
  map (those machines show a new screen address at once, an ST / STE
  only at the next refresh).
- Rain and snow are drawn on every frame. The original drew the rain
  only when the game world took a step (4 times a second), so on a fast
  machine it showed on one frame in five (TT) or every other frame
  (16 MHz). The drops now fall smoothly at any frame rate; drawing them
  costs about 13% of a frame while it rains.
- The intro (title pictures and text) runs at the same pace on every
  machine: its delays were busy loops, 10 times too short on a TT. Its
  palette writes that ran past the palette (blank screen on a TT) are
  fixed.
- Keyboard / mouse: a mouse packet that lost a byte (the blitter held
  the bus too long for the keyboard chip) could send the pointer to a
  garbage address and crash the game; the blitter copy is now done in
  short pieces and a position outside the screen is ignored. Typing in
  the name / save boxes is buffered in a 32-key FIFO and drawn
  immediately so fast typing never drops letters.
- Retire, and the win / lose pictures (new in v1.1): the game keeps
  every picture it loads in a RAM cache that starts at 512 KB and grows
  without a limit; the "you have been defeated" / victory picture landed
  on the patch code (black screen and a hang after Options -> Game ->
  Retire). The cache now stops below the patch; a picture that does not
  fit is read from the disk again the next time it is needed, as on a
  512 KB machine.
- Mega STE: 16 MHz with the cache on (new in v1.2). A Mega STE starts
  at 8 MHz and neither TOS 2.06 nor the game ever switches it to 16 MHz,
  so the patched game ran at about 4.5 frames per second there. The
  loader now writes 3 (16 MHz, CPU cache on) to the Mega STE speed
  register ($FF8E21) at start, before the game runs; in Hatari the map
  view then runs at about 8 frames per second (16 MHz without the
  cache gains only about 12%, the RAM is still on the 8 MHz bus). Only
  a Mega STE is touched (the machine type must be an STE-family one and
  a read of that register must answer without a bus error); ST, STE, TT
  and Falcon are left alone. If the register is already non-zero when
  the game starts, your value is kept: set 16 MHz WITHOUT cache (or any
  other value) in the control panel / a utility before you start the
  game and the loader leaves it as it is. A value of 0 is the power-on
  state and cannot be told from an explicit 8 MHz without cache, so it
  is raised as well.
  What does NOT work: going back to 8 MHz while the game runs (the game
  takes the machine over, there is no desktop or control panel), and
  keeping 8 MHz by leaving the register at 0. If you want a Mega STE to
  stay at 8 MHz, use the v1.1 zips.
  The cache is not proven on real hardware (or on a MiSTer): the game
  loads and unpacks code with its own DMA and rewrites its own
  instructions, which a cache can get wrong. It ran without a
  difference in Hatari (see the notes of the release), nothing more is
  known. If the game misbehaves on your Mega STE, set the speed
  without cache before starting it, or use v1.1.
- The main menu shows the version and credit line (v@VER@ enhanced by
  dad_prg) at the bottom of the screen.
- Every change checks the original bytes first. If anything is not as
  expected nothing is changed and the game starts as the original.

Machines
--------
Tested in the Hatari emulator (not on real hardware): ST (TOS 1.04) 1 MB,
STE (TOS 1.62) 1 MB, Mega STE (TOS 2.06) 4 MB (it starts at 8 MHz, the
loader sets 16 MHz), TT (TOS 3.06) and Falcon (TOS 4.04) 4 MB. Needs
1 MB of RAM.

TT and Falcon: the original game does not start on a 68030 (it runs
code it has just unpacked over the unpacker, and the instruction cache
still holds the old bytes). The loader therefore switches the CPU
caches off on a 68020 or better; the game then runs, at about 20 frames
per second on the TT and 10-12 on the Falcon in Hatari. The Falcon also
needs the fix for the title music (the original writes the sound chip
through addresses the Falcon does not have).

Saving
------
Use the game's own Option -> File menu. The game asks for a SAVE GAME
disk in drive A and can format a blank one itself. Swap the disks when
asked. The disk image has only 31 KB free, so the save disk must be a
second disk, exactly as in the original.

Not tested on real hardware: the DMA sound set-up (taken from the Hunter
patch), and the patches that probe the STE hardware.

Build: v@VER@, git @GIT@ (tools/package.sh)
