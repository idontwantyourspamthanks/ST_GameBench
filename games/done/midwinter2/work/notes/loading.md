# Midwinter 2 (PP/HAGA HD build) — loading pipeline, file format, patch hook points

Read-only analysis, 2026-11-07. Tools: `tools/m68dis.py`, `tools/mw2harness.py` (Hatari 2.6.1,
STE TOS 1.62), Python. Dumps produced by this investigation live in `/tmp/mwload/`
(`ingame_coldboot.bin`, `corridor.bin`, `ram1mb_boot.bin`, `ram1mb_ingame.bin`,
`runF_ingame.bin`, `runF_after_ss.bin`, logs `bootlog2.txt`, `runC_log.txt`, `gemdos_1mb.txt`);
key raw output is embedded below. `work/dumps/ram_ingame_lobos.bin` = 2 MB in-game dump (pre-existing).

**TL;DR**

| Question | Answer |
|---|---|
| Image files | `FILES/FFA..FFC` = raw 720 KB floppy sector images (9 sec/track, 2 sides, 80 tracks), **track-interleaved**: offset(t,s,n) = t·9216 + s·4608 + (n−1)·512 |
| File format | 1536-byte directory: 8-byte magic + 191 × 8-byte entries `[u16 xor-checksum][u16 offset-in-first-track][u8 start-track-side][u24 length]`; files are **contiguous byte streams over consecutive 4608-byte track-sides** |
| Compressed? | **No.** 391 of 392 files verify byte-exact against their stored checksum; several match RAM byte-for-byte (§2). The only LZ code is RUNME's own self-depacker ($480) |
| Load path | game driver $27xxx → PP stubs ($200/$34A/$380) → 200000-byte chunk cache at $81000 → memcpy to game buffer → `sub_27A00` copy to final dest |
| Overlays | Resident code = FFA file9 → $3104–$3DB10 + file8 → $806–$3104 (boot, once). Later loads are data/screens/mission sets; **entering gameplay from `lobos_brief` loads nothing** (0 breakpoint hits over 2 mission starts) |
| Best hook | `sub_278A6` return **$2794A** (`4E75 rts`) — fires per file load, after checksum, before relocation/execution; splice via `jsr $2783E` at **$27D58** (6 clean bytes). Boot-code patches: extend PP's patcher tail `jmp $3104.w` at **$59C** |
| Free RAM (1 MB, primary) | **$B2852–$E83E5 ≈ 215 KB free during gameplay**; safe allocation $B3000–$E8000 (212 KB). 2 MB: $B3000–$100000 (308 KB) free |
| 512 KB | Not possible: README says "1MB RAM min"; PP's chunk cache alone spans $81000–$B1D40 |

---

## 1. How code gets from the image files into RAM

### 1.1 Boot chain (evidence: `work/prof/gemdos_coldboot_trace.txt` + Hatari runs below)

1. `RUNME.TOS` (4122 B, LZ self-extracting; depacker routine stays resident at **$480–$4BA**,
   format: control byte <0 = match with 1- or 2-byte distance, =0 = end, else literal run)
   is Pexec'd by GEMDOS and runs from a low base (trace PCs `$F182`, `$F1B0`, `$FC46`, `$F40A`).
2. It reads `HAGA` (14000 B → $138CC; hardware detect/clock menu) and title picture
   `FFF273.HST` (69888 B → $138CC), probes `GSAU.TOS`, `FILES\D15H5.FIC`, `C:\GAMEX\D15H5.FIC`
   (all "not found" is normal), then `Dsetpath("FILES")`.
