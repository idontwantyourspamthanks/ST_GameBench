import sys,glob
from PIL import Image, ImageDraw
pre=sys.argv[1]; out=sys.argv[2]
fs=sorted(glob.glob(f'tl/{pre}_*.png'))
step=int(sys.argv[3]) if len(sys.argv)>3 else 1
fs=fs[::step]
w,h=416,294
cols=4; rows=(len(fs)+cols-1)//cols
im=Image.new('RGB',(cols*w,rows*h))
for i,f in enumerate(fs):
    a=Image.open(f).convert('RGB').crop((0,0,832,588)).resize((w,h))
    ImageDraw.Draw(a).text((4,4),f.split('_')[-1][:3],fill=(255,255,0))
    im.paste(a,((i%cols)*w,(i//cols)*h))
im.save(out)
print(len(fs))
