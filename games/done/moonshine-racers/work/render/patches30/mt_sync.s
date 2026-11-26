; name: mt_sync
; default: yes
; site: $7b74
; orig: 4eb90000d1e4
; data: $B8F04 4
; doc: Fixed real-time game tick, part 2 of 3: the race pass's pacer replaces the 2-VBL floor and the post-flip wait with a fixed schedule of TICK/300 s per pass.
; note: Fixed tick, part 2 of 3.  Site: $7b74 `jsr $d1e4.l` (the race loop's last call; $d1e4 itself is NOT touched: it also serves $7496) -> `jsr $B8100.l`.
; note: The blob flips with the unchanged $d1ca, marks PEND, clears $611a, then sleeps until CLK reaches the scheduled start NEXT ($B8F04) and adds TICK to it.
; note: More than MAXLAG (2*TICK) behind (pause, disk, stall): the schedule is reset to now (no burst of passes).  A machine too slow for TICK simply does not sleep.
; note: TICK (1/300 s units; 36 = 6 VBL at 50 Hz = 8.333 pass/s = stock 8 MHz driving speed) is the ONE equate to change (30 = 10 pass/s).
TICK    equ     30
MAXLAG  equ     2*TICK
PEND    equ     $B8F08
NEXT    equ     $B8F04
CLK     equ     $B8F00
        org     $7b74
        jsr     $B8100.l

        org     $B8100
newsync:
        jsr     $d1ca.l                 ; flip (unchanged routine)
        move.b  #1,PEND.l               ; its latch is now pending
        clr.b   $611a.l                 ; keep the stock meaning of $611a for any other user
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
