# Snapshot restore: "Insert graphics disk" after a load (cause, evidence, fix)

## Symptom
Restore a snapshot (e.g. `1mb_stark.sav`), click Decisions, click Skiing: the game shows
`Insert graphics disk / Press any key when ready` forever. `work/notes/img/restore_raw_insert_graphics_disk.png`
is the screen after restoring `1mb_ski_stand.sav` straight into Hatari, pressing X (back to Decisions) and
clicking Skiing.

## Cause: the memstate embeds the host path of the emulated hard disk, and GEMDOS resolves the game's files through it
1. A Hatari memstate is a gzip file that also holds the Hatari configuration and the GEMDOS state. Decompressing
   `1mb_stark.sav` and searching for scratch paths (`python3`, `gzip.decompress`, `re.findall(rb"/tmp/strun-...")`):
   ```
   {b'/tmp/strun-asj8t4u6/C/FILES/MWB', b'/tmp/strun-asj8t4u6/C/FILES/', b'/tmp/strun-asj8t4u6/C'}
   ```
   (`1mb_ski_stand.sav` as it was written: `{.../strun-nl9mn_50/C/FILES/MWB, .../strun-nl9mn_50/C, .../strun-nl9mn_50/C/FILES/}`.)
   That is the emulated drive C: of the run that made the snapshot, its current directory `C:\FILES\` and the last file
   opened. Every `Hatari(...)` run uses a fresh `/tmp/strun-<random>/C`, and `close()` deletes `C`.
2. `--trace gemdos` on a raw restore into another scratch dir, then X, then Skiing (the log is complete):
   ```
   INFO : GEMDOS HDD emulation, C: <-> /tmp/strun-oj9mdn3l/C.
   INFO : Memory state file restored: /tmp/strun-oj9mdn3l/state.sav
   GEMDOS 0x3D Fopen("MWB", read-only) at PC=0xF9022
   GEMDOS didn't find filename /tmp/strun-nl9mn_50/C/FILES/MWB
   -> ERROR -34 (errno = 2)
   ```
   The command line said `oj9mdn3l`, but the restored GEMDOS state resolves the relative name `MWB` against
   the *old* directory `nl9mn_50`, which no longer exists. `PC=0xF9022` is in PP's resident HAGA service (copied to
   `phystop-$8000 = $F8000` on a 1 MB machine); its Fopen fails, the game's loader reports a missing disk.
3. Control experiments, same snapshot, same keystrokes:

   | restore into | result |
   |---|---|
   | a new random scratch dir (raw `Hatari(snapshot=...)`) | `Insert graphics disk` (screenshot above) |
   | a scratch dir with the *same* name as the one embedded in the snapshot (`workdir='/tmp/strun-0xmbe_ck'` for the first `1mb_ski_stand.sav`) | ski view loads (clock 06:10) |
   | a new random dir, but the snapshot first rewritten by `retarget_snapshot` (`MW1(snapshot=...)`) | `Fopen("MWB") -> host: /tmp/strun-h2ahq_3x/C/FILES/MWB`, `-> FD 64`, `Fseek`, `Fread(64, 200000, 0x81000)`, `Fclose`, three chunks, ski view up (`restore_retargeted_ski_loaded.png`) |
   | `1mb_stark.sav` -> `MW1(snapshot=...)` -> Decisions -> Skiing (the user's case) | ski view, `in_ski()` True, state x=z=25600 |

## Hypotheses that the evidence rejects
* "HAGA holds a file handle / cached state that a restore breaks": the trace above shows HAGA doing a fresh
  `Fopen / Fseek / Fread(200000) / Fclose` for every chunk (three chunks in one Skiing load, always FD 64), so no handle
  lives across the snapshot.
* "GEMDOS-HD file handles not restored": [INFERENCE] none is needed, because HAGA reopens per chunk; what the trace
  shows failing is the stored directory path.

[INFERENCE] why the MW2 snapshots did not show it: they embed `/tmp/mw2run-l511knmj/C` the same way (`zcat
games/in_progress/midwinter2/work/snapshots/1mb_ingame_foot.sav | strings`), so any load after a restore into another dir would
have failed too; MW2 flows probably rarely loaded after a restore, or ran from a fixed dir. Not tested.

## Fix (in `tools/mw1.py`, no shared tool changed)
`MW1(snapshot=path)` pre-creates the scratch dir, writes `R/snap_in.sav` = the snapshot with every
`/tmp/strun-<id>` / `/tmp/mw2run-<id>` string replaced by `R` (`retarget_snapshot`: gunzip, replace inside the
NUL-terminated field, pad with NULs in place, gzip level 1), and passes that to the base class. Cost: well under a
second. It also works on the older snapshots in `work/snapshots/` (`1mb_options`, `1mb_team`, `1mb_stark`,
`1mb_ski_start`). Anything that restores an MW1 snapshot and then loads data MUST go through `MW1(snapshot=...)`.
With a raw `Hatari(snapshot=...)`, restore into a `workdir` equal to the embedded path instead (the run that made it).
Parallel runs need no shared path with the retarget approach.

Unchanged rules: snapshots hold whatever code was in RAM when saved, are tied to the 1 MB STE TOS 1.62 they were made
on, and `savemem` writes through the shared `/tmp/hatari.sav` (so `MW1.savemem` takes a lock,
`/tmp/hatari-savemem.lock`, to keep concurrent savers apart).
