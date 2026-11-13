; name: tb_flip
; default: yes
; site: $5fd2
; orig: 203a1f98223a
; requires: tb_frame tb_vbl
; data: $8c1b2 16
; note: Triple buffering, part 1 of 3 (needs tb_frame and tb_vbl; work/notes/triple.md).  The flip $5fd2
;       (`move.l $7f6c(pc),d0` / `move.l $7f74(pc),d1` / bchg / exg / store / base write / rts) is replaced by a `jmp`
;       to `tbf`, which is a complete copy of the flip that rotates THREE screen pages A = $23000, B = $2ad00,
;       C = $81000 ($81000-$88CFF: 32 000 B proved free, notes section 2) instead of toggling A/B.  A pass draws into
;       $144(a5); the page the shifter shows is $148(a5).  After the flip the frame just drawn becomes the shown page,
;       the spare page becomes the draw page and the old shown page becomes the spare, so the draw page is never the
;       shown page nor the one the VBL mouse pointer still holds (`$a65c` restores/redraws in the page the video base
;       points at, once per VBL; the >=1-VBL rule below is what guarantees the pointer has left the page before it
;       becomes the draw page again).
;       The 68000 only: the video base is written mid-frame here and is latched at the next frame start.  On a 68020+
;       (TT, Falcon) the base takes effect at once and a mid-frame flip would tear, so `tbf` runs the ORIGINAL flip
;       instead (same instructions, same registers) - behaviour there unchanged.  The CPU is found once (tbi, an
;       illegal-instruction probe with `movec cacr`, like core.s `cflush`).
;       Sites that set $144/$148 themselves (mode changes, $5fca, $d1b6) are untouched: a pair that is not a
;       permutation of A/B/C takes the original path, and a pair with $144 == $148 seeds the rotation.
A       equ     $23000
B       equ     $2ad00
C       equ     $81000
TBB     equ     $8c1b2                  ; state block (zeroed by the `data:` line): +0 VBL counter, +2 VBL at the last flip, +4 mode
TBVBL   equ     TBB+0
TBLAST  equ     TBB+2
TBON    equ     TBB+4                   ; 0 = not probed yet, 1 = triple buffering on (68000), 2 = off (68020+)
TBCODE  equ     $8c1c2                  ; even: code (labels must not be auto-aligned)

        org     $5fd2
        jmp     TBCODE.l

        org     $8c1c2
tbf:    move.l  d2,-(a7)
        move.l  d3,-(a7)
        move.w  TBON.l,d2
        bne.s   .ready
        bsr.w   tbi
        move.w  TBON.l,d2
.ready: cmpi.w  #1,d2
        bne.s   .plain
        ; at most one flip per VBL: a VBL must have run since the previous flip (the pointer has left the page that
        ; was shown until then, and every flipped frame is shown at least once)
        move.w  TBVBL.l,d2
        cmp.w   TBLAST.l,d2
        bne.s   .ok
.spin:  move.w  TBVBL.l,d2
        cmp.w   TBLAST.l,d2
        beq.s   .spin
.ok:    move.w  d2,TBLAST.l
        move.l  $144(a5),d0             ; D: the page this pass drew into
        move.l  $148(a5),d1             ; L: the page the shifter shows
        cmp.l   d0,d1
        beq.s   .seed                   ; $144 == $148 (mode entry): keep L shown, draw into another page
        bsr.s   tbm                     ; D a member of {A,B,C}?
        bne.s   .plain
        exg     d0,d1
        bsr.s   tbm                     ; L a member?
        exg     d0,d1
        bne.s   .plain
        move.l  #A+B+C,d2               ; spare = A+B+C-D-L (the third page)
        sub.l   d0,d2
        sub.l   d1,d2
        bra.s   .rot
.seed:  move.l  d0,d2
        cmpi.l  #A,d2
        bne.s   .s1
        move.l  #B,d2                   ; draw into B while A is shown
        bra.s   .rot
.s1:    move.l  #A,d2
.rot:   move.l  d0,$148(a5)             ; the frame just drawn is shown
        move.l  d2,$144(a5)             ; the spare page is drawn into
        move.l  d0,d1
        bra.s   .base
.plain: move.l  $7f6c.l,d0              ; the original flip, verbatim
        move.l  $7f74.l,d1
        bchg.b  #2,$8f(a5)
        beq.s   .st
        exg.l   d0,d1
.st:    move.l  d0,$144(a5)
        move.l  d1,$148(a5)
.base:  lsr.w   #8,d1                   ; $ff8203 / $ff8201, as the original (256-aligned pages)
        move.b  d1,$203(a6)
        swap    d1
        move.b  d1,$201(a6)
        move.l  (a7)+,d3
        move.l  (a7)+,d2
        rts
; Z = 1 if d0 is A, B or C (clobbers nothing: cmpi only)
tbm:    cmpi.l  #A,d0
        beq.s   .r
        cmpi.l  #B,d0
        beq.s   .r
        cmpi.l  #C,d0
.r:     rts
; one-shot CPU probe: 68000 -> TBON = 1, 68020+ -> TBON = 2.  The exception handler resets a7 from a2 (any frame
; size), exactly as core.s `cflush` does.  d0/d1 scratch (the original flip clobbers exactly those); a0 and a2 are
; saved here: the scripted-mode loop at $5f6a has a0 = its schedule pointer live across `bsr $5fd2` (`$5f78`), and the
; first flip - hence the probe - can be that one (observed on a Falcon floppy cold boot: a0 lost, the tick wait at $5f7e
; never ended).
tbi:    move.l  a0,-(a7)
        move.l  a2,-(a7)
        move.l  $10.w,-(a7)
        movea.l a7,a2
        lea     .trap(pc),a0
        move.l  a0,$10.w
        dc.w    $4e7a,$1002             ; movec cacr,d1: 68020+ executes it, 68000 raises illegal instruction
        moveq   #2,d0
        bra.s   .done
.trap:  movea.l a2,a7
        moveq   #1,d0
.done:  move.l  (a7)+,$10.w
        movea.l (a7)+,a2
        movea.l (a7)+,a0
        move.w  d0,TBON.l
        rts
