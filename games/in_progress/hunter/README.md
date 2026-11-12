# Hunter (PP's "Gamex" hard-disk version, 2010)

Status: **done** (HD and floppy releases, see `REPORT.md`). Activision, 1991: a 3D open-world island game (vehicles, boats, aircraft).

Build: `tools/package.sh` (zips into `dist/`, named `Hunter_v<VERSION>_patched_..._<date>.zip`); play: `tools/play.sh [--floppy] [--original] [--machine ste]`.

**Release credit:** the title screen (both builds) shows a small, dim `v<VERSION> enhanced by dad_prg` at the bottom, drawn by `patches/hn_credit.s`. The version is set in one place, the `; version:` header of that file; `package.sh` and the README/PATCHES.TXT texts take it from there (`tools/huntpatch.py version`). Gate tool: `tools/huntcredit.py`.

PP's packaging here is the older Gamex loader (`START.TOS` + `HUNTER.PCH` + `GXUT251.PRG`), not the HAGA system used by the Midwinter conversions. 1 MB minimum; ST(E), Mega ST(E), Falcon.

## Floppy base (not included)

The user supplies the Paper Bag floppy image in `alt/floppy/` (git-ignored); the floppy set is built from it. The sample bank is built from the user's Amiga ADF in `alt/amiga/`.

| File | MD5 |
|---|---|
| `alt/floppy/Hunter (1991)(Activision)[cr Paper Bag].st` | `f50322aea685f52a8da0dd8e9c84e27a` |
| `alt/amiga/Hunter (Activision).adf` | `83a56af67bc9ce4aa85b40656609f29f` |

## Files you need (not included)

| File | MD5 |
|---|---|
| `START.TOS` | `b5fa1be2684e2a6b3ee9a1140bb54bf8` |
| `HUNTER.PCH` | `63e71b88e8f5b4a859640744cccd93e4` |
| `GXUT251.PRG` | `a11524e0e0dcd77325c33120b7a1d0f6` |
| `HUM.FIC` | `831b4e23a7b5d172f0d3ca248520992e` |
| `D15R_F5.FIC` | `fb30434ffa1eb5dd4681e608697dd10d` |
| `D15R_H5.FIC` | `92a28610421b5d6f7119322b687868f2` |
| `FILES/0` | `3b5602430b40700a12e17c6b7043b750` |
| `FILES/1` | `bb3f7fa74739f02b6d52cbe9f58a7227` |
| `FILES/2` | `3630ef11b29fa134dcdd73b65c9a9774` |
| `FILES/3` | `89ca4eea0f6f5577bd0478064fc80bfe` |
| `FILES/4` | `62ccc99fe51953ab3dcd53cc98b679d6` |
| `FILES/6` | `57796feb9a726e2a6b1eea3be4b664c1` |
| `FILES/7` | `f86907cb67dc119b16b767fa3580693e` |
| `FILES/8`, `9`, `A`, `B` | `2cb4267a…`, `5a6c81a1…`, `1337f471…`, `8d1c17fd…` |
| `FILES/C`, `D` | `e05ba425…`, `11071656…` |
| `FILES/E`, `F` (identical) | `8cfb853d75f625cfbb59c2f09836d2c8` |
