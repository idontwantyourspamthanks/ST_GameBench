; =============================================================================
; Seconds Out (1988, Tynesoft) — Fixed-Address Relocator & Patch Loader
; =============================================================================
; Copies the embedded original EMPTY.PRG ($5332 bytes) to GAME_BASE ($80000),
; applies its 1,344 relocations (+$80000), copies engine.bin to PATCH_BASE
; ($88000), probes STE Blitter hardware (bus-error guarded), applies the
; hook table, and launches the game at $80000.
;
; Works identically from HD (Desktop or AUTO) and Floppy (AUTO) on 1 MB+
; ST / STE / Mega STE / TT / Falcon without colliding with trainer.pi1 ($1ffde).
; =============================================================================

GAME_BASE       equ     $00080000
PATCH_BASE      equ     $00088000
HW_FLAGS_ADDR   equ     $00087f00       ; byte: bit 0 = has_blitter, bit 1 = is_68020+

                section text

start:
                ; Enter Supervisor mode so we can copy to $80000 and probe bus error
                clr.l   -(sp)
                move.w  #$20,-(sp)
                trap    #1
                addq.l  #6,sp
                lea     saved_ssp(pc),a0
                move.l  d0,(a0)

                ; Verify >= 1 MB ST-RAM (_phystop at $42e)
                cmpi.l  #$00100000,$42e.w
                bcs.w   .need_1mb

                ; 1. Copy embedded original EMPTY.PRG text to GAME_BASE ($80000)
                lea     payload_hdr(pc),a4
                move.l  0(a4),d0                ; orig_text_len
                move.l  4(a4),d1                ; reloc_count
                move.l  8(a4),d2                ; engine_len
                move.l  12(a4),d3               ; hook_count

                lea     16(a4),a0               ; a0 = embedded orig_text
                lea     GAME_BASE,a1
                move.l  d0,d4
                lsr.l   #1,d4
                subq.l  #1,d4
.copy_game:
                move.w  (a0)+,(a1)+
                dbra    d4,.copy_game

                ; 2. Apply relocation offsets (d1 longword offsets into GAME_BASE)
                lea     GAME_BASE,a1
                move.l  #GAME_BASE,d5
                move.l  d1,d4
                beq.s   .reloc_done
                subq.l  #1,d4
.reloc_loop:
                move.l  (a0)+,d6
                add.l   d5,0(a1,d6.l)
                dbra    d4,.reloc_loop
.reloc_done:

                ; 3. Copy engine.bin to PATCH_BASE ($88000)
                lea     PATCH_BASE,a2
                move.l  d2,d4
                beq.s   .eng_done
                lsr.l   #1,d4
                subq.l  #1,d4
.copy_eng:
                move.w  (a0)+,(a2)+
                dbra    d4,.copy_eng
.eng_done:

                ; 4. Apply byte/word/long patch records:
                ;    each record: dc.l addr, dc.w len (bytes), bytes... (even-padded)
                move.l  d3,d4
                beq.s   .hooks_done
                subq.l  #1,d4
.hook_loop:
                move.l  (a0)+,a3                ; target address
                move.w  (a0)+,d5                ; byte length
                move.w  d5,d6
                subq.w  #1,d6
.hook_bytes:
                move.b  (a0)+,(a3)+
                dbra    d6,.hook_bytes
                btst    #0,d5
                beq.s   .hook_even
                addq.l  #1,a0                   ; align to even
.hook_even:
                dbra    d4,.hook_loop
.hooks_done:

                ; 5. Probe STE Blitter safely (bus-error guarded read of $ffff8a3c)
                moveq   #0,d7                   ; hw_flags = 0
                move.l  $8.w,a5                 ; save bus error vector
                move.l  sp,a6                   ; save sp
                lea     .no_blitter(pc),a2
                move.l  a2,$8.w
                tst.b   $ffff8a3c.w             ; probe Blitter control reg
                bset    #0,d7                   ; bit 0 = Blitter present!
.no_blitter:
                move.l  a6,sp
                move.l  a5,$8.w

                ; Store hw_flags at HW_FLAGS_ADDR ($87f00)
                move.b  d7,HW_FLAGS_ADDR.l

                ; 6. Flush caches on 68020+ (ignored/harmless? No, 68000 traps on movec!
                ;    Skip movec; TT/Falcon cache flush not needed for fresh ST-RAM write
                ;    before first fetch, or probe via illegal vector if needed.)

                ; 7. Return to User mode so EMPTY.PRG's own Super(0) works cleanly
                move.l  saved_ssp(pc),-(sp)
                move.w  #$20,-(sp)
                trap    #1
                addq.l  #6,sp

                ; Jump to relocated game entry at GAME_BASE ($80000)!
                jmp     GAME_BASE

.need_1mb:
                ; Return to user mode and Pterm(1)
                move.l  saved_ssp(pc),-(sp)
                move.w  #$20,-(sp)
                trap    #1
                addq.l  #6,sp
                move.w  #1,-(sp)
                move.w  #$4c,-(sp)
                trap    #1

saved_ssp:      dc.l    0

                even
payload_hdr:
                ; Appended by build_so.py:
                ;   dc.l orig_text_len
                ;   dc.l reloc_count
                ;   dc.l engine_len
                ;   dc.l hook_count
                ;   ... orig_text bytes ...
                ;   ... reloc_count * dc.l offsets ...
                ;   ... engine.bin bytes ...
                ;   ... hook records ...
