Populous v@VERSION@ enhanced by dad_prg  (floppy version)

Populous_boot.st : double-sided 80x10 (800K) game disk, boot from drive A. Needs 1 MB.
Populous_save.st : blank 720K disk for saved games.
Saving: choose Save a game, put the save disk in A:, give a name, Save. Loading: put the save disk in A:, Load; when the game asks
"Insert the original Populous disk in A:" put the game disk back.

Changes against the original:
- Fixed game speed: 5 world turns per real second on every machine (ST, STE, Mega STE, TT, Falcon) at 50 and 60 Hz; the original
  ran one turn per drawn frame (3 to 9 a second on an 8 MHz STE, up to 40 on a Falcon). Pointer and scrolling stay smooth.
- Faster, same picture: the land score, a multiply routine, the pointer and the background copy were rewritten with identical
  results (a busy map on an 8 MHz STE: about 3.2 -> 5.3 frames a second).
- Keyboard shortcuts during map play (a key does exactly what clicking its icon does):
    R raise/lower land   Q query   P place papal magnet
    M go to magnet  S settle  G gather  T fight
    E earthquake  W swamp  K knight  V volcano  F flood  A A (twice within 3 s) Armageddon
    L view leader  Z view magnet  B view battle  N view knight  H view house
    Space pause  U music on/off  X sound effects on/off
- Tooltips: pointing at an icon shows its name, key and cost at the top of the book page.
- Fixed: the copy-protection check that ended every game with Armageddon once more than 18 peeps existed now passes.
- Fixed: garbled mouse packets during disk access are ignored (they could crash the game).
- Falcon: the sound no longer crashes the title and the game.
- A small credit line on the title menu.

Tested on Hatari: STE 1 MB (TOS 1.62), TT 4 MB (TOS 3.06), Falcon 4 MB (TOS 4.04). Not tested on real hardware.
