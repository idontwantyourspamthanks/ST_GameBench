; standalone copy of jag_poll's probe (FALCON = 1) + a raw group scan, run as a PRG on every machine type (work/jagpad/probe_prg.py)
JAGST   equ     $70300
FALCONX equ     1
J_ST    equ     0
        section text
start:  pea     super(pc)
        move.w  #38,-(sp)
        trap    #14
        addq.l  #6,sp
        clr.w   -(sp)
        trap    #1
super:  move.w  #$2700,sr
        bsr     probe
        move.b  JAGST,$70200            ; verdict
        move.l  #'DONE',$70250
        cmpi.b  #1,JAGST
        bne.s   idle
scan:   lea     $70220,a4
        lea     $ffff9200.w,a1
        lea     sels(pc),a2
        moveq   #3,d7
.g:     move.w  (a2)+,2(a1)
        move.w  #3000,d0
.w:     dbra    d0,.w
        move.l  (a1),(a4)+
        dbra    d7,.g
        move.w  #$ffff,2(a1)
        addq.l  #1,$70204
        bra.s   scan
idle:   bra.s   idle
sels:   dc.w    $ffee,$ffdd,$ffbb,$ff77
probe:
        lea     JAGST,a3
        moveq   #-1,d4                  ; verdict: no
        movea.l a7,a2                   ; bus error guard: the handler puts a7 back here
        moveq   #0,d5                   ; VBR (a 68000 has none)
        moveq   #1,d0
        suba.l  a0,a0
        dc.w    $43f0,$0200             ; lea (0,a0,d0.w*2),a1: 1 on a 68000, 2 on a 68020+
        cmpa.w  #1,a1
        beq.s   .v0
        ifeq    FALCONX
        bra     .pfin                   ; 68020+ (TT, Falcon) = no pad (FALCONX equ 0): no hardware is touched
        endc
        dc.w    $4e7a,$5801             ; movec vbr,d5 (68020+ only)
.v0:    move.w  sr,d6
        ori.w   #$700,sr
        movea.l d5,a1
        addq.l  #8,a1                   ; a1 = the bus error vector
        move.l  (a1),d7
        lea     .berr(pc),a0
        move.l  a0,(a1)
        moveq   #0,d3                   ; stage 0: the DMA sound register must answer (ST / Mega ST fault)
        tst.b   $ffff8901.w
        moveq   #1,d3                   ; stage 1: the SCU must fault (a Mega STE and a TT have it)
        tst.b   $ffff8e01.w
        bra.s   .done                   ; it answered: no pad ports
.berr:  movea.l a2,a7                   ; (entered by a bus error)
        cmpi.b  #1,d3
        bne.s   .done                   ; fault in stage 0 or 2: no
        moveq   #2,d3                   ; stage 2: the pad registers must answer
        move.w  #$ffff,$ffff9202.w      ; deselect every group
        move.w  $ffff9202.w,d1
        move.w  $ffff9200.w,d2
        andi.w  #$ff00,d1               ; idle sanity: all direction / keypad lines high ...
        cmpi.w  #$ff00,d1
        bne.s   .done
        andi.w  #$000f,d2               ; ... and all button lines high
        cmpi.w  #$000f,d2
        bne.s   .done
        moveq   #1,d4
.done:  move.l  d7,(a1)
        move.w  d6,sr
.pfin:  move.b  d4,J_ST(a3)
        bgt.s   .yes
        bra     .out
.yes:
.out:   rts
