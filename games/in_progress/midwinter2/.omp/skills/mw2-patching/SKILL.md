---
name: mw2-patching
description: Write, build, verify and gate Midwinter 2 code patches with tools/mw2patch.py and tools/abtest.py. Covers the patch file format, boot vs deferred sites, the $B3000 payload and its size limits, blob address allocation, hook-writing rules (jmp vs jsr, displaced instructions, register/flag contracts), and the acceptance gates every patch must pass. Use before creating or changing anything in patches/.
---

# Midwinter 2: patching

There is no source code. Patches are applied in RAM:
- **Boot-phase patches** are applied by our trampoline right after PP's own boot patcher.
- **Deferred patches** are applied by a per-file load hook, for code that arrives later from FFB.

Image files are never modified. Full mechanism: `patches/README.md`; loader facts: `work/notes/loading.md`.

## Commands
```
python3 tools/mw2patch.py list | verify
python3 tools/mw2patch.py build [--only A B ...] [--out build/game]   # default set = every `default: yes`
python3 tools/mw2patch.py live  [--only A B ...] --out build/live/x   # x.img (load at $B3000) + x.json (sites) for snapshots
python3 tools/abtest.py --only A B [--snapshot S ...] [--flips N]     # pixel-identity (32000 visible bytes per buffer) + fps gate
tools/package.sh                                                      # default build -> dist/ zips
```
`build` runs `verify` first. It aborts on any `orig` mismatch, on overlapping sites, and on overlapping blob or data ranges.

## Patch file format (`patches/*.s`, vasm mot syntax)
```
; name: p4_example
; default: no                 ; flip to yes only after every gate passes
; site: $3c5e2                ; ONE site per file; multi-site changes = several files with a common prefix
; orig: 48e7fffe41f9          ; expected original bytes (cross-checked against image AND ram dump)
; phase: boot|deferred        ; optional, auto-detected (deferred = re-loaded from an overlay, e.g. FFB f1)
; data: $b3500 16             ; zero-initialised blob-owned data, repeatable
; note: why, evidence pointers
        org     $3c5e2        ; segment at the site = the new bytes (<= orig length, nop-pad)
        jmp     $b3500.l
        org     $b3500        ; blob code at a fixed org inside YOUR range
        ...
```

## File patches (HAGA)
PP's resident loader service is the HAGA file, which moves with RAM size. Patch it as a file, not in RAM:
- Header: `; image: HAGA` plus `; edit: <offset> <orig hex>`.
- Code segments: `org HB+$<offset>`.
- The tool assembles the code at both HAGA bases and requires identical bytes (position independence).
- Example: `patches/pp_nofade.s`.

## Payload and address map
- **Payload:** `$B3000-$BAFFF` (`PAYLOAD_LEN = $8000`, 32 KB).
  - HD: appended to RUNME's data segment. The four pc-relative `lea d(pc),aN` into bss (text `$98`, `$C24`, `$41EA`, `$41FC`) are `movea.l` loads of relocated pointers, so the size is limited only by free RAM. `build_runme` aborts on any other `d16(pc)` operand that reaches bss.
  - Floppy: FFA file 10 on track-sides 72-79, which is all of the free ones (4608 B each); the limit is 8 × 4608 = `$9000` bytes; a larger payload needs another place on the disk (track-side 80 holds data).
  - Free RAM above the payload: `$BB000-$E83E5` on 1 MB.
  - `$B4F00-$BAFFF` is free for new patches. `test_blob16k` (`default: no`) puts a recognisable 16 KB pattern at `$B6000-$B9FFF` to prove the range survives in game.
- **Fixed regions:**

| Range | Contents |
|---|---|
| `$B3000-$B30FF` | Core: trampoline, load hook exit, applier |
| `$BA000-$BAFFF` | Site table plus orig/new byte pool (4 KB). Each site costs 16 B + 2×len. Blob/data orgs may use `$B3100-$B9FFF`. |
| `$B2FF8` | Marker: `MWPO` = all applied, `MWPF` = mismatch, nothing applied |

- **Current blob owners.** Check with `build` before choosing a range: the tool reports overlaps.

