import sys, subprocess, shutil; sys.path.insert(0,'tools')
import poppatch as pp
name, mode = sys.argv[1], sys.argv[2]
orig = pp.runme_segments
def f(img, ranges):
    segs = orig(img, ranges)
    if mode == "none": return []
    if mode == "first": return segs[:1]
    if mode == "all": return segs
    if mode.startswith("n"): return segs[:int(mode[1:])]
    if mode.startswith("s"): return segs[int(mode[1:]):int(mode[1:])+1]
    raise SystemExit(mode)
pp.runme_segments = f
ps=pp.load_patches(); fp=pp.load_file_patches()
sel=[p for p in ps if p.default and p.media in (None,'hd')]; fsel=[p for p in fp if p.default]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    pp.cmd_build(sel, pp.ROOT/f'build/PopRelease/hd_{name}', fsel)
print(name, mode, (pp.ROOT/f'build/PopRelease/hd_{name}/RUNME.TOS').stat().st_size)