3. `Fopen("FFA")`, `Fseek(512)`, `Fread(4096 → $81000)` = original boot stub
   (FFA track 0 side 0 sectors 1–8). Raw bytes at FFA $200: `46FC 2700` (move #$2700,sr),
   writes shifter $FF860D/$FF860B, builds a vector table at $4E9AC.., `23FC 0000 3104 0004E9AC`
   (move.l #$3104,$4E9AC) and ends `4EF8 3104` (jmp $3104) at FFA offset $2F8.
4. RUNME relocates its **resident service** to the top of RAM: text base = **phystop − $8AAC**
   (2 MB: **$1F7554**; 1 MB: **$F7554** — identical offset, verified by signature search:
   the first 32 bytes of `RUNME_unpacked.tos` text (file offset $1C) occur at $1F7554 in
   `ram_ingame_lobos.bin`; trace PCs `$1F9022` (2 MB) vs `$F9022` (1 MB run, §5)).
5. The boot stub (executing with its own stack in $78xxx) loads **FFA file8 → $806** (10494 B)
   and **FFA file9 → $3104** (240140 B, ends exactly at $3DB10) through the PP service
   (trace: FFA chunk reads at seeks 9216 / 211968 / 414720 / 537280 — 537280 = 737280−200000,
   the end-of-file clamp), verifies file9's checksum, and control reaches **PP's patcher at
   $4BC** (breakpoint evidence, §6), which finishes with `jmp $3104` = game entry.

Breakpoint hit at $4BC during cold boot (Hatari `b pc = $4bc :trace :once :file`, run F):

```
D0 0000DABA   D1 0000DABA   D2 00004E75   D3 00000000
A0 0004EF98   A1 0003DB10   A2 00072EBE   A6 0004E9D8   A7 000783E8
SR=2304 (supervisor)   000004bc 4dfa fd42  lea.l ($200,pc),a6
```
D0=D1=$DABA = FFA file9's directory checksum; A1=$3DB10 = end of file9 → the patcher runs
immediately after file9 is loaded and checksum-verified. Stack top [$783E8] holds no return
address (`3E C6 3E C6`) → entered by JMP (tail call). The caller (boot stub copy) is erased
before in-game time: $81000 is reused by the chunk cache and the $2FF00-area copy is overwritten
by file8 — [INFERENCE] PP redirected the stub's final `jmp $3104` to `jmp $4BC`.

### 1.2 Runtime read path (all disk I/O after boot)

The game's own disk driver (resident in file9 code, ~$26F48–$27E46, param block **a6 = $770E**)
had its FDC entry points replaced by PP (patch bytes listed in §6) with jumps to low-RAM stubs:

* **Side-A sector read**: `sub_27AC4` first instr → `jmp $200.w` (`4EF8 0200`; original bytes in
  FFA file9 at offset $249C0: `2E2E 010A` = `move.l $10A(a6),d7`).
* **Side-B sector write**: `sub_27B12` → `jmp $34A.w`; **full-track write**: `sub_27980` →
  `jmp $380.w` (both build mode `'Wr'` → Fwrite/Fcreate; used for the FFD campaign disk).
* FDC helpers neutered to `rts`: $27CFC (seek), $27A38, $27A4E, $27CAA, $27A86, $27C4A.

**Sector → image-offset addressing** — stub helper at $268 (disassembly of RAM dump):

```
000268: movea.l $10a(a6), a4      ; dest buffer (game's, e.g. $78000 window or $E576 dir)
00026c: move.l  #$200, d3         ; 512 bytes
000272: move.w  $f0(a6), d4       ; track = trackside % 80
000276: mulu.w  #$2400, d4        ; track * 9216
00027a: cmpi.w  #$2, $ee(a6)      ; $ee = (trackside / 80) | 2  → side flag
000282: addi.l  #$1200, d4        ; side 1: + 4608
00028a: move.w  $f4(a6), d2       ; sector 1..9
000290: lsl.w #$4,d2 / lsl.l #$5,d2 ; (sector-1) * 512
000294: add.l d2, d4              ; d4 = byte offset in image file
```

i.e. **offset = track·9216 + side·4608 + (sector−1)·512**, with linear track-side index
`$E570: side = idx/80, track = idx%80` (set from the directory entry, `divu #$50` at $2773C).
Matches the observed GEMDOS seeks exactly (e.g. 9216 = track 1 side 0 sector 1 = FFA directory;
0x6AE00 = track 47 side 1 sector 1).

**The $200 stub (read path)**, $200–$310:

```
000204: check drive letter: d2 = [$93D1]/24 + 'A' → filename 3rd char at $3D0 ("FFA/FFB/FFC");
        drive change → invalidate cache [$3D2] = -1
00022e: bsr $268                       ; a4=dest, d3=512, d4=image offset
000232: add.l d4, d3                   ; d3 = end offset
000234: a2 = $3D2 cache descriptor {start, end, filesize=$B4000, buf=[$3E0]=$81000, chunk=[$3E4]=$30D40}
00023a: cache hit ([start,end) covers [d4,d3)) →
000258:   a1 = [$3E0] + (d4 − start);  memcpy a1→a4 ($25e: move.b (a1)+,(a4)+ loop)
000298: cache miss → request block $466 {buf=[$3E0], seek, len=[$3E4]=200000, mode=0, name}
        (whole-file mode if [$3E8]≠0: seek=0, len=filesize), clamped to filesize−200000 at EOF
0002c8: a1 = [$462] = $1F8000 (2MB) / $F8000 (1MB);  jsr (a1,[$1F8008]=$0FC4)  → PP service $1F8FC4
```

**PP service $1F8FC4** (resident loader; disassembly from RAM dump): copies the 28-byte request
block to $1FB360 {buf, seek, len, mode, name}, disables interrupts, switches to its own stack
($1FB614/$1FB7A4), then `Fopen` ($3D) / `Fcreate` ($3C if mode `'cR'` $6352) at $1F9020,
`Fseek($4(a6))` at $1F9044, `Fread/Fwrite` ($3F/$40, `'Wr'` $5772 selects write) at $1F90AA/
$1F910C, `Fclose` at $1F911E, restores caller registers via $1FB37C and `rts` at **$1F9164**.
Chunk reads observed: `Fread(64, 200000, 0x81000)` — buffer never translated on the chunk path.
(The service also contains an unused-on-STE simple path at $1F90E8 translating buf<$180000 by
+$100000 — [INFERENCE] for other machines/modes; all observed 1 MB/2 MB STE reads took the
chunk-cache path with buf=$81000 verbatim.)

**Copy chain after Fread into $81000** (the question "which routine copies/decodes"):

```
$81000 chunk cache ──$200 stub memcpy ($25E: move.b (a1)+,(a4)+)──► game track window $10A(a6)
   (window = $78000..$79200 per track-side, or $E576/$E776/$E976 for directories, or the
    $1200-byte full-track buffer for writes)
$78000 window ──sub_27A00 ($27A00: move.b (a0)+,(a1)+, stops at $79200)──► final dest [$6918]
```

**No decode/decompression step exists** — both stages are plain byte copies (§2 proves the data
is stored raw). Directory load: `sub_277C6` reads sectors 1–3 of track-side [$E544] into
$E576/$E776/$E976 (FFA dir at track-side 1 = offset 9216; FFB/FFC dirs at track-side 0 = offset 0).

### 1.3 File-level read routine (the game's "fopen/fread")

`sub_278A6` (called via `sub_2783E` = dir-load + up to 3 retries + error prompt):

```
0278aa: a0 = $E57E + [$7824]*8          ; directory entry of file number [$7824]=[$770E+$116]
0278be: d1 = (a0)                       ; stored checksum
0278c0: d2 = $2(a0)                     ; byte offset in first track-side
0278c4: d0 = $4(a0).b → $E570           ; start track-side
0278c8: d3 = $4(a0).l & $FFFFFF → $6914 ; length
0278de: bsr sub_2772C                   ; derive $EE/$F0 from $E570 ("seek")
0278e2: a0 = $78000 + d2 ; a1 = [$6918] ; dest
0278f2..02792e: loop { sub_2794C reads 9 sectors (side A) into window $78000 ;
                       sub_27A00 copies window→dest ; sub_279B4: $E570++ ("next track-side") }
027936: bsr sub_27A14                   ; 16-bit XOR checksum over [$6914] bytes at [$6918]
02793c: cmp d1 → mismatch: $9E30 = $FFFF (caller retries / "insert disk" via $2779E/$28B9E)
02794a: rts                             ; ← per-file completion point (§4)
```

`sub_2794C` = 9 × `sub_27AC4` (sectors 1..9 via the $200 stub); `sub_27980`/`sub_27B12` are the
**write** counterparts (jmp $380/$34A, mode 'Wr') used by the FFD file-write routine `sub_27634`.

## 2. File format; are files compressed? (No — proof inside)

**Image layout**: 737280 B = 1440 × 512 sectors. Track-interleaved: `[t0s0][t0s1][t1s0]...`,
`offset(track-side idx) = (idx%80)·9216 + (idx//80)·4608` — exactly the addressing the $268 stub
computes (§1.2) and PP's README parameters ("9 sectors/track, 2 sides, 80 tracks", `README.TXT`;
LOG.TXT: PP built these with his "STX to ST converter" from protected-disk STX images).

**Directory** (1536 B at image offset 0 for FFB/FFC, offset 9216 for FFA):
`[8-byte volume id: 'grafix00' / 'mission0']` + **191 entries × 8 bytes**:

| Field | Size | Meaning |
|---|---|---|
| +0 | u16 | 16-bit XOR checksum over all big-endian words of the file (computed by `sub_27A14`, verified at $2793C) |
| +2 | u16 | byte offset of file start **within its first track-side** (0..4607; =0x600 for file 0 → right after the 1536-B directory) |
| +4 | u8 | start track-side index (side = /80, track = %80) |
| +5 | u24 | file length in bytes |

A file is one contiguous byte stream: `length` bytes starting at `f_off(side)+off`, continuing
through track-sides side+1, side+2, … (4608 B each). Fields decoded from `sub_278A6`/`sub_27634`
usage above; FFA holds only 10 files (rest of directory zero), FFB/FFC 191 each.

**Compression: none.** Every stored checksum matches the raw extracted bytes (391/392; the one
exception, FFA file1 = the boot stub itself, mismatches because PP modified the stub in the
shipped image — "manual deprot" per LOG.TXT), and whole files match RAM byte-for-byte:

* FFB file 92 (5306 B) == `ram_ingame_lobos.bin[$4FA16:$5168C]` — **exact True**
* FFB file 68 (2072 B) == RAM $8D9FC — exact True; FFB file 70 (1424 B) == RAM $8FFDC — exact True

(The only compressor in the whole system is RUNME's self-depacker at $480, used once on RUNME.TOS.)

Verification/extraction script (run from repo root; reproduces every claim above):

```python
import struct
def f_off(s): return (s % 80) * 9216 + (s // 80) * 4608   # track-side -> image byte offset
def extract(d, off, side, ln):                            # contiguous stream over track-sides
    out = bytearray(); s = side; pos = off
    while ln > 0:
        base = f_off(s); n = min(ln, 4608 - pos)
        out += d[base+pos : base+pos+n]; ln -= n; s += 1; pos = 0
    return bytes(out)
def cksum(b):                                             # game's sub_27A14: XOR of BE words
    d1 = i = 0
    while i < len(b):
        w = b[i]; i += 1
        if i < len(b): w = (w << 8) | b[i]; i += 1
        d1 ^= w
    return d1
def dirents(d, base):                                     # base: 0 (FFB/FFC) or 9216 (FFA)
    for i in range(191):
        p = base + 8 + i*8
        w0, w2 = struct.unpack_from('>HH', d, p)
        ln = int.from_bytes(d[p+5:p+8], 'big')
        if ln: yield i, w0, w2, d[p+4], ln
ram = open('work/dumps/ram_ingame_lobos.bin','rb').read()
for img, base in (('FILES/FFA',9216), ('FILES/FFB',0), ('FILES/FFC',0)):
    d = open(img,'rb').read()
    bad = [(i,w0) for i,w0,w2,s,ln in dirents(d,base) if cksum(extract(d,w2,s,ln)) != w0]
    print(img, 'checksum mismatches:', bad)               # FFA: [(1, 0x1256)] only; FFB/FFC: []
ffb = open('FILES/FFB','rb').read()
for fn, addr in ((92, 0x4FA16), (68, 0x8D9FC), (70, 0x8FFDC)):
    i, w0, w2, s, ln = [e for e in dirents(ffb,0) if e[0]==fn][0]
    data = extract(ffb, w2, s, ln)
    print(f'FFB file{fn}: RAM ${addr:X} byte-exact:', ram[addr:addr+ln] == data)   # all True
```

Output observed: `FILES/FFA checksum mismatches: [(1, 4694)]`, `FILES/FFB ... []`,
`FILES/FFC ... []`; `FFB file92: RAM $4FA16 byte-exact: True` (likewise 68, 70).

## 3. What is loaded when (overlay map)

Dynamic method: breakpoints `b pc = $278de :trace :file hit.txt` (file-load setup: logs
[$6918]=dest, [$7824]=file no, [$E570]=start track-side, $3D0=current image letter),
`b pc = $2794a :trace :file rts.txt` (load complete), `b pc = $1f8fc4 :trace :file svc.txt`
(every PP service call: request block at $466). Runs: A = `lobos_brief.sav` → gameplay,
B/C = cold boots (C watched the full intro), logs in `/tmp/mwload/bootlog2.txt`, `runC_log.txt`.

**Boot, always** (runs B & C, identical):

| RAM range | Source | Notes |
|---|---|---|
| $806–$3104 | FFA file 8 (10494 B) | low resident game code/data; ends exactly where file9 starts |
| $3104–$3DB10 | FFA file 9 (240140 B, ck $DABA) | **all resident code** (profile hot funcs $1D768/$3C5E2/… are inside); covers the whole $4000–$3DB10 part of the asked range $4000–$40000 |
| $E576–$EB76 | FFA dir sectors 1–3 | later re-read per disk switch ($E576 = 'grafix00' copy found in RAM dump) |
| $62000 | FFA file 6 (4704 B, ck $1AF) | screen buffer 2 (title/intro pictures) |
| $40040–$49534 | FFA file 7 (38036 B, ck $A32) | title/menu graphics block |
| $62000 | FFB files 111, 110, 45, 41 (ck $2784/$17F8/$62C5/$AD6B) | intro/menu screens (run C, in intro+menu order) |

**Entering gameplay**: from `lobos_brief.sav` (run A: thumbs-up click flow, incl. one full
MISSION TERMINATED cycle) — **zero hits on all three breakpoints**. Cold-boot run C, PARATROOPER
DROP mission start: only FFB file 43 (13024 B) → **$72000** and FFB file 44 (10386 B) → **$47D40**
(script at $2848C: `dest=$47D40, file 44`). Walking around in-game: zero further hits.
**Conclusion: no per-frame streaming; everything needed is resident after boot/menu.**

**Script engine** — the remaining loads are data-driven. Interpreter `sub_27D38` (script = inline
data after `bsr $27D38`: `[dest:u32]` then per file `[fileno:u16][opcode:u16][operands]`,
terminated by fileno $FFFF; opcodes 0/1 = fixup pointer tables via $26F48/$26F74 relative to
[$6918], 2/3/5 = record destinations, 4 = relocate list). 35 call sites decoded statically
(all `bsr $27d38`, scripts inline; file numbers refer to the disk mounted at that moment):

```
$27F1E: dest=$4D8A8  files 90,91,92,93,94        (engine/vehicle overlay set)
$27F62: dest=$4BFA8  files 13,14,15 (tail of this script overlaps $27F80's data)
$27FA8: dest=$40040  file 42        $280DC: dest=$40040 file 97
$28182: dest=$40040  files 16,17,21,22           $282FE: dest=$40040 files 16,18,22,52
$283A6: dest=$40040  file 46        $285F8: dest=$40040 files 2,3,0,4..9
$28034: dest=$68000  files 16,17,18,19,22,23,24,35,36   $28094: dest=$68000 file 17
$28074/$2812C/$281B8/$28206/$28236/$28266/$282CC/$2837A/$28406/$28430/$284B0/$284E0/$28536/$2859E:
        dest=$4E6B8  vehicle/mission object sets (files 10..52,103,116,117)
$27F80: $5C948←f11  $2811A: $51650←f11  $28294: $5AE6C←f11  $28446: $500F6←f11
$281E0: $5BF8C←f10  $28320: $45534←f10  $282A6: $5CD6C←f12  $285B0: $505B8←f12
$2815C: $4FB82←f35,36   $28348: $494D4←f22   $2848C: $47D40←f44 (fired in run C ✓)
sub_27EE6: $555BE←file $58(88)   sub_27E4A/E94: $18D96←file 0/1
```

Cross-check vs `ram_ingame_lobos.bin` (64-byte block search, delta = RAM−file offset):
FFB f90→$4D8A8, f91→$4E3E2, f92→$4FA16, f93→$50ED2, f94→$52244, f96→$49C80, f88→$555BE (=FFA f7
duplicate), f1→$18D96, sprite/object files f52–f86→$81972…$A3000, f87→$54DBE; FFC f1→$B3FA.
Those sessions had loaded the $4D8A8 engine set + sprite files; runs B/C (intro watched or
skipped, campaign + mission-disc mission) did **not** load files 90–94 — i.e. that set is
mission/vehicle-specific, and the resident file9 engine renders without it. Sprite-range loads
($81972+) come from the direct `jsr $2783E` call sites ($286FC, $28710, $287E0, $28A04–$28A28,
$28D4E–$28DC8, $28E32, $304D2) with variable destinations, not from the fixed scripts.

**Answer for $4000–$40000**: populated once, at boot, by FFA file9 ($3104–$3DB10, raw, single
contiguous load); nothing observed ever reloads into $4000–$40000 afterwards. FFC ('mission0')
files appear only in mission-disc flows that read FFC (FFC f1 seen at $B3FA in the old dump);
no FFC access occurred in runs A–C.

## 4. Best hook point for a patcher

**Semantic point: `rts` of `sub_278A6` at $2794A, bytes `4E 75`.**
Fires once per game-file load, *after* the last byte is copied to the destination and *after*
the directory checksum has been verified (patching earlier would trip the $9E30=$FFFF retry /
"insert disk" loop), *before* the script engine's pointer-relocation opcodes and before any
loaded code can execute. Covers every file: code overlays, sprites, screens.

Measured state at the hook (run B/C log, first hit = FFA file 6):

```
D0 000001AF   D1 000001AF (checksum)   D2 0000AF7F   A0 000789FA   A1 00063260 (dest end)
A6 0000770E (param blk)   A7 00007FDE (ISP)   SR=2304 → supervisor, interrupt mask 3
[$6918]=00062000 dest   [$6914]=00001260 len   [$7824]=0006 file no   [$93D1]/$3D0: image letter
```

**Splice**: the `rts` cannot grow in place (next byte $2794C = `sub_2794C`'s `movem.l`).
Use the script engine's call site **$27D58: `4EB9 0002 783E` (`jsr $2783E.l`, 6 bytes)** →
replace with `jsr HOOK` (HOOK in free RAM: `jsr $2783E; <apply patches keyed on [$7824]/[$6918]>; rts`).
This covers all 35 overlay/code scripts. The 16 other `jsr $2783E` sites (same 6-byte pattern)
can be spliced identically if data loads must be hooked too.

**Residency** (Q4 check): bytes $278A6–$2794C are **identical (0 differing bytes)** in
`ram_ingame_lobos.bin` and a fresh dump at `corridor_agent.sav` (`/tmp/mwload/corridor.bin`);
$2794A = `4E75` in those two plus the run-B cold-boot dump and the 1 MB in-game dump;
$27D58 = `4EB9 0002 783E` in all four. No observed load targets that region: all overlay
destinations are ≥$40040, plus $18D96–$210B2 (FFB f0/f1) and $B3FA–$D7B4 (FFC f1) — the nearest
ends 4 KB below $278A6. [INFERENCE] a future/other mission set could in principle load over
$27xxx; the patch tool should verify expected bytes at install time (it must anyway).

**Boot-time patches** (files 8/9 are loaded before $278A6 exists in RAM): extend **PP's own
patcher** instead — its tail `jmp $3104.w` at **$59C** (`4EF8 3104`) can become `jmp $5E4.w`
(`4EF8 05E4`), with a trampoline at $5E4–$805 (verified **all-zero** in all four dumps, i.e.
unused PP slack) that applies boot patches then `jmp $3104`. Alternatively append to PP's
patch list by inserting code the same way — PP's patcher is the mechanism his own fixes use (§6).

**Machine-independence**: $2794A/$27D58/$59C are *game/PP-low-RAM* addresses — identical on
1 MB and 2 MB (verified byte-identical in the 1 MB dump). Only PP's resident service address
differs ($1F8FC4 vs $F8FC4, base = phystop−$8AAC), so avoid service-level hooks; if ever needed,
the dispatch is indirect anyway: stubs `jsr ([$1F8000]+[$1F8008])`, and [$1F8000] itself is
$1F8000/$F8000 per machine. The service's own `rts` ($1F9164/$F9164) fires per chunk operation,
*before* the game has copied data out of $81000 — too early to patch final destinations.

## 5. Free RAM for added code (target machine: **1 MB STE** — primary result)

Method per assignment: stage dumps + zero checks (no fill-pattern test).

**1 MB layout during gameplay** (dump `/tmp/mwload/ram1mb_ingame.bin`, taken in-game — guard
corridor mission, resumed automatically at boot — on `Hatari(snapshot=None, memsize_kb=1024)`):

| Range | Contents |
|---|---|
| $400–$B2851 | game: code $806–$3DB10, vars, screens $40040–$7FFFF, chunk cache **$81000–$B1D40** ($81000+200000), PP data $B1F44–$B2851 (incl. 'RGRG…' table at $B2840; A3=$B1F44 seen in service registers) |
| **$B2852–$E83E5** | **ZERO — free, 220,564 B (~215 KB)** |
| $E83E6–$FB404 | HAGA/PP resident block: loader text base **$F7554** (= phystop−$8AAC; service at **$F8FC4**, found by signature `43FA 239A`; GEMDOS trace PCs `$F9022/$F9046/$F910E/$F9120` — exactly the 2 MB PCs minus $100000), HAGA data/strings ('Selection:' at **$F332A**), stacks |

* 1 MB boot stage (title screen, `/tmp/mwload/ram1mb_boot.bin`): $B3000–$F0000 **all zero**.
* 1 MB gameplay stage: first non-zero above $B2852 is $E83E6; $B3000–$E8000 all zero.
* HAGA savestate (numpad `*`, keypress 94, 2 MB run F): changed 1030 bytes, **all inside the
  loader/HAGA block ≥$1D8B9F**; below $100000 nothing changed → savestates do not touch the
  candidate region (they stream to disk).
* Game itself is RAM-size agnostic: every game address observed is <$B2852 on both machines;
  the only difference 1 MB↔2 MB is the loader/HAGA block position (96 tiny text diffs between
  the two loader copies = relocated absolute address bytes only, e.g. `01`↔`00` high bytes).

**2 MB (secondary)**: $B3000–$100000 = 308 KB **all zero** in three independent in-game dumps
(lobos, corridor, run-B cold boot); highest non-zero below 1 MB = $B2851 in both lobos and
corridor. Loader/HAGA block sits at $1D0000–$1FC000 instead.

**Recommendation**: place patcher code+tables at **$B3000** (8–16 KB fits ~13,000×over).
It clears the cache tail ($B1D40), the PP table at $B1F44–$B2851, and the HAGA block
($E83E6 on 1 MB / $1D0000+ on 2 MB) with margin on both machines. The patch tool should still
assert the target range is zero before installing. 512 KB machines are out of scope and not
possible without reworking PP's loader (chunk cache $81000–$B1D40 exceeds 512 KB; `README.TXT`:
"1MB RAM min").

**Caveat: >= 4 MB (68000 machines).** The chunk-cache description above holds for 1 MB and 2 MB. With ST-RAM >= 4 MB PP's HAGA init
(HAGA+$3218..$3252) switches the stub to *whole-image* mode: `Fread(64, 737280, $81000)`, i.e. `$81000-$135000`, one image at a time. That
overwrites `$B2FF8-$B4EFF` (our payload) and hung the patched game at the title. `patches/pp_bigram_cache.s` keeps the chunked mode on 68000
machines. Evidence, disassembly and tests: `work/notes/bigram.md`. The "free RAM `$B2852-$E83E5`" statement is therefore only true in chunk mode.

## 6. How RUNME.TOS starts the game; where PP applies his patches

Boot flow = §1.1. PP's patches are applied **in RAM** by the routine at **$4BC–$59C** (installed
with the other low-RAM stubs during RUNME init; executed once at boot right after file9's
checksum, then `jmp $3104`). Image files are shipped unmodified except FFA's boot stub (file1
checksum mismatch, §2). Complete patch list, disassembled from RAM (all verified present in
`ram_ingame_lobos.bin`, and the pre-patch originals present in FFA file9):

