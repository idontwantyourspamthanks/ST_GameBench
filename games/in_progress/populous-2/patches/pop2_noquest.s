; name: pop2_noquest
; default: yes
; site: $20a02
; orig: 4a7900039612660e4a790003960a67064eb9000148b2
; doc: the manual question (Zeus's statue question) is skipped
; note: The manual-protection screen ("ZEUS ASKS: HOW MANY STATUES HAVE BEEN BUILT IN THE LIKENESS OF THIS HEAD", head picture, 4-digit counter, OK)
; note: is ONE routine, $148b2, with ONE caller: $20a12 `jsr $148b2.l`, inside the per-object draw routine $20a02, guarded by two words:
; note:   $20a02 tst.w $39612.l / bne.s $20a18      ; $39612 = "question answered" (written ONLY at $14aac `move.w #1,$39612.l`, the success path, then never again)
; note:   $20a0a tst.w $3960a.l / beq.s $20a18      ; $3960a = "the last palette fade went to a real palette, not to $36c82 (black)": $22192 clr / $221a0 set
; note: so the screen appears the first time a visible frame draws an object and the flag is still 0 (every path into play, once per program run).
; note: PP's own patch ($14a88 bne -> bra) accepts any answer; the routine's state effects (work/notes/noquest.md) are the flag $39612 := 1 and
; note: a reload of the game's graphic files ($2d326) that undoes what the screen loaded (head picture); the routine reads $8207/$8209 and $392d0 for the head
; note: choice but writes no random state.  This patch sets the flag at the same place and jumps over the call (nothing else of the screen is needed).
; note: Gates (work/notes/noquest.md): cold boots STE 2 MB / Mega STE / TT --mmu / floppy: no question, play; world by turn identical to a run that
; note: answers (from the frozen pre-question snapshot, turns 11..137; turns 7..10 differ only in the fade flag $3960b); p2tick ab identical.
; note: The 22 original bytes are replaced by `move.w #1,$39612.l ; bra.s $20a18` + nops.
        org     $20a02
        move.w  #1,$39612.l
        bra.s   $20a18
