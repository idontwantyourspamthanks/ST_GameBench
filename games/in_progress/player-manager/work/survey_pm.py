"""Deep architectural survey of Player Manager (Task 1 & Task 2)."""
from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000
ram = open('games/in_progress/player-manager/work/setup_ram.bin', 'rb').read()
md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000)
a4 = 0x2969a

refs = {
    'div_sizes(-70b2)': [],
    'team_ptrs(-2e94..-2e88)': [],
    'player_pool(-2e80)': [],
    'count_44(2c/2b)': [],
    'pool_1500(5db/5dc/f617)': [],
    'div_quotas(-7d22)': [],
    'squad_counts(-77f4)': [],
}

p = 0x10000
while p < 0x2169c:
    got = False
    for i in md.disasm(ram[p:0x2169c], p):
        got = True
        s = f'{i.mnemonic} {i.op_str}'
        if '-$70b2(a4)' in s: refs['div_sizes(-70b2)'].append((i.address, s))
        if any(x in s for x in ['-$2e94(a4)', '-$2e90(a4)', '-$2e8c(a4)', '-$2e88(a4)']):
            refs['team_ptrs(-2e94..-2e88)'].append((i.address, s))
        if '-$2e80(a4)' in s: refs['player_pool(-2e80)'].append((i.address, s))
        if '#$2c,' in s or '#$2b,' in s: refs['count_44(2c/2b)'].append((i.address, s))
        if any(x in s for x in ['#$5db', '#$5dc', '#$f617', '#$f618']):
            refs['pool_1500(5db/5dc/f617)'].append((i.address, s))
        if '-$7d22(a4)' in s: refs['div_quotas(-7d22)'].append((i.address, s))
        if '-$77f4(a4)' in s: refs['squad_counts(-77f4)'].append((i.address, s))
        p = i.address + i.size
    if not got:
        p += 2

for k, v in refs.items():
    print(f'=== {k}: {len(v)} refs ===')
    for addr, s in v[:20]:
        print(f'  {addr:06x}: {s}')
    if len(v) > 20:
        print(f'  ... (+{len(v)-20} more)')

# Also find Malloc calls (trap #1 with #$48) in $10000..$2169c to map all heap allocations!
print('\n=== Malloc ($48) calls in PM ===')
p = 0x10000
prev = []
while p < 0x2169c:
    got = False
    for i in md.disasm(ram[p:0x2169c], p):
        got = True
        prev.append((i.address, f'{i.mnemonic} {i.op_str}'))
        if len(prev) > 6: prev.pop(0)
        if i.mnemonic == 'trap' and i.op_str == '#$1':
            if any('#$48' in x[1] for x in prev[-3:]):
                print('  ---')
                for a, st in prev:
                    print(f'    {a:06x}: {st}')
        p = i.address + i.size
    if not got:
        p += 2

# Find where football.asm code starts/ends! Check references to 0x19072 ('football.asm') and FBGRAPH
print('\n=== Match engine code boundary hints ===')
for label, needle in [('FBGRAPH.PI1', 0x255b4), ('SAMPLES.DAT', 0x24924), ('football.asm', 0x19072)]:
    off = needle - a4
    print(f'  {label} at {needle:06x} (a4{off:+#x})')
