Powermonger: World War One Edition (Bullfrog / Electronic Arts 1992) - patched hard-disk version v@VER@
======================================================================================================

The original game only runs from its own floppy disk (it reads the disk with its own FAT
and floppy-controller code). This folder is the same game with the same patches as the
patched floppy (see README_FLOPPY.TXT and PATCHES.TXT), but loading and saving go
through GEMDOS, so it runs from a hard disk. The copy protection and the request for
the original Powermonger disk are gone, as on the floppy.

Contents
--------
AUTO\WW1.PRG      the game (patched). TOS starts it at boot.
*.PAK, MAPDATA.DAT  the game's data files, read by name
SAVEDISK.DAT      the save game "disk" (400 KB, formatted, empty). The game's Load /
                  Save menu reads and writes it. Back it up.

Installing
----------
Copy the AUTO folder, the data files and SAVEDISK.DAT to the ROOT of the partition you
boot from (C:\AUTO\WW1.PRG, C:\FX.PAK, ..., C:\SAVEDISK.DAT) and reset. The data files
are looked up in the folder the program was started from, which at boot is the root.
[INFERENCE: only the boot-from-AUTO start was tested; a subfolder should work if WW1.PRG
is run with that folder as the current directory.]

Hard-disk drivers and the "TOS swap" (read this)
------------------------------------------------
The game takes over the machine at once: it overwrites the low memory that TOS and the
disk driver live in. To keep the disk usable, the loader copies that memory (TOS's world)
aside at start, and for every file access exchanges it with the game's memory, runs the
GEMDOS call and exchanges it back. So:
- You need a driver that works through TOS's GEMDOS and keeps its code in ST RAM. Tested:
  HDDRIVER on an ACSI disk (STE with TOS 1.62, Mega STE with TOS 2.06) and Hatari's
  built-in GEMDOS folder (STE, Mega STE, Falcon). Other drivers were not tried.
- The swapped region (TOS variables, the driver, resident AUTO programs, accessories)
  may be up to about 112 KB. If yours is bigger, the game prints a message and then asks
  for the disk forever (no harm done to the disk): remove resident AUTO programs / desk
  accessories, or use a smaller driver cache.
- Load and save pause for the two swaps.

Machines
--------
Tested in Hatari only, never on real hardware: STE (TOS 1.62) 1 MB and Mega STE (TOS 2.06)
4 MB, each with HDDRIVER on ACSI and with the GEMDOS folder (each including a save and a
load through the game's menu); Falcon (TOS 4.04) 4 MB through the GEMDOS folder (Hatari
cannot give HDDRIVER a disk on a Falcon). On a 68020 or better the loader switches the
CPU caches off, see the floppy README.

Known issue (one line): after a save or a load, a mouse click can be lost now and then
(the first click afterwards is ignored; click again). Seen in Hatari on a Falcon.

Saving
------
Option -> File -> Save / Load as on the floppy (slots A, B, ...). The game asks
"already exists, overwrite?" for a slot in use.

Build: v@VER@, git @GIT@ (tools/package.sh)
