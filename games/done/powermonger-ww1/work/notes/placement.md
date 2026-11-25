# Where the payload lives: `$72000..$77FFF`  (PMWW1Stage01, 2026-11-23)

Tags: **[obs]** RAM dumps / runs of this session (`work/runs/*.txt`, dumps in `/tmp/pmww1s1/*.bin`, `work/dumps/` git-ignored); **[INFERENCE]** reasoning only.
Question (lead, PLAN risk 1): the branch put its payload at `$72000` "below the resource cache cursor ($80000)"; master's v1.1 Retire / Win / Lose crash was a payload that the game's resource cache grew over. Where may WW1's payload go, with evidence?

## What the game does with RAM (1 MB STE, TOS 1.62)  [obs]
* Zero runs >= 4 KB in 1 MB RAM dumps (python over the dump files; `numpy` run of this session):

| moment | zero runs inside `$71000..$100000` |
|---|---|
| hand-over (`$576` entered) | `$1d2a8-$f7fc7`, `$f8000-$fffff` (everything above the image) |
| option screen | `$71b84-$7ffff`, `$80002-$f7fc7`, `$f8000-$fffff` |
| protection question | `$71b84-$77fff`, `$9fc58-$f7fc7`, `$f8000-$fffff` |
| map view | `$71b84-$77fff`, `$9fc58-$f7fc7`, `$f8000-$fffff` |

* The game's own BSS clear loops end at **`$71b84`** (`$592 lea $71b84,a1`; `$71b7c` is the VBL counter, `$71b80`/`$71b7e` its neighbours): that is the end of the game's declared data.
* **`$78000-$7ffff` is a 32000-byte picture buffer** that is zero on the option screen and non-zero from the territory chart on (the chart / map picture: 4388-5067 non-zero bytes per 8 KB at the protection question and map view). The start-up code also sets the video base to `$78000` (`text $6e..$7a`: `move.l #$78000,d0 ; lsr.w #8,d0 ; move.l d0,$8200.w`). Not available to us.
* **The resource cache** ("bump allocator", master's `pm_cachecap` target) is the same code as master's: cursor `[$2cfda]`; `$5e8 lea $80000,a0 ; move.l a0,$2cfda ; move.w #$3039,(a0)` (probe), `$5fa/$608 clr.l $2cfda` (no RAM -> no cache), the loader `$e344`: `$e3f2 movea.l $2cfda,a1 ... $e424 move.l a1,$2cfda` (a static search of the 118072-byte image finds exactly these 5 references to `$2cfda`). The cursor only ever grows from `$80000` (`$9fc58` at the map view, `$a7958` after the lose picture, `$af658` after the win picture [obs]); its copy loop writes at `[$2cfda]` and above. **It can never write below `$80000`.**
* Static search for references into the free range: the only code that mentions an address in `$71b84..$7ffff` as an operand is the BSS clear (`$592`), the VBL counter (`$71b7c..$71b80`, many sites) and the video base `$78000` setup; the other 260 hits of a byte-pattern search for `$0007xxxx` inside `$71b00..$7ffff` are data tables or false matches on opcode words (checked: `$9f4`, `$d14`, `$1d0b0` are tables / a palette write) [obs: script in this session, not a tool].

## Candidates
| range | size | verdict |
|---|---|---|
| the branch's `$72000-$c1cff` | 328 KB | **rejected**: `$78000-$7ffff` is the chart picture, `$80000-$a7958+` is the resource cache (grows during a session, up to `$af658` after a win) |
| master's `$b8000-` | | **rejected as is**: the cache reaches `$af658` after one win and grows with every first-time resource; it would need `pm_cachecap` and 512 KB / 1 MB behaviour would be tied to it |
| above the cache (`$b0000-$f7fff`) with a cap | 290 KB | possible, but every cap choice costs cache hits (= disk reads, on a floppy) and the cursor value moves with the machine's RAM [INFERENCE]; keep as the fallback for payloads larger than 22 KB |
| **`$72000-$77fff`** | 24576 B (22.5 KB for patch blobs after the 2 KB core) | **chosen**: free at every dump above, referenced by no code, below `$78000` (picture) and `$80000` (cache), so neither can reach it; costs no cache |

Core layout inside it: `$72000` entry/init (`'PMPA'`), `$72140` hook, `$721f0` apply, `$72250` site table (<= 1344 B), `$72790` uinit table, `$727c0` init table, `$727f8` marker, `$72800-$77fff` patch blobs (22528 B).
`pm_credit` takes 164 bytes; master's default set with the same features (tick, keys, tooltips, noprot, interpolation ...) needs about 12-15 KB [INFERENCE from master's blob sizes: tick ~2.5 KB, p3b ~1 KB, tooltip ~4 KB, qol ~2 KB]. **The large optional blocks of master (p4_spr sprite cache, p7 triple buffers `$70000`-class buffers, the DMA-sound sample bank, p6 tables) do not fit** and need their own placement decision when (if) they are ported (stage 4/5); the fallback is above the cache with a cap.

## Proof by pattern fill (the master method)  [obs: see `RESULTS_stage01.md` for the lines]
`wwpatch.py build --fill` stores a deterministic non-zero pattern over every free long of `$72000-$77fff` (23988 B in the default build) next to the real payload; `wwgate.py cell` compares the whole region with the expected image (payload + pattern + zeros) at the option screen, at the map view, after the lose picture, after the win picture and after the third land: any byte the game writes there is a failure. The same check runs on the ordinary build and on the ORIGINAL disk with an all-zero expectation (the game itself must leave the range alone).
