#!/usr/bin/env python3
"""Build standalone enhanced ITALY.TOS (HD + bootable 720 KB floppy) for Italy 1990 (Codemasters).

Embeds our assembled 68000 STE enhancement module (patches/italy90_enh.s) into the
original ITALY.TOS without repacking:
  1. At startup (in $7fd00 copy loop), copies installer+patch to $fe000 (safe high RAM on 1MB+).
  2. Patches $2ba8 (in unpacked menu, right after 11-A-Side Soccer unpacks) -> jmp $fe000.
  3. When 11-A-Side Soccer launches, $fe000 copies patch.bin -> $3a000, applies all hooks
     + Kick Off 2 speed boosts, and jumps to $400.
  4. Soccer Skills (option 2) remains 100% untouched.
"""
import os, shutil, struct, subprocess, sys
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
WORK = GAME / "work"
DIST = GAME / "dist"
HD_DIR = DIST / "hd"
HD_DIR.mkdir(parents=True, exist_ok=True)

PATCH_BASE = 0x3A000
STAGE_ADDR = 0xF8000  # 32 KB free high RAM ($f8000..$fffff, safely above STADIUM_BUF $92000..$f0fff)

# 0. Generate 4 custom 16x30 pixel-art slide tackle sprites (Right, Left, Down, Up) -> work/slide_sprites.bin
#    Format: 30 rows x 10 bytes (mask.w, p0.w, p1.w, p2.w, p3.w), 1=transparent in mask.
def build_slide_sprites():
    cmap = {'.': -1, 'K': 0, 'W': 1, 'S': 10, 'R': 13, 'D': 12, 'G': 4}
    slide_right = [
        "................", "................", "................", "................",
        "................", "................", "................", "................",
        "................", "................", "................", "................",
        "................", "..KKK...........", ".KSSSK..........", "..SSS...........",
        "..RRRR..........", ".SRRRRS.........", ".S.DRRWW........", "....WWWWWW......",
        ".....WWWWSRRK...", "....WWSRRKRRKK..", "....SSKK..KKKK..", "...G..G..G......",
        "................", "................", "................", "................",
        "................", "................",
    ]
    slide_left = [row[::-1] for row in slide_right]
    slide_down = [
        "................", "................", "................", "................",
        "................", "................", "................", "......KKKK......",
        ".....KSSSSK.....", "......SSSS......", "....SRRRRRRS....", "...S.RRRRRR.S...",
        ".....DRRRRD.....", ".....WWWWWW.....", ".....WW..WW.....", "....WW....WW....",
        "....SS....SS....", "....RR....RR....", "....RR....RR....", "...KKK....KKK...",
        "...KKK....KKK...", "....G......G....", "................", "................",
        "................", "................", "................", "................",
        "................", "................",
    ]
    slide_up = [
        "................", "................", "................", "................",
        "................", "................", "................", "....KKK..KKK....",
        "....RRR..RRR....", "....SSS..SSS....", ".....WW..WW.....", ".....WWWWWW.....",
        "....SRRRRRRS....", "...S.DRRRRD.S...", ".....RRRRRR.....", "......KKKK......",
        ".....KKKKKK.....", ".....KSSSSK.....", "......KKKK......", ".....G....G.....",
        "................", "................", "................", "................",
        "................", "................", "................", "................",
        "................", "................",
    ]
    out = bytearray()
    for sp in (slide_right, slide_left, slide_down, slide_up):
        for row in sp:
            m = p0 = p1 = p2 = p3 = 0
            for x, ch in enumerate(row):
                bit = 1 << (15 - x)
                c = cmap[ch]
                if c < 0:
                    m |= bit
                else:
                    if c & 1: p0 |= bit
                    if c & 2: p1 |= bit
                    if c & 4: p2 |= bit
                    if c & 8: p3 |= bit
            out += struct.pack(">5H", m, p0, p1, p2, p3)
    (WORK / "slide_sprites.bin").write_bytes(out)

build_slide_sprites()

# 1. Assemble patches/italy90_enh.s -> work/patch.bin
src_s = GAME / "patches" / "italy90_enh.s"
patch_bin_path = WORK / "patch.bin"
subprocess.run(
    ["vasmm68k_mot", "-Fbin", "-m68000", "-o", str(patch_bin_path), str(src_s)],
    check=True,
)
patch_bin = patch_bin_path.read_bytes()
if len(patch_bin) & 1:
    patch_bin += b"\x00"
