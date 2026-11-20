"""Run the game's own ICE depacker ($8824..$8a52 in the race RAM image) in machine68k."""
import machine68k as m, struct
RAM=open('/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/amiga/ram_race_a.bin','rb').read()
CODE=RAM[0x8824:0x8a60]
def unpack(blob):
    assert blob[:4]==b'Ice!'
    ps,os_=struct.unpack('>II',blob[4:12])
    mach=m.Machine(m.CPUType.M68000,2048)  # 2 MiB
    mem=mach.mem; cpu=mach.cpu
    mem.w_block(0x8824,CODE)
    BUF=0x100000
    # in-place: dest region needs os_ bytes + slack; packed placed at end alignment as game does: simple: place at BUF
    pk=blob[:ps+0]
    mem.w_block(BUF,pk+b'\0'*(os_+0x400))
    mem.w_block(0x1000,struct.pack('>HH',0x4e75,0)) # rts target
    cpu.w_reg(m.Register.A0,BUF); cpu.w_reg(m.Register.A7,0x80000)
    mem.w32(0x80000,0x1000)  # return addr
    mach.execute  # noqa
    cpu.w_pc(0x8824)
    n=0
    while cpu.r_pc()!=0x1000 and n<50_000_000:
        mach.execute(10000); n+=10000
    out=bytes(mem.r_block(BUF,os_))
    return out
if __name__=='__main__':
    import sys
    d=open('/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/alt/amiga/Moonshine Racers Disk 2.adf','rb').read()
    o=unpack(d[0:12255+12])
    print(len(o),o[:32].hex(' '))
