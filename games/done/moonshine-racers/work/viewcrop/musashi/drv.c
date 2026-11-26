#include <stdint.h>
#include <string.h>
#include "m68k.h"
#define RAMSZ 0x200000
static uint8_t ram[RAMSZ];
static uint32_t wrcount_dummy;
unsigned int m68k_read_memory_8(unsigned int a){ return ram[a & (RAMSZ-1)]; }
unsigned int m68k_read_memory_16(unsigned int a){ a&=RAMSZ-1; return (ram[a]<<8)|ram[a+1]; }
unsigned int m68k_read_memory_32(unsigned int a){ a&=RAMSZ-1; return ((unsigned)ram[a]<<24)|(ram[a+1]<<16)|(ram[a+2]<<8)|ram[a+3]; }
unsigned int m68k_read_disassembler_8(unsigned int a){ return m68k_read_memory_8(a);} 
unsigned int m68k_read_disassembler_16(unsigned int a){ return m68k_read_memory_16(a);} 
unsigned int m68k_read_disassembler_32(unsigned int a){ return m68k_read_memory_32(a);} 
void m68k_write_memory_8(unsigned int a, unsigned int v){ ram[a&(RAMSZ-1)]=v; }
void m68k_write_memory_16(unsigned int a, unsigned int v){ a&=RAMSZ-1; ram[a]=v>>8; ram[a+1]=v; }
void m68k_write_memory_32(unsigned int a, unsigned int v){ a&=RAMSZ-1; ram[a]=v>>24; ram[a+1]=v>>16; ram[a+2]=v>>8; ram[a+3]=v; }
uint8_t *ram_ptr(void){ return ram; }
void cpu_init(void){ m68k_init(); m68k_set_cpu_type(M68K_CPU_TYPE_68000); m68k_pulse_reset(); }
void set_reg(int r, unsigned v){ m68k_set_reg(r, v); }
unsigned get_reg(int r){ return m68k_get_reg(NULL, r); }
/* run from pc until pc == stop (checked per instruction via small slices); returns cycles */
static unsigned long pcyc[0x80000], pcnt[0x80000];
void prof_clear(void){ memset(pcyc,0,sizeof pcyc); memset(pcnt,0,sizeof pcnt); }
unsigned long *prof_cyc(void){ return pcyc; }
unsigned long *prof_cnt(void){ return pcnt; }
static unsigned tr_pc[200000]; static int tr_cyc[200000]; static long tr_n=0, tr_on=0;
void trace_set(int on){ tr_on=on; tr_n=0; }
long trace_len(void){ return tr_n; }
unsigned *trace_pcs(void){ return tr_pc; }
int *trace_cycs(void){ return tr_cyc; }
long run_until(unsigned pc, unsigned stop, long maxcyc){
  m68k_set_reg(M68K_REG_PC, pc); m68k_set_reg(M68K_REG_SR, 0x2700);
  long total=0;
  while(total<maxcyc){
    if(m68k_get_reg(NULL,M68K_REG_PC)==stop) return total;
    { unsigned cur = m68k_get_reg(NULL,M68K_REG_PC); int c = m68k_execute(1); total += c; if(tr_on && tr_n<200000){ tr_pc[tr_n]=cur; tr_cyc[tr_n]=c; tr_n++; } if(cur<0x100000){ pcyc[cur>>1]+=c; pcnt[cur>>1]++; } }
  }
  return -1;
}
