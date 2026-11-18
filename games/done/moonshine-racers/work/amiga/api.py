from cl import *
m=machine()
with Session(m) as s:
    s.run_to(1)
    for meth,p in (('media.floppy.query',{}),('media.floppy.query',{'drive':0}),('media.floppy.query',{'unit':0})):
        try: r=s.call(meth,**p); print(meth,p,'OK',str(r)[:600])
        except Exception as e: print(meth,p,'ERR',str(e)[:400])
    for p in ({'drive':0,'path':'x'},{'unit':0,'path':'x'},{'df':0,'path':'x'}):
        try: r=s.call('media.floppy.insert',**p); print(p,'OK',str(r)[:600])
        except Exception as e: print(p,'ERR',str(e)[:400])
