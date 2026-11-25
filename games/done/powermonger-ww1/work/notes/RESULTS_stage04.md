# Stage 4 results (PMWW1Stage04, 2026-11-23): RAM guard, cache cap, HIGH-area gates, then the remaining master defaults, the HD build and the campaign-end gate

Evidence contract: **[obs]** = raw lines from a file named here; **[INFERENCE]** = reasoning only; failures are listed as failures.
Hatari 2.6.1 (`~/Code/AtariST/hattari/build/src/hatari`), private HOME per run, work dirs `/tmp/pmww1s4/*`, one Hatari at a time. Gate logs: `work/runs/s4_*.txt`.
Tools: `tools/wwgate.py` (cell: `--fill-hi --trace --raise-cursor --events-out`, steps `continue lose2 win2 random`, `cmpevents`), `tools/wwram.py` (RAM-size guard), `tools/wwpatch.py`
(HIGH area: `RANGES`, `check_span`, `; scratch:`, `free_hi`, `hi_expect.bin`; `build --hd`), `tools/stage04_gates_a.sh` (the chain of sections 2-3).

## 1. Work item 1: the RAM guard in `core.s` (memory_plan item 2, gate M6)
`front` (the position-independent stub that TOS starts) now reads the basepage's `p_hitpa` (`4(a0)`, `a0 = 4(a7)`) and compares it with `TPAMIN = $f8000`.
Below it (a 512 KB machine: TOS's screen at `$78000`, the program's start-up stack at `$77Fxx`, the payload area `$72000-$77FFF` would be the stack and the screen) it installs NOTHING:
it writes the 8 original `move.l #imm,-(a7)` of the copy routine (48 bytes, kept in `front`; `wwpatch.py` checks that they equal the original text at `PUSH_OFF = $2cc`) back over the
`jmp hook` ones, runs the program's own first instruction (`Super(0)`) and continues at text offset 8: the game runs exactly as the original program does, `MARKER` stays 0.
A 1 MB machine has `p_hitpa = $f8000` [obs: the TOS 1.62 1 MB cell installs with `TPAMIN = $f8000` and refuses with `$f8001`], 4 MB machines `$3f8000`.
```
original ea.st, ST TOS 1.04 512 KB (baseline):   GATE orig512 marker $727f8 = 0 PASS; option screen reached on 512 KB PASS; cache cursor $2cfda = $00000000 (no cache: probe found no RAM at $80000)
patched build, ST 512 KB:                         GATE p512 marker = 0 (refused) PASS; option screen reached on 512 KB PASS; cursor 0
patched build, STE TOS 1.62 512 KB:               GATE p512ste marker = 0 (refused) PASS; option screen reached PASS; cursor 0
patched build, STE 1 MB (control):                GATE p1024 marker = PMPO (installed) PASS; option screen reached PASS; cursor $80000 (cache on)
negative control (TPAMIN = $f8001 built in a WW_PATCHDIR copy), STE 1 MB: marker 0 (refused), option screen reached: the guard really compares p_hitpa
patched build, ST 512 KB, protection answered from RAM (the original flow, `/tmp/pmww1s4/map512.py`): GATE map512 map view reached on 512 KB (refused payload): counter 18 ticking True marker 0000
```
The refused game plays through the (still present) protection question and the key-disk request to the map view, i.e. a 512 KB machine gets the original game, unpatched, as the plan asked.
Tool: `tools/wwram.py`. `core.s` also documents that the init routines may NOT use a2 unsaved (the init loop keeps its table pointer there; `pm_mste` saves it).

