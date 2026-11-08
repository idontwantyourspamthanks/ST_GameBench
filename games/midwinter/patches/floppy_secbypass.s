; name: floppy_secbypass
; media: floppy
; default: yes
; site: $12050
; phase: boot
; note: floppy build only.  The game starts with the "FVPF SECURITY CHECK - Identify these two people by
; note: clicking on their names" screen (strings at $12178..; routine sub_011c7e).  The check is
; note: sub_012050 (called at $11D7E): it sets the failure word $12142 = $FFFF, lets the player click two
; note: names and clears $12142 only if both are right; the caller then tests `tst.w $12142` at
; note: $11D82 (beq = "Identification correct / YOU ARE CLEARED").  PP's HD patcher applies
; note: `move.w #$4e75,$12050.l` (rts) at boot, so the HD game always passes (work/notes/loading.md
; note: section 4); a floppy boot has no PP patcher and shows the real check.  This patch gives the
; note: floppy the same bypass. Enabled by default: the user chose to skip the check on floppy for MW2 as well.
; note: (Midwinter 2's floppy set skips its manual check too).  The original bytes are the raw image
; note: bytes (33fc), not PP's rts, hence `media: floppy`.
        org     $12050
        rts
