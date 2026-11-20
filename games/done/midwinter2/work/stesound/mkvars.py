#!/usr/bin/env python3
"""Diagnostic variants of the v1.6 floppy set (work/stesound/, test-only; nothing here is shipped).

    python3 work/stesound/mkvars.py OUTROOT [VARIANT ...]     (default: all)

Every variant = the default v1.6 floppy patch set (`mw2patch.py build --floppy --only <every default patch minus the excluded ones>`) with, for the asn_*
variants, a bank whose blob (patches/asn/blob.s, a TEMP COPY edited here, the tracked file is never touched) is assembled with vasm and spliced into
build/asn_bank.bin at the blob's place (bank +$4800, the 6 B entry jumps keep their addresses: ORG is unchanged).  Only FFA differs from the published
v1.6 set (FFB/FFC/FFD are byte-identical for every variant), so a variant dir holds FFA only (.st + .msa).

variants
  full         v1.6 exactly (control: FFA md5 must be 25ce70a8...)
  noasn        no asn_* (YM everywhere)                                               [the Phase 0 set]
  noasn_nojag  no asn_*, no jag_* (nothing STE-specific left in the patch set)
  effects      asn_core/lvc/lv1/lv2/wd only: Amiga effects in the 3D view, the YM plays the music (no asn_mus)
  music        asn_mus + asn_wd only: Amiga music, the YM plays the effects
  nomw         full, asn_mwonce returns at once (no Microwire writes at all)
  nodma        full, the DMA is programmed but never started (`move.b #3,1(a0)` -> #0): the mixer runs, nothing plays
  nomix        full, asn_mix returns at once: the DMA plays a silent ring, the mixer's CPU load is ~0
  nosil        full, asn_ymsilence returns at once (no PSG access from the asn code at all; the 3D view's YM is not silenced)
  silmask      full, asn_ymsilence runs with sr = $2700 around its PSG sequence
  silff        full, asn_ymsilence writes $ff to PSG reg 7 (as the game's own silence $c4c) instead of read-modify-write
"""
import os, subprocess, sys, shutil, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BANK = ROOT / "build" / "asn_bank.bin"
OFF_CODE, OFF_MUS = 0x4800, 0x6000
ASN = ["asn_core", "asn_lv1", "asn_lv2", "asn_lvc", "asn_mus", "asn_wd"]
JAG = ["jag_btn", "jag_dir", "jag_poll"]


def default_floppy():
    out = subprocess.run([sys.executable, str(ROOT / "tools/mw2patch.py"), "list"], capture_output=True, text=True, check=True).stdout.splitlines()[1:]
    names = []
    for ln in out:
        f = ln.split()
        if len(f) > 2 and f[1] == "yes" and "(file patch" not in ln:      # `yes` and `yes (floppy)`; HAGA file patches are not floppy
            names.append(f[0])
    return names


def edit(src, old, new, count=1):
    assert src.count(old) == count, (old, src.count(old))
    return src.replace(old, new)


def blob_variant(kind):
    s = (ROOT / "patches/asn/blob.s").read_text()
    if kind == "nomw":
        s = edit(s, "asn_mwonce:\n", "asn_mwonce:\n        rts\n")
    elif kind == "nodma":
        s = edit(s, "        move.b  #3,1(a0)                ; play + repeat", "        move.b  #0,1(a0)                ; (diagnostic: DMA never started)")
    elif kind == "nomix":
        s = edit(s, "asn_mix:                                ; d0 = groups of 8 outputs (>=1): the ring from the write cursor; a4 = SV\n",
                 "asn_mix:\n        rts\n")
    elif kind == "nosil":
        s = edit(s, "asn_ymsilence:\n", "asn_ymsilence:\n        rts\n")
    elif kind == "silmask":
        s = edit(s, "asn_ymsilence:\n", "asn_ymsilence:\n        move.w  sr,d2\n        ori.w   #$700,sr\n")
        s = edit(s, "        move.b  d1,2(a0)\n        rts\nasn_mwonce:", "        move.b  d1,2(a0)\n        move.w  d2,sr\n        rts\nasn_mwonce:")
    elif kind == "silff":
        s = edit(s, "        move.b  #7,(a0)\n        move.b  (a0),d0\n        ori.b   #$3f,d0\n        move.b  #7,(a0)\n        move.b  d0,2(a0)\n",
                 "        move.b  #7,(a0)\n        move.b  #$ff,2(a0)\n")
    else:
        raise SystemExit(kind)
    return s


def make_bank(kind, work):
    src = work / f"blob_{kind}.s"
    src.write_text(blob_variant(kind))
    outb = work / f"blob_{kind}.bin"
    r = subprocess.run(["vasmm68k_mot", "-Fbin", "-m68000", "-quiet", "-o", str(outb), str(src)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr)
    blob = outb.read_bytes()
    assert len(blob) <= OFF_MUS - OFF_CODE, len(blob)
    b = bytearray(BANK.read_bytes())
    old_end = OFF_CODE + 0x1000
    b[OFF_CODE:OFF_MUS] = blob + bytes(OFF_MUS - OFF_CODE - len(blob))
    bp = work / f"bank_{kind}.bin"
    bp.write_bytes(bytes(b))
    return bp


SPEC = {   # name: (excluded patches, blob variant or None)
    "full": ([], None),
    "noasn": (ASN, None),
    "noasn_nojag": (ASN + JAG, None),
    "effects": (["asn_mus"], None),
    "music": (["asn_core", "asn_lv1", "asn_lv2", "asn_lvc"], None),
    "nomw": ([], "nomw"),
    "nodma": ([], "nodma"),
    "nomix": ([], "nomix"),
    "nosil": ([], "nosil"),
    "silmask": ([], "silmask"),
    "silff": ([], "silff"),
}


def build(name, outroot, work):
    excl, kind = SPEC[name]
    names = [n for n in default_floppy() if n not in excl]
    env = dict(os.environ)
    uses_asn = any(n in ASN for n in names)
    if uses_asn:
        env["MW2_BANK"] = str(make_bank(kind, work) if kind else BANK)
    else:
        env["MW2_BANK"] = "/nonexistent"
    out = Path(outroot) / name
    shutil.rmtree(out, ignore_errors=True)
    r = subprocess.run([sys.executable, str(ROOT / "tools/mw2patch.py"), "build", "--floppy", "--only", *names, "--out", str(out)],
                       capture_output=True, text=True, env=env, cwd=ROOT)
    if r.returncode:
        raise SystemExit(f"{name}: {r.stderr[-800:]}")
    import hashlib
    h = hashlib.md5((out / "FFA_boot.st").read_bytes()).hexdigest()
    print(f"{name:12s} FFA_boot.st {h}  ({len(names)} patches, asn={'yes' if uses_asn else 'no'}{', blob variant ' + kind if kind else ''})", flush=True)
    return out


if __name__ == "__main__":
    outroot = Path(sys.argv[1])
    outroot.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="mkvars-", dir="/tmp/mw2s"))
    for n in (sys.argv[2:] or list(SPEC)):
        build(n, outroot, work)
