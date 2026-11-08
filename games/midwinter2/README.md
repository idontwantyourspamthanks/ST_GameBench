# Midwinter II: Flames of Freedom (PP's HAGA hard-disk version)

Status: **done**. Read [`REPORT.md`](REPORT.md) for what was changed and why, [`PLAN.md`](PLAN.md) for the phases and decisions, [`patches/README.md`](patches/README.md) for the patch format and boot mechanism, and `work/notes/` for the evidence.

## Files you need (not included)

Copy PP's HAGA version (2014) here. The tools were built against these exact files:

| File | MD5 |
|---|---|
| `RUNME.TOS` | `dc9f8a6c0a673e2d12d7f428ea120b73` |
| `HAGA` | `b34607ed9baecc5982a5a01ecaf5a3dd` |
| `FILES/FFA` | `b3e128ad8ee6c023d75d7e10f7a86fdd` |
| `FILES/FFB` | `9d4ea2ddfcfe5fa7fdf7b54f26168ed3` |
| `FILES/FFC` | `252d0ad0674db02ba5d104891db12e29` |
| `FILES/FFD` (blank campaign disk) | `5e034299f50432eb6fe5e7048a5d2ccc` |
| `FILES/FFE` | `543b759762797ffc8e861e28a6a1f8c4` |
| `FFF273.HST`, `LFF273.HST`, `FF240R.BMP` | intro pictures |

## Use

```sh
python3 tools/mw2patch.py verify     # your files vs the expected original bytes
python3 tools/mw2patch.py build      # build/game/: patched HD copy (RUNME.TOS + HAGA patched)
python3 tools/mw2patch.py build --floppy --zip out.zip   # bootable floppy set
tools/play.sh [--machine st|megast|ste|megaste|tt|falcon] [--ram KiB] [--original]
tools/package.sh                     # zips into dist/
```

The test harness (`tools/mw2harness.py`, `tools/abtest.py`) needs saved machine states (`work/snapshots/`) and a created campaign disk (`work/disk_overlay/`). Both contain game data, so they aren't in the repository. `boot_to_game()` reaches the 3D view from a cold boot. Save your own snapshots from there with `Hatari.savemem()`.