print(f"Assembled patch.bin: {len(patch_bin)} bytes (fits in $3a000-$3cfff = 12288 B)")
assert len(patch_bin) <= 0x3000, "patch.bin exceeds 12KB free RAM at $3a000!"

# 2. Define all patch sites applied to unpacked 11-A-Side Soccer ($400..$12000)
def jsr_abs(addr):
    return struct.pack(">HI", 0x4EB9, addr)

def jmp_abs(addr):
    return struct.pack(">HI", 0x4EF9, addr)

SITES = [
    # Pillar 1 & 2: Full-width 320x168 STE Blitter + 1-pixel STE hardware scrolling (X AND Y!)
    (0x00D278, jsr_abs(PATCH_BASE + 0x00)),                          # hook_camera (smooth 1px X+Y + tackle + chasers)
    (0x00D27E, bytes([0x4E, 0x71, 0x4E, 0x71, 0x4E, 0x71])),         # NOP old jerky $b2a8 Y-velocity step!
    (0x005FC2, jmp_abs(PATCH_BASE + 0x04)),                          # hook_pitch_render (21x8-line Blitter stadium)
    (0x00C250, jmp_abs(PATCH_BASE + 0x08)),                          # hook_sprite_draw (STE Blitter sprites)
    (0x00C0E0, jmp_abs(PATCH_BASE + 0x0C)),                          # hook_goal_draw (336px goalposts)
    (0x0039DC, jmp_abs(PATCH_BASE + 0x10)),                          # hook_vbl_pal (STE HSCROLL/LINEWID + TB)
    (0x00D2F0, jsr_abs(PATCH_BASE + 0x14) + bytes([0x60, 0x1E])),    # hook_flip (HUD Blitter + Radar + VBASE)
    (0x00BCCC, jsr_abs(PATCH_BASE + 0x18) + bytes([0x60, 0x18])),    # hook_cull_setup (336px bounds)
    (0x00D46E, jmp_abs(PATCH_BASE + 0x1C)),                          # hook_match_exit (reset STE scroll)
    (0x0022D6, jsr_abs(PATCH_BASE + 0x20) + bytes([0x4E, 0x71])),    # hook_vbl_guard (non-pitch guard + X radar)
    (0x00BEC2, bytes([0x60, 0x16])),                                 # remove 3-col goalpost cull check
    (0x00905A, struct.pack(">H", 0x012B)),                           # 1P-4P bubble max X = 320px
    (0x0090C8, struct.pack(">H", 0x012B)),                           # 1P-4P bubble clamp X = 320px
    (0x0090EC, struct.pack(">H", 0x0000)),                           # 1P-4P bubble no +16 offset
    (0x008ED0, jmp_abs(PATCH_BASE + 0x30)),                          # hook_num_bubble (1P-4P indicator via Blitter!)
    (0x00CD52, jmp_abs(PATCH_BASE + 0x2C)),                          # hook_hud_bars (dirty-checked power bars)
    (0x00230C, jmp_abs(PATCH_BASE + 0x34)),                          # hook_fast_wait (6x faster fade transitions!)
    (0x00C6E4, jmp_abs(PATCH_BASE + 0x38) + bytes([0x4E, 0x71])),    # hook_fire_noball (Kick Off 2 Slide Tackle / Jump / Switch!)
    (0x00BD36, jsr_abs(PATCH_BASE + 0x3C) + bytes([0x60, 0x12])),    # hook_player_spr (clean custom slide sprite override!)
    (0x00DD80, struct.pack(">H", 0x0008)),                           # Snappy pre-fixture intro wait (8 VBLs vs 75 VBLs!)

    # Pillar 3: Kick Off 2-inspired Player AI & CPU Ball-Carrier AI
    (0x00A5FC, jmp_abs(PATCH_BASE + 0x24)),                          # hook_ai_outfield (4-4-2 dynamic AI)
    (0x00CA8A, jsr_abs(PATCH_BASE + 0x28)),                          # hook_cpu_joy (shoot/pass/dribble AI)

    # Pillar 1b: 1.5x Kick Off 2 player & ball speeds + walk-through dispossession!
    (0x0108DC, struct.pack(">8H", 38, 32, 38, 32, 38, 32, 38, 32)),  # Speed without ball (1.5x: was 26/22, orig 18/16)
    (0x0108EC, struct.pack(">8H", 33, 28, 33, 28, 33, 28, 33, 28)),  # Speed with ball (1.5x: was 22/19, orig 16/14)
    (0x00A5A8, struct.pack(">H", 0x7024)),                           # AI speed hi: moveq #$24,d0 (36, was 25)
    (0x00A5B0, struct.pack(">H", 0x7020)),                           # AI speed mid: moveq #$20,d0 (32, was 22)
    (0x00A5B8, struct.pack(">H", 0x701D)),                           # AI speed lo: moveq #$1d,d0 (29, was 20)
    (0x009256, struct.pack(">H", 0x5C40)),                           # Accel: addq.w #6,d0 (snappy at 1.5x!)
    (0x009266, struct.pack(">H", 0x5D40)),                           # Decel: subq.w #6,d0 (stops on a dime!)
    (0x00A79A, struct.pack(">HH", 0x5140, 0x5041)),                  # Ball claim Y hitbox: +-8px (was +-5px!)
    (0x00A7B4, struct.pack(">HH", 0x5140, 0x5041)),                  # Ball claim X hitbox: +-8px (was +-5px!)
    (0x00A818, bytes([0x4E, 0x71, 0x4E, 0x71])),                     # Kick Off 2 walk-through tackle (remove speed-rejection!)
    (0x00A8C4, bytes([0x4E, 0x71, 0x4E, 0x71])),                     # Disable walking-dispossession foul (fouls via slide tackle!)
    # Kick Off 2 smart ground pass, reverse-direction chip, and balanced-height power shot!
    (0x00CB64, jmp_abs(PATCH_BASE + 0x40)),                          # hook_kick (replaces $cb64)
    # Instant Kick Off 2 turning with the ball (skip clunky $9148..$91ca turn-around freeze!)
    (0x009148, bytes([0x60, 0x00, 0x00, 0x82])),                     # bra.w $91cc (zero backwards-running!)
    # Kick Off 2 Goalkeeper AI + Manual Human Throw-ins & Goal Kicks!
    (0x0096B0, jmp_abs(PATCH_BASE + 0x44)),                          # hook_gk_ai (replaces $96b0)
    (0x00DB2E, jmp_abs(PATCH_BASE + 0x48)),                          # hook_throwin (replaces $db2e)
    (0x00B004, jmp_abs(PATCH_BASE + 0x4C) + bytes([0x4E, 0x71])),    # hook_goalkick (replaces $b004..$b00b)
    # Snappy Kick Off 2-style set pieces: brisk post-foul wait (16 vs 40) & crisp CPU corners (16 vs 50, faster whip!)
    (0x00D8FA, struct.pack(">H", 0x0010)),                           # Free kick whistle wait: 16 frames (was 40)
    (0x00AEB2, struct.pack(">H", 0x0010)),                           # Corner taker wait: 16 frames (was 50)
    (0x00AEF4, bytes([0x70, 0x2A, 0x72, 0x12])),                     # Corner whip: moveq #42,d0; moveq #18,d1 (1.5x!)
    (0x00AF04, bytes([0x70, 0xD6])),                                 # Corner whip left: moveq #-42,d0
    (0x00AF0E, struct.pack(">H", 0xFFEE)),                           # Corner whip up: move.w #-18,d1
    (0x00AF16, bytes([0x70, 0x2A])),                                 # Corner whip right: moveq #42,d0
]

