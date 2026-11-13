; name: pop2_tick_snd
; default: yes
; site: $191e
; orig: 4eb90002b29a
; note: Fixed-rate world tick, part 7 of 8 (work/notes/timing.md; independent of the others, needed only at 60 Hz).  Sound timing: the VBL handler $18fa calls the sample
; note: sequencer `jsr $2b29a` ($191e) once per VBL while sound is on ($2cade): each call advances `$2b60e` through the sequence at `$2b81a` (pitch/sample steps, timer A data
; note: $2b610/$2b612 via $2a978).  Written for 50 Hz, it plays 20 % fast at 60 Hz.  This hook steps it in 1/300 s units: +6 per VBL at 50 Hz (sync mode bit 1 set), +5 at 60 Hz,
; note: one step per 6 units - every VBL at 50 Hz, five of six at 60 Hz.  Accumulator SACC = D+20 (word; zero in the payload image, and a junk value would be harmless: the first VBLs just step or skip).  Timer A sample playback itself is not tied to the VBL and is untouched.
D       equ     PB+$2800
oSACC   equ     20
        org     $191e
        jsr     PB+$2500.l

        org     PB+$2500
        moveq   #6,d0
        btst    #1,$ffff820a.w
        bne.s   .u
        moveq   #5,d0
.u:     lea     D+oSACC.l,a0
        add.w   d0,(a0)
        cmpi.w  #6,(a0)
        blo.s   .skip
        subq.w  #6,(a0)
        cmpi.w  #6,(a0)
        blo.s   .go
        clr.w   (a0)                    ; junk or a long gap: never more than one step per VBL
.go:    jmp     $2b29a.l
.skip:  rts
