; core_floppy.s -- Hunter FLOPPY carrier (Paper Bag release).  Evidence: work/notes/floppy.md.
; Not a patch (huntpatch.py skips core*.s).  Assembled by `huntpatch.py build --floppy` and APPENDED to the text of the
; patched HUNTER.TOS; no relocations: only pc-relative references and fixed RAM addresses.  Position independent
; (assembled at two origins and compared).  Two entry points, a bra.w each:
;   +0 stage1  bsr'd from HUNTER.TOS $b8 (just after file 800 was read + depacked, TOS alive, supervisor mode, interrupts on):
;              replaces `move.w #$4e73,$90.w` (re-executed here).  Reads HNPATCH.BIN (the payload code, stored as records
;              {dest.l len.w bytes}: zero gaps are not stored) through GEMDOS, runs the payload's STE probe and then
;                SND_FILE  one disk: on STE hardware reads HNSOUND.BIN (the sample bank) to $90000 with GEMDOS;
;                SND_DISK  two disks: on STE hardware asks for the sound disk (drive B or a swap in A), see below;
;                neither:  nothing (lean set; the patched game keeps the YM sound).
;              It also empties the head of the file cache that HUNTER.TOS' cracked loader keeps in RAM (CACHE, which
;              huntpatch.py moved above the payload: the original cache ran over $80200..$FFFFF and overwrote the payload).
;   +4 stage2  bsr'd from HUNTER.TOS $22a (the copy at $6a000: everything is in place, SR $2700, TOS dead), then the
;              original `jmp $800.w`: runs the payload entry (verify ALL sites, apply all or nothing, 'HNPO'/'HNPF').
; Equates injected by huntpatch.py: PAYLOAD PROBE FLAGS PCAP SCRATCH STAGE BANK BANKCAP CACHE SND_FILE SND_DISK SND_LSN SND_SECS
; SND_SPT SND_SER.  Two-disk mode: the sound disk is identified by the 24-bit volume serial at boot sector offset 8..10 (SND_SER);
; the game disk by the serial read from drive A at start, so the game disk is proven to be back in drive A before the game
; starts (it reads levels and saves from A: with its own FDC code).

        org     $0
        bra.w   stage1
        bra.w   stage2

stage2: cmpi.l  #'HNPA',PAYLOAD.l
        bne.s   .no
        jsr     PAYLOAD+4.l
.no:    rts

stage1: move.w  #$4e73,$90.w            ; the instruction HUNTER.TOS had at $b8 (the splice replaced it)
        movem.l d0-d7/a0-a6,-(a7)
        cmpi.l  #$100000,$42e.w         ; phystop: the payload lives above $80000 (1 MB machines)
        blo.w   .done
        clr.l   CACHE.l                 ; empty cache (HUNTER.TOS' loader walks entries from here; RAM may be stale)
        clr.l   CACHE+4.l
        lea     PAYLOAD.l,a0            ; a failed or absent load can never look like a payload (warm boots keep RAM)
        move.w  #PCAP/4-1,d0
.clr:   clr.l   (a0)+
        dbra    d0,.clr
        clr.l   BANK.l                  ; likewise the sample bank magic
        lea     fname(pc),a0
        lea     STAGE.l,a1
        move.l  #PCAP,d3
        bsr.w   readfile
        ble.w   .done
        lea     STAGE.l,a0              ; records {dest.l, len.w (even), bytes}
        lea     0(a0,d0.l),a2
.rec:   cmpa.l  a2,a0
        bhs.s   .recdone
        movea.l (a0)+,a1
        move.w  (a0)+,d1
        cmpa.l  #PAYLOAD,a1
        blo.w   .done                   ; damaged file: dest outside the payload area -> game starts unpatched
        cmpa.l  #PAYLOAD+PCAP,a1
        bhs.w   .done
        subq.w  #1,d1
.cp:    move.b  (a0)+,(a1)+
        dbra    d1,.cp
        bra.s   .rec
.recdone:
        cmpi.l  #'HNPA',PAYLOAD.l
        bne.w   .done
        jsr     PROBE.l                 ; the payload's own STE probe -> FLAGS bit0
        ifne    SND_FILE
        btst    #0,FLAGS+3.l
        beq.s   .done
        moveq   #0,d6                   ; the bank is a contiguous file on drive A: whole tracks per XBIOS Floprd (TOS' own
        bsr.w   loadbank                ; Fread costs ~12 s more at real floppy timing, see floppy.md)
        endc
        ifne    SND_DISK
        btst    #0,FLAGS+3.l
        beq.s   .done
        bsr.w   sound_disk
        endc
.done:  movem.l (a7)+,d0-d7/a0-a6
        rts

; GEMDOS read of a whole file: a0 = name, a1 = destination, d3.l = capacity.  Out: d0.l = bytes read (<= 0: failed).
readfile:
        clr.w   -(a7)                   ; Fopen(name, read)
        move.l  a0,-(a7)
        move.w  #$3d,-(a7)
        trap    #1
        addq.l  #8,a7
        tst.l   d0
        bmi.s   .e
        move.w  d0,d4
        move.l  a1,-(a7)                ; Fread(handle, count, buf)
        move.l  d3,-(a7)
        move.w  d4,-(a7)
        move.w  #$3f,-(a7)
        trap    #1
        lea     12(a7),a7
        move.l  d0,d5
        move.w  d4,-(a7)                ; Fclose
        move.w  #$3e,-(a7)
        trap    #1
        addq.l  #4,a7
        move.l  d5,d0
