# Moonshine Racers: patch delivery (hook instants, payload, 4 MB, floppy)

Companion to `patches/README.md` (the format and the address map). Every claim below cites a raw output kept in this repo
(`build/logs/*.log`, `work/notes/*.txt`, `work/dumps/*.bin`) or a disassembly line. Hatari 2.6.1.

## 1. The loader chain (what runs, in order)

Measured with a `--trace gemdos` cold boot of PP's unmodified conversion, breakpoint `pc = $b204e` (the hook instant).
Raw: `work/notes/entry_ste_1024.txt` (the study's boot trace: `Fopen`/`Fread` order) and `build/logs/*.log` (mine).

```
Pexec(0,"C:\RUNME.TOS")                       ; TOS runs PP's loader
Fread(64, 14000, 0x137dc)                     ; HAGA -> $137DC (= RUNME text $F176 + $4666)
Super; HAGA probes $ff8e21 (bus error on an STE, PP's guarded probe), GSAU.TOS, FILES\D15H5.FIC
Fread(64, 69888, 0x137dc)                     ; cover picture FMR273.HST
Dsetpath("FILES")
Fread(64, 17103,  0x81000)                    ; MSR_S1.FIC = PP's stage 1 (header "C3 .. MSR_S1")
Fread(64, 200000, 0x81000)                    ; MS1 chunk 1  (HAGA chunk cache $81000-$B1D40)
Fread(64, 200000, 0x81000) after Fseek(86507) ; MS1 chunk 2
...                                           ; stage 1 (at $78000) drives MS1/MS2 through PP's stub at $140/$c0/$1000
```
The stack-phase block is copied by RUNME to `a3 = $B1F44` (1 MB chunk mode) and its last instruction is
`0003b4: 4ef900078000  jmp $78000.l` (RAM `$b1fa6`; registers at that instant from `build/logs/` hook run: `A7=000B1F40`, `SR=2704`).

`$78000` is stage 1: an LZ-decoded block that loads the game image and ends in `jmp $1000.w` — as does PP's last patch block:
```
0003ba (stack block, entered via $c0 -> jmp $b1fe4; RAM = text + $B1F44 - $352):
  0003f2: 11fc0032024c        move.b  #$32,$24c.w
  0003f8: 21fcffffffff024e    move.l  #-$1,$24e.w
  000400: 21fc000bc8000256    move.l  #$bc800,$256.w        ; MS2 image size ($bc800 = 772,096)
  000416: 31fc60500146        move.w  #$6050,$146.w         ; PP's stub patches
  00041c: 31fc602c0186        move.w  #$602c,$186.w
  000422: 43f90000cac0        lea.l   $cac0.l,a1 ; 32fc4ef8 / 32bc0140 ; move.w #$4ef8,(a1)+ / #$140
  000430: 21fc600000b27c64    move.l  #$600000b2,$7c64.w
  000446: 123a0028            move.b  $470(pc),d1           ; machine flag: are $d1ac/$d1c4 patched?
  00044a: 6710                beq.b   $45c
  00044c: 33fc600c0000d1ac    move.w  #$600c,$d1ac.l
  000454: 33fc4e750000d1c4    move.w  #$4e75,$d1c4.l
  00045c: 4ef81000            jmp     $1000.w               <-- THE HOOK INSTANT (RAM $B204E)
```
`$1000` holds `60005f4e bra.w $6f50` (measured: `m $1000 8` -> `60 00 5f 4e`, both at `pc=$b1fe4` and at `pc=$6f64`), and `$6f50` is the
game's trap #2 hand-over (`rendering.md` section 7):
```
006f50: 21fc00006f5a0088     move.l  #$6f5a,$88.w
006f58: 4e42                 trap    #$2
006f5a: 46fc2700             move.w  #$2700,sr              <- trap handler
006f5e: 41f900070000         lea.l   $70000.l,a0            <- test_marker's site
006f64: 61006242             bsr.w   $d1a8                 ; first screen
```
So **one trampoline at `$b204e` covers the whole game**: everything the game runs is in RAM there. Registers at the hook instant
(1 MB STE, raw `build/logs/` hook run): `D0=$C8 D1=0 D2=$7026C D3=$8000 D4=7 D5=$3F D6=6 D7=$FFFFFFFF`,
`A0=$1000 A1=$CFFA A2=$164A A3=$1546 A4=0 A5=$78000 A6=$507AC A7=$7FFF0`, `USP=$B1F40 ISP=$7FFF0 SR=2304` (supervisor, IPL 3),
`m $1000 8` = `60 00 5f 4e 00 00 00 00`.

Two candidate hooks were rejected in favour of this one:
- `$6f5e` (the trap handler's first instruction, the study's suggestion): works, but the trampoline would run *after* PP's patcher
  has already returned, on a fresh stack — no advantage, and the `$b204e` site is the exact instruction PP's own tail ends with, so
  the trampoline's own end (`jmp $1000.w`) is byte-identical to the displaced instruction.
- the stack block's first `jmp $1000.w` (text `$3ee`, RAM `$B1FE0`): it runs **before** the second `$c0` block and before PP's last
  patch block, so the game is not loaded yet. Measured order of the hooks (one tracing breakpoint each, `build/logs` hook run):
  `$b1fa6` (stage phase, `m $1000 8` = all zeros: the stub is written later) -> `$b1fe0` (`m $1000 8` = `60 00 09 14`, `bra.w $1316`; the
  MS1 loads `Fread(64,200000,0x81000)` follow it) -> `$b1fe4` (the `$c0` entry, `m $1000 8` = `60 00 5f 4e`) -> **`$b204e`**
  (`bra.w $6f50`) -> `$6f64`.

## 2. Staging the payload (how the image gets to $B2700)

Addresses by RAM size (2 MB is not boot-tested here: the HAGA base comes from RUNME text `$124-$146`, `cmpi.b #$4,$46e` -> `$F8000`,
`cmpi #$8` -> `$1F8000`, else `$3F8000`):

| | 1 MB | 2 MB | 4 MB (`pp_bigram_cache`) | 4 MB without it |
|---|---|---|---|---|
| HAGA resident base | `$F8000` | `$1F8000` | `$3F8000` | `$3F8000` |
| HAGA chunk cache | `$81000-$B1D40` | `$81000-$B1D40` | `$81000-$B1D40` | `$81000-$C6F2B` (MS1 whole) |
| RUNME stack-phase copy | `$B1F44-$B26C3` | `$B1F44-$B26C3` | `$B1F44-$B26C3` | measured `USP=$C712A` (stack after the MS1 image) |
| payload `$B2700` | free | free | free | **overwritten by the MS1 load** |

- **Mechanism.** The payload image is appended to RUNME's data segment (= zero-cost: RUNME is loaded by TOS, the bytes are in RAM before
  RUNME runs). A copy routine appended at the old bss start (`text $4446`) copies it to `$B2700` and then executes the displaced
  `jmp $78000.l`; the stack-phase block's `jmp $78000.l` (text `$3b4`) becomes `jmp $4446.l` (relocated, a new reloc entry).
  It runs in supervisor mode on `A7=$B1F40` (`SR=2704`, IPL 7), before any game/stage memory is touched. Registers and SR are
  preserved (`movem.l d0/a0-a1` + `move.w sr`). The copy is `move.l (a0)+,(a1)+ / dbra`, `len/4-1` in `D0`.
