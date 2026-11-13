; name: sav_hook
; default: no
; hdonly: yes
; requires: sav_open
; site: $d542
; orig: 4ef900000150
; note: Working in-game Save and Load on the HD build (idea 10 of reports/hunter_ideas.md; work/notes/save.md).  The game's disk layer is called through
; note: `jmp $d30e` from three places ($108e4 plain load, $10926 `moveq #0,d3` read, $10952 `moveq #$fe,d3` write); on the HD build $d30e ends in
; note: `$d542: jmp $150.l`, PP's file hook, which ignores d3 and always READS `FILES\<hex digit of d0>`.  So a "write" was a read of the same file back
; note: into the game's buffer (the Save list showed PP's decoy names from the dir template in FILES/0, and a Save click re-read FILES/0 over the game's
; note: variables).  This patch sits in front of the hook (the site) and handles only the disk menu's files; everything else goes to `jmp $150.l`:
; note:   d0 = $0f  the directory (224 B: "HUNTER SAVES 1.1" + 6 x 32).  Read: FILES\SAVES.DIR; missing or not 224 B = a fresh directory (6 x "free*",
; note:                what the game's own Init Disk builds).  Write: FILES\SAVES.DIR.
; note:   d0 = $10..$15  the six slot files, 51,328 B (the game checksums all of it: word at +$3e, loop at $10442).  FILES\SLOT1.SAV .. SLOT6.SAV.  Read:
; note:                the size and the game's checksum are verified here (the game's own compare is nopped by the crack); a slot that is not valid shows
; note:                a dialog and the load is abandoned (the stack returns to $10344, so nothing of the buffer is applied).  Write: the loader writes the file.
; note:   d0 = 0, d3 = $fffe  (the "write file 0" every Load/Save click does at $1032a; $10fb2, 70,000 B): nothing to write, skipped.  It would only
; note:                overwrite PP's FILES\0 with the running game's variables (on the floppy that file is rewritten; PP made it a re-read).
; note: Disk I/O is PP's own loader (D15R `$c0100+4`, write mode `$c0742 = $5772`) called exactly as `$150` calls it.  A missing file on a write is created by
; note: sav_open.  Failure: a dialog in the game's own menu style (`jsr $1f6e`, title + one button; the button's handler is $8cda `moveq #0,d0 / rts`), and
; note: for a failed slot write bit 3 of $95(a5) is set, which the Save code ($100ca `bsr $10338 / bne $10008`: `bclr #3,$95(a5)` at $10348) turns into an
; note: abort, so the directory is not updated and the slot stays "free".
; note: Machines: none-specific (a bus-free 68000 routine); the floppy build has the cracker's loader at $d30e and is not touched (hdonly).
SLOTLEN equ     51328
DIRLEN  equ     224
SAVHOOK equ     $8c72c

        org     $d542
        jmp     SAVHOOK.l               ; replaces `jmp $150.l` (PP's file hook, which stays the fall-through)

        org     $8c72c
sav_hook:
        moveq   #0,d1
        move.b  d0,d1                   ; file number (d0 may carry garbage above the byte, PP uses the byte)
        cmp.w   #$fffe,d3
        beq.s   .w
        cmpi.b  #$f,d1
        beq.s   .rdir
        cmpi.b  #$10,d1
        blo.s   .pp
        cmpi.b  #$15,d1
        bls     .rslot
.pp:    jmp     $150.l                  ; every other read, and every other write, is exactly as before

.w:     cmpi.b  #$f,d1
        beq     .wdir
        cmpi.b  #$10,d1
        blo.s   .w0
        cmpi.b  #$15,d1
        bls     .wslot
        bra.s   .pp
.w0:    tst.b   d1
        bne.s   .pp
        jmp     $d60a.l                 ; write of file 0: skipped (the hook's own exit: pops d0-d7/a0-a4)

; ---- directory read -----------------------------------------------------------------------------------------------------
.rdir:  lea     n_dir(pc),a1
        move.l  #DIRLEN,d2
        moveq   #0,d4
        bsr     ldcall
        cmp.l   #DIRLEN,d0
        bne.s   .fresh
        cmpi.l  #'HUNT',(a0)
        beq.s   .ok
.fresh: movea.l a0,a1                   ; a fresh directory: the game's Init Disk output
        lea     dirhdr(pc),a2
        moveq   #3,d0
.h:     move.l  (a2)+,(a1)+
        dbra    d0,.h
        moveq   #3,d0
.z:     clr.l   (a1)+
        dbra    d0,.z
        moveq   #5,d1
.e:     st      (a1)+                   ; byte 0 = $ff: the slot is free
        moveq   #14,d0
.z1:    clr.b   (a1)+
        dbra    d0,.z1
        move.l  #'free',(a1)+
        move.b  #'*',(a1)+
        moveq   #10,d0
.z2:    clr.b   (a1)+
        dbra    d0,.z2
        dbra    d1,.e
.ok:    jmp     $d60a.l

; ---- slot read ----------------------------------------------------------------------------------------------------------
.rslot: bsr     slotname                ; a1 = FILES\SLOTn.SAV
        move.l  #SLOTLEN,d2
        moveq   #0,d4
        bsr     ldcall
        cmp.l   #SLOTLEN,d0
        bne.s   .rbad
        move.w  #$1b0,d1                ; the game's checksum ($10442): $1b0 + all 25,664 words with the word at +$3e taken as $b241
        movea.l a0,a1
        move.w  #$643f,d3
.s:     add.w   (a1)+,d1
        dbra    d3,.s
        move.w  $3e(a0),d2
        sub.w   d2,d1
        add.w   #$b241,d1
        cmp.w   d2,d1
        beq     .ok
        lea     l_damaged(pc),a1
        bra.s   .lfail
.rbad:  lea     l_missing(pc),a1        ; -33: no such file
        cmp.l   #-33,d0
        beq.s   .lfail
        lea     l_damaged(pc),a1        ; short file
        tst.l   d0
        bpl.s   .lfail
        lea     l_readerr(pc),a1
.lfail: bsr     dialog
        movem.l (a7)+,d0-d7/a0-a4       ; the frame the game's $d53e pushed
        cmpi.l  #$103c2,(a7)            ; called from $103be, the slot read of the Load code ($10350 reached by `bsr.b` at $10342)?
        bne.s   .lerr
        addq.l  #4,a7                   ; abandon the load: nothing of the buffer is applied; the game continues at $10344 ($10338's end)
        cmpi.l  #$1005c,4(a7)           ; ... and $10338 was called by the Load menu handler ($10058)?
        bne.s   .lret
        move.l  #$10008,4(a7)           ; then return as the list's CANCEL does: $10008 `moveq #$ff,d0 / rts`, so the disk menu
                                        ; redraws as after CANCEL instead of continuing into the mission page ($1005c..)
.lret:  rts
.lerr:  moveq   #-1,d0
        rts

; ---- slot write / directory write ---------------------------------------------------------------------------------------
.wslot: bsr     slotname
        move.l  #SLOTLEN,d2
        bra.s   .wr
.wdir:  lea     n_dir(pc),a1
        move.l  #DIRLEN,d2
.wr:    move.w  #$5772,d4
        bsr     ldcall
        cmp.l   d2,d0
        beq     .ok
        bset    #3,$95(a5)              ; the game's error bit: the Save code skips the directory write ($100ca bne $10008)
        lea     s_err(pc),a1
        tst.l   d0
        bpl.s   .full
        cmp.l   #-36,d0
        bne.s   .e1
        lea     s_access(pc),a1
.e1:    cmp.l   #-13,d0
        bne.s   .e2
        lea     s_wprot(pc),a1
.e2:    cmp.l   #-33,d0
        beq.s   .nf
        cmp.l   #-34,d0
        bne.s   .show
.nf:    lea     s_nofolder(pc),a1
        bra.s   .show
.full:  lea     s_full(pc),a1
.show:  bsr     dialog
        jmp     $d60a.l

; ---- helpers ------------------------------------------------------------------------------------------------------------
; slotname: a1 = "SLOTn.SAV" for file d1 = $10..$15 (n = 1..6)
slotname:
        lea     n_slot(pc),a1
        move.b  d1,d0
        add.b   #'1'-$10,d0
        move.b  d0,4(a1)
        rts

; ldcall: the loader call exactly as PP's $150 makes it.  a0 = buffer, a1 = name, d2 = length, d4 = 0 read / $5772 write.
; Out: d0 = $c0358 (bytes done, negative = GEMDOS error).  Keeps a0, d1, d2, d4; trashes d0, d3, a1-a3.
ldcall: clr.l   $c0736.l
        move.l  d2,$c073a.l
        move.l  a0,$c073e.l
        move.w  d4,$c0742.l
        lea     $c0752.l,a2
.n:     move.b  (a1)+,(a2)+
        bne.s   .n
        move.w  sr,-(a7)
        move.w  #$2700,sr
        lea     $c0100.l,a3
        moveq   #0,d0
        move.w  4(a3),d0
        adda.l  d0,a3
        jsr     (a3)
        clr.w   $c0734.l
        move.l  #$5b4e748b,$1e02.w      ; PP's hook does this after every call
        move.w  (a7)+,sr
        move.l  $c0358.l,d0
        rts

; dialog: a1 = the message, NUL-terminated and ended by '*' (the game's text printer stops at '*').  The disk menu's own
; error message uses the same tools ($1027c: jsr $663e - clear the page and print - / bsr $10dd0 - wait for the mouse - /
; jsr $6658).  The caller redraws its screen afterwards (the Load list, or the 3D view).
dialog: movea.l a1,a0
        jsr     $663e.l
.rel:   btst.b  #4,$ce(a5)              ; the click that chose the slot may still be latched: wait for its release
        bne.s   .rel
.press: btst.b  #4,$ce(a5)              ; then for the next button press (what the game's own prompt waits for, $10dd0)
        beq.s   .press
        jsr     $6658.l
        rts

n_dir:  dc.b    'SAVES.DIR',0
n_slot: dc.b    'SLOT1.SAV',0
dirhdr: dc.b    'HUNTER SAVES 1.1'
s_full:  dc.b    10,11,'SAVE FAILED - DISK FULL*',0
s_wprot: dc.b    10,11,'SAVE FAILED - WRITE PROTECTED*',0
s_access: dc.b   10,11,'SAVE FAILED - ACCESS DENIED*',0
s_nofolder: dc.b 10,11,'SAVE FAILED - NO FILES FOLDER*',0
s_err:   dc.b    10,11,'SAVE FAILED - DISK ERROR*',0
l_missing: dc.b  10,11,'LOAD FAILED - FILE MISSING*',0
l_damaged: dc.b  10,11,'LOAD FAILED - FILE DAMAGED*',0
l_readerr: dc.b  10,11,'LOAD FAILED - READ ERROR*',0
        even
dlgbuf: ds.b    58