# 3. Assemble tiny installer at STAGE_ADDR ($fe000) that copies patch.bin -> $3a000,
#    applies all SITES from its embedded table, and jumps to $400!
table_bytes = bytearray()
for addr, data in SITES:
    table_bytes += struct.pack(">IH", addr, len(data)) + data
    if len(data) & 1:
        table_bytes += b"\x00"
table_bytes += struct.pack(">I", 0)  # terminator

installer_s = WORK / "installer.s"
installer_s.write_text(f"""
                org     ${STAGE_ADDR:x}
install_start:
                ; Copy patch.bin -> $3a000
                lea     patch_payload(pc),a0
                lea     ${PATCH_BASE:x}.l,a1
                move.w  #{(len(patch_bin)//2)-1},d0
.cp:            move.w  (a0)+,(a1)+
                dbra    d0,.cp

                ; Apply site table: [addr.l, len.w, bytes..., pad-to-even], 0.l terminator
                lea     site_table(pc),a0
.sloop:         move.l  (a0)+,d0
                beq.s   .sdone
                movea.l d0,a1
                move.w  (a0)+,d1
                move.w  d1,d2
                subq.w  #1,d1
.bcp:           move.b  (a0)+,(a1)+
                dbra    d1,.bcp
                btst    #0,d2
                beq.s   .sloop
                addq.l  #1,a0
                bra.s   .sloop
.sdone:
                jmp     $400.l

                even
site_table:
                incbin  "{(WORK / 'site_table.bin').resolve()}"
                even
patch_payload:
                incbin  "{patch_bin_path.resolve()}"
""")
(WORK / "site_table.bin").write_bytes(table_bytes)
installer_bin_path = WORK / "installer.bin"
subprocess.run(
    ["vasmm68k_mot", "-Fbin", "-m68000", "-o", str(installer_bin_path), str(installer_s)],
    check=True,
)
installer_bin = installer_bin_path.read_bytes()
if len(installer_bin) & 1:
    installer_bin += b"\x00"