- **Why not PP-style HAGA chunks?** The image is 22.8 KB at minimum (site table + trampoline + zero padding to `$B8000`); it lives in
  RUNME's own segment, so it needs no extra file, no GEMDOS call and no format of its own. The cost is RUNME's bss moving up (below).
- **bss relocation.** RUNME's text `$98`/`$b34`/`$40fa`/`$410c` hold `lea d(pc),aN` into the bss; a `lea d16(pc)` cannot span the
  payload, so each becomes `movea.l d(pc),aN` (4 B, same register, no flags) reading a relocated pointer slot; the whole text is scanned
  for other `d16(pc)` operands reaching `>= $4446` (`verify` prints `4 lea d(pc),aN, no others`). Header data length, every relocated
  long `>= $4446` and the reloc table are rewritten, and the table round-trip is asserted.
- **Measured RUNME.** Original: text `$4430` (17,456 B), data 22, bss 111,206, 24,602 B file. Marker build: data 22,852 (= 26 + 8 + 22,784
  + 22 + ...), file 40,467 B. TOS Pexec's it unchanged (`build/logs/marker_ste_1024.log` boots to the race).

## 3. The trampoline (applied at `$b204e`)

`patches/core.s`, disassembled from the built image (`python3 tools/m68dis.py` on `$B2700`-based image):
```
0b2708: 48e7fffe              movem.l  d0-d7/a0-a6,-(a7)
0b270c: 40e7                  move.w   sr,-(a7)
0b270e: 23fc4d535046000b2700  move.l   #'MSPF',$b2700.l      ; preset failure
0b2718: 41f9000b7000          lea.l    $b7000.l,a0           ; site table
0b271e: 2018                  move.l   (a0)+,d0             ; addr 0 = end
0b2720: 6716                  beq.b    $b2738               ; all verified -> apply
...                           cmpm.b (a1)+,(a3)+ / dbne    ; pass 1 compare, whole site
0b2738: ...                   move.b (a2)+,(a3)+ / dbra    ; pass 2 write
0b2756: 23fc4d53504f000b2700  move.l   #'MSPO',$b2700.l
0b2760: 610a                  bsr.b    $b276c               ; cflush (68020+ only)
0b2762: 46df                  move.w   (a7)+,sr
0b2764: 4cdf7fff              movem.l  (a7)+,d0-d7/a0-a6
0b2768: 4ef81000              jmp      $1000.w              ; the displaced instruction, byte-identical
```
- Verify-then-apply, all or nothing: one site's bytes wrong -> nothing is written, marker `MSPF`.
- `cflush` (0b276c-0b27b2, the same scale-factor test as `midwinter2/patches/cpulib.s cl_detect`): 68000 -> `rts`; 68020/030 -> `CACR |= CI|CD`;
  040/060 (`_CPU` cookie >= 40) -> `cpusha bc`. The trampoline was entered right after the payload was written as data, so on a cached
  030 the game would otherwise execute stale bytes on TT.
