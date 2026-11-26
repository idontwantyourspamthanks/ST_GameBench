; name: ms_cloud_b
; default: no
; site: $de6c
; orig: 45f829c82a781008
; doc: Cloud pass 2/2 skip (needs ms_cloud_a): the draw pass $de6c only repeats the rows >= 65 of the clouds when ms_cloud_a skipped the pass.
; note: See ms_cloud_a (work/notes/sprites.md).  $de6c = `lea.l $29c8.w,a2 / movea.l $1008.w,a5` (8 B) -> `jmp $BC400.l`.  When FLAG (set by the $de1c hook) is clear the original runs on at $de74.
; note: When set: per slot `$28 := SAVED` (the offset the draw would leave: the old $2a, equal because the keys match) and, for clouds reaching row 65 or below, the original draw kernel $15052
; note: is called for the rows >= 65 only (y := max(y, 65), rows and bitmap pointer advanced by the skipped rows: 8 B per bitmap row); finally $100c := the last slot's offset (the original leaves it so).
STATE   equ     $BCC00
FLAG    equ     STATE+8
SAVED   equ     STATE+$100
CNT     equ     STATE+$FE
        org     $de6c
        jmp     $BC400.l
        nop

        org     $BC400
cloud_b:
        lea     $29c8.w,a2
        movea.l $1008.w,a5
        tst.w   FLAG.l
        bne.s   .sk
        jmp     $de74.l                 ; the original continues with lea.l $6f000.l,a6
.sk:    clr.w   FLAG.l
        lea     $6f000.l,a6
        lea     SAVED.l,a0
        move.w  #11,CNT.l
.lp:    move.w  (a0)+,d0                ; the offset the draw would leave
        move.w  d0,$28(a2)
        cmpi.w  #$ffff,d0
        beq.s   .nx
        btst    #0,4(a2)
        beq.s   .nx
        move.w  $a(a2),d3               ; rows
        move.w  2(a2),d1                ; y
        move.w  d1,d2
        add.w   d3,d2
        cmpi.w  #65,d2
        ble.s   .nx
        moveq   #65,d4
        sub.w   d1,d4
        bpl.s   .r
        moveq   #0,d4                   ; r0
.r:     move.w  6(a2),d0                ; frame entry: $34 + 14 * ($6 + $8)
        add.w   8(a2),d0
        add.w   d0,d0
        move.w  d0,d2
        lsl.w   #3,d0
        sub.w   d2,d0
        movea.l $34(a2),a1
        adda.w  d0,a1
        tst.w   4(a1)
        ble.s   .nx                     ; the original draws nothing for a width <= 0
        movea.l (a1),a1                 ; bitmap, 8 B per row
        move.w  d4,d0
        lsl.w   #3,d0
        adda.w  d0,a1
        move.w  d3,d7
        sub.w   d4,d7                   ; rows left
        add.w   d4,d1                   ; y' = max(y, 65)
        move.w  (a2),d0                 ; x
        movem.l a0/a2,-(a7)
        jsr     $15052.l
        movem.l (a7)+,a0/a2
.nx:    lea     $38(a2),a2
        subq.w  #1,CNT.l
        bpl.s   .lp
        move.w  SAVED+22.l,$100c.w
        rts
