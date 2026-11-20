# Strict Hatari: YM2149 I/O port-direction model

Stock Hatari 2.6.x keeps `PSGRegisters[14]` (port A: floppy drive-select bits 1-2, side bit 0) and selects the drive whatever PSG register 7 says. A real
YM2149 drives port A only while reg 7 bit 6 = 1 (bit 7 = port B); with bit 6 = 0 the lines float high: no drive selected, no side, the floppy is dead.
Midwinter 2 v1.5/v1.6 shipped with exactly that on STE / Mega STE ("music plays, no disk activity") and every emulator gate passed.

`psg_portdir.patch` (against Hatari `b5c3a7d5`, files `src/psg.c`, `src/fdc.c`, `src/includes/psg.h`) adds `PSG_GetPortAPins()`:
reg 7 bit 6 = 0 -> the pins read $ff (all deselected, side 0), else the reg-14 latch. The FDC drive/side model, the drive LEDs and reads of reg 14 use the pins;
a reg-7 write that flips bit 6 re-evaluates drive/side; a reg-14 write with port A an input is logged (`WARN : PSG strict: reg 14 := ...`, first 20) and has no effect.
Port B (bit 7) is not modelled (the printer port is not used by games); `HATARI_PSG_LENIENT=1` in the environment turns the whole model off in the same binary (A/B control).

## Build (separate tree and build dir; never touches the `build/` other agents run)
```
cd ~/Code/AtariST
rsync -a --exclude build --exclude .git hattari/ hattari-strict/
cd hattari-strict && patch -p1 < ../gamebench/tools/hatari-strict/psg_portdir.patch
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_SDL3=ON -DCMAKE_C_COMPILER_LAUNCHER=ccache
make -j10 hatari          # binary: hattari-strict/build/src/hatari (2 min with a warm ccache)
```
Same options as `hattari/build` (RelWithDebInfo, SDL3), so TT/Falcon behave like the user's patched build. Re-apply after the user rebuilds from newer sources.

## Use from the harness (opt-in; default unchanged)
- `Hatari(..., strict=True, sound=True, trace_psg=True)`, then `h.close()` and `h.psg_check()` (the trace is streamed into `tools/psgcheck.py`, never stored: sample-playing games write 10 MB/s of it); or `HATARI_STRICT_PSG=1` in the environment (every harness that calls `hatari_bin()`);
  `HATARI_STRICT=/path/to/hatari` overrides the binary path.
- The game's floppy MUST be mounted as a disk image (`--disk-a`, `extra=[...]`): a game folder mounted as GEMDOS drive C: never touches the FDC or PSG port A.
- Verdicts: a failing build shows `drive=-1` in every `fdc type` trace line and loops at its disk check; `tools/psgcheck.py` reports the same from the trace in a stock build.
