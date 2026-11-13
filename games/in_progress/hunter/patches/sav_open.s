; name: sav_open
; default: no
; hdonly: yes
; site: $c0268
; orig: 3f3c003d4e41508f
; note: Creates a missing file when the game WRITES (second half of the HD Save feature, see sav_hook.s).  PP's loader D15R ($c0100) opens its
; note: file with `move.w #$3d,-(a7) / trap #1 / addq.l #8,a7` (Fopen, mode in the word below the name: 1 when `$c0742 = $5772` = write mode) and
; note: never creates.  Here the Fopen is made as before; only if it fails with -33 (file not found) in write mode, the call is repeated as
; note: Fcreate (`$3c`, attribute word 0 in place of the mode).  A read open, a successful open and every other error are untouched.  The same bytes
; note: ($c0100..$c0733) are in D15R_F5.FIC, the TT/Falcon loader (`huntpatch.py verify` checks it).
SAVOPEN equ     $8cb2c

        org     $c0268
        jmp     SAVOPEN.l
        nop                             ; the 8 bytes `move.w #$3d,-(a7) / trap #1 / addq.l #8,a7` become jmp + nop

        org     $8cb2c
sav_open:
        move.w  #$3d,-(a7)              ; Fopen: the original three instructions
        trap    #1
        tst.l   d0
        bpl.s   .out
        cmpi.w  #$5772,$c0742.l         ; only a write can create
        bne.s   .out
        cmp.l   #-33,d0                 ; EFILNF
        bne.s   .out
        clr.w   6(a7)                   ; Fcreate(name, attribute 0)
        move.w  #$3c,(a7)
        trap    #1
.out:   addq.l  #8,a7
        jmp     $c0270.l
