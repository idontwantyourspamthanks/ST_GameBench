"""Run Hatari with the debugger on stdin: python3 dbg.py IMG EXCEPT SECS [extra hatari args]  -> prints debugger transcript."""
import os, subprocess, sys, threading, time, tempfile, shutil, queue
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[6] / "tools"))
from stharness import Hatari, TOS
img, exc, secs = sys.argv[1], sys.argv[2], int(sys.argv[3])
extra = sys.argv[4:]
work = Path(tempfile.mkdtemp(prefix="pmdbg-"))
shutil.copy(img, work / "hd.img")
n = Hatari._reserve_display()
env = dict(os.environ, DISPLAY=f":{n}", SDL_VIDEODRIVER="x11", SDL_AUDIODRIVER="dummy")
xv = subprocess.Popen(["Xvfb", f":{n}", "-screen", "0", "1024x768x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.5)
args = ["hatari", "--confirm-quit", "no", "--machine", "tt", "--tos", str(TOS["3.06"]), "--memsize", "4096", "--monitor", "vga",
        "--cpuclock", "32", "--mmu", "true", "--gemdos-drive", "skip", "--acsi", f"0={work/'hd.img'}", "--sound", "off",
        "--fast-boot", "yes", "--debug", "--debug-except", exc] + extra
p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, text=True, bufsize=1)
q = queue.Queue()
def rd():
    for line in p.stdout:
        q.put(line)
    q.put(None)
threading.Thread(target=rd, daemon=True).start()
def drain(t=1.0):
    out = []
    end = time.time() + t
    while time.time() < end:
        try:
            l = q.get(timeout=0.2)
        except queue.Empty:
            continue
        if l is None:
            break
        out.append(l)
    return "".join(out)
def cmd(c, t=0.8):
    p.stdin.write(c + "\n"); p.stdin.flush()
    return drain(t)
try:
    t0 = time.time()
    import re
    n = 0
    while time.time() - t0 < secs and n < int(os.environ.get("MAXN", "60")):
        s = drain(4.0)
        m = re.findall(r"(Bus error exception at 0x[0-9a-f]+|Address error exception at 0x[0-9a-f]+)", s)
        v = re.findall(r"VBL=(\d+)", s)
        if not s:
            continue
        n += 1
        pc = int(m[-1].split("0x")[1], 16) if m else 0
        print(n, m, v, flush=True)
        if os.environ.get("STOPPC") and pc and (pc >= int(os.environ["STOPPC"], 16)) and pc < 0xe00000 or (os.environ.get("STOPN") and n == int(os.environ["STOPN"])):
            print(s)
            for c in os.environ.get("DBGCMDS", "r").split(";"):
                print(f"--- {c}")
                print(cmd(c, 1.2))
            break
        p.stdin.write("c\n"); p.stdin.flush()
finally:
    p.kill(); xv.kill()
    shutil.rmtree(work, ignore_errors=True)
