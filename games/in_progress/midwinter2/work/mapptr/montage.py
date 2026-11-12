import sys, glob
from PIL import Image
d=sys.argv[1]; fs=sorted(glob.glob(d+'/*.png')); 
cols=5; rows=(len(fs)+cols-1)//cols
W=Image.new('RGB',(cols*280,rows*185))
for i,f in enumerate(fs):
    im=Image.open(f).convert('RGB').crop((96,58,736,458)).resize((280,175))
    W.paste(im,((i%cols)*280,(i//cols)*185))
W.save(d+'_montage.png'); print(len(fs))