print(f"Assembled installer+patch payload: {len(installer_bin)} bytes (staged at ${STAGE_ADDR:x})")
assert STAGE_ADDR + len(installer_bin) <= 0x100000, "installer_bin overflows 1MB STE RAM!"

# 4. Patch original ITALY.TOS (clean Hotline base)
orig = (WORK / "extracted" / "hotline" / "ITALY.TOS").read_bytes()
magic, ts, ds, bs, ss, res1, flags, absf = struct.unpack(">HLLLLLLH", orig[:28])
assert magic == 0x601A and ds == 0 and bs == 0 and ss == 0
text = bytearray(orig[28 : 28 + ts])
reloc = orig[28 + ts :]

# Verify original loader at $4b8..$52a
assert text[0x4B8:0x4BE] == bytes.fromhex("203c00000015"), f"Unexpected stub at $4b8: {text[0x4b8:0x4be].hex()}"
assert text[0x524:0x52A] == bytes.fromhex("4ef900000400"), f"Unexpected jmp $400 at $524: {text[0x524:0x52a].hex()}"

# Append our stage stub + installer_bin at end of TEXT (even-aligned)
if len(text) & 1:
    text.append(0)
stub_off = len(text)

# The original $4b8 stub runs at TEXT+$4b8 (relocated by GEMDOS! Notice original $4b8 used
# absolute reloc addresses for $4d6, $c3ae, $2a2b2 — we MUST use PC-relative in our appended stub!).
# At $4b8: jump to stub_off via `bra.w`? No, $52586 is > 32KB away!
# Instead: overwrite $4d0 (`jmp $7fd00.l` = 6 bytes, NOT relocated!) with `bra`? No,
# overwrite $4b8..$4d5 (30 bytes!) to:
#   - copy installer_bin (from basepage TEXT + payload_off) -> $fe000
#   - copy $4d6..$529 -> $7fd00 (same as original!)
#   - patch $7fd00 + ($524-$4d6) (`jmp $400.l`) -> `jmp $7fd60.l` where we put:
#       move.l #$4ef9000f, $2ba8.l
#       move.w #$e000, $2bac.l
#       jmp    $400.l
# Wait: we can compute basepage TEXT start with `lea $4b8(pc)` -> subtract $4b8!
# Actually even simpler: put `bsr.w`? No, > 32KB. Put `lea -$4b8(pc), a0`? No, $4b8 is < 32KB!
# Wait: at $4b8, `lea $0000(pc)` gives current PC = TEXT + $4ba! So `suba.l #$4ba, a0` -> a0 = TEXT base!
# Then `adda.l #payload_off, a0` -> a0 = installer_bin! Copy to $fe000!
# Let's assemble that tiny 80-byte pre-stub + post-stub at $7fd00 cleanly!

payload_off = len(text)
text += installer_bin
new_ts = len(text)