.e:     rts

fname:  dc.b    'HNPATCH.BIN',0
sname:  dc.b    'HNSOUND.BIN',0
        even

        ifne    SND_DISK
; ------------------------------------------------------------------------------------------------------------------
; XBIOS Floprd of one boot sector: d0.w = device (0 A, 1 B).  Out: d0.l = 0 ok (else the XBIOS error), d1.l = serial.
bootsec:
        move.w  #1,-(a7)                ; count
        clr.w   -(a7)                   ; side
        clr.w   -(a7)                   ; track
        move.w  #1,-(a7)                ; sector
        move.w  d0,-(a7)                ; device
        clr.l   -(a7)                   ; filler
        pea     SCRATCH.l
        move.w  #8,-(a7)                ; Floprd
        trap    #14
        lea     20(a7),a7
        tst.l   d0
        bne   .e
        moveq   #0,d1
        move.b  SCRATCH+8.l,d1
        lsl.l   #8,d1
        move.b  SCRATCH+9.l,d1
        lsl.l   #8,d1
        move.b  SCRATCH+10.l,d1
.e:     rts

; print the 0-terminated string at a0 (GEMDOS Cconws)
puts:   move.l  a0,-(a7)
        move.w  #9,-(a7)
        trap    #1
        addq.l  #6,a7
        rts

; keyboard / joystick poll.  Out d0.w: 0 nothing, 1 go (RETURN, FIRE), 2 skip (SPACE, ESC, joystick UP)
input:  move.w  #$b,-(a7)               ; Cconis
        trap    #1
        addq.l  #2,a7
        tst.l   d0
        beq   .joy
        move.w  #7,-(a7)                ; Crawcin
        trap    #1
        addq.l  #2,a7
        cmpi.b  #13,d0
        beq   .go
        cmpi.b  #' ',d0
        beq   .skip
        cmpi.b  #27,d0
        beq   .skip
.joy:   move.b  joy0(pc),d1
        or.b    joy1(pc),d1
        btst    #7,d1                   ; fire
        bne   .go
        btst    #0,d1                   ; up
        bne   .skip
        moveq   #0,d0
        rts
.go:    moveq   #1,d0
        rts
.skip:  moveq   #2,d0
        rts

; joystick vector (IKBD packet at a0: header $fd both / $fe port 0 / $ff port 1, then the state byte(s))
joyh:   movem.l d0/a1,-(a7)
        lea     joy0(pc),a1
        move.b  (a0),d0
        cmpi.b  #$fd,d0
        beq   .both
        cmpi.b  #$fe,d0
        bne   .p1
        move.b  1(a0),(a1)
        bra   .out
.p1:    move.b  1(a0),1(a1)
        bra   .out
.both:  move.b  1(a0),(a1)
        move.b  2(a0),1(a1)
.out:   movem.l (a7)+,d0/a1
        rts
joy0:   dc.b    0
joy1:   dc.b    0
oldjoy: dc.l    0
joyadr: dc.l    0
ser1:   dc.l    0

; ------------------------------------------------------------------------------------------------------------------
sound_disk:
        moveq   #0,d0                   ; remember the game disk: serial of drive A
        bsr   bootsec
        tst.l   d0
        bne.w   .ret                    ; cannot read our own disk: no sound disk handling, game starts as is
        lea     ser1(pc),a0
        move.l  d1,(a0)
        move.w  #$22,-(a7)              ; Kbdvbase -> joyvec at +24
        trap    #14
        addq.l  #2,a7
        movea.l d0,a0
        lea     24(a0),a0
        lea     joyadr(pc),a1
        move.l  a0,(a1)
        lea     oldjoy(pc),a1
        move.l  (a0),(a1)
        lea     joyh(pc),a1
        move.l  a1,(a0)
        move.w  #$002,$ffff8240.w       ; background (the game loader blanked the palette), text = pen 15
        move.w  #$777,$ffff825e.w
.prompt:
        lea     m_title(pc),a0
        bsr   puts
        cmpi.w  #2,$4a6.w               ; _nflops
        bcs   .one
        lea     m_two(pc),a0
        bra   .p2
.one:   lea     m_one(pc),a0
.p2:    bsr   puts
        lea     m_keys(pc),a0
        bsr   puts
.again: lea     joy0(pc),a0             ; fresh presses only
        clr.b   (a0)
        clr.b   1(a0)
.wait:  bsr   input
        tst.w   d0
        beq   .wait
        cmpi.w  #2,d0
        beq.w   .end                    ; skip
        ; ---- find the sound disk: drive A first (quick), then drive B
        moveq   #0,d0
        bsr   bootsec
        tst.l   d0
        bne   .tryb
        cmpi.l  #SND_SER,d1
        beq   .inA
