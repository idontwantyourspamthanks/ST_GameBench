; name: cp_flhint
; default: yes
; site: $7446
; orig: 21d210e8205a
; gate: ram2mb
; media: floppy
; requires: cp_title
; doc: Campaigns, floppy release: the title screen says F10 = CAMPAIGNS (2 MB and more; the floppy flow never shows the WELCOME PARTNERS screen, which carries the hint in the HD release).
; note: Site $7446 = the first two instructions of the body of the title's face / typed-text loop ($7446-$74d8, one pass per message, `move.l (a2),$10e8.w / movea.l (a2)+,a0`) -> `jsr $B9F12.l` = cp_title's e4: the displaced pair,
; note: then the same hint line as the welcome screen (`t_whint`, text row 23, below the three text rows of the messages) into both screens: the loop clears both from line 64 down between two messages (`jsr $d8ca`, $74c8).
; note: Only where list 2 is applied (>= 2 MB, ST family): a 1 MB machine keeps the stock screen.
        org     $7446
        jsr     $B9F12.l
