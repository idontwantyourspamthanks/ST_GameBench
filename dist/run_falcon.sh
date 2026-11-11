#!/usr/bin/env bash
# Boot a FLOPPY build in Hatari as a Falcon (TOS 4.04, 4 MB ST-RAM, 16 MHz, VGA).
#   ./run_falcon.sh DISK1.st [DISK2.st]          DISK1 -> drive A, DISK2 (optional) -> drive B
# This is a floppy launcher, not a hard-disk one: the all-games hard disk image does NOT work on Hatari's Falcon.
#   Finding: the Falcon has no ACSI; on its IDE port HDDRIVER 10.15 probes the status register ($fff00039 reads $50) and then
#   the next channels ($fff00079/$b9/$f9: bus error), but never issues an IDE command, so it reports "No partitions" and no C:
#   appears (TOS 4.04's own IDE driver does not mount the image either; EmuTOS does). SCSI: "No LUN configured".
#   Details: games/in_progress/hunter/work/notes/ttfalcon.md section 3.
# Floppy builds: Hunter (HUNTER_disk1.st [+ HUNTER_disk2_sound.st]) and Powermonger (Powermonger_patched.st)
#   from games/in_progress/*/dist/*.zip.  The Midwinters have no floppy build.
# Images are used directly (write-enabled), so game saves go into the .st file: pass a copy if the original matters.
# Hatari keys: F12 menu, AltGr+M mouse grab, AltGr+Q quit.
set -euo pipefail
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd -P)"
TOS="$HERE/../tos/TOS_4_04.img"
[[ $# -ge 1 && $# -le 2 ]] || { echo "usage: $0 DISK1.st [DISK2.st]" >&2; exit 1; }
for f in "$@"; do [[ -f "$f" ]] || { echo "disk image not found: $f" >&2; exit 1; }; done
[[ -f "$TOS" ]] || { echo "TOS image not found: $TOS (see gamebench/tos/README.md)" >&2; exit 1; }
echo "Falcon (TOS 4.04, 4 MB, 16 MHz): A: $1${2:+  B: $2}"
args=(--machine falcon --tos "$TOS" --memsize 4096 --cpuclock 16 --monitor vga
      --gemdos-drive skip --confirm-quit no --disk-a "$1" --drive-a true)
[[ $# -eq 2 ]] && args+=(--disk-b "$2" --drive-b true)
exec hatari "${args[@]}"
