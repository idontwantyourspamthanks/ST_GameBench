"""Unicorn 68000 model of the Moonshine Racers race pass (private to MSRExtrap).
Loads a 1 MB RAM dump taken at pc=$7a88 (pass start), runs ranges of game code, records reads/writes on request."""
import struct, sys
from unicorn import *
from unicorn.m68k_const import *

IO_BASE, IO_SIZE = 0xFF8000, 0x8000

class Emu:
    def __init__(self, dump, regs=None):
        self.uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        try:
            self.uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
        except Exception as e:
            print("cpu model:", e)
        self.uc.mem_map(0, 0x100000)
        self.uc.mem_map(IO_BASE, IO_SIZE)
        self.uc.mem_map(0xFFFF8000, 0x8000)
        def bad(uc, access, addr, size, value, ud):
            print('UNMAPPED', access, hex(addr), size, 'pc', hex(uc.reg_read(UC_M68K_REG_PC)))
            return False
        self.uc.hook_add(UC_HOOK_MEM_UNMAPPED, bad)
        self.uc.mem_write(0, open(dump, "rb").read()[:0x100000])
        self.uc.reg_write(UC_M68K_REG_SR, 0x2300)
        self.uc.reg_write(UC_M68K_REG_A7, 0x77ffc)
        self.rd = None; self.wr = None
        self.hooks = []
        self.icount = 0

    # memory helpers
    def b(self, a): return self.uc.mem_read(a, 1)[0]
    def w(self, a): return struct.unpack(">H", self.uc.mem_read(a, 2))[0]
    def l(self, a): return struct.unpack(">I", self.uc.mem_read(a, 4))[0]
    def sw(self, a): return struct.unpack(">h", self.uc.mem_read(a, 2))[0]
    def read(self, a, n): return bytes(self.uc.mem_read(a, n))
    def setb(self, a, v): self.uc.mem_write(a, bytes([v & 255]))
    def setw(self, a, v): self.uc.mem_write(a, struct.pack(">H", v & 0xffff))
    def setl(self, a, v): self.uc.mem_write(a, struct.pack(">I", v & 0xffffffff))
    def write(self, a, d): self.uc.mem_write(a, bytes(d))

    def trace(self, on=True):
        if on and not self.hooks:
            self.rd = {}; self.wr = {}
            def hk(uc, access, addr, size, value, ud):
                if access == UC_MEM_READ:
                    self.rd[addr] = self.rd.get(addr, 0) + 1
                    if size > 1: self.rd[addr+1] = self.rd.get(addr+1, 0)+1
                    if size > 2:
                        for i in range(2, size): self.rd[addr+i] = self.rd.get(addr+i, 0)+1
                else:
                    for i in range(size): self.wr[addr+i] = self.wr.get(addr+i, 0)+1
            self.hooks.append(self.uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, hk))
        elif not on:
            for h in self.hooks: self.uc.hook_del(h)
            self.hooks = []

    def run(self, start, until, maxins=20_000_000):
        """Run from `start` until PC == `until` (not executed). Entering a stage means the previous insn was a jsr/fallthrough."""
        self.uc.ctl_flush_tb()
        self.uc.emu_start(start, until, count=maxins)
        pc = self.uc.reg_read(UC_M68K_REG_PC)
        if pc != until:
            raise RuntimeError(f"stopped at {pc:#x}, wanted {until:#x} (a7={self.uc.reg_read(UC_M68K_REG_A7):#x})")
        return pc

    def call(self, addr, maxins=20_000_000):
        """Call a subroutine at addr like jsr; returns when it returns."""
        sp = self.uc.reg_read(UC_M68K_REG_A7)
        ret = 0x7bf0  # any address we don't execute; put a stop marker
        sp -= 4
        self.uc.mem_write(sp, struct.pack(">I", ret))
        self.uc.reg_write(UC_M68K_REG_A7, sp)
        self.uc.ctl_flush_tb()
        self.uc.emu_start(addr, ret, count=maxins)
        pc = self.uc.reg_read(UC_M68K_REG_PC)
        assert pc == ret, hex(pc)

if __name__ == "__main__":
    e = Emu(sys.argv[1])
    import time
    t = time.time()
    e.run(0x7a88, 0x7b74)
    print("ran pass body in", time.time() - t, "s")
    print("100e", e.w(0x100e), "5ff8", e.w(0x5ff8), "130c", e.w(0x130c))
