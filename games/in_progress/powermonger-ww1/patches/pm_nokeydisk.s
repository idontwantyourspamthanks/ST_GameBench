; name: pm_nokeydisk
; default: yes
; site: $13cec
; orig: 4eb90001cf7c
; note: key-disk request.  The first START NEW CONQUEST of a session calls `jsr $1cf7c` (new-conquest start, $13cd2: after resource 0 is loaded, before resources 2-4):
;       the requester "PLEASE INSERT ORIGINAL POWERMONGER DISK" ($1cc26), then `$1cfa6` loads the file `DATA\SPRITE8.DAT` (name at $1cfb8) from drive A: into the scratch buffer
;       $320c0 through the game's FAT loader $d962, and a failure shows "DISK IN DRIVE A: IS NOT THE ORIGINAL POWERMONGER DISK" ($1cc2e) and asks again.  Nothing but the
;       presence of that file is used (the buffer $320c0 is a scratch area many routines reuse, $e4d6 $f5ea $119b8 $12882 $1301a); the next resource load then asks for the WW1 disk
;       back ($d932 -> $1cc1a "PLEASE INSERT THE POWERMONGER DATA DISK").  It is the second half of the copy protection, next to pm_noprot's manual question: without this patch
;       the release would need the user's original Powermonger floppy.  The patch removes the call (3 nops): the WW1 disk stays in the drive.
;       FDC evidence (work/notes/RESULTS_stage02.md): the reads from the Powermonger disk are 16 ordinary multi-sector reads (FDC command $90) + seeks, no read-address / read-track /
;       write command, i.e. FAT12 boot sector + FAT + root + DATA directory + the 8724-byte file: no track-level key-disk check.
        org     $13cec
        nop
        nop
        nop
