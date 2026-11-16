import sys; sys.path.insert(0,'work/hud')
from PIL import Image, ImageDraw
B=[('1 thermometer (efc6)',(0,18,31,64),(255,60,60)),('2 minimap (f214+f22c)',(16,15,95,64),(255,255,0)),('3 dial (f53c)',(80,16,111,46),(0,255,255)),
   ('4 position no. (f430)',(80,49,111,62),(255,128,0)),('5 score (f3b6)',(32,1,79,14),(255,0,255)),('6 text (11ef0)',(112,16,271,64),(0,255,0)),
   ('7 face (f90c)',(272,17,303,64),(0,160,255)),('8 turbo-fuel tank (f620)',(0,172,31,199),(255,255,255)),('9 speedometer (f7f0)',(256,151,319,174),(255,128,128)),
   ('10 gear lever (f76a)',(272,180,303,194),(128,255,128))]
def box(src,dst):
    im=Image.open(src).convert('RGB'); d=ImageDraw.Draw(im)
    for name,(x0,y0,x1,y1),c in B:
        X0,Y0,X1,Y1=96+2*x0-1,58+2*y0-1,96+2*(x1+1),58+2*(y1+1)
        d.rectangle((X0,Y0,X1,Y1),outline=c,width=1)
        n=name.split()[0]
        d.text((X0+2,Y0-11 if Y0>70 else Y1+1),n,fill=c)
    im.crop((96,58,736,458)).save(dst)
box('work/hud/shots/raw_grid_2.png','work/hud/shots/hud_boxed_speech.png')
box('work/hud/shots/raw_drv_1.png','work/hud/shots/hud_boxed_driving.png')
im=Image.open('work/hud/shots/hud_boxed_speech.png'); print(im.size)
