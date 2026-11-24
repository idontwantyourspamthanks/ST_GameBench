import sys
sys.path.insert(0,'../../tools')
from planar import decode
from pix3 import *
from PIL import Image
dump, kind, ntest, p0, tag = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
e = Emu(dump); apply_live(e); e.setb(0xB8F21, ntest)
shots = []
def hk(uc, addr, size, ud):
    b = struct.unpack('>I', uc.mem_read(0x1008, 4))[0]
    shots.append((len(shots), e.w(0x100e), bytes(uc.mem_read(b, 0x7d00)), e.w(0x130c), e.w(0x5ff8)))
e.uc.hook_add(UC_HOOK_CODE, hk, begin=0xd1ca, end=0xd1cb)
for p in range(p0 + 2):
    v = schedule(p, kind)
    if v is not None: e.setb(0x6105, v)
    e.setb(0xB8F08,0); e.setl(0xB8F00,36*(p+1))
    if p == p0: shots.clear()
    e.run(0x7a88, 0x7b7a); e.run(0x7b7a, 0x7a88)
    if p == p0 + 1: break
# frames: main p0, extras..., main p0+1
print(len(shots), "frames captured; counters", [(s[0], s[1]) for s in shots])
imgs = [decode(s[2]) for s in shots]
W = 320 * 2; H = 200 * 2
sheet = Image.new("RGB", (W * 3, H * ((len(imgs) + 2) // 3)))
for i, im in enumerate(imgs):
    sheet.paste(im.resize((W, H), Image.NEAREST), ((i % 3) * W, (i // 3) * H))
sheet.save(f'ab/{tag}_sheet.png')
for i, im in enumerate(imgs): im.save(f'ab/{tag}_f{i}.png')
# corner crop strip: road centre rows 120-199, x 100-220
crop = (90, 100, 250, 200)
strip = Image.new("RGB", ((crop[2]-crop[0]) * 3 * len(imgs), (crop[3]-crop[1]) * 3))
for i, im in enumerate(imgs): strip.paste(im.crop(crop).resize(((crop[2]-crop[0])*3, (crop[3]-crop[1])*3), Image.NEAREST), (i * (crop[2]-crop[0]) * 3, 0))
strip.save(f'ab/{tag}_strip.png')
