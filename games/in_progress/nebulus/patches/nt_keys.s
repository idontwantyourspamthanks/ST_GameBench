; name: nt_keys
; media: hd
; default: no
; site: $3dcf4
; orig: 4eb90003853a
; requires: nt_tmrhook nt_enhook
; conflicts: nt_freeze nt_noenemy
; ram: $76c00..$76c6d (102+ bytes, PLACEHOLDER: the loader owner picks the address; edit NT here and in nt_tmrhook/nt_enhook)
; doc: work/notes/trainers.md sections 3
; note: Trainer toggle keys: T = freeze/unfreeze the level timer, E = remove/restore enemies (each press toggles).  This patch owns the blob and the
; note: frame-loop hook: the site is the key poll `jsr $3853a.l` at the top of the game loop ($3dcf4, reached every iteration in every game mode).
; note: The hook runs the original poll, then compares the game's own last-IKBD-byte cell $38498 (written by the ISR at $384fc) with the byte it saw
; note: on the previous call and toggles on a NEW $14 (T make) or $12 (E make).  Joystick state bytes never have bits 4-6 set (the game's own test in
; note: $3853a), so they cannot collide.  d0 and a0 are free/saved (the caller reloads d0 from $3849a right after).  No self-modifying code.
; note: A tap shorter than one loop iteration (~40 ms) can lose the make byte: only the last byte is kept.  Blob layout (all fixed offsets):
; note:   NT+0 prev byte, NT+2 frz word, NT+4 noen word (initial values = boot default: put $ffff for "on at start"), NT+$08 key hook,
; note:   NT+$40 timer hook (nt_tmrhook), NT+$58 enemy hook (nt_enhook).
NT      equ     $76c00

        org     $3dcf4
        jsr     NT+$08.l

        org     NT
prev:   dc.b    0,0
frz:    dc.w    0
noen:   dc.w    0
        org     NT+$08
nt_kb:  jsr     $3853a.l                ; the original instruction
        move.l  a0,-(a7)
        lea     prev(pc),a0
        move.b  $38498.l,d0
        cmp.b   (a0),d0
        beq.s   .out                    ; nothing new since last iteration
        move.b  d0,(a0)
        cmp.b   #$14,d0                 ; T make
        bne.s   .e
        not.w   2(a0)
.e:     cmp.b   #$12,d0                 ; E make
        bne.s   .out
        not.w   4(a0)
.out:   move.l  (a7)+,a0
        rts

        org     NT+$40
nt_timer:
        move.w  frz(pc),d0              ; d0 is dead at the site (sub_03b0a4 loads it later)
        bne.s   .frozen
        tst.w   $33938.l                ; the original instruction
        rts
.frozen: cmp.w  d0,d0                   ; Z=1: the caller's beq.w skips the tick
        rts

        org     NT+$58
nt_enemy:
        move.w  noen(pc),d0
        beq.s   .norm
        clr.l   $3398c.l                ; state words of creature slots 0,1 (retroactive: alive creatures vanish next frame)
        clr.l   $33990.l                ; slots 2,3
        addq.l  #4,a7                   ; drop the return address: sub_03792c returns at once (no spawn)
        rts
.norm:  move.w  $33a20.l,d0             ; the original instruction
        rts