```
0004c0: $27AC4 ← 4EF8 0200   jmp $200   (side-A sector READ; orig 2E2E 010A)
0004d2: $26A stub operand fixups: +2←$10A, +C←$F0, +24←$F4, +16←$EE
0004ea: $1F5EA ← 4EB9 0000 0314  jsr $314  ($314: nops the $202 stub call, sets [$770E+$11E]=1)
0004fc: $27CFC ← 4E75 rts    (FDC head seek killed; also $27A38, $27A4E, $27CAA, $27A86, $27C4A)
000530: $27B12 ← 4EF8 034A   jmp $34A   (sector WRITE, mode 'Wr')
000542: $2798A ← 4EF8 0380   jmp $380   (full-track WRITE, len $1200)
000554: $1ACC8 ← 4EF8 0322   jmp $322
000566: $1AA14 ← 4EF8 0336   jmp $336   ($336: $93D0←$3130; jsr $271D6; jmp $1AA1A)
000574: $2C542 ← 601C bra.s   000594: $2C574 ← 6002 bra.s
00057c: $1F636 ← 4E71 nop
000584: $26A24 ← 4EF8 03EA   jmp $3EA   (drive-letter/'cVal' handler; $3EA checks marker
                                         $6356616C at (a0)-8, hooks $400/$426 save-restore)
00059c: jmp $3104.w                      ; game entry
```

