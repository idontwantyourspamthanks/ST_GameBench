"""Real run of tools/play.sh --keep-ovl on a private Xvfb: boot, F10 editor, Save to disk, kill Hatari, check copy-back."""
import os, subprocess, time, signal, sys, shutil
from pathlib import Path
R = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus'); W = R / 'work/release/playtest'
shutil.rmtree(W / 'home', ignore_errors=True); (W / 'home').mkdir()
ovl = W / 'home/NEBLEVEL.OVL'
D = 131
xv = subprocess.Popen(['Xvfb', f':{D}', '-screen', '0', '1024x768x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.5)
env = dict(os.environ, DISPLAY=f':{D}', SDL_VIDEODRIVER='x11', SDL_AUDIODRIVER='dummy', NEBULUS_OVL=str(ovl), HOME=str(W / 'home'))
env.pop('WAYLAND_DISPLAY', None)
def xdo(*a): return subprocess.run(['xdotool', *a], env=env, capture_output=True, text=True)
ovl.write_bytes(bytes(8192))
(W/'fifo').unlink(missing_ok=True)
log = open(W / 'play.log', 'w')
p = subprocess.Popen([str(R / 'tools/play.sh'), '--keep-ovl', '--', '--cmd-fifo', str(W / 'fifo')], env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
try:
    win = None
    for _ in range(300):
        ids = xdo('search', '--name', 'Hatari').stdout.split()
        if ids: win = ids[0]; break
        time.sleep(0.5)
    print('window', win)
    xdo('windowfocus', win); xdo('mousemove', '--window', win, '416', '294')
    t0=time.time(); found=False
    def fifo(c): open(W / 'fifo', 'w').write(c + '\n')
    while time.time()-t0 < 120:
        time.sleep(2)
        n0 = len(open(W/'play.log').read())
        fifo('hatari-debug m $3d00f 4'); time.sleep(0.6)
        if '48 69 67 68' in open(W/'play.log').read()[n0:].upper(): found=True; break
        if time.time()-t0 < 20: xdo('key','--window',win,'space')
    print('title marker', found, '%.0fs' % (time.time()-t0))
    time.sleep(2)
    def key(k, hold=0.5):
        xdo('keydown', '--window', win, k); time.sleep(hold); xdo('keyup', '--window', win, k); time.sleep(0.7)
    key('F10', 1.0); time.sleep(2.5)
    xdo('import') if False else None
    subprocess.run(['import', '-window', 'root', str(W / 'ed0.png')], env=env)
    for _ in range(3): key('Down', 0.4)
    subprocess.run(['import', '-window', 'root', str(W / 'ed05.png')], env=env)
    key('Control_R', 0.5); time.sleep(3)
    subprocess.run(['import', '-window', 'root', str(W / 'ed1.png')], env=env)
finally:
    # find the hatari child of this session and terminate it so play.sh continues to the copy-back
    subprocess.run(['pkill', '-TERM', '-P', str(p.pid), 'hatari'])
    try: p.wait(timeout=30)
    except Exception: p.kill()
    xv.terminate()
print(open(W / 'play.log').read()[-1500:])
print('ovl size', ovl.stat().st_size, 'head', ovl.read_bytes()[:16].hex(), 'nonzero', sum(1 for b in ovl.read_bytes() if b))
