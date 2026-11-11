; name: p3b_delta
; default: yes
; site: $130c8
; orig: 4eb900006a3a
; note: P5 (needs tick_* and p3b_interp). The pass's `jsr $6a3a` (first UI call, right after the men update `jsr $14b62`) is replaced by
;       `jsr dlt`; dlt ends with `jmp $6a3a` (the return goes to $130ce). On every pass that ran a world tick (D+6 RON = 0) it
;       rebuilds the mover list of p3b_interp from the people table ($51b66, 512 x $32 bytes, x/z = words $8/$a): one entry
;       {record byte offset, dx, dz, -, -} per record whose position differs from OLD (the positions after the previous scan)
;       by at most STEP (56) units per axis; bigger changes (teleport, spawn into a slot, the landing step of a projectile) get no
;       entry = no extrapolation. OLD := the new positions. NMOV (PD+2) = number of entries.
;       The scan only runs while render-only passes keep happening (D+12 RPASS changed during the last 8 ticks, PD+16 / PD+24 ACTIVE): a machine
;       that never has render-only passes (8 MHz: every pass is a tick pass) pays the check only, NMOV stays 0 and every frame is the
;       tick-only frame. When render-only passes start (a faster scene) the first interval has no list and the second a list
;       built against stale OLD (changes above STEP are dropped): smoothing is complete from the third tick.
;       Cost of a scan: ~52 cycles per record, 24-39 k cycles per tick (measured).
D       equ     $b8a00
PD      equ     $b8a80
OLD     equ     $b8d00
LST     equ     $b9500
PEOPLE  equ     $51b66
STEP    equ     56
        org     $130c8
        jsr     $b8bc0.l

        org     $b8bc0
dlt:    tst.w   D+6.l                   ; RON: no tick in this pass
        bne.s   .done
        movem.l d0-d7/a0-a2,-(a7)
        move.l  D+12.l,d0               ; RPASS: render-only passes so far
        cmp.l   PD+16.l,d0
        beq.s   .nor
        move.l  d0,PD+16.l
        move.w  #8,PD+24.l              ; ACTIVE: ticks left to scan for after the last render-only pass seen
        bra.s   .scan
.nor:   tst.w   PD+24.l                 ; 2 s without any: nothing to extrapolate for (an 8 MHz machine never starts)
        beq.s   .skip
        subq.w  #1,PD+24.l              ; (a pair of tick passes without a render-only pass between them is normal at 16 MHz)
.scan:  addq.l  #1,PD+20.l
        lea     PEOPLE+8.l,a0
        lea     OLD.l,a1
        lea     LST.l,a2
        moveq   #0,d3                   ; count
        move.w  #511,d2
.lp:    move.l  (a0),d0                 ; x.w:z.w
        cmp.l   (a1)+,d0
        bne.s   .chg
.nx:    lea     $32(a0),a0
        dbra    d2,.lp
        move.w  d3,PD+2.l
.out:   movem.l (a7)+,d0-d7/a0-a2
.done:  jmp     $6a3a.l
.skip:  clr.w   PD+2.l                  ; no list
        bra.s   .out
.chg:   move.l  -4(a1),d1
        move.l  d0,-4(a1)
        move.w  d0,d4
        sub.w   d1,d4                   ; dz
        swap    d0
        swap    d1
        sub.w   d1,d0                   ; dx
        cmpi.w  #STEP,d0
        bgt.s   .nx
        cmpi.w  #-STEP,d0
        blt.s   .nx
        cmpi.w  #STEP,d4
        bgt.s   .nx
        cmpi.w  #-STEP,d4
        blt.s   .nx
        move.l  a0,d6
        sub.l   #PEOPLE+8,d6            ; record byte offset
        move.w  d6,(a2)+
        move.w  d0,(a2)+
        move.w  d4,(a2)+
        addq.l  #4,a2
        addq.w  #1,d3
        bra.s   .nx