# Note: check which offsets in $4b8..$52a are in the GEMDOS reloc table so we don't corrupt relocs!
reloc_addrs = []
if len(reloc) >= 4:
    cur = struct.unpack(">I", reloc[:4])[0]
    if cur != 0:
        reloc_addrs.append(cur)
        for b in reloc[4:]:
            if b == 0:
                break
            elif b == 1:
                cur += 254
            else:
                cur += b
                reloc_addrs.append(cur)
print("Original GEMDOS reloc offsets:", [hex(a) for a in reloc_addrs])

# We must NOT disturb any reloc offsets! Look: $524 (`jmp $400.l`) is NOT in reloc_addrs!
# And $4d0 (`jmp $7fd00.l`) is NOT in reloc_addrs!
# Let's put our tiny bootstrap right after $52a? No, $52a is packed data!
# Where can we run our copy-to-$fe000 before $4b8?
# Look at $0052: `bra.w $104b8` -> $0052 is at offset $52!
# Even simpler: check if $4b8..$52a has any relocs:
for a in reloc_addrs:
    if 0x4B0 <= a <= 0x530:
        print(f"  reloc inside 4b8..52a: {a:#x}")

# Let's assemble a tiny reloc-free replacement for $4b8..$4d5 (30 bytes) + $524 (6 bytes)?
# Wait: $4b8..$4d5 has 2 relocs? Let's check above! For now let's build a clean GEMDOS PRG
# wrapper that includes ITALY.TOS intact or patches via the reloc-safe spot!
# Wait: let's check reloc_addrs output first — actually we can do it cleanly right here:
# Put a 64-byte bootstrap at payload_off + len(installer_bin), and patch $0052 (`bra.w $4b8`, 4 bytes)
# or add 1 reloc entry? No, $4b8..$4d5 is 30 bytes! Let's check relocs at $4b8..$52a:
in_4b8 = [a for a in reloc_addrs if 0x4B8 <= a < 0x52A]
print("Relocs in $4b8..$52a:", [hex(a) for a in in_4b8])

# Cleanest possible zero-reloc-touch approach:
# Original $0000..$0055 is the entry point (starts at $0000!).
# Look at $0048..$0055:
#   0048: move.w $56.l, $ff8240.l  (10 bytes)
#   0052: bra.w  $04b8             (4 bytes)
# And our original $4d6..$529 (copied to $7fd00!) copies $68000->$400, $c3ae->$12000, $2a2b2->$2ff04,
# then at $524 executes `jmp $400.l`!
# Look at $4b8:
#   04b8: move.l #$15, d0          (6 bytes) -> copies 22 longs ($4d6..$52d) to $7fd00!
#   04be: movea.l #$4d6, a0        (6 bytes, RELOCATED at $4c0!)
#   04c4: movea.l #$7fd00, a1      (6 bytes)
#   04ca: move.l (a0)+, (a1)+      (2 bytes)
#   04cc: dbra d0, $4ca            (4 bytes)
#   04d0: jmp $7fd00.l             (6 bytes)
#
# So if we put our `pre_boot` at `pre_boot_off` (appended after `installer_bin`), and
# replace $4d0 (`jmp $7fd00.l`, 6 bytes, NOT relocated!) with `jsr`? No, `pre_boot_off` is > $7fff,
# so we can't `bra.w` to it from $4d0, UNLESS we add 1 reloc entry for a `jmp pre_boot_off.l`!
# Adding 1 reloc entry at the end of a GEMDOS reloc table is 5 lines of Python!

