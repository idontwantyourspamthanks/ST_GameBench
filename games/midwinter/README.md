# Midwinter (PP's HAGA hard-disk version)

Status: **in progress**. See [`PLAN.md`](PLAN.md), [`patches/README.md`](patches/README.md) and `work/notes/`. The working patch system (`tools/mw1patch.py`), harness (`tools/mw1.py`) and patches are already usable. Not every patch is on by default yet.

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
```
