import sys, numpy as np
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/work/hud/build'); sys.path.insert(0, '.')
from emuhud import idx_img, PAL, PALR
from ana import load
from PIL import Image, ImageDraw
def rgb(buf, swrow=74):
    idx = idx_img(buf); out = np.zeros((200, 320, 3), np.uint8)
    for y in range(200):
        pal = PAL if y < swrow else PALR
        for i, v in pal.items(): out[y][idx[y] == i] = [((v >> s) & 7) * 36 for s in (8, 4, 0)]
    return out
def panel(F, byidx, i, d):
    f = byidx[i]; g = byidx[i - d]
    img = rgb(f['final']).astype(np.float32)
    gi = np.frombuffer(g['final'], np.uint8).reshape(200, 160); fx = np.frombuffer(f['exit'], np.uint8).reshape(200, 160)
    ov = np.zeros((200, 320, 3), np.float32); a = np.zeros(200)
    for k in range(len(f['recs'])):
        row = 199 - k
        same = k < len(g['recs']) and g['recs'][k] == f['recs'][k]
        clean = (gi[row] == fx[row]).all()
        col = (0, 255, 0) if (same and clean) else (0, 120, 255) if same else (255, 0, 0)
        ov[row, :, :] = col
        a[row] = 0.45
        if same and not clean:      # mark the dirty 16-px slots darker blue, others light blue
            pass
    A = a[:, None, None]
    out = (img * (1 - A) + ov * A).astype(np.uint8)
    n = len(f['recs']); ns = sum(1 for k in range(n) if k < len(g['recs']) and g['recs'][k] == f['recs'][k])
    nc = sum(1 for k in range(n) if k < len(g['recs']) and g['recs'][k] == f['recs'][k] and (gi[199 - k] == fx[199 - k]).all())
    return Image.fromarray(out).resize((640, 400), Image.NEAREST), n, ns, nc
F, nx, w = load('res/c_start_zig_x3.pkl'); by = {f['idx']: f for f in F}
i = 402
while by[i]['kind'] != 'extra' or by[i]['j'] != 2: i += 1
P = []
for d, lab in ((2, 'gap 0.50 tick (dest = frame i-2 of a 3-per-tick run)'), (4, 'gap 1.25-1.50 tick (8 MHz-like)')):
    im, n, ns, nc = panel(F, by, i, d); dr = ImageDraw.Draw(im); dr.text((4, 4), f'{lab}: road rows {n}, record equal {ns}, clean {nc}', fill=(255, 255, 255)); P.append(im)
W = Image.new('RGB', (1280, 400)); W.paste(P[0], (0, 0)); W.paste(P[1], (640, 0)); W.save('mock_leverD_rows.png'); print('ok', i)