pre_boot_off = len(text)
# Assemble pre_boot (PC-relative! Runs at TEXT + pre_boot_off):
#   1. Copy installer_bin (PC-relative!) -> $fe000
#   2. Copy 64 bytes of post_menu_hook -> $7fd60
#   3. Patch $7fd00 + ($524 - $4d6) = $7fd4e (`jmp $400.l`) -> `jmp $7fd60.l`
#   4. Jump to $7fd00!
# Where post_menu_hook (at $7fd60, runs AFTER menu is unpacked to $400..$12000):
#   1. Patch $2ba8.l (`jmp $400.l` in menu's 11-a-side launcher) -> `jmp $fe000.l`
#   2. Jump to $400.l!
pre_boot_s = WORK / "pre_boot.s"
pre_boot_s.write_text(f"""
                org     ${pre_boot_off:x}
pre_boot:
                ; 1. Copy installer_bin -> $fe000 (PC-relative!)
                lea     pre_boot(pc),a0
                suba.l  #{len(installer_bin)},a0
                lea     ${STAGE_ADDR:x}.l,a1
                move.w  #{(len(installer_bin)//2)-1},d0
.cp_inst:       move.w  (a0)+,(a1)+
                dbra    d0,.cp_inst

                ; 2. Copy post_menu_hook -> $7fd60 (36 words = 72 bytes)
                lea     post_menu_hook(pc),a0
                lea     $7fd60.l,a1
                moveq   #35,d0
.cp_pmh:        move.w  (a0)+,(a1)+
                dbra    d0,.cp_pmh

                ; 3. Patch $7fd4e (copied $524 `jmp $400.l`) -> `jmp $7fd60.l`
                move.l  #$4ef90007,$7fd4e.l
                move.w  #$fd60,$7fd52.l

                ; 4. Jump to $7fd00 (original menu+payload copier!)
                jmp     $7fd00.l

post_menu_hook:
                ; Runs at $7fd60 AFTER menu is copied to $400..$12000!
                ; 1. Skip 'PLEASE SELECT F1 ST / F2 STE' at $e20 -> auto-select STE (`st.b $1198.l; rts`)
                move.l  #$50f90000,$e20.l
                move.l  #$11984e75,$e24.l
                ; 2. Instant menu fades & transitions: RTS at $54e + cut $d5c & $bb8 waits!
                move.w  #$4e75,$54e.l
                move.w  #$7001,$d5c.l
                move.w  #$0008,$bb8.l
                ; 3. Patch $2ba8 (`jmp $400.l` after 11-A-Side Soccer unpacks) -> `jmp ${STAGE_ADDR:x}.l`
                move.l  #${0x4ef90000 | (STAGE_ADDR >> 16):08x},$2ba8.l
                move.w  #${STAGE_ADDR & 0xffff:04x},$2bac.l
                jmp     $400.l
""")
pre_boot_bin_path = WORK / "pre_boot.bin"
subprocess.run(
    ["vasmm68k_mot", "-Fbin", "-m68000", "-o", str(pre_boot_bin_path), str(pre_boot_s)],
    check=True,
)
pre_boot_bin = pre_boot_bin_path.read_bytes()
if len(pre_boot_bin) & 1:
    pre_boot_bin += b"\x00"
text += pre_boot_bin
new_ts = len(text)

# Patch $4d0 (`jmp $7fd00.l`) -> `jmp pre_boot_off.l` AND add $4d2 to GEMDOS reloc table!
text[0x4D0:0x4D6] = jmp_abs(pre_boot_off)
reloc_addrs.append(0x4D2)
reloc_addrs = sorted(set(reloc_addrs))

# Re-encode GEMDOS relocation table
new_reloc = bytearray(struct.pack(">I", reloc_addrs[0]))
prev = reloc_addrs[0]
for a in reloc_addrs[1:]:
    diff = a - prev
    while diff > 254:
        new_reloc.append(1)
        diff -= 254
    new_reloc.append(diff)
    prev = a
new_reloc.append(0)

# Write final standalone dist/hd/ITALY.TOS!
new_hdr = struct.pack(">HLLLLLLH", 0x601A, new_ts, 0, 0, 0, 0, flags, absf)
out_tos = HD_DIR / "ITALY.TOS"
out_tos.write_bytes(new_hdr + bytes(text) + bytes(new_reloc))
print(f"Built {out_tos} ({out_tos.stat().st_size} bytes)")

# 5. Also build a clean auto-booting 720 KB floppy image dist/Italy1990_Enhanced.st!
floppy_st = DIST / "Italy1990_Enhanced.st"
if floppy_st.exists():
    floppy_st.unlink()
subprocess.run(["mformat", "-C", "-f", "720", "-i", str(floppy_st), "::"], check=True)
subprocess.run(["mmd", "-i", str(floppy_st), "::AUTO"], check=True)
subprocess.run(["mcopy", "-i", str(floppy_st), str(out_tos), "::AUTO/ITALY.PRG"], check=True)
print(f"Built auto-booting 720 KB floppy: {floppy_st} ({floppy_st.stat().st_size} bytes)")
