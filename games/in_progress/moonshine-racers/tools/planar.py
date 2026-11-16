#!/usr/bin/env python3
"""Convert a 32000-byte ST low-res planar screen dump to PNG (320x200, ST palette words)."""
import sys
from PIL import Image
# palette B = $ff8240 while the road area is drawn ($3cf2 table), palette A = HUD/sky set at $3cd4 (the game switches by timer B)
PAL_GAME = [0x000, 0x000, 0x222, 0x333, 0x500, 0x630, 0x421, 0x541, 0x131, 0x210, 0x552, 0x444, 0x223, 0x666, 0x532, 0x457]
PAL_HUD = [0x000, 0x111, 0x000, 0x754, 0x333, 0x330, 0x664, 0x666, 0x221, 0x432, 0x543, 0x765, 0x410, 0x550, 0x667, 0x000]
SPLIT = 91


def decode(data: bytes, pal=PAL_GAME, pal2=PAL_HUD, split=SPLIT):
    cv = lambda pl: [((p >> 8 & 7) * 36, (p >> 4 & 7) * 36, (p & 7) * 36) for p in pl]
    rgbA, rgbB = cv(pal2), cv(pal)
    img = Image.new("RGB", (320, 200))
    px = img.load()
    for y in range(200):
        rgb = rgbA if y < split else rgbB
        row = data[y * 160:(y + 1) * 160]
        for c in range(20):
            w = [int.from_bytes(row[c * 8 + 2 * p:c * 8 + 2 * p + 2], "big") for p in range(4)]
            for b in range(16):
                v = sum(((w[p] >> (15 - b)) & 1) << p for p in range(4))
                px[c * 16 + b, y] = rgb[v]
    return img


if __name__ == "__main__":
    decode(open(sys.argv[1], "rb").read()[:32000]).save(sys.argv[2])
