"""Hatari helpers for MSRMxFast (private tool builds, snapshots, counters)."""
import sys, json, re, time
from mflib import *
sys.path.insert(0, GAME + '/work/timing'); sys.path.insert(0, GAME + '/tools'); sys.path.insert(0, GAME + '/work/int/mx')
from live import apply_live as _apply
from msr import Moonshine, SNAP as SNAPDIR
def open_snap(name, mhz=8, **kw):
    h = Moonshine(snapshot=str(SNAPDIR / name), **kw)
    time.sleep(3)
    if mhz: h.set_cpuclock(mhz)
    return h
def apply_prefix(h, prefix, pokes=(), at_pc=0x7a88):
    spec = json.load(open(prefix + '.json')); img = open(prefix + '.img', 'rb').read()
    sites = [(s['addr'], bytes.fromhex(s['new'])) for s in spec['sites']] + list(pokes)
    return _apply(h, [(spec['img_base'], img)], sites, at_pc=at_pc)
def mem_parse(txt):
    g = {}
    for ln in txt.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
    return g
