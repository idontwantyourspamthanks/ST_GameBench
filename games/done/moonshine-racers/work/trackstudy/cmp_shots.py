import sys, numpy as np
from PIL import Image, ImageChops
a, b, out = sys.argv[1:4]
A = Image.open(a).convert('RGB'); B = Image.open(b).convert('RGB')
d = np.array(ImageChops.difference(A, B)).sum(axis=2)
# game area: the 640x400 ST screen starts at (96,58) in the 832x588 Hatari window
roi = d[58:458, 96:736]
ys, xs = np.nonzero(roi)
print('differing pixels in game area:', len(ys), 'rows', (ys.min()+58, ys.max()+58) if len(ys) else None, 'cols', (xs.min()+96, xs.max()+96) if len(ys) else None)
# side-by-side with diff marker
W, H = A.size
C = Image.new('RGB', (W*3, H)); C.paste(A, (0, 0)); C.paste(B, (W, 0))
m = np.zeros((H, W, 3), np.uint8); m[d > 0] = (255, 0, 0); C.paste(Image.fromarray(m), (2*W, 0)); C.save(out)
