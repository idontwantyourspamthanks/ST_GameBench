; name: fl_driveb
; default: yes
; media: floppy
; site: $d6fa
; orig: 0c410320640870004ef90000cac00441032070044ef90000cac0
; doc: Floppy release only: second floppy drive.  Disk 2 may be in drive B (or, as before, swapped into drive A at the "Insert Disk 2" prompt); the game asks A first and looks at B when the disk in A is not the wanted one.  One drive: nothing changes except that each key press at the "Insert Disk 2" prompt BEFORE the swap takes about 1 s longer (drive B is probed once per check; 2 s if drive B exists but holds no disk); to build without it use `msrpatch.py build --floppy --only` with the default set minus fl_driveb.
; note: Two-drive support (floppy build only).  The game's own FDC driver sub_00cac0 already handles two drives (unit = bit 0 of the device word: PSG port A select 2 = A / 4 = B in sub_00cece, and a per-unit
; note: head position table at $cfac that sub_00ce64 loads into the FDC track register before every command and sub_00ce96 stores after it: the FD1772 has ONE track register for both drives, the driver keeps
; note: one saved position per unit and restores a unit whose position is unknown ($ffff)), but its only entry sub_00d6fa always passes unit 0: `moveq #0,d0` / `moveq #4,d0` (4 = side 1 for sectors >= $320).
; note: The game never asks for a drive: it identifies the disks by the boot sector it reads (sub_00d798 reads sector 1 of the disk in the drive into $68000): disk 1 = `MOON` at offset 2 (sub_00d778), disk 2 =
; note: the long $66055505 at offset $e (sub_00d788, the loop at $76fc / $751c / $75e8 / $16718 that shows "Insert Disk 2 and press a key.").
; note: The patch replaces sub_00d6fa (26 bytes, the only caller of sub_00cac0) with a jump into this blob.  `unit` (0 = A, 1 = B) is ORed into the device word, so every read of the game goes to the drive that held
; note: the wanted disk at its last check.  When the caller is sub_00d798 (return address $d7b2, i.e. a disk check; the return address under it, $d77a / $d78a, says which disk is wanted) the blob does the check itself:
; note: read the boot sector from the preferred drive of that disk (A at power-on) with the game's own reads, compare the long the caller will compare (the two probe longs are cleared first, so a failed read is a mismatch and never
; note: a stale match); on a mismatch / read error switch to the other drive and read again; the drive that matched becomes the preferred drive of that disk and the current `unit` for all later reads.  If both fail `unit` is
; note: back at the preferred drive, the caller sees the mismatch and shows its prompt as before.  2 tries per check, so there is no endless reselecting of B.
; note: Drive B is only handed to the game's driver after `bpres` (own short probe: restore + index pulse).  Measured per failed check at the prompt (Hatari 2.6.1, real FDC timing, 50 Hz VBL): no drive B 0.9 s, drive B without a disk 2.0 s,
; note: an unrelated disk in B (blank / random / disk 1 copy) 0.2-0.5 s, no fl_driveb 0.04-0.2 s.  Without `bpres` (first version of this patch) the game's own waits for the FDC interrupt ($60000 / $60000 / $40000 loops: restore, seek 0, read) ran out one after the other
; note: for a drive B that does not spin a disk: 4.4 s each in Hatari = 13.3 s per check (by instruction count 2.1 s / 2.1 s / 3.7 s = 7.8 s); a real ST with no drive B would sit in them too, hence `bpres`.
; note: One drive (swap route, disk 2 into A at the prompt): the first check reads A (disk 1, mismatch), probes B (`bpres`: restore + index pulse), prompt; after the swap A matches at once and stays preferred.
; note: Two drives: first check A (disk 1) mismatch, B matches: disk 2 is read from B for the rest of the session while disk 1 stays in A.  Real hardware and the MiSTer core: not tested (work/notes/floppy_driveb.md).
; note: Blob $BB400-$BB52F (free gap between hd_stage and hd_init); `unit`, `pref[2]` (word per disk: 0 = disk 1, 1 = disk 2) are in the blob, initialised to 0 by the image.
        org     $d6fa
        jmp     $bb400.l

        org     $bb400
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
.try:   tst.w   unit.l
        beq.s   .rd
        bsr.s   bpres                   ; trying drive B: does a drive answer there at all?
        tst.w   d0
        bne.s   .miss                   ; no: do not start the game's long waits on it
