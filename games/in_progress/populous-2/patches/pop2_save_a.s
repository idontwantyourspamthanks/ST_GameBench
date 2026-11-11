; name: pop2_save_a
; default: no
; site: $140
; orig: 48e73ffe2849
; data: PB+$2f0 2
; note: Part A of the in-game save/load fix (part B = pop2_save_b; they ship together).  PP's `jmp $140` replaced the game's whole disk layer
; note: $36efc (`movem.l d1-d7/a0-a6,-(a7)` ... a command dispatcher: d0 = 0 read file, 1, 2, 3 ... 5, a0 = file name, a1 = buffer) by a stub that
; note: only knows "copy file number N out of the P2D image in RAM" and ignores d0, so SAVE GAME / LOAD GAME / the file requester (callers $2cb0e,
; note: $2cbe4, $2cc58) are answered with garbage and the game crashes (work/notes/delivery.md).  Fix: the stub entry runs PP's code only when
; note: the file-by-number function $2cc98 has just announced a file number (flag at PB+$2f0, set by pop2_save_b); every other call runs the
; note: game's own code (its own FAT12 + FDC driver) by re-executing the displaced prologue and continuing at $36f00.
FLAG    equ     PB+$2f0
STUBENT equ     PB+$300

        org     $140
        jmp     STUBENT.l

        org     PB+$300
        tst.b   FLAG.l
        beq.s   .orig
        clr.b   FLAG.l
        movem.l d2-d7/a0-a6,-(a7)       ; PP's displaced prologue
        movea.l a1,a4
        jmp     $146.w                  ; the rest of PP's stub
.orig:  movem.l d1-d7/a0-a6,-(a7)       ; the game's own prologue of $36efc
        jmp     $36f00.l
