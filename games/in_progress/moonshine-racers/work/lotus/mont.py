import sys
from PIL import Image
out=sys.argv[1]; names=sys.argv[2:]
ims=[Image.open(f'shots/{n}.png').crop((96,58,736,458)).resize((416,260)) for n in names]
m=Image.new('RGB',(832,260*((len(ims)+1)//2)))
for i,im in enumerate(ims): m.paste(im,((i%2)*416,(i//2)*260))
m.save(f'shots/{out}.png')
