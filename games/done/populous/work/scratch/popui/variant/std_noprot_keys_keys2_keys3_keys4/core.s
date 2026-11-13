; core.s - Populous patch delivery mechanism (always installed by poppatch.py).
; Assembled into the payload image at $B3000.  Image layout (poppatch.py IMG_BASE / META / TABLE / ORG_CORE2):
;   $B3000  header   'POPP' magic, marker.l, flags.l, probe.l (see MACHV)
;   $B3010  apply    called by the loader (patches/loader.s) after Pexec(3) of a game program and
;                    before Pexec(4): d0.w = program (0 DEMO.TOS, 1 POPULOUS.TOS), a1 = its base page.
;                    All registers are preserved.
;   $B3100  meta     relocation list pointer.l, delta already applied to the payload.l, 2 spare longs
;   $B3110  site table (entries {addr.l len.w prog.w orig.l new.l}, addr 0 ends) + byte pool, up to $B3DFF
;                    prog.w = machine mask << 8 | program; mask 0 = every machine, else bit n = machine class n
;   $B3E00  core2    the supervisor-mode machine/CPU probe (256 bytes), $B3F00 core2b the cache flush
;   $B4000  patch blobs ... $B7FFF is poppatch.py's, $C0000-$C7FFF is reserved for the land-score code.
;   top     the relocation list: addresses of the longs of the image that hold game addresses (see below)
; The game's text base is wherever TOS puts the Pexec'd program: $AD96 in PP's ST layout (loader.s steers it there),
; but TOS 3.06 on a TT leaves its own data up to $E6FC and TOS 4.04 on a Falcon up to $FA04, so the program lands higher.
; poppatch.py builds every address into a game location for the base TNOM and lists the longs that hold one; `apply` adds
; delta = p_tbase - TNOM to each of them once (RELDLT remembers it), then verifies and applies as before.  With
; delta = 0 nothing is touched: an ST/STE/Mega STE run executes exactly the bytes of the old payload.
; Marker (MARKER = $B3004): 'POPF' preset, 'POPO' once the POPULOUS.TOS sites were verified and applied,
;   'POPF' again if any site's original bytes differ (nothing is applied then: all or nothing per program).
; flags.l (FLAGS = $B3008): bit 0 DEMO.TOS sites applied, bit 1 POPULOUS.TOS sites applied.
; MACHV (= $B300C, 4 bytes, filled on the first `apply`): +0 probed flag, +1 machine class (_MCH high word: 0 ST, 1 STE and
;   Mega STE, 2 TT, 3 Falcon), +2 CPU class (_CPU cookie: 0 68000/010, 1 68020/030, 2 68040/060), +3 0.
IMG     equ     $b3000
MARKER  equ     $b3004
FLAGS   equ     $b3008
MACHV   equ     $b300c
RELPTR  equ     $b3100
RELDLT  equ     $b3104
TABLE   equ     $b3110
MPROBE  equ     $b3e00                  ; core2: the machine probe
CFLUSH  equ     $b3f00                  ; core2b: the cache flush
TNOM    equ     $ad96                   ; text base of POPULOUS.TOS / DEMO.TOS in PP's ST layout (loader.s keeps it)

        org     $b3000
        dc.b    'POPP'
        dc.b    'POPF'
        dc.l    0
        dc.l    0

        org     $b3010
apply:  movem.l d0-d7/a0-a6,-(a7)
        moveq   #0,d7
        move.w  d0,d7                   ; d7 = program
        move.l  8(a1),d6                ; p_tbase of the program that was just loaded
        subi.l  #TNOM,d6                ; d6 = delta
        tst.b   MACHV.l
        bne.s   .pr
        bsr.w   MPROBE
.pr:    move.l  d6,d0
        sub.l   RELDLT.l,d0             ; what is still to be added to the payload's game addresses
        beq.s   .rd
        movea.l RELPTR.l,a0
.rl:    movea.l (a0)+,a2                ; address of a long to relocate, 0 = end
        move.l  a2,d1
        beq.s   .rs
        add.l   d0,(a2)
        bra.s   .rl
.rs:    move.l  d6,RELDLT.l
.rd:    lea     TABLE.l,a0              ; pass 1: every original byte of this program's sites must match
.v:     move.l  (a0)+,d0                ; addr, 0 = end
        beq.s   .apply
        move.w  (a0)+,d1                ; len
        move.w  (a0)+,d2                ; mask << 8 | program
        movea.l (a0)+,a2                ; orig bytes
        addq.l  #4,a0                   ; skip new
        bsr.s   sel
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
        bsr.s   sel
        bne.s   .a
        movea.l d0,a3
        subq.w  #1,d1
.ab:    move.b  (a2)+,(a3)+
        dbra    d1,.ab
        bra.s   .a
.done:  bset    d7,FLAGS+3.l            ; bit 0 = DEMO, bit 1 = POPULOUS
        cmpi.w  #1,d7
        bne.s   .fl
        move.l  #'POPO',MARKER.l
.fl:    bsr.w   CFLUSH
.out:   movem.l (a7)+,d0-d7/a0-a6
        rts

; sel: d2 = mask << 8 | program of a site, d7 = program being applied.  Returns EQ if the site is for this program and
; this machine class, NE if it is to be skipped.  Uses d2, d3.
sel:    cmp.b   d7,d2
        bne.s   .no
        lsr.w   #8,d2
        beq.s   .yes
        moveq   #0,d3
        move.b  MACHV+1.l,d3
        btst    d3,d2
        beq.s   .no
.yes:   moveq   #0,d2
        rts
.no:    moveq   #1,d2
        rts

        org     $b3e00
; mprobe: read the machine and CPU class in supervisor mode (Supexec), once.
mprobe: pea     probe(pc)
        move.w  #38,-(a7)
        trap    #14
        addq.l  #6,a7
        rts
probe:  move.b  #1,MACHV.l
        movea.l $5a0.w,a0               ; _p_cookies
        move.l  a0,d0
        beq.s   .x
.c:     move.l  (a0)+,d0                ; cookie id, 0 = end of the jar
        beq.s   .x
        move.l  (a0)+,d1                ; value
        cmpi.l  #'_MCH',d0
        bne.s   .n1
        swap    d1
        move.b  d1,MACHV+1.l
        bra.s   .c
.n1:    cmpi.l  #'_CPU',d0
        bne.s   .c
        moveq   #0,d2
        cmpi.l  #20,d1
        blo.s   .s
        moveq   #1,d2
        cmpi.l  #40,d1
        blo.s   .s
        moveq   #2,d2
.s:     move.b  d2,MACHV+2.l
        bra.s   .c
.x:     rts

        org     $b3f00
; cflush: the patched code and the blobs were written with data moves: empty both CPU caches (68020 and up only).
cflush: tst.b   MACHV+2.l
        beq.s   .x
        pea     cfsup(pc)
        move.w  #38,-(a7)
        trap    #14
        addq.l  #6,a7
.x:     rts
cfsup:  cmpi.b  #2,MACHV+2.l
        bhs.s   .f40
        dc.w    $4e7a,$0002             ; movec cacr,d0
        ori.l   #$0808,d0               ; CI + CD: clear the instruction and the data cache
        dc.w    $4e7b,$0002             ; movec d0,cacr
        rts
.f40:   dc.w    $f4f8                   ; cpusha bc
        rts
