#!/usr/bin/env python3
"""Enemies per original tower and spawn-queue pressure (work/notes/enemies.md).
Spawn order = row-major from row 0 (the game scans col 0..15 per row); max4 = max enemies that
lie within any 22-row window (the visible height = 176 px / 8)."""
import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/work/editor'.replace('/work/editor','/games/in_progress/nebulus/work/editor'))
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/level/tools')
import ovl
def enem(g, rows):
    return [(r,a,g[a][r]) for r in range(rows) for a in range(16) if not g[a][r]&0x80 and g[a][r]&0x70]
def stats(g, rows):
    e = enem(g, rows); rs=[r for r,_,_ in e]
    w = max([sum(1 for x in rs if r0<=x<r0+22) for r0 in range(rows)]+[0])
    best = max([(sum(1 for x in rs if r0<=x<r0+22),r0) for r0 in range(rows)]+[(0,0)])
    return len(e), best
if __name__=='__main__':
    for m in (1,2):
        for t in range(8):
            g,rows = ovl.original(m,t); n,(w,r0)=stats(g,rows)
            print(f"M{m} T{t+1} rows {rows} enemies {n} max-in-22-row-window {w} (rows {r0}..{r0+21})")
