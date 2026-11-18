# Nebulus (Gamex HD build): load chain, RAM map, patch delivery  (NebBoot2)

Tags: **[obs]** raw tool output this session (dumps in `work/dumps/boot/`, scripts in `work/boot/`); **[disasm]** read from the unpacked START.TOS
(`tools/pp_depack.py originals/NEBULGX/START.TOS` -> 32975 B: text `$7fa4`, bss `$1b046`, 163 relocations, = `work/boot/START_unpacked.tos`);
**[INFERENCE]** not proven. START text offsets are written `S+$xxx`. 1 MB STE / TOS 1.62 / HDDRIVER: START text at **$1AE16** (basepage $1AD16);
4 MB Mega STE / TOS 2.06: **$21094** [obs: first 12 text bytes found at those addresses in `ram_entry.bin` of each machine].

## 1. Files and what loads them
| file | size | role |
|---|---|---|
| `START.TOS` | 7206 (PP LZ) -> 32975 | the whole loader: HW detect, picture 1, picture 2, game load, Gamex hooks |
| `NEBULUS.PCH` | 102470 | picture 1 (box art, many colours = palette changes per scanline), played by START's own routine at `S+$1878` (data `S+$7b..` bss $7fa4+) |
| `NEBULTIT.FIC` | 27406 -> 32128 | picture 2 (Nebulus title). 'C3' header, LZ stream from +$20; unpacks to a 128-byte header + 32000 bytes screen at **$77f80/$78000** |
| `NEBEXE.FIC` | 166648 -> 271849 | the game: an ordinary GEMDOS program image (`601a`, text $a866, data $373a6, bss 0, reloc table 2497 B) |
| `GXUT270.PRG` | 12990 | **not in the boot chain**: desktop utility after F9 ("PLAY GAME IN RAM", save/load game states; looks for 'PPGX' at phystop, strings `GAMEX-utility for gamestate store`) |
| `README.TXT`, `NEBCHEAT.TXT` | | text only (cheat code `HELLOIAMJMP`, F1..F8 towers) |

## 2. START.TOS flow [disasm, offsets S+]
1. `$000` Supexec(`$736`) = machine detect (`$73c..$8a2`): OS header `$4f2` -> TOS ver `$804/$805`, region `$80a`, phystop>>19 -> memory class **`$806`**
   (1 MB = 2, 4 MB = 8; class 1 = 512 KB: no Gamex hooks, game read to $4e000); STE/MSTE/TT/Falcon probes via bus-error handlers (`$8e21`, `$200000` pattern, `$8006`).
   `sne $3bc` = Gamex hooks on unless class 1. Basepage himem set to $78000 (`$80`).
2. `$0a6` `Setscreen($78000)`; `$126` flush keys; HW-detect text screen `$8a8` ("Machine / TOS RAM / GAMEX: key F9"); 0x499 x Vsync (~25 s) or key; **M** -> machine settings `$b52` (Mega STE 16 MHz via `$ff8e21`, Falcon bus/cache), no key = continue.
3. Picture 1: class 4 (TT/Falcon) `$122a` (screen at $380000, NEBULUS.PCH read whole to START+$7fa4) else `$1798`: probes NEBULUS.PCH (Fopen `$121e`, Fread 6 B -> $3e93a [obs bp `S+$1850`: `003f 0006 00000006 0003e93a`]) then plays it with `$1878` (own palette/raster code at `S+$7970..$7e1c`); waits for **space** (`$1362`: key 0x20, up to $2f1e8 polls).
4. Gamex setup (`$19a`..`$2a8`): `a7 = S+$b2e`; saves MFP/regs/palette into the F9 state at `$fff80..`; builds the F9 table `$fff40` (`$7fcf8,$ffd20,$fff80,$7fd20,$380,$206,...` [obs `$fff40` dump]); `$200`..: copies `S+$5fa` (128 longs) to **$ffd20** (F9 code); on class>=4 `$102008` else **$c0108** receives a copy of RAM `$8..S+$b2e` (TOS state, loop `$258`; obs: 1 MB $c0108..$dba48, 4 MB $102008..$122e18, START text copy found at $daf16 / $123094); `$640` = `rts` (TT/Falcon: 23 longs).
5. `$2aa` Fopen NEBULTIT.FIC, Fread $6b0e (27406) -> **$70000** [obs bp: `003f 0006 00006b0e 00070000`], depack (`$3c0`, same LZ as `tools/pp_depack.py`) from $70020 to **$77f80**, `Setpalette($77f84)`.
6. `$300` Fopen NEBEXE.FIC, Fread $28af8 (166648) -> **$81000** (class 1: $4e000) [obs `003f 0006 00028af8 00081000`]. `$34c..$35a` = 128 Vsyncs (HD settle). `$35c` SR=$2700.
7. `$360`: copies 128 longs `S+$376..$575` to **$7fd00** and `jmp (a3)`: depack NEBEXE.FIC (from $81020) to **$33b00** (`$376`: `lea $33b00,a4`); then, if hooks on, copies `S+$3fa..` (101 longs) to **$200..$393** (the Gamex F1-F9/IKBD handler; F9 = scancode $c3 -> `$478` saves state, `jmp $ffd20`) and writes `4ef9 00000200` over the game's `cmp.b #$f6,d0 / bcc` at **$3850c**; then **`jmp $33b00`** (`S+$3b2`: `4ef9 00033b00`) = game entry.
8. `$57c` (called earlier at `$084`): sets **phystop $42e = $80000** on every machine and `$436 = $78000`; `$5de`: writes 'PPGX' + `$fff40` at $80000. The game believes it has 512 KB.
No D15R-style `$150` file hook and no later file loads: everything the game needs is in the one depacked image.