Plus a sound/PSG redirector at $C6C (installs $C2E/$C34 into the game's sound-vector triplets
$1242/$124A/$124E, $1292/…, $12E2/…, driven by table $142C+12·[$B96]) and the chunk-cache
descriptor at $3D2. The stubs call the resident service through the pointer `[$462]` =
$1F8000 (2 MB) / $F8000 (1 MB) with dispatch word `[$1F8008]` = $0FC4 → `$1F8FC4/$F8FC4`.

**Why this matters for patching**: PP's design already is "load original bytes from images,
then patch in RAM". Our patcher can (a) ride the same pattern at $59C for boot code, and
(b) use the per-file hook at $2794A/$27D58 for everything loaded later — no image files need
to be modified at all (avoids the FFA-file1-style checksum breakage entirely).

## Appendix — raw evidence index

* Traces: `work/prof/gemdos_coldboot_trace.txt` (2 MB), `/tmp/mwload/gemdos_1mb.txt` (1 MB;
  shows `Fopen("FFA") at PC=0xF9022`, `Fread(64, 200000, 0x81000) at PC 0xF910E`).
* Breakpoint file-logging used throughout:
  `hatari-debug b pc = $278de :trace :file /tmp/mwload/hit.txt` with hit.txt =
  `r / m $6918 4 / m $7824 2 / m $e570 2 / m $93d1 2 / m $3d0 2`; VBL-handler test
  (`b pc = $26298 :trace :once :file`, hit logged) proves the mechanism works, so the
  zero-hit results in run A are real.
* Run C load log (all 31 hits, boot→intro→menu→mission-disc mission→gameplay):
  service seeks FFA $2400/$33C00/$65400/$832C0, FFB $0/$6AE00/$64200/$75000/$7BC00;
  loads: FFA f6(ck 1AF,len 1260)→$62000, f7(A32,9494)→$40040; FFB f111(2784,E66)→$62000,
  f110(17F8,2912)→$62000, f45(62C5,2930)→$62000, f41(AD6B,28A1)→$62000, f43(EE37,32E0)→$72000,
  f44(27EE,2892)→$47D40. Zero hits after gameplay entry (incl. walking, 30 s).
* $4BC patcher hit registers: §1.1. $2794A hook registers: §4.
* Dumps compared: `ram_ingame_lobos.bin` vs `corridor.bin`: sub_278A6 0 diffs; PP loader text
  89 diffs, all inside data fields ($1F94AD–$1F9570 palette sums, $1F9F86 palette save,
  $1FB365–$1FB3A3 request block). $B3000–$100000 zero in both; highest non-zero <1 MB: $B2851
  in both. 1 MB: §5.
