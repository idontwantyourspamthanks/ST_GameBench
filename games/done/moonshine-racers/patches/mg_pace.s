; name: mg_pace
; default: yes
; site: $7b74
; orig: 4eb90000d1e4
; requires: mt_clock mt_pre mg_sync
; conflicts: mt_sync mx_sync mf_sync
; doc: Pacer of mg_sync: sleeps until the tick; flips the frame itself only when mg_sync's blob (site $7b52) did not (not plain racing).
; note: mx_sync's `newsync` without the extra frames: if FLIPPED ($B8F6E) is set the main frame was flipped at $7b52 (before the post stages); otherwise flip, PEND, bands, flip log here.  Then the unchanged sleep (CLK vs NEXT, MAXLAG resync, TICK).
TICK    equ     30
MAXLAG  equ     2*TICK
CLK     equ     $B8F00
NEXT    equ     $B8F04
PEND    equ     $B8F08
FLIPPED equ     $B8F6E
        org     $7b74
        jsr     $B8180.l

        org     $B8180
pace:   tst.b   FLIPPED.l
        bne.s   .fl
        jsr     $d1ca.l                 ; not flipped yet (finish / start sequences: $1024 != 0)
        move.b  #1,PEND.l
        clr.b   $611a.l
        move.w  $1302.w,$12fe.w
        move.w  $1304.w,$1300.w
        moveq   #0,d0
        jsr     $B8380.l
.fl:    clr.b   FLIPPED.l
.rd:    move.l  CLK.l,d0                ; torn-read safe long read
        cmp.l   CLK.l,d0
        bne.s   .rd
        sub.l   NEXT.l,d0               ; lag = now - next
        bmi.s   .rd                     ; not due yet: sleep until the tick
        cmp.l   #MAXLAG,d0
        bls.s   .ok
        move.l  CLK.l,d0                ; more than MAXLAG behind: resync, no burst
        cmp.l   CLK.l,d0
        bne.s   .rd
        move.l  d0,NEXT.l
.ok:    add.l   #TICK,NEXT.l
        rts
