import sys
from PIL import Image
d = sys.argv[1]; out = sys.argv[2]; tags = sys.argv[3:]
cols = 4; rows = (len(tags)+cols-1)//cols
W = Image.new('RGB', (cols*480, rows*300))
for i, t in enumerate(tags):
    im = Image.open(f'{d}/{t}.png').convert('RGB').crop((0,0,640,400)).resize((480,300))
    W.paste(im, ((i%cols)*480, (i//cols)*300))
W.save(out)
