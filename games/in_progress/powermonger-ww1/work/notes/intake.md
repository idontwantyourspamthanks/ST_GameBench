# WW1 intake: the EA original (PMWW1Stage01, 2026-11-23)

Tags: **[obs]** a command I ran this session (output kept in the file named); **[INFERENCE]** reasoning only. Hatari 2.6.1, STE, TOS 1.62, 1 MB unless stated.

## The user's files (`originals/`, git-ignored)
| file | md5 | bytes | use |
|---|---|---|---|
| `powermonger_-_world_war_i_edition_electronic_arts.zip` | `934d176f1781b22bb03b276aa067c130` | 889898 | **BASE** (user decision 2026-11-23) |
| `Cobra #26.zip` / `Fuzion #156.zip` / `Pompey Pirates #106.zip` / `Flame Of Finland_Superior #109A.zip` / `Cobra #27.zip` | `46eab0d1…` / `73dd799f…` / `fd564266…` / `0c1833a0…` / `de732ddd…` | 756737 / 769016 / 787818 / 817858 / 772075 | comparison only; not examined in stage 1 |

## EA disk
* zip contains `powermonger_-_world_war_i_edition_electronic_arts.stx`, md5 `8d2f6c6b6ecc060524950aab4ffefb7b`, 889658 B (Pasti; 84 track records: tracks 0-79 = 10 normal sectors each, tracks 80-83 raw images without sectors).
* `tools/stx2st.py` (sector data taken by (track, sector id); asserts no sector carries an error flag / odd size) -> `disks/ea.st`, **409600 B, md5 `95354c89884a4cb82b62fe63400bf750`** [obs]. Single sided, 80 tracks x 10 sectors, FAT12, 2 sectors/cluster, 112 root entries, 36864 B free [obs `mdir`]. Sector 0 is not executable: TOS runs `AUTO\WW1.PRG`.
* The 4 raw tracks (80-83) are dropped. The converted disk boots to the title, runs a whole new game, Retire / Win / Lose and the protection question, so the game does not read them [obs, stage-0 gates]; whether they hold a track-based protection read that only a real drive would exercise is **not** proven [INFERENCE: no].
* Files (`MTOOLS_SKIP_CHECK=1 mcopy -s -m -n -i disks/ea.st :: extracted/ea/`, md5 of each):

| file | bytes | md5 |
|---|---|---|
| `AUTO\WW1.PRG` | 76336 | `dc93b917458125398a072c95f452f4b0` |
| `CAPGRAPH.PAK` | 11672 | `7c0c8fefb9fceb701fe8db5d3e2fb3b5` |
| `FX.PAK` | 75544 | `be715581023b1336f359862c20af7ec2` |
| `LOSE.PAK` | 24584 | `8249be9e9fa87f49a7969391336829a0` |
| `MAP.PAK` | 38348 | `93dc13ae77c04833cddd24b37683e73d` |
| `MAPDATA.DAT` | 71928 | `43e5a96418d081789c261a7f287a587c` |
| `QAZ.PAK` | 13748 | `be2700b2f6a190088d2b3c2bbaa9955b` |
| `SPRITE8.PAK` / `SPRITE16.PAK` / `SPRITE24.PAK` / `SPRITE32.PAK` | 9432 / 4064 / 8212 / 12840 | `de288a9f…` / `1c01d4bf…` / `aeb3a453…` / `f8930951…` |
| `TEXTURES.PAK` | 8104 | `5768ddf339fee77121826ee2caff9ff2` |
| `WIN.PAK` | 12672 | `cd233801a15057746f10ef03e084b7d6` |
(full md5s: `find extracted/ea -type f | xargs md5sum`.)

## It is a DATA DISK: the game asks for the original Powermonger disk  [obs, new fact]
The title says "Powermonger WW1 Data Disk". The first START NEW CONQUEST of a session shows a requester **"DISK STATUS REQUESTER: PLEASE INSERT ORIGINAL POWERMONGER DISK"** (OK / CANCEL), then after reading it **"PLEASE INSERT THE POWERMONGER DATA DISK INTO DRIVE A:"** (= the WW1 disk back). Other strings in RAM: "DISK IN DRIVE A: IS NOT THE ORIGINAL POWERMONGER DISK", "PLEASE INSERT SAVE GAME DISK", "FORMAT THE POWERMONGER DISK?". With master's `games/done/powermonger/disks/protected.st` (the user's original Powermonger floppy, md5 `b0f6972e81067a5822c0b21e6d00b8dc`) inserted through `hatari-option --disk-a` the requester accepts it and the game goes on; the second START NEW CONQUEST of the same session does not ask again [obs, `work/runs/`]. So a user needs both floppies (as with the 1992 release); the harness swaps them (`tools/pmww.py swap_disk`). The cracks (Fuzion etc.) presumably merge those files; not examined.

## The protection question is the same as Powermonger's [obs]
After the island click: "Between Pages 2-7: How many Houses / People in this land?" with four digit columns and two OK buttons, same screen layout as master (arrows at ST x 41/45/49/53, y 170; OK (19,176)). The expected answer is a word the game computed itself (type word `$5a85c`: 0 houses / 1 people; answer table `$5b008`), read from RAM by the harness, like master's. It is asked on the first land of a session and again after a lost game (round 3), not on the second land right after a first correct answer [obs].

## Program structure (see `delivery.md`, `tools/wwdepack.py`)
`AUTO\WW1.PRG` text 76304 B at TOS load address $AA9A (TOS 1.62) = a 110-byte loader (Super(0), vectors, copy of the rest to $514) + an **RNC method-1 variant unpacker** (stub text $d0..$244, decoder with no CRC fields, reads the stream backwards) + the packed stream at text $2fe ('RNC\x01', unpacked 145036 B, packed 75525 B). The unpacked result is itself a TOS program (header `601a`), relocated by the stub to base $576; text+data (118072 B, $576..$1d2ae) are copied to $576 and the stub jumps there. Nothing is read from disk later by the program itself except the data files and the Powermonger disk.
