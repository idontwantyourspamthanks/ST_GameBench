# The four resources WW1 names but the WW1 disk lacks (lead, 2026-11-23)

User decision: if the game needs them, take them from the original Powermonger disk and ship them on our WW1 disk.

## Facts [obs]
- WW1's resource-name table (EA game, RAM at the title, `/tmp/pmww1/ea_title_ram.bin`): `SPRITE8.PAK` $e5ac, `CAP_SPR.PAK` $e5d4, `BITMAP.PAK` $e5e0, `MAPDATA.DAT` $e60c, `END_PIC1.PAK` $e618, `END.PAK` $e626; the key-disk routine's own name `DATA\SPRITE8.DAT` at $1cfb8.
- EA WW1 disk (`disks/ea.st`): has CAPGRAPH FX LOSE MAP MAPDATA QAZ SPRITE8/16/24/32 TEXTURES WIN (.PAK, MAPDATA.DAT), **no** END_PIC1, END, BITMAP, CAP_SPR.
- Original Powermonger disk (`games/done/powermonger/disks/protected.st`; a normal FAT12 disk, 80x2x10, media $F9: `mdir` needs `MTOOLS_SKIP_CHECK=1`): `DATA\` holds SPRITE40 MAP TEXTURES QAZ SPRITE16 SPRITE8 SPRITE24 SPRITE32 CAPGRAPH FX MAPDATA WIN LOSE **END_PIC1.DAT (16960 B)** and **END.DAT (60936 B)**; **no** BITMAP or CAP_SPR.
- Same file format: PM `FX.DAT` and `TEXTURES.DAT` are byte-identical to WW1's `FX.PAK` and `TEXTURES.PAK` (md5 be715581 / 5768ddf3); WW1's own SPRITE8/CAPGRAPH/QAZ differ (WW1 art). So a PM `.DAT` can be shipped under the `.PAK` name WW1 asks for.
- The cracked versions (Cobra #26, Fuzion #156) hold the game as packed bundles (`WW1_FUZI.LFB`, `SHADOW.LNK`), so the names can't be grepped there; whether they carry the end pictures is not determined (unpack with a verified depacker to check).

## To do (campaign-end gate, before packaging)
1. Does any WW1 code path load END_PIC1/END/BITMAP/CAP_SPR (find the resource-id call sites), and when (campaign end?)?
2. Play to the end of a campaign with the WW1 disk only: does the game request one of them, or show a blank/garbled ending?
3. If needed: copy `END_PIC1.DAT` and `END.DAT` from the Powermonger disk onto our WW1 disk as `END_PIC1.PAK` / `END.PAK` (the floppy writer and the HD folder), and re-run the ending. BITMAP and CAP_SPR exist on neither disk: if code reaches them, report what happens (probably unused leftovers of Powermonger's table).
