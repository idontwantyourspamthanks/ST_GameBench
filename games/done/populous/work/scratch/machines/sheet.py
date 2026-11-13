import sys
from PIL import Image
out=sys.argv[1]; files=sys.argv[2:]
cols=3
ims=[Image.open(f).convert("RGB") for f in files]
w,h=ims[0].size; s=0.5
W=Image.new("RGB",(int(w*s)*cols,int(h*s)*((len(ims)+cols-1)//cols)))
for i,im in enumerate(ims):
    W.paste(im.resize((int(w*s),int(h*s))),((i%cols)*int(w*s),(i//cols)*int(h*s)))
W.save(out)
