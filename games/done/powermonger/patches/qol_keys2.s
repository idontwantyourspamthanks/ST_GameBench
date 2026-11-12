; name: qol_keys2
; default: yes
; stage: 2
; site: $199c
; orig: 13c00001c490
; note: the interrupt half of qol_keys (see there; harmless without it: it only writes PEND bytes).  $199c is the make-code path of the game's
;       ACIA keyboard handler $18be (`st.b (a0,d0.w)` just stored the key in the table $2de6c, d0 = the scan code, 0 for a break):
;       `move.b d0,$1c490` (the game's "last key" byte) becomes `jsr KH`; KH does that same move, and for a make code sets
;       PEND[scancode] = 1 (+ 2 when Shift is down, $2df8a) in qol_keys' data block.  qol_keys consumes PEND once per pass, so a tap shorter
;       than a pass is not lost.  The handler already saved d0-d2/a0-a1 ($18be) and pushed a0 again ($1962): d0, d1, a0 are free here.
;       A press is recorded only while the map loop runs: qol_keys stamps LASTV (the VBL counter of its last pass hook) every pass, and a press
;       more than WIN VBLs after that (name prompt, menus, the territory chart, a disk access) is not a shortcut and is dropped (before this
;       the letters of the player's name were replayed as icon clicks at the first pass of the map: work/notes/phantom_click.md).
;       KH sits at $cd610 (the old place $cd530 has room for 48 bytes only; $cd560 is qol_hover2's hook).
PEND    equ     $cd4a4
ANY     equ     $cd4a2
LASTV   equ     $cd524                  ; qol_keys: D + $c4
WIN     equ     150                     ; = qol_keys.s

        org     $199c
        jsr     $cd610.l

        org     $cd610
kh:     move.b  d0,$1c490.l             ; the displaced instruction
        tst.b   d0
        beq.s   .r                      ; a break code (d0 was cleared)
        move.l  $6f304.l,d1             ; VBL count now
        sub.l   LASTV.l,d1              ; VBLs since the last pass hook (LASTV = 0 before the first pass: a huge difference)
        cmp.l   #WIN,d1
        bhi.s   .r                      ; the loop is not running: not a shortcut
        lea     PEND.l,a0
        moveq   #1,d1
        tst.w   $2df8a.l                ; Shift down?
        beq.s   .s
        moveq   #3,d1
.s:     move.b  d1,(a0,d0.w)
        move.w  #1,ANY.l                ; after PEND: the pass hook scans only when this is set
.r:     rts
