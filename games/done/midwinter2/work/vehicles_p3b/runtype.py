#!/usr/bin/env python3
"""runtype.py TYPE SCEN [SET=C] [--ticks N] : A vs SET gate for one vehicle type and input scenario; prints the vcmp summary.
SCEN: stand | move | turn | movturn | bank | movbank | allin"""
import sys, subprocess, struct, os
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
HERE = '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b'
NAMES = "Tank Jeep Truck Bus Train Foot Speedboat Crawler Minisub Submarine Ship Frogman Biplane Helicopter Zeppelin Balloon Rocket Parachute FlyingBoat Hovercraft FlyingSub Swimming".split()
SNAPS = {1:'raid_jeep_dhafra.sav',2:'raid_truck_aledo.sav',3:'raid_bus_galva.sav',5:'raid_onfoot_dhafra.sav',6:'raid_speedboat_iquitos.sav',7:'raid_crawler_panao.sav',
         9:'raid_submarine_jebba.sav',10:'raid_ship_bourem.sav',12:'raid_biplane_maracay.sav',13:'raid_helicopter_lobos.sav',15:'raid_balloon_corozal.sav',
         17:'raid_parachute_calabar.sav',18:'raid_flyingboat_vicenza.sav',19:'raid_hovercraft_thar.sav',21:'raid_swimming_vitoria.sav'}
FORCE = {0:1, 4:1, 8:9, 11:9, 14:12, 16:13, 20:18}      # forced type -> snapshot type it is poked into
d = open('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/dumps/ram_ingame_lobos.bin','rb').read()
def blk(t):
    b = d[0x54dc0+t*0x3e:0x54dc0+(t+1)*0x3e]
    w = lambda o: int.from_bytes(b[o:o+2],'big',signed=True)
    return dict(Ydz=w(4), Ylo=w(6), Yhi=w(8), Xdz=w(0x12), Xlo=w(0x14), Xhi=w(0x16))
def pokes(t, scen):
    b = blk(t); p = []
    fwd = min(b['Yhi'], b['Ydz'] + 150); turn = -(b['Xdz'] + 60)
    if turn < b['Xlo']: turn = b['Xlo']
    if b['Xhi'] == 0: turn = 0
    if 'mov' in scen or scen == 'allin':
        p.append('6fba=%08x' % ((fwd & 0xffff) << 16))
    if 'turn' in scen or scen == 'allin':
        p.append('6fb6=%08x' % ((turn & 0xffff) << 16))
    if 'bank' in scen or scen == 'allin':
        p.append('6fbe=0002')
    return p
def main():
    a = sys.argv[1:]
    t = int(a[0]); scen = a[1]; sset = 'C'; ticks = '41'; mhz = '16'
    rest = a[2:]
    while rest:
        x = rest.pop(0)
        if x == '--ticks': ticks = rest.pop(0)
        elif x == '--mhz': mhz = rest.pop(0)
        else: sset = x
    st = FORCE.get(t, t)
    snap = SNAPS[st]
    pk = pokes(t, scen)
    extra = []
    if t in FORCE: pk.append('6220=%04x' % t)
    late = []
    if scen.startswith('esc'):
        # esc<dv>: hold Esc (key table $7687) from dv VBL after the apply flip, re-poked every 4 VBL for 40 VBL
        dv0 = int(scen[3:] or 30)
        late = ['%d:7687=ff' % (dv0 + 4 * i) for i in range(10)]
        pk = []
    tag = f'{NAMES[t]}_{scen}_{mhz}'
    sync = f'/tmp/vg/{tag}.sync'
    if os.path.exists(sync): os.remove(sync)
    cmdA = ['python3', HERE + '/vgate.py', 'run', snap, tag + '_A', 'A', '--ticks', ticks, '--mhz', mhz, '--sync', sync, '--poke'] + pk + (['--late'] + late if late else [])
    cmdB = ['python3', HERE + '/vgate.py', 'run', snap, tag + '_' + sset.replace(':','_').replace(',','_')[:20], sset, '--ticks', ticks, '--mhz', mhz, '--sync', sync, '--poke'] + pk + (['--late'] + late if late else [])
    pa = subprocess.Popen(cmdA, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    pb = subprocess.Popen(cmdB, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    oa = pa.communicate()[0]; ob = pb.communicate()[0]
    print(oa.strip().splitlines()[-1], '|', ob.strip().splitlines()[-1])
    IGN = '5380-53af 6776-6777 67a6-67ac 67c0-67ff 6808-6809 6900-695f 6a00-6eff 7020-7021 7706-7707 770c-7714 77c0-77d0 18124-18140 672e-6733 6840-6860 7710-7750 53c0-53ff 682a-686f 6f7a-6fcf 7682-7683 71c0-71c3'.split()
    r = subprocess.run(['python3', HERE + '/vcmp.py', tag + '_A', tag + '_' + sset.replace(':','_').replace(',','_')[:20], '--quiet', '--ign'] + IGN, capture_output=True, text=True)
    print(f'## {NAMES[t]} ({t}) {scen} pokes {pk}\n' + r.stdout + r.stderr[-500:])
if __name__ == '__main__':
    main()
