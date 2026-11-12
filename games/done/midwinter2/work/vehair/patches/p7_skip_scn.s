; name: p7_skip_scn
; default: yes
; site: $1dc12
; orig: 31fc000867c4
; phase: deferred
; note: P7 item 5(a), part 2/7 (work/notes/p7_static_skip.md).  Scene renderer $1dc12 (stub $505c), entered
;       from $1dbbe (return address $1dbe2) and from the alternate scene render $328e2.  A call from anywhere
;       but $1dbe2 draws a different image into the back buffer: clear VAL[] (p7_skip_render).  A call from
;       $1dbe2 sets SCN: the camera was not below the terrain, so $1dcae-$1dcca (wave phase advance) runs;
;       p7_skip_render records SCN per buffer and replays that advance when it skips.
;       Displaces `move.w #$8,$67c4.w` (6 bytes); rejoins at $1dc18.
D       equ     $b6000
VAL     equ     D+$00
NINV    equ     D+$1c
SCN     equ     D+$38

        org     $1dc12
        jmp     $b7c40.l

        org     $b7c40
        cmpi.l  #$1dbe2,(a7)
        beq.s   .m
        clr.l   VAL.l
        addq.l  #1,NINV.l
        bra.s   .x
.m:     move.w  #1,SCN.l
.x:     move.w  #$8,$67c4.w             ; displaced
        jmp     $1dc18.l
