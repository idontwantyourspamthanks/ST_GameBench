import sys
from PIL import Image
a, b, out = sys.argv[1:4]
tt = len(sys.argv) > 4 and sys.argv[4] == 'tt'
box = (0,0,640,400) if tt else (96,58,736,458)
A = Image.open(a).convert('RGB').crop(box); B = Image.open(b).convert('RGB').crop(box)
W = Image.new('RGB', (1290, 400), (255,0,255)); W.paste(A, (0,0)); W.paste(B, (650,0)); W.save(out)
