; name: p3b_par
; default: no
; site: $33cc2
; orig: 3a38764c3c387680
; note: SCRATCH (MW2VehAir). Type 17 (Parachute) block of sub_033bde ($33cc2). Original per tick:
;         vk = $7680 (set by apply sel 3, $34586: clamp($7680+$6740,-100,-10))
;         alt += vk ; $7680 = 2*vk                       (the exponential fall)
;         alt < 0            -> type 21 (Swimming)
;         AGL = alt - $66e4  (ground at the tick START, from $3489a) ; AGL < 50 -> type 5, bank 0
;         speed $6740 = clamp(AGL/10, 0, 100) -> $344ac -> position along the heading
;       The doubling is a once-per-tick state update, so it is NOT split: the 5 Hz game's $7680 sequence
;       is kept (v_k = clamp(2 v_{k-1} + b, -100, -10)) and only its effect on the altitude is spread:
;         first pass (HOLD = 0): VK = vk, FA = alt + vk (the altitude the tick ENDS on), $7680 = 2*vk,
;                                Bresenham remainder cleared
;         every pass:            alt += floor((rem + VK)/5) (sum over 5 passes = VK exactly)
;         passes 1..4:           AGL = FA - $66e4 (the tick-end value) -> straight to the speed code
;                                ($33d00); no transition test (they would fire early)
;         pass 5:                alt == FA: the original tests from $33cd2 (type 21 / type 5 / speed)
;       Everything the original computes from AGL (speed) therefore sees the group-end value on all 5
;       passes, so p3b_pos's 5 steps sum to the original tick step (heading frozen by p3b_hdg HF).
D       equ     $b42e0
D2      equ     $b8f00
PVK     equ     D2+6
PFA     equ     D2+8
PREM    equ     D2+10
PTR     equ     D2+12
        org     $33cc2
        jsr     $b8400.l
        nop

        org     $b8400
        tst.w   D+8.l                   ; SUB
        bne.s   .sub
        move.w  $764c.w,d5              ; displaced
        move.w  $7680.w,d6
        rts
.sub:   addq.l  #4,a7
        tst.w   D+10.l                  ; HOLD
        bne.s   .step
        move.w  $7680.w,d6              ; vk
        move.w  d6,PVK.l
        move.w  $764c.w,d5
        add.w   d6,d5
        move.w  d5,PFA.l                ; altitude the 5 Hz tick ends on
        add.w   d6,d6
        move.w  d6,$7680.w              ; the doubling, once per tick
        clr.w   PREM.l
        clr.w   PTR.l                   ; TR = 1: the 5 Hz tick ends in a transition (type 21 / type 5):
        tst.w   d5                      ;   the original does not move in that tick
        bmi.s   .tr
        sub.w   $66e4.w,d5
        subi.w  #$32,d5
        bpl.s   .step
.tr:    addq.w  #1,PTR.l
.step:  move.w  PVK.l,d1
        lea     PREM.l,a1
        jsr     $b4d14.l                ; d0.l = 2q
        asr.w   #1,d0
        add.w   d0,$764c.w
        cmpi.w  #5,D+6.l                ; PH
        beq.s   .last
        move.w  PFA.l,d0
        sub.w   $66e4.w,d0
        move.w  d0,$66e2.w              ; AGL of the tick end
        tst.w   PTR.l
        beq.s   .go
        jmp     $33e30.l                ; transition tick: no movement (the original skips $344ac)
.go:    jmp     $33d00.l
.last:  move.w  $764c.w,d5
        jmp     $33cd2.l
