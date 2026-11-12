Populous v@VERSION@ enhanced by dad_prg  (patched PP HAGA hard-disk conversion)

Copy the folder over PP's Populous folder (RUNME.TOS, HAGA, FILES\POLA are replaced; FILES\POM and FILES\POP are unchanged, so your saves stay).
Run RUNME.TOS as before. Needs 1 MB or more.

Changes against PP's release:
- Fixed game speed: the world runs 5 turns per real second on every machine (ST, STE, Mega STE, TT, Falcon) at 50 and 60 Hz.
  The original ran one turn per drawn frame: about 3 to 9 turns a second on an 8 MHz STE depending on how busy the map was,
  twice that at 16 MHz and up to 40 on a Falcon. The pointer and scrolling stay smooth while the world waits; a click acts on
  the next turn (at most 0.2 s later). Paused, painting land and two-player link games run as before.
- Faster, same picture: the land score the game recomputes around every building each turn, its multiply routine, the pointer
  (only redrawn when something changed) and the background copy were rewritten with identical results. A busy map on an 8 MHz
  STE went from about 3.2 to 5.3 frames a second, enough for the full 5 turns a second.
- Keyboard shortcuts (during map play only; typing names or using dialogs never triggers them). A key does exactly what
  clicking its icon does:
    R raise/lower land   Q query   P place papal magnet
    M go to magnet  S settle  G gather  T fight
    E earthquake  W swamp  K knight  V volcano  F flood  A A (twice within 3 s) Armageddon
    L view leader  Z view magnet  B view battle  N view knight  H view house
    Space pause  U music on/off  X sound effects on/off
  Keys follow the UK/US key positions.
- Tooltips: pointing at an icon shows its name, key and cost in the white strip at the top of the book page.
- Fixed: the copy-protection check that ended every game with Armageddon once more than 18 peeps existed now passes.
- Fixed: a crash after loading a saved game (seen on the Mega STE, LOAD then next map), caused by a garbled mouse packet
  during disk access; such packets are now ignored.
- Loading no longer fades to grey, and is faster.
- Falcon: the sound no longer crashes the title and the game; TT and Falcon run the patched game.
- HAGA no longer overwrites the patch code on 4 MB machines.
- A small credit line on the title menu.

Every patch checks the original bytes it replaces first; if anything is not as expected, nothing is changed.
Tested on Hatari: STE 1 and 4 MB (TOS 1.62, 8 and 16 MHz, 50 and 60 Hz), ST 1 MB (TOS 1.04), Mega STE 4 MB (TOS 2.06).
TT and Falcon: use the floppy version (PP's hard-disk loader fails on those machines in Hatari, unpatched too).
Not tested on real hardware.
