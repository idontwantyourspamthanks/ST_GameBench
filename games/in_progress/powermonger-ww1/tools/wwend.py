#!/usr/bin/env python3
"""Campaign-end gate (work/notes/endfiles.md): which resources does the end of a WW1 campaign load, and what happens with the WW1 disk only?

    python3 tools/wwend.py final  --disk build/default/floppy.st --workdir DIR     # force the campaign end, RETIRE won: the ending that exists
    python3 tools/wwend.py orphan --disk build/default/floppy.st --workdir DIR     # call the orphan END_PIC1 / END routine ($1b3a6) instead
    python3 tools/wwend.py orphan --hd build/x/hd [--acsi] --endfiles DIR          # same on the HD build with END_PIC1.PAK / END.PAK next to the data files

Facts [static, tools/m68dis.py on work/dumps/entry576.bin]: the win routine $1b182 (called by the retire dispatch $d6da) adds up the bytes of the per-land table $44760..$44837
(216 bytes, non-negative ones, `cmp.w #$b1,d0`): >= 177 -> `jsr $1b264` = the WIN picture (resource 15) with the closing text "AT LAST THE WAR IS OVER AND NOW EUROPE CAN AGAIN REST IN PEACE"
(strings $1a916 / $1a93a), else the normal win text.  The routine that loads END_PIC1.PAK (resource 12, call $1b3b2) and END.PAK (13, $1b3cc) starts at $1b3a6 and NOTHING
references it (no jsr / jmp / bsr / bra / lea pc / long / word reference in the whole resident image; master's equivalent $1a486 has one caller, the win routine's last-island test).
`final`: the table is poked to all ones, RETIRE with the won balance forced: the loader trace must show resource 15 only (no 12 / 13 / 6 / 7), the closing-text routine $1b264 must run,
no disk requester may appear.  `orphan`: the retire dispatch's `jsr $1b182` is rewritten to `jsr $1b3a6` (live debugger write): what the original code WOULD do if it were reached.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402
import wwgate  # noqa: E402


def span_hits(h, watch):
    """{pc: n} of the `--watch` breakpoints (log blocks of sp_*.txt)."""
    res = {}
    for blk in h._logtext().split("Reading debugger commands")[1:]:
        if "/sp_" in blk.split("\n", 1)[0]:
            m = re.findall(r"\$([0-9a-f]+) \(hex\)", blk)
            if m:
                res[int(m[0], 16)] = res.get(int(m[0], 16), 0) + 1
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["final", "orphan"])
    ap.add_argument("--disk")
    ap.add_argument("--hd")
    ap.add_argument("--acsi", action="store_true")
    ap.add_argument("--endfiles", help="folder with END_PIC1.PAK / END.PAK to copy next to the data files of --hd (the original Powermonger's DATA\\END_PIC1.DAT / END.DAT)")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--manifest", help="the build's manifest.json: sites are masked in the resident-image check")
    ap.add_argument("--orig-flow", action="store_true", help="a build without pm_noprot / pm_nokeydisk (core only, the original): the game's own disk swap and protection question")
    ap.add_argument("--watch", help="file with spans `$a-$b, ...` (the differing spans of a first run): breakpoints from the first instruction; any pc inside = code executed from a span that is not the hand-over image")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    a = ap.parse_args()
    ok = True
    tag = f"end_{a.mode}"

    def line(name, good, detail=""):
        nonlocal ok
        ok &= bool(good)
        print(f"GATE {tag} {name} {'PASS' if good else 'FAIL'} {detail}", flush=True)
    if a.hd:
        import shutil
        import wwhd
        folder = Path(a.workdir) / "hdfolder"
        shutil.rmtree(folder, ignore_errors=True)
        shutil.copytree(a.hd, folder)
        if a.endfiles:
            for n in ("END_PIC1.PAK", "END.PAK"):
                shutil.copy(Path(a.endfiles) / n, folder / n)
        h = wwhd.PMWHD(folder, acsi=a.acsi, workdir=str(Path(a.workdir) / "run"), machine=a.machine, tos=pmww.TOS[a.tos], memsize_kb=1024)
    else:
        h = pmww.PMW(disk=Path(a.disk), workdir=a.workdir, machine=a.machine, tos=pmww.TOS[a.tos], memsize_kb=1024)
    try:
        wwgate.arm_trace(h)
        watch = [tuple(int(x, 16) for x in t.replace("$", "").split("-")) for t in re.split(r"[,\s]+", Path(a.watch).read_text().strip()) if t] if a.watch else []
        CTL = (0x1B182, 0x1B19F)                                      # positive control: the win routine's first instructions MUST be seen by the same kind of breakpoint
        for i, (x, y) in enumerate(watch + [CTL]):                            # code-execution watch from the very first instruction: any instruction fetched inside a span that differs from the hand-over image
            (h.R / f"sp_{i}.txt").write_text("e pc\n")
            h.cmd(f"hatari-debug b pc > ${x - 1:x} && pc < ${y + 1:x} :trace :file {h.R / f'sp_{i}.txt'}")
            time.sleep(0.1)
        h.boot_to_map(noprot=not a.orig_flow, swap=a.orig_flow, log=lambda s: print("  " + s, flush=True))
        time.sleep(2)
        man = json.loads(Path(a.manifest).read_text()) if a.manifest else None
        class _G0:
            def line(self, name, good, detail=""):
                line(name, good, detail)
        wwgate.imgcheck(h, _G0(), f"{a.mode}_map", man, info=True)   # the image at the map view (before the ending), listed only
        h.watch_pcs([0x1B182, 0x1B264, 0x1B3A6, 0x1B3B2, 0x1B3CC])
        if a.mode == "final":
            f = h.R / "ones.bin"
            f.write_bytes(bytes([1]) * 216)
            h.debug(f"loadbin {f} $44760", 0.5)
            line("campaign table $44760..$44837 forced to all ones (sum >= $b1)", h.ram(0x44760, 216) == bytes([1]) * 216)
        else:
            h.debug("w $d6da $4e $b9 $00 $01 $b3 $a6", 0.5)
            line("retire dispatch rewritten: jsr $1b182 -> jsr $1b3a6", h.ram(0xD6DA, 6).hex() == "4eb90001b3a6", h.ram(0xD6DA, 6).hex())
        c0 = len(wwgate.loader_calls(wwgate.loader_events(h)))
        h.retire(win=True, log=lambda s: print("  " + s, flush=True))
        t0 = time.time()
        txt = ""
        while time.time() - t0 < 90:
            time.sleep(3)
            txt = h.wtext().upper()
            if "INSERT" in txt:
                break
            if a.mode == "final" and h.hits().get(0x1B264, 0) and time.time() - t0 > 20:
                break
            if a.mode == "orphan" and a.hd and time.time() - t0 > 60:
                break
        h.shot(str(Path(a.workdir) / f"{tag}.png"))
        class _G:
            def line(self, name, good, detail=""):
                line(name, good, detail)
        # is all code resident?  the image $576-$1d2ad after the ending vs the hand-over dump; a differing span that holds an EXECUTED instruction is code that was loaded later (FAIL)
        if a.mode == "final":
            wwgate.imgcheck(h, _G(), f"{a.mode}_end", man, executed=span_hits(h, watch), ctl=CTL, watch=watch)
        else:                                                         # orphan: the dispatch is rewritten on purpose ($d6de), the win routine does not run: listed only
            wwgate.imgcheck(h, _G(), f"{a.mode}_end", man, info=True)
        calls = wwgate.loader_calls(wwgate.loader_events(h))[c0:]
        res = [c["n"] for c in calls]
        hits = h.hits()
        print("LOADER (after the retire click) " + wwgate.fmt_calls(calls), flush=True)
        print("HITS " + ", ".join(f"${p:x}:{n}" for p, n in sorted(hits.items())), flush=True)
        if a.mode == "final":
            line("the win routine ran ($1b182) and the closing text routine ($1b264)", hits.get(0x1B182, 0) >= 1 and hits.get(0x1B264, 0) >= 1, f"$1b182 {hits.get(0x1B182, 0)}x, $1b264 {hits.get(0x1B264, 0)}x")
            line("the orphan END routine ($1b3a6) never ran", hits.get(0x1B3A6, 0) == 0, f"{hits.get(0x1B3A6, 0)}x")
            line("only resource 15 (WIN.PAK) was requested at the end", set(res) <= {15}, f"resources {res}")
            line("no disk requester", "INSERT" not in txt, repr(h.wtext().strip()[:60]))
            ok2, best, seen = wwgate._picture(h, "end_final")
            line("the (closing) win picture is shown and stable", ok2, f"non-black {best[0]:.2f}, {best[1]} colours, stable x{seen}")
        else:
            line("the orphan routine ran", hits.get(0x1B3A6, 0) >= 1, f"$1b3a6 {hits.get(0x1B3A6, 0)}x, $1b3b2 {hits.get(0x1B3B2, 0)}x, $1b3cc {hits.get(0x1B3CC, 0)}x")
            if a.endfiles:
                line("with END_PIC1 / END next to the data: both resources requested and loaded", {12, 13} <= set(res), f"resources {res}")
                line("no disk requester", "INSERT" not in txt, repr(h.wtext().strip()[:60]))
            else:
                line("WW1 disk only: the requester for the missing file appears (the game would wait for it forever)", "INSERT" in txt, repr(h.wtext().strip()[:70]) + f" resources {res}")
        print(f"CELL DONE {tag}: {'OK' if ok else 'FAIL'}", flush=True)
        return 0 if ok else 2
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main())