.rd:    clr.l   $68002.l
        clr.l   $6800e.l
        bsr.s   rd
        tst.w   d4
        bne.s   .c2
        cmpi.l  #$4d4f4f4e,$68002.l
        bra.s   .cc
.c2:    cmpi.l  #$66055505,$6800e.l
.cc:    beq.s   .ok
.miss:  eori.w  #1,unit.l               ; mismatch or read error: the other drive (flips back after the second failure)
        dbra    d5,.try
        moveq   #1,d0
        bra.s   .out
.ok:    move.w  unit.l,(a2,d4.w)        ; the drive that holds this disk is the preferred one from now on
        moveq   #0,d0
.out:   movem.l (sp)+,d4-d5/a2
        rts

; Does a drive with a disk answer on B?  (1) A restore (no spin-up wait: h=1) must reach track 0 without seek error within ~1.2 s (the wait loop is 42 cycles a pass at 8 MHz
; in the game's own code; here the same loop shape): a drive that is not there never shows TR00, the FD1772 steps 255 times (0.77 s at 3 ms) and ends with seek error, or no
; interrupt comes at all: forced interrupt.  (2) With a drive there, an INDEX pulse must show in the Type I status (bit 1) within ~1.5 s (11k status reads, about 130 us each
; with the game's register delays): a disk rotates (the ST drives spin while selected, the pulse comes every 200 ms); an empty drive never gives one, and then the game's own
; read would wait out its restore / seek / read timeouts ($60000 / $60000 / $40000 loops) for nothing.  Those waits are only entered once a disk has answered.
; Out: d0 = 0 a drive with a disk answers, 1 not.  B is deselected afterwards; TOS's floppy VBL is kept off the FDC with $43e as sub_00ce64 does.
bpres:  move.l  d1,-(sp)
        move.w  $43e.w,-(sp)
        st.b    $43e.w
        moveq   #3,d0                   ; PSG port A bits: drive B, side 0 (%011, active low)
        jsr     $cf0e.l
        move.w  #$80,$ff8606.l          ; command register
        moveq   #$0b,d0                 ; restore, h=1, V=0, 3 ms
        jsr     $cf8e.l
        move.l  #$38000,d1
.w:     btst.b  #5,$fffffa01.w          ; GPIP bit 5 low = FDC interrupt
        beq.s   .d
        subq.l  #1,d1
        bne.s   .w
        jsr     $cf5a.l                 ; nothing came: force an interrupt
        moveq   #1,d0
        bra.s   .o
.d:     jsr     $cf78.l                 ; status (d0 = status & $ff)
        btst    #4,d0                   ; seek error
        bne.s   .no
        btst    #2,d0                   ; TR00
        beq.s   .no
        move.l  #$2d00,d1
.ix:    jsr     $cf78.l                 ; status again: bit 1 = index pulse
        btst    #1,d0
        bne.s   .y
        subq.l  #1,d1
        bne.s   .ix
        bra.s   .no
.y:     moveq   #0,d0
        bra.s   .o
.no:    moveq   #1,d0
.o:     move.l  d0,-(sp)
        moveq   #7,d0                   ; deselect
        jsr     $cf0e.l
        move.l  (sp)+,d0
        move.w  (sp)+,$43e.w
        move.l  (sp)+,d1
        rts

unit:   dc.w    0                       ; drive of the last successful check (0 A, 1 B)
pref:   dc.w    0,0                     ; preferred drive per disk: disk 1, disk 2
