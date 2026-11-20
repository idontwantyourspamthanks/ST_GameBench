#!/usr/bin/env python3
"""Package the mkvars.py variants as one zip each: work/stesound/sets/MW2_v1.6_diag_<name>.zip = FFA_boot.st/.msa + TEST.TXT
(FFB/FFC/FFD of every variant are byte-identical to the published v1.6 disks: the user keeps using his v1.6 FFB..FFD).
    python3 work/stesound/mkzips.py VARROOT [NAME ...]
Deterministic (fixed member order and times)."""
import hashlib, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHIP = {"FFB_graphics.st": "9d4ea2ddfcfe5fa7fdf7b54f26168ed3", "FFC_missions.st": "252d0ad0674db02ba5d104891db12e29",
        "FFD_campaign_blank.st": "5e034299f50432eb6fe5e7048a5d2ccc"}

ONE = {
    "noasn": "NO Amiga sound/music at all: the YM chip plays everything (all other v1.6 patches identical).",
    "noasn_nojag": "NO Amiga sound AND no Jaguar-pad patches (jag_*): nothing STE-specific is left in the patch set; only the v1.6 floppy fixes + speed patches.",
    "effects": "Amiga sound EFFECTS only (3D view); the title/hall/map music is the original YM tune (the music patch asn_mus is left out).",
    "music": "Amiga MUSIC only (title/hall/map); the 3D-view effects are the original YM effects (the effect patches asn_core/lv* are left out).",
    "nomw": "Full v1.6 but the Microwire (volume chip, $ff8922/24) is never written: the DMA music plays at whatever the machine's reset volume is (may be quiet or silent).",
    "nodma": "Full v1.6 (Amiga music mixing runs, same CPU load) but the DMA sound is programmed and NEVER STARTED: no Amiga sound is heard, the YM is parked, so SILENCE.",
    "nomix": "Full v1.6 but the software mixer does no work: the DMA sound plays a silent ring (silence, ~no CPU load); tests 'DMA hardware running' without the CPU load.",
    "nosil": "Full v1.6 but the effect-session start does not touch the YM chip at all (asn_ymsilence is a no-op): no PSG access from the Amiga code.",
    "silmask": "Full v1.6 but the effect-session start accesses the YM chip with interrupts masked (sr=$2700 around the PSG read-modify-write).",
    "silff": "Full v1.6 but the effect-session start writes $FF to PSG register 7 (as the game's own silence does) instead of read-modify-write.",
}
NEEDS3D = {"effects", "nomw", "nodma", "nomix", "nosil", "silmask", "silff"}


def test_txt(name):
    ps = [
        f"Midwinter 2 v1.6 DIAGNOSTIC set '{name}' (2026-11-20)", "=" * 60, "",
        "What it is (ONE change against the published v1.6):", "  " + ONE[name], "",
        "Files: FFA_boot.st / FFA_boot.msa ONLY. FFB, FFC, FFD are byte-identical to the published v1.6 disks: keep using yours.",
        "FFA_boot.st md5: @MD5@", "",
        "How to test on the STE / Mega STE (the machines where v1.6 shows 'music playing, no disk activity'):",
        "  1. Write FFA_boot (this one) to a 720K DD disk as before; use your v1.6 FFB.",
        "  2. Boot FFA. Logo + title tune appear. When the game asks for the graphics disk, swap FFA for FFB in drive A and press a key.",
        "  3. Report: does the drive read FFB (disk activity, then the Mission/Jeep/Kamikaze screen), or is it silent as with v1.6?",
    ]
    if name in NEEDS3D:
        ps.append("  4. (only if step 3 worked) start a mission and get to the 3D view; report whether sound effects / disk loads still work, "
                  "and whether the disk can be used afterwards (e.g. leaving the vehicle and entering the map).")
    ps += ["", "Answer in one line: 'works' / 'fails the same' / what you saw and heard (tune playing? screen? drive light/noise?)."]
    return "\n".join(ps) + "\n"


def main():
    root = Path(sys.argv[1])
    names = sys.argv[2:] or list(ONE)
    outd = ROOT / "work/stesound/sets"
    outd.mkdir(parents=True, exist_ok=True)
    for n in names:
        d = root / n
        for f, md5 in SHIP.items():
            assert hashlib.md5((d / f).read_bytes()).hexdigest() == md5, (n, f)
        ffa = (d / "FFA_boot.st").read_bytes()
        md5 = hashlib.md5(ffa).hexdigest()
        txt = test_txt(n).replace("@MD5@", md5)
        zp = outd / f"MW2_v1.6_diag_{n}.zip"
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            for mname, data in (("FFA_boot.st", ffa), ("FFA_boot.msa", (d / "FFA_boot.msa").read_bytes()), ("TEST.TXT", txt.encode())):
                zi = zipfile.ZipInfo(mname, date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = 0o644 << 16
                z.writestr(zi, data)
        print(f"{zp.name} {hashlib.md5(zp.read_bytes()).hexdigest()}  FFA.st {md5}  FFA.msa {hashlib.md5((d / 'FFA_boot.msa').read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
