cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
F=work/fdb/fdb.py
python3 $F our_startB_ste work/fdb/build/disk_a.st work/fdb/build/disk_b.st startB --tos 1.62 --tail 40
python3 $F orig_insB_ste work/floppy/disk_a.st work/floppy/disk_b.st insB --tos 1.62 --tail 40 --answer
python3 $F orig_startB_ste work/floppy/disk_a.st work/floppy/disk_b.st startB --tos 1.62 --tail 40 --answer
python3 $F stale_insB_ste work/fdb/stale/MOONSHR_floppy/disk_a.st work/fdb/stale/MOONSHR_floppy/disk_b.st insB --tos 1.62 --tail 40
python3 $F stale_startB_ste work/fdb/stale/MOONSHR_floppy/disk_a.st work/fdb/stale/MOONSHR_floppy/disk_b.st startB --tos 1.62 --tail 40
