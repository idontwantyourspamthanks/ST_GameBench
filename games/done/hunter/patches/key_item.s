; name: key_item
; default: yes
; site: $a534
; orig: 4ef900002686
; note: One-key items and direct weapon keys (idea 2 of reports/hunter_ideas.md; work/notes/keys.md).
; note: The game's key command dispatch ($b0b6 `btst.b #7,$93(a5)` / `bne.w $a526`: only in the 3D view, never in menus or the log book) looks the
; note: ASCII of the key (d1) up in an 8-entry table at $a516 (c r l m f a ~ -> clock radar log map flares drone help); a miss leaves by `jmp $2686.l`
; note: at $a534 (Esc, Return, Space, or nothing).  That jmp is the site: it now goes to a second table.  A hit sets d0 = the item number and enters the
; note: game's own ownership test at $a540 (`move.l $24a(a5),d1 / btst.l d0,d1`; not owned = rts), which stores the item in $252(a5), loads a3 = $a28c
; note: and d2/d3 = the icon's cell and uses it through $adc8: the handler a click on that icon runs.  A miss goes on to $2686 with d0/d1 untouched.
; note: KEYS (ASCII, so the keypad digits work too):  1..9  weapons 0..8 (the weapon row of the item table: the same handler, $a00a);  h  medical kit (14, handler $a3ae);  g  fuel can (15, $a45e);
; note:   j  parachute (18, $a27c: the handler Space already runs).  Nothing else changes; no time stop (like the existing F and A keys).
; note: Jaguar pad: the buttons `#`, `0`, `8` inject h, g, j through the key decoder (jag_pad's table, scancodes $23 $22 $24).
KEYTAB   equ    12                      ; entries
        org     $a534
        jmp     $8d820.l                ; replaces `jmp $2686.l` (a miss)

        org     $8d820
key_item:
        lea     key_chars(pc),a0
        moveq   #KEYTAB-1,d2
.l:     cmp.b   (a0)+,d1
        beq.s   .hit
        dbra    d2,.l
        jmp     $2686.l                 ; not ours: Esc, Return, Space, ... as before (d0, d1 untouched)
.hit:   moveq   #0,d0
        move.b  KEYTAB-1(a0),d0         ; the item number
        jmp     $a540.l                 ; the game's ownership test and use
key_chars:
        dc.b    '1','2','3','4','5','6','7','8','9','h','g','j'
key_items:
        dc.b    0,1,2,3,4,5,6,7,8,14,15,18
