# Powermonger entities, names and backstories

Addresses are RAM addresses (1 MB STE run); dumps: `work/dumps/{map_idle,get_men,battle_320}.bin`. Evidence = disassembly (`tools/m68dis.py`) and the RAM bytes quoted; unproven = [INFERENCE].

## Tables (all fixed-size arrays in the data area, no heap)

| table | base | stride | count / end | evidence |
|---|---|---:|---|---|
| **people ("men")** | `$51b66` | `$32` (50) | 512 (`$57f66`) | counted for the "People" protection answer by `sub_00b892` (`$b8d6-$b8f0`: `move.b $5(a0),d2; ble` -> live when byte 5 > 0) |
| houses / settlement buildings | `$4f916` | `$12` | 400 (`$51536`) | same routine, byte 5 non-zero = used (the "Houses" answer) |
| captains | `$51538` | `$13c` (316) | 6 (`$51b66`) | `$3e06` (`mulu.w #$13c`), `$d23a`, `$165b2`, `$178ae` index them by `$57ffe` |
| armies/groups | `$4e514` | `$20` | 160 (`$4f914`) | `$d322` scans them; in the snapshots 3 are live (bytes `02 03 ..`, `02 03 ..`, `01 06 ..`) |
| animals (type `$11`/`$12` = sheep etc.) | `$4ccd6` | `$14` | 40 (`$4cff6`) | `$b8f4-$b91e` |
| trees/objects | `$4d252` | `$c` | 400 (`$4e512`) | `$b922-$b93c` (`tst.w $a(a0)`) |
| cell grid | `$47970` | word per cell, 64 cells per row (`$80` bytes) | `$47970-$4b970` | `$f938`, `$fdca` (`lea $80(a2),a2`) and `$d322`: each word = head of a chain of objects in that cell (0 = empty) |
| height/terrain bytes | `$438ee` | 1 byte per cell, row `$40` | | `$f932`, `$fdc6` (`lea $40(a1),a1`) |
| kingdom names | `$582f9` | 16 bytes | 4 | holds the typed name: `Bench`, `Jayne III`, `Jos XVIII`, `Harold II` (RAM bytes read in `get_men.bin`) |

### Person record (`$32` bytes) - fields seen in the data
Records 1-3 of get_men.bin: `1: b4 92 00 00 00 02 00 24 13 10 2a 00 20 20 27 00 20 60 00 02 13 90 2a 80 ... ` (index 2: `00 00 00 00 00 02 00 01 14 40 2b 40 e0 e0 17 00 20 e0 00 00 14 00 2b 00 ...`).
* `+5` (byte): 0 = unused, >0 = live (type/slot; values 1 and 2 seen; 47 live records of 512 in get_men).
* `+8` word = x, `+10` word = z (world units; a walker changes them by exactly 32 per axis per pass). `+20..+23` = a second x/z pair, equal to a neighbour of the first when the man walks [INFERENCE: destination/waypoint].
* `+14` (`$e`) byte = age: `(age-12)/20` (capped 4) indexes the word list `Tender/Young/Mature/Ripe/Great` (`$a4ae-$a4d4`, table `$a508`) and the number itself is printed through `$e39e` (`$a4d6-$a4ec`) as "At nn years old".
* `+$2c`, `+$2d` bytes: `+$2d` is read by `$3e06` as strength (`/20`), `+$10` = health byte written by the captain code (`$4001c: move.b d3,$10(a1)`), the health word list is `Very Sickly/Sickly/Very Weak/Weak/Well/Fit/Strong/Very Strong/Dead` (`$a2e0`).
* `+$18/+$1a` = link to the next person in a chain (`$3f9c-$3faa`: `move.w $1a(a1),d0; bne`).
The names, spouse, profession and equipment are NOT fields that hold text: see below.

