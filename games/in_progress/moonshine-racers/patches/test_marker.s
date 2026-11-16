; name: test_marker
; default: no
; site: $6f5e
; orig: 41f900070000
; data: $B2FF0 4
; note: Proof of the delivery mechanism (README.md "Test patches"): sets the long 'MSTM' at $B2FF0 and nothing else.
; note: Site: the game's first run-time code after PP's hand-over, the trap #2 handler $6f5a (`move.w #$2700,sr`) at its `lea.l $70000.l,a0`
; note: ($6f5e, 6 bytes; the handler is entered by `trap #2` at $6f58, rendering.md section 7).  The blob replays the lea and jumps back to $6f64
; note: (`bsr.w $d1a8`), so the trampoline's patch application, the blob area and a game-side hook are all proven when the marker is set.
        org     $6f5e
        jmp     $B2800.l

        org     $B2800
        move.l  #'MSTM',$B2FF0.l
        lea     $70000.l,a0
        jmp     $6f64.l
