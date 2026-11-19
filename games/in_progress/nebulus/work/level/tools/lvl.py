"""Nebulus tower-map decoder (from disasm of $377a2). RAM-image based; see work/notes/level.md."""
import struct
BASE=0x33b1c  # RAM address of unpacked-file offset 28
def load_img(path='/tmp/neb_reloc.bin'):
    return open(path,'rb').read()
def decode(img, a3, tower):
    """img = relocated text+data (RAM $33b1c..). returns (cols, grid[row][col], offs)"""
    def b(a): return img[a-BASE]
    t=a3+0x1000+tower
    off=(b(t+8)<<8)|b(t)
    ncols=b(t+0x10)
    mask=a3+tower*0x200
    s=a3+off
    grid=[[0]*256 for _ in range(16)]
    mp=mask
    for c in range(ncols+1):
        for half in range(2):
            m=b(mp); mp+=1
            for bit in range(8):
                if m&(1<<bit):
                    grid[half*8+bit][c]=b(s); s+=1
    return ncols+1, grid, off, s

def cell_addr(img, a3, tower, ang, h):
    """RAM address of the stream byte for grid cell (angle 0..15, height h), or None if the mask bit is clear."""
    def b(a): return img[a-BASE]
    t=a3+0x1000+tower
    off=(b(t+8)<<8)|b(t); s=a3+off; mp=a3+tower*0x200
    for c in range(b(t+0x10)+1):
        for half in range(2):
            m=b(mp); mp+=1
            for bit in range(8):
                if m&(1<<bit):
                    if c==h and half*8+bit==ang: return s
                    s+=1
    return None
