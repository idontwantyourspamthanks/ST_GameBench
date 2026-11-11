; core.s - Populous patch delivery mechanism (always installed by poppatch.py).
; Assembled into the payload image at $B3000.  Image layout (poppatch.py IMG_BASE / TABLE):
;   $B3000  header   'POPP' magic, marker.l, flags.l, reserved.l
;   $B3010  apply    called by the loader (patches/loader.s) after Pexec(3) of a game program and
;                    before Pexec(4): d0.w = program (0 DEMO.TOS, 1 POPULOUS.TOS), a1 = its base page.
;                    All registers are preserved.
;   $B3100  site table (entries {addr.l len.w prog.w orig.l new.l}, addr 0 ends) + byte pool, up to $B3FFF
;   $B4000  patch blobs ... $B7FFF is poppatch.py's, $C0000-$C7FFF is reserved for the land-score code.
; Marker (MARKER = $B3004): 'POPF' preset, 'POPO' once the POPULOUS.TOS sites were verified and applied,
;   'POPT' when the loaded text base is not the one the sites were built for, 'POPF' again if any site's
;   original bytes differ (nothing is applied then: all or nothing per program).
; flags.l (FLAGS = $B3008): bit 0 DEMO.TOS sites applied, bit 1 POPULOUS.TOS sites applied.
IMG     equ     $b3000
MARKER  equ     $b3004
FLAGS   equ     $b3008
TABLE   equ     $b3100
TNOM    equ     $ad96                   ; text base of POPULOUS.TOS / DEMO.TOS in PP's layout (loader.s keeps it)

        org     $b3000
        dc.b    'POPP'
        dc.b    'POPF'
        dc.l    0
        dc.l    0

        org     $b3010
apply:  movem.l d0-d7/a0-a6,-(a7)
        moveq   #0,d7
        move.w  d0,d7                   ; d7 = program
        cmpi.l  #TNOM,8(a1)             ; p_tbase of the program that was just loaded
        beq.s   .base
        move.l  #'POPT',MARKER.l
        bra.s   .out
.base:  lea     TABLE.l,a0              ; pass 1: every original byte of this program's sites must match
.v:     move.l  (a0)+,d0                ; addr, 0 = end
        beq.s   .apply
        move.w  (a0)+,d1                ; len
        move.w  (a0)+,d2                ; program
        movea.l (a0)+,a2                ; orig bytes
        addq.l  #4,a0                   ; skip new
        cmp.w   d7,d2
        bne.s   .v
        movea.l d0,a3
        subq.w  #1,d1
.vb:    cmpm.b  (a2)+,(a3)+
        dbne    d1,.vb
        beq.s   .v                      ; all len bytes equal
        move.l  #'POPF',MARKER.l        ; mismatch: apply nothing
        bra.s   .out
.apply: lea     TABLE.l,a0              ; pass 2
.a:     move.l  (a0)+,d0
        beq.s   .done
        move.w  (a0)+,d1
        move.w  (a0)+,d2
        addq.l  #4,a0                   ; skip orig
        movea.l (a0)+,a2                ; new bytes
        cmp.w   d7,d2
        bne.s   .a
        movea.l d0,a3
        subq.w  #1,d1
.ab:    move.b  (a2)+,(a3)+
        dbra    d1,.ab
        bra.s   .a
.done:  bset    d7,FLAGS+3.l            ; bit 0 = DEMO, bit 1 = POPULOUS
        cmpi.w  #1,d7
        bne.s   .out
        move.l  #'POPO',MARKER.l
.out:   movem.l (a7)+,d0-d7/a0-a6
        rts