- The core is 172 bytes in a 248-byte area (`$B2708-$B27FF`).

## 4. Boots (raw outputs in `build/logs/`)

`python3 tools/msr_boot_test.py --machine M --mem K --game build/<b> --peek b2700 b2ff0` = cold boot, SPACE navigation to the first race,
`$1021` (mode byte) = 2 and `$100e` (frame counter) > 40, then `m $b2700`/`m $b2ff0`.

| machine / TOS / RAM | build | result | `$B2700` | `$B2FF0` | log |
|---|---|---|---|---|---|
| STE 1.62 1024 | marker | in_race True, vbl 5808 | `4d 53 50 4f` MSPO | `4d 53 54 4d` MSTM | `build/logs/marker_ste_1024.log` |
| STE 1.62 4096 | marker | in_race True, vbl 5807 | MSPO | MSTM | `build/logs/marker_ste_4096.log` |
| Mega STE 2.06 4096 | marker | in_race True, vbl 6047 | MSPO | MSTM | `build/logs/marker_megaste_4096.log` |
| ST 1.04 1024 | marker | in_race True, vbl 5807 | MSPO | MSTM | `build/logs/marker_st_1024_tos104.log` |
| TT 3.06 4096 | marker | in_race True, vbl 5882 | MSPO | MSTM | `build/logs/marker_tt_4096_tos306.log` |
| STE 1.62 1024 | zero (no patches) | in_race True, vbl 5805 | MSPO | zero (no marker patch) | `build/logs/zero_ste_1024.log` |
| STE 1.62 4096 | zero (no patches) | **in_race False** vbl 20225 | zero | zero | `build/logs/zero_ste_4096_boot.log` (section 5) |
| STE 1.62 1024 | blob36k (`IMG_MAX_LEN`) | in_race True, vbl 5807 | MSPO | MSTM + ramp at `$B3100` | `build/logs/blob36k_ste_1024.log` |
| Mega STE 2.06 1024 | blob36k (`IMG_MAX_LEN`) | in_race True, vbl 6046 | MSPO | MSTM + ramp at `$B3100` | `build/logs/blob36k_megaste_1024.log` |
| STE 1.62 1024 | `build/hd` (the default build) | in_race True, vbl 5808 | MSPO | (no marker patch) | `build/logs/hd_ste_1024.log` |

