p='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/patches/mx_sync.s'
s=open(p).read()
s=s.replace("TSTART  equ     $B8F48          ; long: clock at the start of the extra frame being drawn\n","TSTART  equ     $B8F48          ; long: clock at the start of the extra frame being drawn\nVBLU    equ     $B8F4C          ; word: clock units per VBL (6 at 50 Hz, 5 at 60 Hz)\n")
# set VBLU at entry
s=s.replace("""        clr.w   NEXTRA.l
        bsr     readclk
        addq.l  #6,d0                   ; the flipped frame is displayed from the next VBL
        move.l  d0,TMAIN.l""","""        clr.w   NEXTRA.l
        moveq   #5,d0
        btst    #1,$ffff820a.w          ; bit 1 set = 50 Hz
        beq.s   .hz
        moveq   #6,d0
.hz:    move.w  d0,VBLU.l
        bsr     readclk
        add.w   VBLU.l,d0               ; the flipped frame is displayed from the next VBL
        move.l  d0,TMAIN.l""")
# unknown estimate
s=s.replace("""        move.l  TMAIN.l,d1              ; no estimate yet: the main pass's own duration
        subq.l  #6,d1
        sub.l   NEXT.l,d1
        add.l   #TICK,d1
        cmp.l   #6,d1
        bgt.s   .have
        moveq   #6,d1""","""        move.l  TMAIN.l,d1              ; no estimate yet: the main pass's own duration
        sub.w   VBLU.l,d1
        sub.l   NEXT.l,d1
        add.l   #TICK,d1
        cmp.w   VBLU.l,d1
        bgt.s   .have
        move.w  VBLU.l,d1""")
s=s.replace("""        move.l  d6,d2
        add.l   d1,d2
        addq.l  #6,d2                   ; display time of this frame""","""        move.l  d6,d2
        add.l   d1,d2
        add.w   VBLU.l,d2               ; display time of this frame""")
s=s.replace("""        sub.l   TSTART.l,d0             ; duration in clock units (VBL granular)
        cmp.l   #6,d0
        bge.s   .dm
        moveq   #6,d0""","""        sub.l   TSTART.l,d0             ; duration in clock units (VBL granular)
        cmp.w   VBLU.l,d0
        bge.s   .dm
        move.w  VBLU.l,d0""")
# wantnext unknown-estimate
s=s.replace("""        move.l  TMAIN.l,d2
        subq.l  #6,d2
        sub.l   NEXT.l,d2
        add.l   #TICK,d2""","""        move.l  TMAIN.l,d2
        sub.w   VBLU.l,d2
        sub.l   NEXT.l,d2
        add.l   #TICK,d2""")
# decay lower limit: 2 VBL
s=s.replace("""        move.w  DEXT.l,d0
        cmp.w   #12,d0
        bls     .done""","""        move.w  DEXT.l,d0
        cmp.w   #12,d0
        bls     .done""")
# sound flag: zero $11ce at group start (restored by restoreundo with $11c4-$11cf)
s=s.replace("""        bsr     saveundo                ; lazily: only when a first extra frame is really drawn
""","""        bsr     saveundo                ; lazily: only when a first extra frame is really drawn
        clr.b   $11ce.w                 ; the HUD item $f620 plays its alarm sound once for this flag: the main frame does that (flag restored below)
""")
open(p,'w').write(s)
print("ok")
