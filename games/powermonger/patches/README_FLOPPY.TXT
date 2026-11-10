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
  the map view runs at 4.6 frames per second instead of 2.3-2.8, and a
  marching army at 4.8-5.4 instead of 3.5 (measured in Hatari). The mouse
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
  of the screen.
- The main menu shows the version and credit line (v@VER@ enhanced by
  dad_prg) at the bottom of the screen.
- Every change checks the original bytes first. If anything is not as
  expected nothing is changed and the game starts as the original.

Machines
--------
Tested in the Hatari emulator (not on real hardware): ST (TOS 1.04) 1 MB,
STE (TOS 1.62) 1 and 4 MB, Mega STE (TOS 2.06) 4 MB at 8 and 16 MHz,
TT (TOS 3.06) and Falcon (TOS 4.04) 4 MB. Needs 1 MB of RAM.

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
