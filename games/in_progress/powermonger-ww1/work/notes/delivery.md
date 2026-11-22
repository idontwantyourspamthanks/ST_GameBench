# Powermonger WW1: the delivery engine (patch carrier) — findings

Evidence tags: **[obs]** = raw output pasted/reproducible, **[disasm]** = read from the shipped
file, **[INFERENCE]** = not verified. Tool so far: `tools/wwdepack.py` (incomplete, see 5).

## 1. The file format [obs, disasm]

`WWIEDITN.PRG`, 283902 bytes:

| part | bytes | notes |
|---|---:|---|
| GEMDOS header | 28 | `60 1a`, text **62050**, data 0, bss 0, sym 0, no flags |
| the program text | 62050 | **itself compressed** — see 2 |
| reloc | 4 | `00 00 00 00` (none) |
| the POPI payload | 221820 | from file offset 62082 |

## 2. The stub's own text is compressed [obs]

The file's text is *not* plain 68000 all the way through: strings appear mangled
(`'WIEDIT'` + `\xc0N.PRGo`, `'es\\qa'`, `'POWERMONGER - WORLD WAR I EDITION'` only partially
readable) and long stretches disassemble as nonsense. The entry instructions at text `0` are
valid, so the *entry* code is real and the rest is a packed stream that the entry code
expands. That matches the earlier live trace: at runtime the stub calls
`Super(0)`, `Cconws`, then `Fopen("WWIEDITN.PRG")`, `Fseek`, `Fread` from code at
`pc $12582..` — addresses far above the 62050-byte text, i.e. **the code doing the Fread is
in the expanded region**, not the shipped text.

Consequence for delivery: a front stub cannot simply be prepended to the text (the text is a
compressed stream with no slack, and the entry code's expectations about what follows it are
not yet mapped). The 1990 game's carrier design assumed a plain text segment; this one does
not have it.

## 3. The payload is a chunked archive, not one packed stream [obs]

The payload is a sequence of chunks, each ending in

```
[packed data ...][uint32 packed_len][uint32 unpacked_len]["POPI"]
```

Found 12 chunks; each chunk's data begins where the previous one ended (minus a 6-byte
prefix). Sizes:

| # | data offset | packed | unpacked |
|---:|---:|---:|---:|
| 1 | `$001b04` | 12554 | **32000** (a screen) |
| 2 | `$004c0e` | 3776 | 7680 |
| 3 | `$005ace` | 7602 | 19580 |
| 4 | `$007880` | 7508 | 20640 |
| 5 | `$0095d4` | 11608 | 27520 |
| 6 | `$00c32c` | 11172 | **32000** |
| 7 | `$00eed0` | 75952 | 93034 |
| 8 | `$021780` | 34286 | 65920 |
| 9 | `$029d6e` | 15340 | 71928 |
| 10 | `$02d95a` | 23470 | **32000** |
| 11 | `$033508` | 11624 | **32000** |

Chunk 0 is the odd one: its declared packed length (6928) does not fit before offset 0, so its
data starts at the head of the payload; it is presumably the *program* chunk whose
decompressed form contains the runtime code (2).

**This is the important structural finding: the WW1's "game proper" is the decompressed
chunk 0, and the other chunks are screens/assets.** The `$c1d84` Fread target seen live is
where chunk 0 lands before it is expanded.

## 4. What this means for the carrier

Two viable routes, neither yet proven:

- **A. Hook the chunk-0 expander** (the natural analogue of the 1990 `hook2` at `$10a6`):
  find the code that expands chunk 0 and the address it hands over at; install the
  1990-style verify-then-apply table there. Needs the expansion code located (blocked by 2 —
  see 5).
- **B. Append a plain carrier segment** past the POPI blob and grow the file: then the stub's
  `Fseek(62082)`/`Fread` constants must be patched — but those live in the *compressed* text
  (2), so this also needs the text expanded first.

Either way the first requirement is the same: **a working depacker for the stub text**, which
would also give the `verify` half of the patch tool (deriving original bytes from the shipped
file).

## 5. The depacker transcription (unfinished) [disasm]

The decode loop is at text `$0x1c..$0xde`. Fully disassembled; the exact semantics are in
`tools/wwdepack.py`. What is established:

- the bit reader reads the packed stream **backwards** (`move.b -(a0),d0`), 8 bits per byte,
  and the `lsr/roxr` pair means the low bit of the accumulated byte is handed out first;
- `bits(n)` at `$ce` loops `n+1` times with `addx.w d2,d2` (a left shift), so the first bit
  read ends up as the LSB of the result [disasm; the alternative — MSB first — also tested,
  see below];
- there are three token classes selected by a 1- then 1- then 1-bit chain, plus a 2-bit
  selector at `$ae` that computes a length-of-length (`d4 = ((v+1)<<2)-1`);
- the match copy is `move.b 0(a2,d2),-(a2)`: destination decremented, source at the **old**
  `a2 + d2`;
- output is written backwards from the end of the chunk.

**What fails.** Every transcription tried so far (bit order MSB-first and LSB-first; copy
source before/after the decrement; run lengths 4/5 and the variable class) hits
`run out of range` after decoding a few thousand bytes of chunk 0 correctly, which means the
*token grammar* is close but one branch's bit budget is off. Four variants are recorded in the
tool's history.

**The decisive next move** (not yet done): capture the live expanded chunk 0 and iterate
against it byte-for-byte. Two attempts to locate it by heuristics over a whole-RAM dump failed
to identify it unambiguously (the 12928-byte blob was not isolated), so the reliable way is a
watchpoint on the expansion destination — find the routine that reads a POPI chunk (it must
read the chunk's two length words at `POPI-8`/`POPI-4`) and break on its store loop.

## 6. What IS proven and usable for the patch tool

- The **payload layout** (section 3) is exact and reproducible from RAM or the file.
- `verify` can already derive the *shipped* bytes of any site: the payload at `$c1d84` is the
  file's bytes verbatim [obs: compared 40000 bytes, identical], and the free-RAM span
  `$72000-$c1cff` is proven (the tick prototype lives there and the state gate passes).
- The **tick patch itself is complete and proven** (`work/tickproto/tick.s`, 4.00 ticks/s at
  8/16 MHz, 12-tick state equality) — it needs only a carrier, not a redesign.

So the delivery work is blocked on exactly one thing: a working chunk depacker (or, equally
good, a hook at the expansion routine without needing to depack offline at all — the runtime
hook approach the 1990 game used does not require the tool to unpack anything, only to
`verify` the site bytes, which are in RAM/file verbatim).

## 7. Revised recommendation

Given 6, the pragmatic route is the **runtime hook** (route A in section 4) and to skip the
offline depacker for now:

1. Find the chunk-expansion routine by breaking on a read of a `POPI-8` length word (the
   chunk headers are at known `$c1d84 + offset` addresses), or by watching writes into a
   32000-byte picture buffer.
2. The hand-over after chunk 0 is expanded is the hook point; install the 1990-style
   verify-then-apply table there (the site bytes come from the file, not from a depack).
3. The carrier: the file can grow (the `Fseek(62082)`/`Fread` constants are in the expanded
   stub text, which is *running* when they are used — so they can be patched in RAM at the
   hook, or the whole stub text replaced in the file once the depacker works).

The offline depacker remains valuable for `verify`-by-derivation and for a clean file-level
carrier, but it is not required for a working patch.
