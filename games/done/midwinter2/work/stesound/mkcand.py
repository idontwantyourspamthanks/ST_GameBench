#!/usr/bin/env python3
"""v1.6.1 candidate test zip: FFA only (FFB..FFD of the published v1.6 are byte-identical).  python3 mkcand.py DIR_WITH_BUILD [OUT.zip]"""
import hashlib, sys, zipfile
from pathlib import Path
d = Path(sys.argv[1]); out = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent / "sets/MW2_v1.6.1_candidate_STE_fix.zip")
out.parent.mkdir(exist_ok=True)
ffa = (d / "FFA_boot.st").read_bytes(); md5 = hashlib.md5(ffa).hexdigest()
txt = f"""Midwinter 2 v1.6.1 CANDIDATE for STE / Mega STE (2026-11-20)  -  fix for "music plays, no disk activity"
==========================================================================================================

What it is: the published v1.6 with ONE fix. The Amiga music/effects (STE / Mega STE only) replaced the YM sound tick, and that tick was
also what kept the sound chip's register 7 (bits 6+7 = "I/O ports A/B are outputs") set. The game's sound init writes 0 there. With
bit 6 = 0 the chip does not drive the floppy drive-select / side lines (they are on port A), so on a real STE / Mega STE no drive was ever
selected: no light, no seek, no disk activity - while the music keeps playing. (An emulator does not model that bit, which is why
all tests passed.) Now the Amiga sound code keeps register 7 = $FF while it owns the sound, and the init writes $C0 instead of 0.
The logo screen still says "v1.6". FFB, FFC, FFD are byte-identical to the published v1.6: keep using yours.

Files: FFA_boot.st / FFA_boot.msa ONLY.  FFA_boot.st md5: {md5}

How to test on the STE / Mega STE (the machines where v1.6 failed):
  1. Write this FFA_boot to a 720K DD disk (as before); use your v1.6 FFB (and FFC / FFD).
  2. Boot FFA. Wait for the logo; the first disk check should now show drive activity (light on, head noise) a few seconds after the music starts.
  3. At the prompt swap FFA for FFB in drive A and press a key: the drive should read FFB, then the Mission/Jeep/Kamikaze screen.
  4. Report: works / still no disk activity (and WHEN: right after the music starts, or only after the swap; and which screen: orange logo or black
     'Insert Graphics Disk').
"""
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for n, b in (("FFA_boot.st", ffa), ("FFA_boot.msa", (d / "FFA_boot.msa").read_bytes()), ("TEST.TXT", txt.encode())):
        zi = zipfile.ZipInfo(n, date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16
        z.writestr(zi, b)
print(out, hashlib.md5(out.read_bytes()).hexdigest(), "FFA.st", md5, "FFA.msa", hashlib.md5((d / "FFA_boot.msa").read_bytes()).hexdigest())