| Range | Owner |
|---|---|
| `$B3400` | Data: `tick_vbl` clock |
| `$B3500` | `p4_grid` |
| `$B3800` | `p4_proj_cols` |
| `$B3880` | `p4_proj_div` |
| `$B3900` | `p4_proj_axis` |
| `$B3C00` | `p4_walk*` |
| `$B42E0-$B42FF` | `p3cp_head` data block D (scheduler words, SKIP) |
| `$B4102` | `p3c_render` |
| `$B3700` | `tick_vbl` (30 B) |
| `$B4300-$B46FF` | `p5_ctl_*` |
| `$B4700-$B4BFF` | `p4_blit_*` (off) |
| `$B8000-$B8FFF` | `p3cp_head` (code from $B8000 (below $B8700), NPC snapshot $B8700-$B8EBF, data $B8F00-$B8FFF); `p3c_head` (alternative) uses the same range |
| `$B44C0-$B4693` | `p4_hud_pfx_*`/`p4_hud_reset` (default) and the crop prototype (they conflict) |

- **Free RAM on a 1 MB machine** in game: `$B2852-$E83E5`. Only the payload is copied there, though.
  - Below it, PP's stack-phase installer copy occupies `$B1F44-$B2853` (stack `$B1F40` downwards) on 1 MB and 4 MB; it ends before `$B3000`. Evidence: `work/notes/payload32k.md`.
  - Floppy: the game's disk-copy buffer is `$80000-$AD000` after `floppy_copybuf`.
- **PP's disk cache must stay chunked on 68000 machines.** With >= 4 MB, HAGA switches to a whole-image cache at `$81000-$135000`, which would wipe the payload at `$B3000` (the cause of the title-screen hang); `pp_bigram_cache` (HAGA+`$3228`) prevents that. Anything below `$135000`, including all of the payload, is exposed if that patch is dropped. Test RAM sizes 1, 2, 4 and 8 MB. See `work/notes/bigram.md`.

## Rules for writing hooks
- **Jump with `jmp`, not `jsr`, when the blob replaces an exit sequence and must see the caller's stack frame.** The load-hook crash was a `jsr` splice pushing 4 extra bytes.
- **When a site replaces instructions, the blob must re-execute them exactly.**
  - If the site was `jsr X`, use `jmp X` as a tail call from the blob, so X's `rts` returns to your caller.
  - Some displaced instructions write memory or set flags that callers test, e.g. `move.w (a7)+,$62f2.w` sets CCR. Preserve their effects.
- **Prove the register and flag contract from the disassembly of every caller and callee.** Run `m68dis --callers`, then read what each caller uses after the call. Unproven = not allowed.
- **Machine independence:**
  - Hook only game and low-RAM addresses. PP's resident service moves with RAM size: `$1F7554` on 2 MB, `$F7554` on 1 MB.
  - Use runtime detection for hardware features.
  - `$5a0`/`$42e` are clobbered by PP, so probe the hardware under a bus-error trap instead. `p4_blit_sky` has a working STE/ST/Mega STE probe.
- **Timers:** use the patched free-running clock (`tick_vbl`, long at `$B3400`, units of 1/300 s: +6 per 50 Hz VBL, +5 per 60 Hz VBL).
  - `$7020` is cleared every frame and by game wait loops.
  - `$770c` wraps at 6.
- **Snapshot gates:** a patch that only matters at boot or load time still needs a cold-boot test, since snapshots already hold loaded code.

## Gates (in this order)
1. `mw2patch.py verify`: ALL OK.
2. **Display or perf patch:** `abtest.py --only <set>` must exit 0 (pixel-identical) on both default snapshots, with `--flips 10` AND `--flips 40`. Report fps over 1000 VBL plus the 68000 cycle math, old vs new.
   - Gate WITHOUT the `tick*`, `p3b*` and `p5*` patches. They change frame timing and input handling, so frame-N comparisons stop being meaningful.
   - Intentional visual changes need before/after screenshots and the user's approval.
   - Dithered landscape fills must be kept.
3. **Timing patch:** world rate (`world_rate`, or position delta per VBL) must match within 5% across 8 MHz and 16 MHz. Group-end state must equal the reference build.
4. **Cold boot of the full default build** on 1 MB STE: `boot_to_game('M')` reaches the 3D view, `MWPO` is set, walking works, and a turn works. Run the same check on a plain ST (`machine='st'`, TOS 1.04) for anything hardware-specific.
5. Set `default: yes`, and add a line to `patches/README.md`.

## Known dead ends
- **STE blitter:** no gain on an 8 MHz STE.
  - Sky fill: −0.15% of a frame.
  - Span interiors are at most 0.5% of a frame; spans are 2–6 groups wide.
  - HOG mode stalls interrupts.
  - See `work/notes/blitter.md`.
- **Full 25 Hz logic** (option B) is too expensive: +88% frame time. Partial B (player only, on foot) is what ships. See `work/notes/tick_inventory.md`.
