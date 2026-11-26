; name: fl_deprot
; default: yes
; media: floppy
; disk: A $e3d0 7e023f07
; doc: Floppy release only: the original manual-lookup copy protection ("type in the word at page n, paragraph n, line n, word n") is skipped; the game starts as if the right word had been typed.
; note: Disk A $E3D0 = the first two instructions of the loader's question routine, RAM $7BD0 (called by `jsr $7bd0.l` at $71A2 after the credits):
; note:   7bd0  7e02  moveq  #2,d7      ; three attempts
; note:   7bd2  3f07  move.w d7,-(a7)
; note: become  `bra.w $7d1a` = the routine's own "word accepted" exit (the code after `addq.l #6,a7` at $7d18: fade the palette out, wait for
; note: it, clear the screens, rts), so the question is never drawn or asked, the stack is exactly what the caller left, and the loader goes on
; note: as after a correct answer.  (The accepted exit is reached by `beq.w $7d18` at $7c7c / $7ce2 when the typed text equals the answer
; note: word the routine picked from the table at $7fd3 with a random index; a wrong answer drops to `bra.b $7d12` after three tries.)
; note: The displacement is hand-encoded: the file offset ($E3D0) is not the RAM address ($7BD0) the branch is relative to ($7BD0 + 2 + $148 = $7D1A).
        org     $e3d0
        dc.w    $6000,$0148             ; bra.w $7d1a