## 3. The game image
`$33b00` = `601a` header; `$33b1c` relocator: adds $33b1c to every longword in the reloc table (offset list at **$75728..$760e9**, first offset $50 = the `jmp` operand at **$33b6c**), then `jmp $4b08` which becomes **`jmp $38624`** = `lea $800,a7; jmp $3db62` (game proper). Text $33b1c..$3e382, data $3e382..$75728.
Verified [obs]: relocating the depacked file in Python and installing the `$3850c` hook reproduces RAM at `pc=$38624` **byte for byte** (`nepatch.py verify`: 271849 bytes compared, 0 differ; dump `work/dumps/boot/ram_stage2_1mb.bin`). At `pc=$33b00` only 5 bytes differ from the file (`$3850c..$38510`, the hook). => **the only PP patch in the game image is the keyboard hook**; the rest of PP's RAM changes are `$200..$393`, `$640`, `$42e/$436`, `$ffd20..`, `$fff40..`, `$80000`, TOS-state copy.
Game workspace: `$8700..$33a4f` cleared at init (`sub_03dfe0`: `lea $8700 / move.w #$acd3 / clr.l`), screens **$900** (32000) and **$78000** (double buffer; flip `sub_03868a` writes `$ff8201/03`), vectors: VBL `$70 = $382d8`, timer B `$120` chain, ACIA `$118 = $384fc`.

## 4. RAM map [obs: ram_entry/ram_settle/ram_stage2 dumps, 1 MB and 4 MB]
| range | 1 MB STE (TOS 1.62) | 4 MB Mega STE (TOS 2.06) |
|---|---|---|
| $000-$7ff | vectors, TOS vars, Gamex hook `$200..$393`, `$640` rts | same |
| $900-$86ff, $78000-$7ffff | the two screens | same |
| $8700-$33a4f | game workspace | same |
| $33b00-$760e9 | game (reloc table dead after relocation: $75728..$760e9) | same |
| $760e9-$76b0e | dead NEBULTIT raw tail (2492 non-zero bytes) | same |
| **$76b0e-$77ec5** | **zero** at stage 2 and in the tower (5 KB) | same |
| $80000 | 'PPGX',$fff40 | same |
| $80008-$ffdc8 | F9 swap area (game RAM $8..$7fdc8 copied here on F9). Free during play, **volatile on F9** | same |
| $81000-$a9af7 | raw NEBEXE.FIC residue (intact in the tower dump, 0 differing bytes) | same |
| $a9af8-$c0107 | zero (91 KB) | zero |
| $c0108-$dba48 | TOS-state copy (needed by F9; ~180 bytes of it change after entry: low-RAM sysvars such as $466 are refreshed [obs entry vs tower dump], so treat as live) | $102008-$122e18, then **free $123bd8-$3f7fc7** |
| $dba67-$f7fc7 | zero (116 KB) | |
| $f8000-$fffff | TOS screen (stale HW-detect text), F9 code $ffd20-$fffc1, state `$fff40..` | $3f8000.. TOS screen; F9 code still at **$ffd20** |
Top of memory: phystop forced to $80000 (`$42e`) on all machines; real 1 MB top $100000, real 4 MB top $400000 (TOS screen $3f8000).
**No 4 MB cache hazard**: START has no RAM cache; the only 4 MB-dependent items are class>=4 -> TOS-state copy at $102008, the TT/Falcon probe at $200000 (restores the longword), and TT/Falcon screen $380000. The Mega STE speed register `$ff8e21` is only touched in the M menu / probe.
Letterbox: **none**. Game, NEBULTIT and NEBULUS.PCH are all 320x200 low-res in the same window rectangle (shots `work/shots/01..02`, `99_tower.png`: picture area x 96..735, y 58..457 in the 832x588 shot = 640x400 = 2x).
F9 consequences for patching: the **only** memory F9 preserves and restores is game RAM $8..$7fdc8. A payload above $80000 is overwritten by F9 and not restored; a game-state file saved by GXUT270 contains the patches but not an upper-RAM payload. Resident code must therefore live in game RAM: the dead zone **$75728..$77ec5 (10,141 B; $76b10..$77ec0 verified zero is allowed as a blob area)**.

