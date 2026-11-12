; name: pop2_floppy_head
; default: yes
; media: floppy
; site: $1770
; orig: 2e7c00012522
; note: Floppy build only (`build --floppy`).  Fixes the floppy on TOS 2.06 / 3.06 / 4.04 (Mega STE, TT, Falcon); TOS 1.0x/1.62 already worked.  PP's HAGA file service wraps every GEMDOS call
; note: of the game in a swap of low RAM: `$3f9372` (HAGA's code at the top of RAM) exchanges `$8`.. with a snapshot of TOS's state that HAGA took when it was loaded, calls TOS (`trap #1`),
; note: exchanges back.  On the FIRST call TOS therefore sees the floppy driver's variables as they were at HAGA's load: the head position of drive A (`$160c` = 2(a1) of the drive table at
; note: `$160a`, TOS 2.06) = $12 (track 18, where HAGA itself had just been read), while the physical head sits on track 75 (where RUNME then read P2M.FIC).  Evidence (Hatari
; note: `--trace gemdos,bios,fdc`, work/gates/rel_trace_ms206.txt, rel_curtrack_ms206.txt): `Fopen("P2D") -> BIOS Rwabs(0,$61a8,1,16,0)`; the FDC track register is written with $12
; note: (`fdc write 8604 track=0x12`) and a seek to track 0 with verify steps 18 tracks from track 75, so every attempt reads `ID_TR=0x39` (track 57): `fdc type I verify track failed
; note: ID_TR=0x39 TR=0x0` forever, Fopen returns -1 (Falcon -46) and HAGA's error path ends in the fade routine and a crash.  TOS 1.62 recovers (re-homes) and does not notice.
; note: Machines with the _MCH cookie high word >= 2 (TT, Falcon) skip it: they use HAGA's PMMU variant of the swap and fail elsewhere (work/notes/release.md).
; note: The fix: before the game's first instruction does anything, make the physical head agree with that snapshot: one TOS Floprd (XBIOS 8) of track 18, side 0, sector 1 into a scratch
; note: buffer; TOS (whose live state is still right, it was running RUNME's reads) seeks 75 -> 18 correctly.  The snapshot's track is where HAGA's last sector lives on OUR floppy layout
; note: (`pop2patch.py build --floppy` checks it).  The call is made at IPL 3 like HAGA's own TOS calls; then the displaced `movea.l #$12522,a7` is replayed and the game continues at `$1776`.
TRACK   equ     18
BUF     equ     $90000
        org     $1770
        jsr     PB+$1200
        org     PB+$1200
hd:     movea.l #$12522,a7              ; the game's own stack (the displaced instruction, done first: TOS needs a sane stack)
        movea.l $5a0.w,a0               ; _p_cookies; no jar (TOS 1.00-1.04) = an ST
        move.l  a0,d0
        beq.s   .go
.c:     move.l  (a0)+,d0
        beq.s   .go                     ; end of the jar, no _MCH: run
        move.l  (a0)+,d1
        cmpi.l  #'_MCH',d0
        bne.s   .c
        swap    d1
        cmpi.w  #2,d1                   ; high word >= 2 = TT (2) / Falcon (3): not this fix, see the notes
        bcc.s   .skip
.go:    move.w  sr,d7
        move.w  #$2300,sr
        move.w  #1,-(a7)                ; count
        clr.w   -(a7)                   ; side
        move.w  #TRACK,-(a7)            ; track
        move.w  #1,-(a7)                ; sector
        clr.w   -(a7)                   ; device A:
        clr.l   -(a7)                   ; filler
        pea     BUF.l                   ; buffer
        move.w  #8,-(a7)                ; Floprd
        trap    #14
        lea     20(a7),a7
        move.w  d7,sr
.skip:  jmp     $1776.l