## 2. Work item 2: `pm_cachecap` (site `$e3f2`, `CAPLIM = $B0000`, memory_plan item 3)
`patches/pm_cachecap.s`: master's 24-byte hook, re-sited (`movea.l $2cfda.l,a1` -> `jsr $75800`), blob in `$75800-$75817` (LOW area), `CAPLIM equ $b0000`; the build refuses a `CAPLIM` that is not
`HI_BASE` (`wwpatch.py`). A resource that would end above `$B0000` is not cached (`a1 = 0`: the game's own no-cache branch, as on a 512 KB machine).

### Gates M3a / M3b / M3c (`tools/wwgate.py cell ... --trace`, loader trace = breakpoints at `$e34c` call / `$e388` not cached / `$e3f8` cache step / `$e42a` return; `A1` at `$e3f8` = 0 is a skip)
Raw lines (`work/runs/s4_*.txt`):
```
M3a  s4_m3a_compare.txt: GATE M3a loader trace of ev_default.json == ev_nocap.json PASS 36 / 36 loader calls, 16 / 16 from the disk, skips 0 / 0
     (the same full scenario on the capped build and on a build WITHOUT pm_cachecap: boot, map, save+load, lose, win, CONTINUE, lose, START NEW (YES), win, PLAY RANDOM LAND)
     s4_ste_full.txt: GATE ... cap normal: no skip (M3a) PASS 0 skip(s); loader: every cacheable resource (1 8 10 14 15 16) came from the disk at most once PASS {1:1, 8:1, 10:1, 14:1, 15:1, 16:1}; 20 cache hits <= 40 VBL
     cache cursor maximum $af658 on STE / Mega STE / ST (`cache cursor@<step>` lines, all <= $b0000)
M3b  s4_m3b_forced.txt (cursor raised by $10000 at the option screen): LOADER ... 14:DS178 ... 15:DS120; GATE cap forced: the resource that would end above the limit was skipped (M3b) PASS 2 skip(s): [(14, 8173), (15, 13198)];
     lose and win pictures stable after 8 s, cursor stays $afc58, hi@lose / hi@win 0 of 290816 bytes changed, CELL DONE OK
M3c  s4_m3c_nocap.txt (same raise, build without the cap): GATE hi@lose FAIL 30981 of 290816 bytes changed in $b0000-$b7957; cache cursor@lose FAIL [$2cfda] = $b7958; CELL DONE FAIL  (the gate can fail)
```

## 3. Work item 3: the HIGH-area scaffolding and the fill gates (memory_plan section 6 item 1, gates M0-M7)
`wwpatch.py`: `HI_BASE = $B0000`, `HI_END = $F7000` (one constant = `CAPLIM`), `RANGES` (name prefix -> LOW ranges and HIGH ranges, memory_plan 3.1 / 3.2 plus where stage 2 / 3 put pm_tooltip and qol_keys),
`check_span` (build errors: span outside its patch's ranges, between the areas, below `HI_BASE`, a LOW span larger than 2 KB, HIGH blobs only inside the patch's HIGH range), overlap check across both
areas, new header `; scratch: ADDR LEN` (a HIGH span the patch writes at run time that needs no initial value: no record, no zero fill, masked by the gate), HIGH blobs as records,
manifest `hi_used / hi_data / hi_scratch / free_hi`, `hi_expect.bin` (pattern in the free spans, blob bytes where a HIGH blob sits).
`wwgate.py cell --fill-hi`: the debugger loads a position-dependent non-zero pattern (`fill_byte`, never 0) into every HIGH byte the manifest does not declare at the hand-over (`b pc = $576 && ($576).w = $41f9 :once`,
`loadbin`; on a machine with more than 1 MB also `$f7000-$fffff`; on 1 MB `$f7000-$ffffff` is TOS's start-up stack and screen and never checked) and compares it at EVERY checkpoint (`hi@<step>` lines); HIGH code /
constants byte-exact, `data` / `scratch` masked; plus a cache-cursor line (`cursor <= $b0000`).
Full scenario cells (steps boot,map,saveload,lose,win,continue,lose2,round3,win2,random; `--fill-hi --trace`), build = stage-3 default set + pm_cachecap:
```
s4_ste_full      STE TOS 1.62 1 MB   CELL DONE OK (656s)  76 PASS 0 FAIL   hi@<every step> 0 of 290816 bytes changed in $b0000-$f6fff; payload@* unchanged; save/load 0 of 101376 differ
s4_nocap_full    STE, build without the cap  CELL DONE OK (654s) 75 PASS 0 FAIL   (also 0 changed: the game alone never reaches $b0000 in this scenario)
s4_megaste_full  Mega STE TOS 2.06 4 MB 60 Hz  CELL DONE OK (666s) 76 PASS 0 FAIL   pattern also $f7000-$fffff
s4_st_full       ST TOS 1.04 1 MB    CELL DONE OK (655s)  76 PASS 0 FAIL
```
M1 negative control (`s4_m1_negative.txt`, a WW_PATCHDIR copy of pm_cachecap whose hook also writes one byte at `$ee500`, the reserve): `GATE hineg hi@map FAIL 1 of 290816 bytes changed; changed $ee500-$ee500`, `CELL DONE FAIL`.
Not covered: a real battle (the scenario ends with PLAY RANDOM LAND on the map view; no attack order was scripted), HD, TT / Falcon, 20-minute soak with the HIGH pattern.

## 4. Remaining items: state at the end of this run (budget exhausted)
**Written and building, NOT gated in Hatari** (all assemble into one floppy: `wwpatch.py build --floppy` 83 clusters, 28 672 B free, `checkdisk` PASS; none has been booted):
`pm_mste` ($75900, master verbatim), `p4_clamp` (site $ed6), `tt_ptr` (site $e20; the 314-byte pointer block is the verbatim resident bytes $87e-$9b7, LIVE at $75bf0), `tick_rain` (site $13e24, replaces `tick_wx`, now `; default: no`),
`p3b_interp` / `p3b_delta` (sites $13e1e / $13e3c; WW1 people table = 350 records of $36 bytes at $55df4-$5a7c7, NOT master's 512 x $32 (the profile note's `PS = 0x32` is wrong); OLD $c0000, LST $c0800 zero-filled),
`qol_hover` / `qol_hover2` (sites $13e2a / $12ee0; WW1's Build order is a 3-entry table $510c, no wood / iron rules: hover says `Build here: tanks|planes|rifles (3|2|1 swords)`; T = [$5a914+owner*$20+8]+4, +$400 plane / tank; house table $54234-$5574c, stride $12),
`snd_core/start/stop/setup` (sites $1c4de $1bbbc $1bb96 $6de; STAGE `$bc000`; the DMA probe moved into snd_core's own init), HD: `hd_core/hd_load/hd_sector/hd_kbd` (sites $d962 $ddea $e78; S `$c3000`, no overlay), `wwpatch.py build --hd` writes `hd/` (AUTO\WW1.PRG, the 12 game files, SAVEDISK.DAT).
Gate tools written, never run: `wwrain.py` (rain per frame, tick_rain vs tick_wx at 16 MHz), `wwinterp.py` (people table restored every pass, offsets touch only low bytes), `wwhover.py` (hover text == settlement record, pixel-exact vs wwtt composer), `wwptr.py` (TT pointer visibility), `wwhd.py` (GEMDOS / ACSI+HDDRIVER harness, SAVEDISK load/save), `wwend.py` (campaign end), and two prepared edits of `wwgate.py` (`--psg` strict sound gate, step `hw`, `--hd`) in `/tmp/pmww1s4/patch_wwgate*.py` (volatile).
**pm_intro_***: not applicable [static]: the WW1 image has no CPU busy-loop delays (scan for `move.l #n,dn / subi.l` and `move.w #n,dn / dbra` finds only the IKBD command delay `$dda` (10000 dbra) and disk time-outs); title / retire waits use the VBL counter `$71b7c`.
**Campaign end** [static + trace of the existing win path, not run live]: the real end is the WIN picture (resource 15) with the text "AT LAST THE WAR IS OVER AND NOW EUROPE CAN AGAIN REST IN PEACE" (`$1b182` sums the 216 land bytes at $44760; >= $b1 -> `jsr $1b264`). The routine that loads END_PIC1 / END (`$1b3a6`, calls `$1b3b2` / `$1b3cc`)
has NO reference anywhere in the resident image (no jsr / jmp / bsr / bra / pc-relative / long / word reference); master's equivalent has one caller, WW1's win routine does not. BITMAP.PAK (resource 7, `$14994`) loads only when the land word `$5a9b6` (= `$5a90a`) is < $100; no run loaded 6 or 7 (all loader traces above). So no copy of `END_PIC1.DAT` / `END.DAT` was made (the floppy has only 28 KB free; they need 90 KB). `wwend.py final|orphan` is the gate that would prove it live.

