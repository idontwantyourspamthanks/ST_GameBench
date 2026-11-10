; name: floppy_driveb
; media: floppy
; default: yes
; site: $10cea
; orig: 3d7c000201346100065261000126b03c00806716610003162d790002c34a015061000110b03c0080660661000062675270007200342e015c4eb900010da8342e015cc4fc000a2079000258a241f020020641000a342800084eb900010da820790002c34a0641000a34104eb900010da82d790002c34a01504eb900010db86000ff8a
; note: Two-drive floppy support (floppy build only).  The original game is hard-wired to drive A: `move.w #2,$134(a6)`
; note: at $10CEA (loader sub_010cd2), $10334 (save-disk reader) and $10F22 (writer); sub_011344 turns $134(a6) into the PSG
; note: port-A drive-select bits (2 = A, 4 = B).  Nothing ever sets 4, so a graphics disk (MWB) put in drive B was never read.
; note: Behaviour here mirrors Midwinter 2's own disk logic (sub_028b20: `eori.w #6,$27d34` = flip the drive code A<->B and retry
; note: once before asking for the disk): try the preferred drive (A at power-on) exactly as the original does; ONLY when the file
; note: check fails (read error or xor-16 mismatch, the place where the original shows "Insert graphics disk"), and only for
; note: the graphics-disk directory ($258A2 = $2590C), try the OTHER drive once before the prompt.  The other drive is first probed
; note: with a bounded FDC operation (restore + seek 0 + read sector 1 that must move the DMA pointer by 512, the game's own sub_011016/sub_01102e/sub_0110fe whose
; note: wait loops time out and force-interrupt), so an absent/empty drive cannot hang the loader (the game's normal read
; note: loop `$112CA` waits for the FDC IRQ with no timeout).  If the other drive answers, the file is re-read from it and, when
; note: the checksum is right, that drive becomes the preferred one for later graphics-disk loads (no more failed reads from A).
; note: One drive, correct disk in A: the only differences from the original are the `jmp` into this blob and a `tst.w`.
; note: FDC bookkeeping: the FD1772 has ONE track register for both drives, so every drive change saves the track register of the
; note: drive being left and loads the saved head position of the drive being entered (first use of B: restore).  After every
; note: load from B the loader switches back to A with A's track register, so the rest of the game (save/load menus, always
; note: drive A, MWC) sees exactly the original state.  The save disk stays on drive A.
; note: The site is the whole body of sub_010cd2 from the drive select to the checksum/error loop ($10CEA-$10D6B, 130 bytes,
; note: no branch from outside reaches the inside; the success exit $10D6C stays in the game so the deferred-patch hook there
; note: still works).  Blob range $B9400-$B97FF.
        org     $10cea
        jmp     $b9400.l

        org     $b9400
blob:   clr.w   tried.l
        tst.w   pref.l
        bne.s   .pb
        move.w  #2,$134(a6)             ; original: drive A
        jsr     $11344.l
        bra.s   .read
.pb:    moveq   #1,d3                   ; graphics disk was found in B last time
        bsr     switch
.read:  jsr     $10e1c.l                ; seek + read the file
        cmp.b   #$80,d0
        beq.s   .chk
        jsr     $11016.l                ; read failed: restore, retry once (original)
        move.l  $2c34a.l,$150(a6)
        jsr     $10e1c.l
        cmp.b   #$80,d0
        bne.s   .fail
.chk:   jsr     $10d78.l                ; xor-16 against the directory entry
        bne.s   .fail
        clr.w   tried.l
        move.w  cur.l,pref.l            ; the drive that worked is the preferred one
        tst.w   cur.l
        beq.s   .done
        moveq   #0,d3
        bsr     switch                  ; leave B: A selected, A's track register
.done:  jmp     $10d6c.l

.fail:  cmpi.l  #$2590c,$258a2.l        ; only the graphics disk may come from the other drive
        bne.s   .err
        tst.w   tried.l
        bne.s   .back
        move.w  #1,tried.l
        move.w  cur.l,d3
        eori.w  #1,d3                   ; the other drive
        bsr     probe
        bne.s   .nob
        move.l  $2c34a.l,$150(a6)
        bra     .read                   ; full read from the other drive
.nob:   clr.w   tried.l
        bra.s   .err
