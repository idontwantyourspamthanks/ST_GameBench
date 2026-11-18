; name: ed_floppy_capture
; media: floppy (reference code for the floppy build's boot stub; NOT part of any HD build, no .nep)
; doc: work/notes/editor.md section 13.4
; note: The editor's campaign-disk Load/Save calls TOS (a "TOS excursion": swap the TOS-owned low RAM $8..$8+(n+1)*48 back in, restore TOS's MFP state, call GEMDOS
; note: at SR $2500, swap everything back).  PP's Gamex START.TOS keeps the needed copy of the TOS state ($c0108 on 1 MB, $102008 on 4 MB; its address is the long at
; note: $ffd80, the count word at $ffd86, TOS's MFP block at $fffaa).  The floppy build has no Gamex, so its boot stub must take the same snapshot ONCE, at the very
; note: start (before the game's init clears $8700..$33a4f) and publish it to the editor through three runtime-state variables (ed_editor.s: RS+rsTosP long, RS+rsTosN word,
; note: RS+rsMfpP long); the editor uses them when rsTosP is non-zero and reads $ffd80/$ffd86/$fffaa only when it is zero (the HD build).
; note: UNTESTED on the floppy flow (this tree has no floppy harness that runs the editor's disk code): see editor.md 13.4 for what has to be checked there.
; note: Assemble inside the stub with the editor's symbols (mfp_save is the editor routine that reads the 24 MFP registers into V+vMfp and finds the timers' reload
; note: values by max-scan); `capture` is entered with SR = $2700 from the stub, before `jmp $38624`.
RS      equ     $77c80
V       equ     $77cc0
vMfp    equ     92
rsTosP  equ     52
rsTosN  equ     56
rsMfpP  equ     58
CAP     equ     $C0108                  ; free on a >= 1 MB machine (the HD build's Gamex copy is here too); the editor needs >= 1 MB anyway

capture:
        movem.l d0-d7/a0-a6,-(a7)
        move.l  $432.w,d1               ; membot: everything below is TOS's own state (basepage of the running loader, TPA start)
        subq.l  #8,d1
        divu.w  #48,d1
        and.l   #$ffff,d1               ; d1 = whole 48-byte units in $8..membot
        move.w  d1,d2
        subq.w  #1,d2
        move.w  d2,RS+rsTosN.l          ; the editor's (n+1)*48 = d1*48 bytes
        move.l  #CAP,RS+rsTosP.l
        lea     8.w,a0
        lea     CAP.l,a1
        mulu.w  #2,d1                   ; 24-byte steps
        subq.w  #1,d1
.c:     movem.l (a0)+,d3-d7/a2
        movem.l d3-d7/a2,(a1)
        lea     24(a1),a1
        dbra    d1,.c
        move.l  a1,-(a7)
        bsr.w   mfp_save                ; V+vMfp = the MFP registers as they are now (TOS-owned at this moment: nothing of the game has run yet)
        move.l  (a7)+,a1
        lea     V+vMfp.l,a0
        move.l  a1,RS+rsMfpP.l          ; the 24-byte block follows the copy
        moveq   #23,d0
.m:     move.b  (a0)+,(a1)+
        dbra    d0,.m
        movem.l (a7)+,d0-d7/a0-a6
        rts