## Names and backstories: generated on demand from the table offset (no stored text, no seed table)
**Code: `sub_00a9ce`** (called from `$a4a2` for a person, from `$9830/$99d4/$9aae/...` for houses, towns, forests). Input `d0` = seed. For a man the seed is the **record's byte offset in the people table**: `$a49a: move.l a3,d0; subi.l #$51b66,d0; jsr $a9ce` (so man number k has seed k*50).
```
a9d2  move.l $2df84.l,d1 / ext.l d0 / move.l d0,$2df84.l    ; save RNG state, load the seed
a9e0  jsr $12c9a.l                                          ; one RNG step: s = s*$bb40e62d mod 2^32, r = (s>>8)&$7fff  (seed 0 -> $bc614e)
a9e6  move.l d1,$2df84.l                                    ; restore RNG state
      3 syllables (d4 = 2,1,0): d0 = r&3 picks length 3,3,2,1 and table offset 0,24,48,64 ($aa4c);
      r>>=2; index = r&7; r>>=3; syllable = $aa5c + part*$48 + offset + index*length; first letter upper-cased (andi.b #$df)
```
Syllable table in RAM at `$aa5c` (3 parts of `$48` bytes): `briheaparropscrvombritogfinmachayfuttoltimjoslictomowhdesimyemreabmfcdhjfofninataovewarbal|fernogzarquebolbrotatbetcancidffllssmmttggdglyaeiouoaeiseeuxistogyliariaionandmanboyingralemetteagemitedesshtheremenryamdnsyhr`.
A Python re-implementation of that algorithm gives for men 1,2,3,4,5,6,7,8: `Vomed, Hayoem, Reggman, Clyogy, Bllion, Togbroa, Tolbetth, Mocidage`. The Query window of the house at the village in the explore dev snapshot read `People Name: Togbrog & Bllion` - man 5 = `Bllion` matches exactly, man 6 `Togbrog` vs my `Togbroa` differs in the last letter (I did not trace the last-part rule; [INFERENCE] the third-part index is shifted differently). So the 'spouse' names come from the neighbouring records (offsets 5 and 6), the house/town names the same way with their own table offsets.

**Backstory** = the query window `a37b-a41b` template filled by `@` placeholders (`sub_00a91a` expander: each `@` run calls the next function of a table `(a6)` that returns a string pointer; `$a4ae`/`$a4d6`/`$a4ee` shown above are some of them). Text in RAM (`$a37b`...):
```
 @@@@@@@@@ is @@@@@@@@@@@ and lives in
 a @@@@@@@@@@ with @@@@@@@@@,
 @@@@@@@@@@ working as a @@@@@@@@ @@@
 holds @@@@@@@@@@@@@@@@@@@@@@@. At @@@
 years old @@@ obeys @@@@@@@@@@@@@@.
```
= name, health word, building type + town name (settlement type list Village/Hamlet/Town/City/Capital/Base; buildings TownHall/Tavern/FishHut/FarmHouse/Ranch/Barn/Church/WorkShop/Turret/Square), spouse name, adverb (slowly/tirelessly/endlessly), profession (soldier/farmer/merchant/fisher/shepherd/leader), equipment (Nothing/a Pike/a Sword/a Bow/a Plough/a Boat/a Pot/a Catapult/a Cannon), age, he/she, ruler (kingdom list at `$582f9`: Bench, Jayne III, Jos XVIII, Harold II). Death text: `$a54b ' @@@@@@@@@@@@@@ has died whilst faithfully in the service of @@@...'`.
So the backstory is a *view* of the record's numeric fields (age byte, health, profession/equipment codes, house link) plus name syllables from the offsets; nothing is generated at game start and nothing is stored as text.

### Cost when shown
Measured with `e CycleCounter` at `$a91a/$a996` and `$a9ce/$aa4a` while querying a house (explore dev snapshot, 8 MHz): the whole window text expansion = 3 217 778 228 - 3 217 690 488 = **87 740 cycles (0.55 VBL)**, of which the four name generations cost 1604, 1604, 1572 and 1468 cycles. Once per click; not per frame. (I could not hit a moving man with the Query pointer in the time available, so a person window was not timed; it uses the same expander and `$a9ce`.)

## Per-entity update cost and waste
* People are not updated in a separate per-man loop that shows in the profile: logic stages total 43-74 k cycles per pass (2 %), `$d322` 13-22 k, `$3e06` 25-38 k, `$127e6` 3-4 k. Men are advanced by the 32-unit step in code reached from the army/captain logic (`$4342`, `$165b2`, `$15fa8`; 12-32 k per pass each). [INFERENCE] the walk update itself lives in the per-army code paths, not found as a single `add #32,$8(a0)` loop; I did not locate the exact instruction.
* `$d322` is NOT O(n^2): it walks the 160 group records (`$4e514`), skips empty ones (byte 0 = 0: 157 of 160 in the snapshots), and for each live one scans the 20-odd neighbour cell offsets from the table `$d49e` in the cell grid `$47970`, checking the chain heads with byte/bit tests. Cost 13-22 k per pass. No sqrt, no distance multiply: purely cell-grid + `cmpi`/`btst`.
* Redundant: `$d322` re-scans all 160 slots each pass (`$d34a-$d494`) though only 3 are live - a live-list would cut ~10 k cycles/pass (0.5 %). Names are never recomputed per frame (on demand only). The expensive per-entity cost is drawing, not thinking: each visible object costs one `$115e0` entry + a sprite blit (~18 k cycles, `$12326` family) and every cell with an object forces `$115e0` inside the terrain loop (`$fdb2-$fdbc`).
