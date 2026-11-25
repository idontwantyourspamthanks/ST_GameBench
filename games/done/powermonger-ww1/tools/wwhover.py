#!/usr/bin/env python3
"""Gate for the village hover (qol_hover + qol_hover2 on top of pm_tooltip).  Cold boot of a BUILT floppy to the map view (noprot), STE 8 MHz.

    python3 tools/wwhover.py cold --disk build/default/floppy.st --workdir DIR [--tag NAME]

1. A breakpoint at the sprite hook ($12ee0) logs (d0, d1, a3) of every drawn object for a few passes; the houses (a3 in $54234..$5574c, in use) are the candidates.
2. The pointer words ($2edb2 / $2edb4: the words the game's own pick reads) are set to the middle of a house sprite (the harness mouse, `goto_st`: a debugger poke of the words did not hold: something rewrote them within the second) and
   the pointer rests: after the 10-VBL rest the hook arms, the next render fills HIT, the pass hook composes the text.
3. Checks: HIT == the house; SB (the 52-char line) matches `<name>: making <item>s (NN%)` / `workshop idle` / `no workshop` AND equals what the settlement record says (item, T = [$5a914 + owner * $20 + 8]
   + 4 (+ $400 plane / tank), percent = (T - countdown) * 100 / T clamped 0..99; computed here from RAM); BUF (the composed rows) == the reference rendering of SB (wwtt.expected_bytes);
   one of the two screen buffers holds BUF at rows 0-5 / byte 56 (the text is on the screen); moving the pointer away removes it (no hover text, bar black).
4. Build mode: with the command word $5a836 = $e (Build waits for a target) the same hover says `Build here: <tanks|planes|rifles> (3|2|1 swords)` from the selected captain's posture
   ($259e: tank / plane / rifle for 3 / 2 / 1 swords), or `Build here: no workshop here`.
"""
from __future__ import annotations
import argparse
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402
import wwtt  # noqa: E402
import wwpatch  # noqa: E402

HOUSE_LO, HOUSE_HI = 0x54234, 0x5574C
SETT = 0x53332
HS, S = 0x73900, 0x74800
BUF, SB = S + 0x20, S + 0x290
TREC = 0x5A914
ITEMS = 0x9CD0


def item_names():
    b = wwpatch.resident_bytes(ITEMS, 0x90)
    out = {}
    for code in range(2, 0x12, 2):
        off = int.from_bytes(b[code:code + 2], "big")
        s = b[0x14 + off:].split(b"\0")[0].decode("latin1")
        out[code] = (s[:1].lower() + s[1:] + "s")
    return out


