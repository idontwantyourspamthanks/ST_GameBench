# Midwinter (PP's HAGA hard-disk version)

Status: **done**. Read [`REPORT.md`](REPORT.md) for what was changed and why, [`PLAN.md`](PLAN.md), [`patches/README.md`](patches/README.md) and `work/notes/` for the evidence.

## Files you need (not included)

| File | MD5 |
|---|---|
| `RUNME.TOS` | `6156606e5cb79ff75b0e226841ffef9b` |
| `HAGA` | `b34607ed9baecc5982a5a01ecaf5a3dd` (same as Midwinter II's) |
| `FILES/MWA` | `3e3d3b1966ed6d119b06de5fbf2b2c7c` |
| `FILES/MWB` | `ae1dbe50dcef64e3ed19503892afebdb` |
| `FILES/MWC` (data/save disk) | `22e592651ab1564fafed23a13c22d171` |
| `FMW273.HST`, `LMW273.HST`, `MW240R.BMP` | intro pictures |

```sh
python3 tools/mw1patch.py verify
python3 tools/mw1patch.py build [--floppy]
tools/play.sh [--machine st|megast|ste|megaste|tt|falcon] [--ram KiB] [--original]
tools/package.sh                     # zips into dist/ (Midwinter_v<VERSION>_patched_..._<date>.zip)
python3 tools/mw1patch.py version    # the release version
```

**Release credit:** the Game Options screen (both builds) shows a small, dim `v<VERSION> enhanced by dad_prg` in its bottom-left corner, drawn by `patches/mw_credit.s`. The version is set in one place, the `; version:` header of that file; `package.sh` and the README/PATCHES.TXT texts take it from there (`mw1patch.py version` / `doc`). Evidence: `work/notes/credit.md`.
