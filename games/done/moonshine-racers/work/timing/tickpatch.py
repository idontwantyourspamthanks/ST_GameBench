import sys; sys.path.insert(0, '.')
from live import assemble
def j4(a): return b"\x4e\xb9" + a.to_bytes(4, "big")
def build(tick=36, src="tick.s"):
    blob, sy = assemble(0xb8000, open(src).read(), f"TICK equ {tick}\nMAXLAG equ {2*tick}", syms=True)
    sites = [(0xd128, j4(sy["vblclk"])), (0x7b74, j4(sy["newsync"])), (0x7b0a, j4(sy["pre17c42"]))]
    return [(0xb8000, blob)], sites, sy
def sync_only(src="sync.s"):
    """D = wait moved + raster copy moved;  E (src="sync2.s") = wait moved, copy left in place."""
    blob, sy = assemble(0xb8000, open(src).read(), syms=True)
    sites = [(0xd1e4, j4(sy["sync"])), (0x7b0a, j4(sy["wait"])), (0xd128, j4(sy["vbl"]))]
    return [(0xb8000, blob)], sites, sy