Raw excerpt (STE 1 MB):
```
t=  114s vbl=5708 $1021/$100e=(2, 62)
RESULT in_race = True vbl 5808
PEEK $b2700: > m $b2700 16
000B2700: 4d 53 50 4f 00 00 00 00 48 e7 ff fe 40 e7 23 fc  MSPO....Hτ¯³@τ#ⁿ
PEEK $b2ff0: > m $b2ff0 16
000B2FF0: 4d 53 54 4d 00 00 00 00 00 00 00 00 00 00 00 00  MSTM............
```
**A zero-patch build is not pristine.** `build --only` (no names) still holds the staging copy routine, the trampoline, the HAGA edits
(if named) and the enlarged RUNME; only the site table is empty (trampoline writes `MSPO` and returns). Pristine comparisons must use
`originals/MOONSHR` (which `msr.py` copies to a scratch drive; originals are never written).

## 5. 4 MB: the whole-image cache (and why `pp_bigram_cache` is required)

PP's HAGA init (HAGA+`$3218`-`$326e`) sets the disk-cache record from the RAM size: `cmp.b #$8,RAM/512K` (HAGA+`$321c`,
`bcs` = below 4 MB keeps the default 200,000-byte chunks). At >= 4 MB on a 68000 it switches to "whole image" mode — the record's
chunk becomes the image size and RUNME's stub Freads the whole MS1 (286,507 B = `$45F2B`, cf. `move.l #$45f2b,$590.l` at text `$28c`)
to `$81000`, i.e. `$81000-$C6F2B`. MS2 (772,096 B = `$BC800`, text `$400`) would cover `$C7900-$13D7FF` on its own load.
That is exactly what the study measured as the 4 MB free-RAM boundary (`rendering.md` section 3: zero runs start at `$C7900` at 4 MB,
`$B2700` at 1 MB) — **[INFERENCE, now proven for the payload's sake]**: with the payload at `$B2700` and no HAGA patch, the MS1 load
overwrites it.

`patches/pp_bigram_cache` (2 bytes at HAGA+`$3228`: `2412` -> `602a`, i.e. `move.l (a2),d2` -> `bra.b $3254`) makes 68000 machines take the
below-4-MB path (the default record) at any RAM size. 68020+ (TT/Falcon) are untouched: their cache is at `$300100`.

**Measured, this wave** (`build --only` = no patches, so no HAGA edit) at STE 1.62 4 MB, `build/logs/zero_ste_4096_hook.log` +
`build/logs/zero_ste_4096_boot.log`:
```
GEMDOS 0x3F Fread(64, 14000, 0x1910a) at PC 0xF1B0     ; RUNME at $14AA4 (4 MB TPA base)
GEMDOS 0x3F Fread(64, 17103, 0x81000) at PC 0xF432
GEMDOS 0x3F Fread(64, 286507, 0x81000) at PC 0x3F910E  ; WHOLE MS1: $81000-$C6F2B, over the payload
2. CPU breakpoint condition(s) matched 1 times.
        pc = $b2708                                   ; the trampoline address was still jumped to...
USP  000C712A ISP  0007FFF0 SR=2304                    ; ...and the stack block had moved up to $C712A (whole-image mode)
WARN : Address Error writing at address $ffffff6d, PC=$e09598     ; ...but the payload was MS1 data: garbage execution
RESULT in_race = False vbl 20225
PEEK $b2700: 000B2700: 00 00 00 00 00 00 00 00 ...     ; MSPO/MSPF gone, the payload area is zeroed MS1 data
```
Same build with `pp_bigram_cache` (`build/marker`, STE 4 MB): `RESULT in_race = True vbl 5807`, `$B2700 = MSPO`. That is the
proof that the HAGA edit is required, not cosmetic.

## 6. Image capacity (RUNME's own limit)

RUNME refuses to start when its bss start + `$8000` reaches `$38270` on a 1 MB machine:
```
00009c: d3fc00008000   adda.l  #$8000,a1
0000a2: b83c0002       cmp.b   #$2,d4              ; RAM code 2 = 1 MB
0000a8: b3fc00038270   cmpa.l  #$38270,a1
0000ae: 64000018       bcc.w   $c8                 ; -> "Too much low RAM occupied"
```
With `bss = text_end + data + N` and RUNME's text base `T`, the limit is `N < $38270 - $4446 - T`. Measured `T`:
`Fread(64,14000,0x137dc)` at 1 MB STE 1.62 -> `T = $137dc - $4666 = $F176` (limit ~ `$A5CA`); at 4 MB (RAM code 8, the `cmpa #$14e790`
path instead) `T = $1910a - $4666 = $14AA4`. The tool caps the image at `IMG_MAX_LEN = $F000` (61,440 B, `$B2700-$C16FF`), safely below
both and well above the 22.8 KB minimum. On TOS 2.06 the TPA base is higher (Midwinter 2 measured 61 KB of growth on a 1 MB Mega STE), so
`$F000` is the cap that covers 1 MB TOS 2.06 too. The test build `test_blob36k` fills the image to exactly `IMG_MAX_LEN` (61,440 B, RUNME
79,123 B with data 61,508) and boots to the race on a 1 MB STE and a 1 MB Mega STE (`build/logs/blob36k_ste_1024.log`,
`build/logs/blob36k_megaste_1024.log`): the copy routine's `dbra` count and RUNME's own limits are both proven at the cap. Note that the TPA
base moves with the file size (79 KB build: RUNME at `$1E1A4`, `Fread(64,14000,0x2280a)`; original: `$F176`), so the headroom must be
derived per build, never hardcoded — `verify` prints the unpacked size and the check is RUNME's own.

## 6a. `live` (A/B on a snapshot, no boot)

`msrpatch.py live --only NAMES --out build/live/patches` writes `<out>.img` (the payload image, load at `$B2700`) and `<out>.json`
(`img_base`, every site's orig/new bytes). `stharness.Hatari.capture_frames(live=...)` loads the image and writes the sites; nothing else is
needed because the trampoline/table are only used at boot.
`python3 tools/msr_live_test.py` demonstrates it on `work/snapshots/ste1m_race_start.sav` with `test_framecount` (a per-frame counter at
`$B2FF4`): raw output in `build/logs/live_ste1m_race_start.log`:
```
applied test_framecount at $d1ca: 2038100822381004 -> 4ef9000b29004e71
read back $d1ca: 0000D1CA: 4e f9 00 0b 29 00 4e 71     N..).Nq
counter $B2FF4: 10 -> 60 = 50 increments; the game's own frame counter $100e: 75 -> 125 = 50 frames (True)
```
i.e. the patched code runs in the restored snapshot and increments exactly once per game frame (its own frame counter `$100e` agrees,
rendering.md section 4.1 `addq.w #1,$100e`). No boot, no cold start. This is the A/B lever for the next wave (patch a snapshot, compare frames).

## 7. Floppy

**Superseded: there IS a floppy release path.** The earlier version of this section ("there is no floppy release", HD files only, "a new
two-disk/HD-swap loader would be needed") was written before the user added the original STX disks (`originals/moonshine_racers_millennium.zip`).
With them the MW2 way applies (original disk images + payload on blank sectors + hook in the original loader). Everything is in
`work/notes/floppy.md`; in short:

- The STX images are standard 800 KB 10-sector disks (plain `.ST` conversion lossless, `tools/stx2st.py`). Disk A is bootable (custom boot
  sector, `60 04` + "MOON", sum `$1234`), loads the whole game into low RAM in two loader phases, plays the intro, asks the manual-lookup
  question and starts the game at the **same addresses as PP's HD release** (`$1000 = bra.w $6f50`, code at `$6f50/$796a/$d1ca`), so the RAM
  sites and the trampoline of this document apply unchanged. Disk B is the data disk (`MS2`'s bytes); the game itself asks for it ("Insert
  Disk 2 and press a key.", `$76f4`) and reads every sector through drive A.
- **Payload**: `$B2700` is reached through the same marker/trampoline mechanism, delivered differently: a stage-0 loader placed in the boot
  sector's free area (the original header untouched; first original instruction displaced) reads the image from blank sectors of disk A
  (tracks 0 s2-10 and 50-61 side 0) with XBIOS `Floprd` before the original boot code runs. The trampoline (`patches/core_floppy.s`) is entered
  from `fl_hook`: disk A `$C350` (= RAM `$6f50`, the game's entry stub `move.l #$6f5a,$88.w / trap #2`) becomes `jmp $B2708.l`, and the trampoline
  replays the two displaced instructions at its end.
- **Protection**: the randomised manual question is skipped by the 4-byte `fl_deprot` disk patch (`bra.w $7d1a` over the first two instructions
  of the question routine at RAM `$7bd0` = disk A `$E3D0`).
- **Not the HD path**: no RUNME, no HAGA, no MS1/MS2 files; `pp_bigram_cache` and `RUNME` edits do not apply. The floppy game does not use PP's
  chunk cache: whether `$B2700-$E8400` stays free at run time was checked by the marker and the `mt_*` clock after a 30 s race (floppy.md section 8).

The stage-0 loader is position independent: **TOS runs the boot sector at its disk buffer (`$185C` on STE TOS 1.62), not at `$7800`**.

## 8. Traps found
- **The 4 MB whole-image cache** (section 5): the payload must not sit where MS1/MS2 land; `pp_bigram_cache` is the fix (needs every
  68000 build with 4 MB or more, so it is `default: yes`, and it is listed as a file patch, not a RAM patch).
- **`$b1fe0` is not a one-shot hook** (section 1): the stage-1 block's own `jmp $1000.w` runs twice.
- **`$d1ac`/`$d1c4` PP patches are machine-dependent** (`move.b $470(pc),d1` at text `$446`): the tool refuses sites overlapping PP's RAM
  patches, because their bytes differ on machines where `$470` is set.
- **The game overwrites `$4ff8-$5ff9`** (span buffer) and self-modifies sprite kernels (`$12c96`, `$133c4`... in the study's dumps): a
  site inside those regions would fail the verify cross-check (entry vs race dump) — no shipped site is near them.
- **TT/Falcon execute code with caches on**: the payload is written as data, so the trampoline flushes (section 3).
- **PP's low-RAM stub block (`$140-$41B`)** is machine dependent and belongs to his file service; the tool forbids sites there.
- **`/tmp` snapshot name**: the harness's default `--memstate /tmp/hatari.sav` is shared; cold-boot runs here never save a state.