def wb(h, a, v):
    h.debug(f"w ${a:x} ${v >> 8:02x} ${v & 255:02x}", 0.3)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["cold"])
    ap.add_argument("--disk", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--tag")
    a = ap.parse_args()
    tag = a.tag or Path(a.disk).parent.name
    ok = True

    def line(name, good, detail=""):
        nonlocal ok
        ok &= bool(good)
        print(f"GATE hover {tag} {name} {'PASS' if good else 'FAIL'} {detail}", flush=True)
    names = item_names()
    h = pmww.PMW(disk=Path(a.disk), workdir=a.workdir, machine="ste", tos=pmww.TOS["1.62"], memsize_kb=1024)
    try:
        h.boot_to_map(noprot=True, swap=False, log=lambda s: print("  " + s, flush=True))
        time.sleep(3)
        line("pm_tooltip alive ('PTIP')", h.peekl(S + 0xE) == 0x50544950, f"${h.peekl(S + 0xE):08x}")
        # ---- 1. candidates
        (h.R / "hv.txt").write_text("r\n")
        h.debug("b all", 0.3)
        mark = len(h._logtext())
        h.cmd(f"hatari-debug b pc = $12ee0 :trace :file {h.R / 'hv.txt'}")
        time.sleep(9)
        h.debug("b all", 0.3)
        txt = h._logtext()[mark:]
        cand = {}
        for blk in txt.split("Reading debugger commands")[1:]:
            d0, d1, a3 = (re.search(rf"{r}\s+([0-9A-Fa-f]{{8}})", blk) for r in ("D0", "D1", "A3"))
            if d0 and d1 and a3:
                x, y, p = (int(m.group(1), 16) for m in (d0, d1, a3))
                x16, y16 = (x & 0xFFFF), (y & 0xFFFF)
                if HOUSE_LO <= p < HOUSE_HI and x16 < 400 and y16 < 200:
                    cand[p] = (x16, y16)
        print(f"  house candidates drawn in the view: {len(cand)}: " + ", ".join(f"${p:x}@({x},{y})" for p, (x, y) in list(cand.items())[:8]), flush=True)
        line("the sprite hook ran for houses (candidates found)", len(cand) > 0, f"{len(cand)} houses")
        if not cand:
            return 2
        # ---- 2. rest the pointer on the houses until one hovers.  Houses of a town WITH a workshop (a house of kind $7 in the settlement's chain) come first; if no drawn town has one,
        #         the kind byte of the first candidate is set to 7 (a test setup, printed) so that the 'workshop' branches (idle / making / Build here: planes ...) run on a real workshop.
        def chain_has_ws(hp):
            sro = int.from_bytes(h.ram(hp + 0xE, 2), "big")
            a_ = int.from_bytes(h.ram(SETT + sro + 2, 2), "big")
            hb_ = h.ram(HOUSE_LO, HOUSE_HI - HOUSE_LO)
            n = 0
            while a_ and n < 300:
                if hb_[a_ + 7] == 7:
                    return True
                a_ = int.from_bytes(hb_[a_ + 8:a_ + 10], "big")
                n += 1
            return False
        usable = [p for p in cand if 0 < h.ram(p, 0x18)[5] < 0x80]
        ws = [p for p in usable if chain_has_ws(p)]
        print(f"  houses drawn {len(usable)}; of towns with a workshop: {len(ws)}", flush=True)
        if not ws and usable:
            hb_ = h.ram(HOUSE_LO, HOUSE_HI - HOUSE_LO)
            sro = int.from_bytes(h.ram(usable[0] + 0xE, 2), "big")
            a_ = int.from_bytes(h.ram(SETT + sro + 2, 2), "big")
            h.debug(f"w ${HOUSE_LO + a_ + 7:x} $07", 0.3)                         # the first house of the chain becomes a workshop
            print(f"  TEST SETUP: no drawn town has a workshop: kind byte of house ${HOUSE_LO + a_:x} (chain head of settlement ${SETT + sro:x}) set to 7 (was {hb_[a_ + 7]})", flush=True)
            ws = [usable[0]] if chain_has_ws(usable[0]) else []
        line("the hovered town has a workshop (house kind 7 in the chain)", bool(ws), f"{len(ws)} town(s)")
        if not ws:
            return 2
        cand = {p: cand[p] for p in ws}
        res = None
        for p, (x, y) in cand.items():
            rec = h.ram(p, 0x18)
            if rec[5] == 0 or rec[5] >= 0x80:
                continue
            for dx, dy in ((12, 12), (8, 14), (14, 8)):                # the object square is 16-32 px ($12ebe); the pointer is moved with the mouse (the words $2edb2 / $2edb4 are rewritten every VBL: a debugger poke does not hold)
                h.goto_st(x + dx, y + dy)
                t0 = time.time()
                while time.time() - t0 < 25:
                    time.sleep(1.0)
                    if h.peekw(S + 0x12) == 1 and h.peekl(HS + 2) == p:
                        res = (p, x + dx, y + dy)
                        break
                if res:
                    break
            if res:
                break
        line("a house under the resting pointer is picked (HIT)", res is not None, f"HIT ${h.peekl(HS + 2):x}, RES {h.peekw(HS + 0xE)}, ARM {h.peekw(HS)}" + (f", house ${res[0]:x} at pointer ({res[1]},{res[2]})" if res else ""))
        if not res:
            return 2
        p, px, py = res
        rec = h.ram(p, 0x18)
        sett_off = int.from_bytes(rec[0xE:0x10], "big")
        sr = h.ram(SETT + sett_off, 0x20)
        owner, item, cdown = sr[0], int.from_bytes(sr[0xC:0xE], "big"), int.from_bytes(sr[0x10:0x12], "big")
        trec = int.from_bytes(h.ram(TREC + owner * 0x20 + 8, 2), "big")
        sbb = h.ram(SB, 64)
        text = "".join(chr(c) if 32 <= c < 127 else " " for c in sbb[:52]).rstrip()
        print(f"  SB = {text!r}; settlement ${SETT + sett_off:x} owner {owner} item {item} countdown {cdown} T-base {trec}", flush=True)
        m = re.match(r"^([A-Za-z' -]+): (making ([a-z]+) \((\d+)%\)|workshop idle|no workshop)$", text)
        line("SB has the hover format", bool(m), repr(text))
        if m:
            T = trec + 4 + (0x400 if item >= 0xE else 0)
            if item and item <= 0x10 and not item & 1:
                pct = 0 if (cdown > T or T == 0) else min(99, (T - cdown) * 100 // T)
                want = f"making {names[item]} ({pct}%)"
                line("text equals the settlement record (item, percent)", m.group(2) == want, f"got '{m.group(2)}' want '{want}' (T {T}, countdown {cdown})")
            else:
                line("text equals the settlement record (no item: workshop idle / none)", m.group(2) in ("workshop idle", "no workshop"), f"'{m.group(2)}', item word {item}")
        buf = h.ram(BUF, 624)
        want = wwtt.expected_bytes(text)
        line("BUF == reference rendering of SB (wwtt composer)", buf == want, f"{sum(1 for x, y in zip(buf, want) if x != y)} of 624 bytes differ")
        onscr = [n for n, base in (("A", 0x1D500), ("B", 0x25200)) if wwtt.screen_region(h.ram(base, 32000)) == buf]
        line("the text is in a screen buffer at rows 0-5 / byte 56", bool(onscr), f"buffers {onscr}")
        # ---- away
        h.goto_st(250, 150)
        time.sleep(4)
        gone = all(wwtt.screen_region(h.ram(base, 32000)) != buf for base in (0x1D500, 0x25200))
        line("pointer away: the hover text is gone from both buffers", gone, f"HIT ${h.peekl(HS + 2):x}")
        # ---- an item in the making: poke the settlement record (item word +$c, countdown +$10), rest the pointer again, the text must follow the record
        def rec_state():
            r = h.ram(SETT + sett_off, 0x20)
            return int.from_bytes(r[0xC:0xE], "big"), int.from_bytes(r[0x10:0x12], "big")
        for item_w, frac in ((6, 2), (14, 4)):
            T = trec + 4 + (0x400 if item_w >= 0xE else 0)
            cd = T - T // frac                                     # a third / quarter of the way: percent = 100 // frac
            wb(h, SETT + sett_off + 0xC, item_w)
            wb(h, SETT + sett_off + 0x10, cd)
            h.goto_st(250, 150)
            time.sleep(1.0)
            h.goto_st(px, py)
            got, t0 = "", time.time()
            while time.time() - t0 < 25:
                time.sleep(1.0)
                got = "".join(chr(c) if 32 <= c < 127 else " " for c in h.ram(SB, 52)).rstrip()
                if "making" in got:
                    break
            it_now, cd_now = rec_state()
            ok_pcts = {min(99, max(0, (T - c) * 100 // T)) for c in (cd, cd_now)}
            m2 = re.match(r"^[A-Za-z' -]+: making ([a-z]+) \((\d+)%\)$", got)
            line(f"item {item_w:#x} in the making: the text follows the record", bool(m2) and m2.group(1) == names[item_w] and int(m2.group(2)) in ok_pcts,
                 f"got {got!r}, want making {names[item_w]} ({sorted(ok_pcts)} %), record item {it_now:#x} countdown {cd_now} (T {T})")
            buf2 = h.ram(BUF, 624)
            line(f"item {item_w:#x}: BUF == reference rendering of the text", buf2 == wwtt.expected_bytes(got), f"{sum(1 for x, y in zip(buf2, wwtt.expected_bytes(got)) if x != y)} of 624 bytes differ")
        wb(h, SETT + sett_off + 0xC, 0)
        wb(h, SETT + sett_off + 0x10, 0)
        # ---- build mode
        wb(h, 0x5A836, 0x0E)
        h.goto_st(px, py)
        t0 = time.time()
        txt2 = ""
        while time.time() - t0 < 25:
            time.sleep(1.5)
            sbb = h.ram(SB, 64)
            txt2 = "".join(chr(c) if 32 <= c < 127 else " " for c in sbb[:52]).rstrip()
            if txt2.startswith("Build here"):
                break
        post = h.peekw(0x5574E + h.peekw(0x5A834) + 0x3C)
        pp = (post - 2) if 2 <= post <= 4 else 1
        wantb = {0: "tanks (3 swords)", 1: "planes (2 swords)", 2: "rifles (1 sword)"}[pp]
        has_ws = False
        a_ = int.from_bytes(sr[2:4], "big")
        hb = h.ram(HOUSE_LO, HOUSE_HI - HOUSE_LO)
        while a_:
            if hb[a_ + 7] == 7:
                has_ws = True
                break
            a_ = int.from_bytes(hb[a_ + 8:a_ + 10], "big")
        wantb = ("Build here: " + wantb) if has_ws else "Build here: no workshop here"
        line("Build icon selected: the hover says what Build would make here", txt2 == wantb, f"got '{txt2}' want '{wantb}' (posture word {post}, workshop {has_ws})")
        wb(h, 0x5A836, 0)
        print(f"CELL DONE hover {tag}: {'OK' if ok else 'FAIL'}", flush=True)
        return 0 if ok else 2
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main())
