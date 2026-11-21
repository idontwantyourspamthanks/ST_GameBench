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

**v1.6.2:** hard-disk version on a 1 MB machine: PP's loader keeps a copy of TOS's memory that can overwrite the end of the Amiga sample bank (always on a 1 MB Mega STE; on a 1 MB STE once a hard-disk driver is resident), so some vehicle engine sounds played from overwritten data. The game now detects that and uses the original YM sound and music. In practice the hard-disk version's Amiga sound needs 2 MB; the floppy version keeps it at 1 MB (`patches/asn/blob.s` end canary `ASNE`, `work/notes/banktail.md`).

## Floppy release (v1.6.1): real drives

`tools/package.sh` writes `dist/Midwinter2_v<version>_patched_floppies_<date>.zip`: `FFA_boot`, `FFB_graphics`, `FFC_missions`, `FFD_campaign_blank` as `.st` and as `.msa`, `README.TXT` (from `patches/FLOPPY.TXT`) and `WRITING_DISKS.TXT` (`patches/WRITING_DISKS.TXT`: how to write the disks raw 80 x 2 x 9 on DD media, why FFA/FFB/FFC look corrupt to BPB-checking writers, the black-prompt rule, test plan). v1.6 parks the drive head on track 0 before the game starts, doubles the game's FDC time-out on 68000 machines and skips the drive-B probe on one-drive machines (`work/notes/realfloppy.md` is the investigation, `work/notes/realfloppy_v16.md` the fix and its gates, `work/floppy16/` the gate scripts and raw output). Real hardware: v1.6 did not work on a real STE / Mega STE; v1.6.1 was confirmed on real STEs by a tester.

v1.6.1 fixes that STE / Mega STE failure of v1.5/v1.6 (the Amiga sound left PSG reg 7 bit 6 = port A direction = the floppy drive select at 0, so no drive was selected after the music started; Hatari cannot show it): `patches/ym_porta.s`, `asn_mixer` / `asn_ymsilence` in `patches/asn/blob.s`, `work/notes/stesound.md`. Gates run with sound emulation on plus the PSG-direction check `work/stesound/psgcheck.py` (`work/stesound/run_gates.sh`).

The test harness (`tools/mw2harness.py`, `tools/abtest.py`) needs saved machine states (`work/snapshots/`) and a created campaign disk (`work/disk_overlay/`). Both contain game data, so they aren't in the repository. `boot_to_game()` reaches the 3D view from a cold boot. Save your own snapshots from there with `Hatari.savemem()`.
