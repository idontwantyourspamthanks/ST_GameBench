Midwinter 2 (Atari ST) - patched FLOPPY set, 2026-11-16
Release v1.5 enhanced by dad_prg

This is the original floppy game (the disk images shipped with PP's HD release) with
the same speed, display and control patches as the patched hard-disk build:
- Game speed is fixed to real time: the world no longer speeds up on faster
  machines (16 MHz Mega STE, accelerators).
- On foot, movement is smooth at whatever frame rate the machine manages.
- fixed (v1.5): on foot and in ground / surface vehicles (Crawler, Jeep, ...) the view height in the smooth
  in-between frames now follows the terrain; before, going downhill the view sank in steps at every world step.
- About 15% faster 3D display on a stock 8 MHz ST/STE, pixel-identical.
- Direct controls: the mouse turns only while it moves; joystick/keyboard turn at
  a constant rate while held and stop on release.
The orange MIDWINTER II logo screen (the one with "Insert Graphics Disk - press any key") shows a small, dim
"v1.5 enhanced by dad_prg" at the bottom; nothing else on it changes.
(The "no grey fading while loading" fix of the HD build does not apply: there is no
loader service on floppy and nothing fades.)

Needs 1 MB RAM (as the original), a double-sided 80-track drive.
Tested in Hatari 2.6.1: STE with TOS 1.62 and Mega ST with TOS 1.04, 1 MB.
The disks are standard 720K .ST images (9 sectors, 2 sides, 80 tracks).

DISKS
  FFA_boot.st            START-UP disk (disk A). Boot from it. It is the original FFA plus
                         one extra file (the patch code) on tracks 72-79 of side 0.
  FFB_graphics.st        GRAPHICS disk (disk B), unchanged original.
  FFC_missions.st        MISSIONS disk (disk C), unchanged original.
  FFD_campaign_blank.st  A blank, formatted disk for your campaign, unchanged.
                         Make a copy of it for each campaign.
(The game also has a PERSONNEL disk for saving/loading agents: another blank copy.)

STARTING
  1. Put FFA_boot.st in drive A and reset. The title picture loads (about a minute
     in the emulator), then "Insert Graphics Disk - press any key".
  2. Put FFB_graphics.st in drive A and press a key. Press M, J or K for mouse,
     joystick or keyboard control.
  3. The security check (identify a Secret Police member) is skipped, as in the
     HD release.
  4. Whenever the game needs another disk it shows "Insert ... Disk, press any key":
     swap the disk in drive A and press a key. A campaign disk left in drive B
     was found by the game without a prompt in the tests.

CAMPAIGN DISK (needed before you can play a mission)
  War Room -> START NEW CAMPAIGN -> type a name, RETURN -> CREATE CAMPAIGN DISK.
  The game copies the whole MISSIONS disk onto the pre-formatted campaign disk (copy
  of FFD_campaign_blank.st, not write-protected) in 4 passes of 40 track-sides. Use
  drive A for both disks and leave drive B empty. Each pass:
    - "Insert your 'MISSIONS' disk": put FFC_missions.st in drive A, click the copy icon;
    - "Insert your 'CAMPAIGN' disk": put the campaign disk in drive A, click the copy icon.
  When the fourth pass is done the creation is finished. Never use FFA/FFB/FFC as the
  destination. From then on the game asks for the campaign disk as "Insert Campaign
  Disk".
  Emulator note: with Hatari 2.6.1 the creation did not finish in a test run. Its log said
  "Writing not possible, discarded the contents of floppy image" for the campaign .st
  file from the second pass on (probably because the game's first write replaces the DOS
  boot sector) and the last pass ended with "Disk Error". Use real drives or another
  emulator, or the HD version, to create the campaign disk.

PATCHES IN THIS SET
asn_core, asn_lv1, asn_lv2, asn_lvc, asn_mus, asn_wd, floppy_copybuf, jag_btn, jag_dir, jag_poll, mw2_credit, p3c_render, p3c_sim, p3cp_head, p3cp_keys, p4_grid, p4_hud_pfx_circle, p4_hud_pfx_fill, p4_hud_pfx_replay, p4_hud_pfx_ymin, p4_hud_reset, p4_proj_axis, p4_proj_cols, p4_proj_div, p4_walk, p4_walk_c4, p4_walk_ret, p4_walk_tab, p5_ctl_vbl, p5_ctl_x, p7_cell_cull, p7_cell_pre, p7_ck_enter, p7_ck_exit, p7_ck_obj, p7_ck_poly, p7_ck_tab, p7_skip_enter, p7_skip_gate, p7_skip_render, p7_skip_scn, p7_skip_wv1, p7_skip_wv2, p7_skip_wv3, p8_tt_ptr, tick_vbl
(floppy_copybuf: keeps the game's own disk-copy buffer below the patch code.)

MD5 OF THE IMAGES
  d34daadecf683db76ae808f378275b0c  FFA_boot.st
  9d4ea2ddfcfe5fa7fdf7b54f26168ed3  FFB_graphics.st
  252d0ad0674db02ba5d104891db12e29  FFC_missions.st
  5e034299f50432eb6fe5e7048a5d2ccc  FFD_campaign_blank.st

Technical notes: patches/README.md ("Floppy build") and work/notes/floppy.md of the
patch project.

- Amiga sound effects and music (new in v1.5; patches asn_core asn_wd asn_lvc asn_lv1 asn_lv2 asn_mus; STE and Mega STE
  only): the Amiga release's sound effects AND music replace the YM chip's, played through the STE's DMA sound (mono;
  effects 6258 Hz, music 12517 Hz, mixed in software). ST, Mega ST, TT and Falcon keep the YM sound. The title, hall and
  map screens play the Amiga tunes, the 3D view the Amiga effects. Costs about 5-9% of the frame rate while effects play
  and about 30% of the CPU while a tune plays on the title, hall and map screens. Known: the music stutters where the
  game loads. The boot stub's title tune (about 28 s on floppy) stays YM; the Amiga tunes start at the logo screen. The
  sample bank (176 KB; samples plus the sound code) is included, on the spare tracks of the first disk (FFA track-sides
  81-126, after the patch code); it was converted from disk 1 of the Amiga release.