.tryb:  cmpi.w  #2,$4a6.w
        bcs   .nf
        moveq   #1,d0
        bsr   bootsec
        tst.l   d0
        bne   .nf
        cmpi.l  #SND_SER,d1
        bne   .nf
        moveq   #1,d6                   ; sound disk in drive B: nothing to swap
        bra   .load
.inA:   moveq   #0,d6
        bra   .load
.nf:    lea     m_nf(pc),a0
        bsr   puts
        bra   .again
.load:  lea     m_load(pc),a0
        bsr   puts
        bsr   loadbank
        tst.w   d6
        bne   .end                    ; read from B: the game disk never left A
        ; ---- the game disk back into A: prove it by its serial, not by the keypress
.back:  lea     m_back(pc),a0
        bsr   puts
        lea     joy0(pc),a0
        clr.b   (a0)
        clr.b   1(a0)
.bw:    bsr   input
        cmpi.w  #1,d0
        bne   .bw
        moveq   #0,d0
        bsr   bootsec
        tst.l   d0
        bne   .nb
        cmp.l   ser1(pc),d1
        beq   .end
.nb:    lea     m_nb(pc),a0
        bsr   puts
        bra   .bw
.end:   movea.l joyadr(pc),a0
        move.l  oldjoy(pc),(a0)
        lea     m_cls(pc),a0
        bsr   puts
        clr.w   $ffff825e.w
        clr.w   $ffff8240.w
.ret:   rts

        endc
        ifne    SND_DISK+SND_FILE
; Read SND_SECS sectors from LSN SND_LSN of device d6 (SND_SPT sectors per track, 2 sides) to BANK.  Bad read or no 'HSND' -> no bank.
loadbank:
        move.l  #SND_LSN,d3
        move.l  #SND_SECS,d4
        lea     BANK.l,a3
.lp:    move.l  d3,d0
        divu.w  #SND_SPT*2,d0           ; d0.w = track, d0 high = sector within the cylinder
        move.w  d0,d2                   ; track
        swap    d0
        andi.l  #$ffff,d0
        divu.w  #SND_SPT,d0             ; d0.w = side, d0 high = sector - 1
        move.w  d0,d1                   ; side
        swap    d0
        addq.w  #1,d0                   ; sector (1-based)
        moveq   #SND_SPT,d5
        add.w   #1,d5
        sub.w   d0,d5                   ; sectors left on this track
        cmp.l   d4,d5
        bls   .cnt
        move.w  d4,d5
.cnt:   move.w  d5,-(a7)                ; count
        move.w  d1,-(a7)                ; side
        move.w  d2,-(a7)                ; track
        move.w  d0,-(a7)                ; sector
        move.w  d6,-(a7)                ; device
        clr.l   -(a7)
        move.l  a3,-(a7)
        move.w  #8,-(a7)
        trap    #14
        lea     20(a7),a7
        tst.l   d0
        bne   .bad
        moveq   #0,d0
        move.w  d5,d0
        add.l   d0,d3
        sub.l   d0,d4
        lsl.l   #8,d0
        add.l   d0,d0                   ; * 512
        adda.l  d0,a3
        moveq   #'.',d0
        move.w  d0,-(a7)
        move.w  #2,-(a7)                ; Cconout: one dot per track read
        trap    #1
        addq.l  #4,a7
        tst.l   d4
        bne   .lp
        cmpi.l  #'HSND',BANK.l
        beq   .ok
.bad:   clr.l   BANK.l
.ok:    rts
        endc
        ifne    SND_DISK

; VT52: ESC E clear, ESC p / ESC q reverse video on / off, ESC Y row col (+32) cursor
m_title:dc.b    27,'E',27,'p',' HUNTER - STE SAMPLED SOUND         ',27,'q',13,10,10,0
m_one:  dc.b    'Insert the SOUND DISK (disk 2) in',13,10
        dc.b    'drive A in place of the game disk,',13,10
        dc.b    'then press RETURN or joystick FIRE.',13,10,0
m_two:  dc.b    'Insert the SOUND DISK (disk 2) in',13,10
        dc.b    'drive B (or in drive A in place of',13,10
        dc.b    'the game disk), then press RETURN',13,10
        dc.b    'or joystick FIRE.',13,10,0
m_keys: dc.b    10,'SPACE or joystick UP: skip, keep the',13,10
        dc.b    'original sound (game disk stays in).',13,10,0
m_nf:   dc.b    27,'Y',32+19,32,'The sound disk was not found.',13,10
        dc.b    'Check the disk, press RETURN again.',0
m_load: dc.b    27,'Y',32+17,32,'Loading ',0
m_bad:  dc.b    13,10,'Sound disk error: original sound.',13,10,0
m_back: dc.b    27,'E',27,'p',' HUNTER - GAME DISK                ',27,'q',13,10,10
        dc.b    'Insert the GAME DISK (disk 1) in',13,10
        dc.b    'drive A, then press RETURN or',13,10
        dc.b    'joystick FIRE.',13,10,0
m_nb:   dc.b    27,'Y',32+19,32,'That is not the game disk.',13,10,0
m_cls:  dc.b    27,'E',0
        even
        endc
