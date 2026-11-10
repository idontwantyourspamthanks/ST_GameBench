Powermonger (Bullfrog 1990) - patched hard-disk version v@VER@
==============================================================

The original game only runs from its own floppy disk (it reads the disk
with its own FAT and floppy-controller code). This folder is the same
game with the same patches as the patched floppy (see the README of that
zip), but loading and saving go through GEMDOS, so it runs from a hard
disk.

Contents
--------
AUTO\WAR.PRG     the game (patched). TOS starts it at boot.
DATA\*.DAT       the game's 15 data files (read by name)
PMLATE.DAT       part of the patch code, restored after the title program
                 has been loaded (keep it in the same folder as DATA\)
SAVEDISK.DAT     the save game "disk" (400 KB, formatted, empty). The
                 game's Load / Save menu reads and writes it. Back it up.

Installing
----------
Copy AUTO\, DATA\, PMLATE.DAT and SAVEDISK.DAT to the ROOT of the
partition you boot from (C:\AUTO\WAR.PRG, C:\DATA\..., C:\SAVEDISK.DAT)
and reset. The data files are looked up in the folder the program was
started from, which at boot is the root. To use a subfolder instead,
run WAR.PRG with that folder as the current directory, DATA\ inside it
[INFERENCE: only the boot-from-AUTO start was tested].

Hard-disk drivers and the "TOS swap" (read this)
------------------------------------------------
The game takes over the machine at once: it overwrites the low memory
that TOS and the disk driver live in. To keep the disk usable, the
loader copies that memory (TOS's world) aside at start, and for every
file access exchanges it with the game's memory, runs the GEMDOS call
and exchanges it back. So:
- You need a driver that works through TOS's GEMDOS and keeps its code
  in ST RAM. Tested: HDDRIVER 10.15 on an ACSI disk (STE with TOS 1.62,
  Mega STE with TOS 2.06, TT with TOS 3.06; all in Hatari), and Hatari's
  built-in GEMDOS folder. Other drivers (AHDI, ICD, CBHD...) work the same
  way in principle but were not tried.
- The swapped region (everything from address 8 up to the program's own
  memory: TOS variables, the driver, resident AUTO programs, accessories)
  may be up to about 100 KB. It was 77 KB (STE, TOS 1.62) and 86 KB (Mega
  STE, TOS 2.06) with HDDRIVER. If yours is bigger, the game prints a
  message and then asks for the disk forever (no harm done to the disk):
  remove resident AUTO programs / desk accessories, or use a smaller
  driver cache.
- Load and save pause for the two swaps (not timed).

Machines
--------
Tested in Hatari only, never on real hardware: STE (TOS 1.62) 1 MB and
Mega STE (TOS 2.06) 4 MB and TT (TOS 3.06) 4 MB with HDDRIVER on ACSI
(each including a save and a load through the game's menu), and the
GEMDOS folder on an STE. On a 68020 or better (TT, Falcon) the loader
switches the CPU caches off, see the floppy README. A Falcon: Hatari cannot give HDDRIVER a disk
there, so the Falcon is only tested with the floppy version.

Saving
------
Option -> File -> Save / Load as on the floppy (slots A, B, ...).
The game asks "already exists, overwrite?" for a slot in use.
