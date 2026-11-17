; name: fl_driveb
; default: yes
; media: floppy
; site: $d6fa
; orig: 0c410320640870004ef90000cac00441032070044ef90000cac0
; doc: Floppy release only: the second floppy drive.  Disk 2 may be in drive B (or in A, swapped in at the "Insert Disk 2" prompt as before); the game asks A first and tries B when the disk in A is not the wanted one.
; note: Two-drive support (floppy build only).  The game's own FDC driver sub_00cac0 already handles two drives (unit = bit 0 of the device word: PSG port A select 2 = A / 4 = B in sub_00cece, and a per-unit
; note: head position table at $cfac that sub_00ce64 loads into the FDC track register before every command and sub_00ce96 stores after it: the FD1772 has ONE track register for both drives, the driver keeps
; note: one saved position per unit and restores a unit whose position is unknown ($ffff)), but its only entry sub_00d6fa always passes unit 0: `moveq #0,d0` / `moveq #4,d0` (4 = side 1 for sectors >= $320).
; note: The game never asks for a drive: it identifies the disks by the boot sector it reads (sub_00d798 reads sector 1 of the disk in the drive into $68000): disk 1 = `MOON` at offset 2 (sub_00d778), disk 2 =
; note: the long $66055505 at offset $e (sub_00d788, the loop at $76fc / $751c / $75e8 / $16718 that shows "Insert Disk 2 and press a key.").
; note: The patch replaces sub_00d6fa (26 bytes, the only caller of sub_00cac0) with a jump into this blob.  `unit` (0 = A, 1 = B) is ORed into the device word, so every read of the game goes to the drive that held
; note: the wanted disk at its last check.  When the caller is sub_00d798 (return address $d7b2, i.e. a disk check; the return address under it, $d77a / $d78a, says which disk is wanted) the blob does the check itself:
; note: read the boot sector from the preferred drive of that disk (A at power-on) with the game's own reads (their FDC waits are bounded: forced interrupt after $40000/$60000 loops, so an absent drive B or an empty one cannot hang),
; note: compare the long the caller will compare (the two probe longs are cleared first, so a failed read is a mismatch and never a stale match); on a mismatch / read error switch to the other drive and read again; the drive
; note: that matched becomes the preferred drive of that disk and the current `unit` for all later reads.  If both fail `unit` is back at the preferred drive, the caller sees the mismatch and shows its prompt as before.
; note: One drive (swap route, disk 2 into A at the prompt): the first check reads A (disk 1, mismatch), probes B (bounded; slower by the time B needs to give up), prompt; after the swap A matches at once and stays preferred.
; note: Two drives: first check A (disk 1) mismatch, B matches: disk 2 is read from B for the rest of the session while disk 1 stays in A.  Real hardware and the MiSTer core: not tested (work/notes/floppy_driveb.md).
; note: Blob $B8E00-$B8EA5 (the gap between mg_sync's blob end $B8D8B and its data $B8F00); `unit`, `pref[2]` (word per disk: 0 = disk 1, 1 = disk 2) are in the blob, initialised to 0 by the image.
        org     $d6fa
        jmp     $b8e00.l

        org     $b8e00
blob:   cmpi.l  #$d7b2,(sp)             ; called from sub_00d798 = boot sector read of a disk check?
        beq.s   probe
        bsr.s   rd                      ; every other read: the drive of the last check
        rts
; the original sub_00d6fa with the unit: d1 = sector (>= $320: side 1), d0 = side | unit; d3 low byte = command (0 read; a write / format, which no
; caller the game uses for the floppy release makes, is pinned to drive A)
rd:     moveq   #0,d0
        tst.b   d3
        bne.s   .u
        move.w  unit.l,d0
.u:     cmpi.w  #$320,d1
        bcc.s   .hi
        jmp     $cac0.l                 ; (returns to the caller of rd)
.hi:    subi.w  #$320,d1
        addq.w  #4,d0
        jmp     $cac0.l

; disk check: 4(sp) = $d78a -> disk 2 (slot 1, long $66055505 at $6800e), else disk 1 (slot 0, 'MOON' at $68002)
probe:  moveq   #0,d0
        cmpi.l  #$d78a,4(sp)
        bne.s   .s
        moveq   #2,d0
.s:     movem.l d4-d5/a2,-(sp)
        move.w  d0,d4                   ; byte offset of the slot in pref
        lea     pref.l,a2
        move.w  (a2,d4.w),unit.l        ; the preferred drive of this disk first
        moveq   #1,d5                   ; two tries: preferred drive, other drive
.try:   clr.l   $68002.l
        clr.l   $6800e.l
        bsr.s   rd
        tst.w   d4
        bne.s   .c2
        cmpi.l  #$4d4f4f4e,$68002.l
        bra.s   .cc
.c2:    cmpi.l  #$66055505,$6800e.l
.cc:    beq.s   .ok
        eori.w  #1,unit.l               ; mismatch or read error: the other drive (flips back after the second failure)
        dbra    d5,.try
        moveq   #1,d0
        bra.s   .out
.ok:    move.w  unit.l,(a2,d4.w)        ; the drive that holds this disk is the preferred one from now on
        moveq   #0,d0
.out:   movem.l (sp)+,d4-d5/a2
        rts

unit:   dc.w    0                       ; drive of the last successful check (0 A, 1 B)
pref:   dc.w    0,0                     ; preferred drive per disk: disk 1, disk 2
