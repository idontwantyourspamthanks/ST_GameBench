import re
CYC = 160256

def parse(path):
    import gzip, os
    txt = (gzip.open(path + ".gz", "rt", errors="replace") if (not os.path.exists(path) and os.path.exists(path + ".gz")) else open(path, errors="replace")).read()
    blocks = txt.split("Reading debugger commands from")[1:]
    ev = []
    last_pc = None
    # pc line precedes each "Reading": find via regex on the text preceding; easier: split on header lines
    parts = re.split(r"\n\t(pc = \$[0-9a-f]+) :trace :file [^\n]*\nReading debugger commands from[^\n]*\n", txt)
    # parts: [pre, pcline, body, pcline, body...]
    for i in range(1, len(parts) - 1, 2):
        pc = int(parts[i].split("$")[1], 16)
        body = parts[i + 1]
        vals = re.findall(r"#(\d+) \(dec\)", body)
        if len(vals) < 3: continue
        e = {"pc": pc, "tag": int(vals[0]), "vbl": int(vals[1]), "fc": int(vals[2])}
        if len(vals) > 3: e["a2"] = int(vals[3])
        regs = {}
        for m in re.finditer(r"\b([DA][0-7]) ([0-9A-F]{8})", body):
            regs[m.group(1).lower()] = int(m.group(2), 16)
        m = re.search(r"USP\s+([0-9A-F]{8}) ISP\s+([0-9A-F]{8})", body)
        if m: regs["isp"] = int(m.group(2), 16)
        e["r"] = regs
        mem = bytearray()
        for m in re.finditer(r"^([0-9A-F]{8}): ((?:[0-9a-f]{2} ?)+)", body, re.M):
            mem += bytes.fromhex(m.group(2).replace(" ", ""))
        e["mem"] = bytes(mem)
        ev.append(e)
    # absolute time via wrap fit
    c0best = None
    cands = sorted({e["fc"] for e in ev}) + [CYC]
    # events are in time order: choose c0 minimizing violations
    best = None
    for c0 in cands[:: max(1, len(cands) // 400)]:
        t = [(e["vbl"] + (1 if e["fc"] < c0 else 0)) * CYC + e["fc"] for e in ev]
        bad = sum(1 for i in range(1, len(t)) if t[i] < t[i - 1])
        if best is None or bad < best[0]: best = (bad, c0)
    c0 = best[1]
    for e in ev:
        e["t"] = (e["vbl"] + (1 if e["fc"] < c0 else 0)) * CYC + e["fc"]
    return ev, best