.back:  clr.w   tried.l                 ; the other drive failed too: back to the first one, then the original prompt
        move.w  cur.l,d3
        eori.w  #1,d3
        bsr     switch
.err:   moveq   #0,d0                   ; original error page and prompt ($10D1A-$10D68)
        moveq   #0,d1
        move.w  $15c(a6),d2
        jsr     $10da8.l
        move.w  $15c(a6),d2
        mulu.w  #$a,d2
        movea.l $258a2.l,a0
        lea     2(a0,d2.w),a0
        addi.w  #$a,d1
        move.w  8(a0),d2
        jsr     $10da8.l
        movea.l $2c34a.l,a0
        addi.w  #$a,d1
        move.w  (a0),d2
        jsr     $10da8.l
        move.l  $2c34a.l,$150(a6)
        jsr     $10db8.l
        bra     .read

; switch to drive d3 (0 = A, 1 = B): save the track register of the current drive, select d3, load its saved track.
; First use of a drive: restore (bounded).  Out: d0 = 0 ok, 1 = restore did not reach track 0 (no drive).
switch: jsr     $11214.l                ; d0 = FDC track register
        move.w  cur.l,d1
        add.w   d1,d1
        lea     pos(pc),a0
        move.w  d0,(a0,d1.w)
        move.w  d3,cur.l
        move.w  d3,d2
        add.w   d2,d2
        addq.w  #2,d2                   ; 2 = A, 4 = B
        move.w  d2,$134(a6)
        jsr     $11344.l
        move.w  d3,d1
        add.w   d1,d1
        lea     known(pc),a1
        tst.w   (a1,d1.w)
        bne.s   .have
        jsr     $11016.l                ; first use: head and track register to 0
        move.w  d3,d1
        add.w   d1,d1
        btst    #2,d0                   ; TR00 reached ...
        beq.s   .bad
        btst    #4,d0                   ; ... and no seek error (MiSTer: drive without an image reports RNF here)
        bne.s   .bad
        lea     known(pc),a1
        move.w  #1,(a1,d1.w)
        lea     pos(pc),a0
        clr.w   (a0,d1.w)
        moveq   #0,d0
        rts
.bad:   moveq   #1,d0
        rts
.have:  lea     pos(pc),a0
        move.w  (a0,d1.w),$136(a6)
        jsr     $1124c.l                ; track register := saved head position
        moveq   #0,d0
        rts

; probe drive d3: switch to it and read sector 1 of track 0 into pbuf (bounded FDC waits, two tries).
; Out: Z = 1 drive d3 is selected and answers; Z = 0 the previous drive is selected again.
probe:  move.w  cur.l,-(sp)
        bsr     switch
        tst.w   d0
        bne.s   .pf
        clr.w   $136(a6)
        jsr     $1102e.l                ; seek 0
        move.w  #1,-(sp)
.try:   lea     pbuf(pc),a0
        move.l  a0,$150(a6)
        move.w  #1,$13a(a6)
        jsr     $110fe.l                ; read sector 1 -> pbuf
        cmp.b   #$80,d0
        bne.s   .tf
        moveq   #0,d1                   ; a forced interrupt (nothing answered) also leaves status $80:
        move.b  $ff8609.l,d1            ; the sector really arrived only if the DMA pointer moved 512 bytes
        lsl.l   #8,d1
        move.b  $ff860b.l,d1
        lsl.l   #8,d1
        move.b  $ff860d.l,d1
        lea     pbuf+512(pc),a0
        cmp.l   a0,d1
        beq.s   .pok
.tf:    subq.w  #1,(sp)
        bpl.s   .try
        addq.l  #2,sp
.pf:    move.w  (sp)+,d3
        bsr     switch                  ; back to the old drive
        moveq   #1,d0
        rts
.pok:   addq.l  #4,sp
        moveq   #0,d0
        rts

cur:    dc.w    0                       ; drive the loader is on now (0 A, 1 B)
pref:   dc.w    0                       ; drive that held the graphics disk last time
tried:  dc.w    0
known:  dc.w    1,0                     ; head position known (A: yes; B: after the first restore)
pos:    dc.w    0,0                     ; saved track register per drive
        even
pbuf:   dcb.b   512,0
