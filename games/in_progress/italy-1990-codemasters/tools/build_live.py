#!/usr/bin/env python3
"""Assemble italy90_enh.s and live-test on match_baseline.sav in Hatari (8 MHz STE)."""
import subprocess, sys, os, re, time, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GAME = Path(__file__).resolve().parents[1]
WORK = GAME / "work"
SHOTS = WORK / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)

# 1. Assemble italy90_enh.s with vasmm68k_mot
src = GAME / "patches" / "italy90_enh.s"
out_bin = WORK / "patch.bin"
subprocess.run(
    ["vasmm68k_mot", "-Fbin", "-m68000", "-o", str(out_bin), str(src)],
    check=True,
)
print(f"Assembled {out_bin} ({out_bin.stat().st_size} bytes)")

# 2. Define patch sites in 11-A-Side Soccer RAM
# Entry table at $3a000:
#   +$00 = hook_camera
#   +$04 = hook_pitch_render
#   +$08 = hook_sprite_draw
#   +$0c = hook_goal_draw
#   +$10 = hook_vbl_pal
#   +$14 = hook_flip
#   +$18 = hook_cull_setup
def jsr_abs(addr):
    return struct.pack(">HI", 0x4eb9, addr)

def jmp_abs(addr):
    return struct.pack(">HI", 0x4ef9, addr)

SITES = [
    # $d278: jsr $d488.l -> jsr $3a000.l (hook_camera)
    (0x00d278, jsr_abs(0x3a000)),
    # $d2ac: bsr.w $5fc2 (4 bytes) -> patch $5fc2 itself with jmp $3a004.l!
    (0x005fc2, jmp_abs(0x3a004)),
    # $c250: sprite draw -> jmp $3a008.l (hook_sprite_draw)
    (0x00c250, jmp_abs(0x3a008)),
    # $c0e0: goal draw -> jmp $3a00c.l (hook_goal_draw)
    (0x00c0e0, jmp_abs(0x3a00c)),
    # $39dc: VBL pitch palette routine itself -> jmp $3a010.l (survives goal/cutscene resets of $11a72!)
    (0x0039dc, jmp_abs(0x3a010)),
    # $d46e: match exit screen restore -> jmp $3a01c.l (cleanly resets STE HSCROLL/LINEWID!)
    (0x00d46e, jmp_abs(0x3a01c)),
    # $22d6: VBL indirect call (movea.l $11a72.l,a0; jsr (a0) = 8 bytes) -> jsr $3a020.l + nop
    (0x0022d6, jsr_abs(0x3a020) + bytes([0x4e, 0x71])),
    # $a5fc: Outfield player AI -> jmp $3a024.l (Kick Off 2-inspired AI!)
    (0x00a5fc, jmp_abs(0x3a024)),
    # $ca8a: CPU ball-carrier virtual joystick (jsr $b8c4.l) -> jsr $3a028.l (Kick Off 2 CPU AI!)
    (0x00ca8a, jsr_abs(0x3a028)),
    # $cd52: Power-bar HUD redraw -> skip when unchanged? (patch $d2d4 bsr.w $cd52 -> no, patch $cd52 or call via $3a02c)
    # Wait: $d2d4 is 4 bytes (bsr.w $cd52), so patch $d2d4..$d2d7? No, $cd52 itself is called from $d2d4; let's check $d2d4!
    # Actually $cd52 is 6 bytes `movea.l $11cf6.l, a0` -> we can't jump back to $cd52 if we overwrite $cd52.
    # Instead patch $cd52 -> jmp $3a02c, and hook_hud_bars executes `movea.l $11cf6.l, a0` + `jmp $cd58.l`!
    (0x00cd52, jmp_abs(0x3a02c)),
    # $d2f0: screen flip (0xd2f0..0xd315 = 38 bytes) -> jsr $3a014 + bra.s $d316
    (0x00d2f0, jsr_abs(0x3a014) + bytes([0x60, 0x1e])),
    # $bccc: sprite culling setup (0xbccc..0xbceb = 32 bytes) -> jsr $3a018 + bra.s $bcec
    (0x00bccc, jsr_abs(0x3a018) + bytes([0x60, 0x18])),
    # $bec2: goalpost cull column check (0xbec2..0xbed9 = 24 bytes) -> bra.s $beda
    (0x00bec2, bytes([0x60, 0x16])),
    # $9058: 1P-4P number bubble max X ($eb -> $12b) and $90c6 ($eb -> $12b) and $90ea (+$10 -> +$0)
    (0x00905a, struct.pack(">H", 0x012b)),
    (0x0090c8, struct.pack(">H", 0x012b)),
    (0x0090ec, struct.pack(">H", 0x0000)),
]

# 3. Boot snapshot in Hatari, inject patch live, measure FPS, capture screenshots!
sys.path.insert(0, str(ROOT / "tools"))
from stharness import Hatari, TOS

h = Hatari(
    machine="ste",
    tos=TOS["1.62"],
    game_dir=WORK / "extracted" / "hotline",
    snapshot=str(WORK / "snapshots" / "match_baseline.sav"),
    extra=["--joy1", "keys"],
)
try:
    # Write debugger script to load patch.bin and apply all sites atomically at next flip ($d2f0)
    apply_txt = WORK / "apply_live.txt"
    lines = [f"loadbin {out_bin.resolve()} $3a000"]
    for addr, data in SITES:
        hex_bytes = " ".join(f"${b:02x}" for b in data)
        lines.append(f"w ${addr:x} {hex_bytes}")
    apply_txt.write_text("\n".join(lines) + "\n")

    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = $d2f0 :trace :once :file {apply_txt.resolve()}")
    time.sleep(1.0)

    # Wait a bit for several patched frames to render
    time.sleep(1.5)
    h.shot(str(SHOTS / "enh_01_fullwidth.png"))

    # Measure FPS!
    h.debug("b all", 0.3)
    h.cmd("hatari-debug b pc = $d2f0 :trace")
    time.sleep(0.3)
    start = h._arm_vbl(100)
    out = h._wait_removed(start)
    h.debug("b all", 0.3)
    flips = len(re.findall(r"pc = \$d2f0", out, re.I))
    print(f"ENHANCED STE: {flips} frames in 100 VBLs -> {flips*50/100:.2f} fps ({100/flips if flips else 0:.2f} VBLs/frame)")

    # Move right / left to test horizontal scrolling and take another shot
    h.key("Right", hold=0.8)
    time.sleep(0.5)
    h.shot(str(SHOTS / "enh_02_scrolled.png"))
    print("camX=", h.peekw(0xee50), "fine_x=", h.peekw(0x3a024), "ballX=", h.peekw(0xfb9a))
finally:
    h.close()
