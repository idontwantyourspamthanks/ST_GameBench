from trace import *
m=Machine(floppies=disks())
with Session(m) as s:
    boot_to_mwii(s)
    s.run_to(58)
    s.save_state(STATES+'t58.clstate')
    # runtime address of the variables from the code operands
    base=0x24cd9c-0x3065c
    print('base0',hex(base))
    g=lambda flat,off=2: s.read_l(base+flat+off)
    cur=g(0x25aea)     # cmp.w $60a8e,d0
    print('cur tune var', hex(cur))
