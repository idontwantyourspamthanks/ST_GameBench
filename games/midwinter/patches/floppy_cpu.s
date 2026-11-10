; floppy_cpu.s — floppy build only, NOT a patch (no `; site:`): the code mw1patch.py writes into the free zero bytes of MWA's boot stub at $D7E0
; (file offset $200 + ($D7E0-$CFE4); the zero run $D7E0-$DC5B is 1147 bytes, nothing in the stub refers to it; the zero bytes below $D618 are the
; stub's STACK ($d618 downwards, ~110 bytes deep: our first version there was overwritten) and reaches through two 6-byte splices:
;     $D000  lea $d618.l,a7      -> jmp st_entry          (the first instruction of the stub)
;     $D05E  jmp $3df44.l        -> jmp st_s2             (the stub's jump into stage 2, after its FDC read of stage 2)
; On a 68000/68010 both only run the displaced instruction (st_entry also stores CPUFLAG = 0), so ST/STE/Mega STE behave exactly as before.
; On a 68020+ (TT, Falcon, accelerators; work/notes/tt.md): caches off, and the three FDC drivers the boot chain carries (this stub, stage-2,
; the game) get longer waits.  The original driver counts loops for an 8 MHz 68000: the 1.4 s seek/read time-out of sub_d3c0 is ~0.1 s on a
; 32 MHz 68030, shorter than a seek over 55 tracks, and its "force interrupt" on time-out aborts the seek, so the stub read the wrong track
; and stage 2 was garbage.  The game's copy is widened by core.s cpufix (FDCTAB), the stub's own and stage-2's here.
CPUFLAG equ     $b2ff4
        org     $d7e0
st_entry:
        lea     $d618.l,a7
        bsr.w   cl_detect
        move.b  d0,CPUFLAG.l
        beq.s   .go
        bsr.w   cl_cacheoff
        bsr.w   cl_ttres
        lea     st_tab(pc),a0
        bsr.w   cl_patch
.go:    jmp     $d006.l
        ds.b    $d810-*                 ; st_s2 is at the fixed address mw1patch.py splices to
st_s2:  movem.l d0-d7/a0-a6,-(a7)
        tst.b   CPUFLAG.l
        beq.s   .go
        lea     s2_tab(pc),a0
        bsr.w   cl_patch
.go:    movem.l (a7)+,d0-d7/a0-a6
        jmp     $3df44.l

;@CPULIB

; cl_ttres: on a TT (_MCH cookie $0002xxxx) select ST low resolution.  The game never sets the resolution itself (an ST boots in low res); TOS 3.06
; boots a TT in its NVRAM mode (TT medium, 640x480x4, on VGA), where the game's 320-pixel pictures come out as tiled garbage.  $ff8262 is the TT
; shifter mode byte TOS itself writes (Setscreen); 0 = ST low.  No jar / no _MCH / other machine (Falcon = $0003xxxx): nothing.  Trashes d1,d2,a0.
cl_ttres:
        move.l  $5a0.w,d1
        beq.s   .r
        movea.l d1,a0
.k:     move.l  (a0)+,d1
        beq.s   .r
        move.l  (a0)+,d2
        cmp.l   #'_MCH',d1
        bne.s   .k
        swap    d2
        cmp.w   #2,d2
        bne.s   .r
        clr.b   $ffff8262.w
.r:     rts

; {addr.l, size.w, value.l}: the time-out long (was $40000), the 3 dbra delays (were $180, $100, $20)
st_tab: dc.l    $d3c2
        dc.w    4
        dc.l    $00800000
        dc.l    $d382
        dc.w    2
        dc.l    $0600
        dc.l    $d204
        dc.w    2
        dc.l    $0400
        dc.l    $d3fc
        dc.w    2
        dc.l    $0080
        dc.l    0
s2_tab: dc.l    $3ef4a
        dc.w    4
        dc.l    $00800000
        dc.l    $3ef0a
        dc.w    2
        dc.l    $0600
        dc.l    $3ede4
        dc.w    2
        dc.l    $0400
        dc.l    $3ef84
        dc.w    2
        dc.l    $0080
        dc.l    0