## 5. Delivery: `tools/nepatch.py` (built, proven)
Hunter's design with the carrier changed because this START has a different tail:
- `START.TOS` (shipped unpacked, 32975 B, same size) changes **4 bytes + a 102-byte stub** (+ the 4-byte `jmp` operand at run time): `S+$34c` `3e3c007f` -> `bsr.w stub`; stub at `S+$7c10` in the zero run `$7c06..$7dc5` (no relocation or pc-relative reference points there [checked]). Stub (position independent) = Fopen/Fread/Fclose `NEPATCH.BIN` with START's own GEMDOS context (at `$34c` SR is as at `$2aa`; the HD works), to **$B0000** (max 64 KB), and only if `'NEPA'` is there rewrites `S+$3b2` to `jmp $B0008`. Missing file = untouched START = unpatched game.
- core1 (`$B0008`, where `jmp $33b00` was): stores `core2-$33b1c` in the long at `$33b6c`, which the game's own relocator turns into its final `jmp` operand, then `jmp $33b00`.
- core2 (after relocation: **all site addresses are final RAM addresses**, same as dumps): pass 1 compares original bytes of EVERY site, pass 2 writes, marker `$B0020` = `'NEPO'` (`'NEPF'` otherwise), count word at `$B0024`, `jmp $38624`.
- Site table `$B0100..$B0FFF`, entries `{addr.l len.w orig new}`; original bytes are derived from the predicted stage-2 image (so they cannot be mistyped) and `verify` checks them against the real dump. Sites: inside the game image or the zero gap `$76b10..$77ec0`; no overlaps; even lengths.
- Patch files `patches/*.nep` (`patch NAME` / `default yes|no` / `site HEXADDR NEWHEX`). Commands: `verify`, `list`, `build [--only ..] [--corrupt] [--fill] [--out]`, `live` (prints Hatari `w` commands), `boot OUT [--machine --mem --tos --game]`, `taildump`.
- Proof [obs, cold boots, `patches/test.nep` = 2 poke sites in the dead reloc table: `$75728 -> 'NEPK'`, `$75730 -> 'NEPQ'`]:

| machine | build | marker | sites applied | `$75728..` | game reaches title (`$3d00f`='High') |
|---|---|---|---|---|---|
| STE 1 MB TOS 1.62 | good | `NEPO` | 2 | `4e45504b 019a0198 4e455051` | yes |
| STE 1 MB | first site's original byte flipped | `NEPF` | 0 | `00000050 019a0198 0101b610` (both sites untouched) | yes |
| Mega STE 4 MB TOS 2.06 | good | `NEPO` | 2 | same as above | yes |
| Mega STE 4 MB | corrupt | `NEPF` | 0 | untouched | yes |
(`work/dumps/boot/np_{1mb_ok,1mb_bad,4mb_ok,4mb_bad}`; 4 MB reaches the entry in ~52 s, 1 MB in 14 s.)
Not done: free-RAM poison test of $76b10..$77ec0 across a played tower (`build --fill` fills the $B0000 area only); trainers' sites file (lead); `live` snapshot image (only the `w` list).

## 6. Junk RAM (MiSTer does not clear RAM; NebJunkRam, details and evidence: `junkram.md`)
core2 no longer relies on zero RAM for STATE: nep directive `clear ADDR LEN` (RS+V `$77c80..$77dbf`, trainer flags `$76c00..07`, latch `$76d00..03`) is zeroed unconditionally in pass 2; the blob sites around them are split (`plan_install`).
Pass 1 now accepts a site holding its ORIGINAL or already its NEW bytes (relaunch on RAM that kept an earlier patched run); `$B0026` = how many were already new.  A blob zone with random junk is still `NEPF` (stock game) while `ZONE_STRICT = True`; see `junkram.md` section 5.
