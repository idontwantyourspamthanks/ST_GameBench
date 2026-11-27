# Gamebench Agent Guidelines

## Release Artifacts

For every game release, always build and include a standalone, auto-booting single-game hard-disk image (`.vhd`) for MiSTer / Hatari / real Atari ST hardware in the game's `dist/` directory alongside the HD zip (and floppy image where applicable):

- Register the game in `tools/make_game_vhds.py` (`SPECS`) and wire the game's `tools/package.sh` (or release script) to invoke `python3 tools/make_game_vhds.py <slug>` so every release automatically produces the single-game `*_vhd*.zip` in `games/<done|in_progress>/<slug>/dist/`.
- Each `.vhd` is an 8 MB raw `HDDRIVER` + FAT16 BGM partition image with `DESKTOP.INF` (TOS 1.x) and `NEWDESK.INF` (TOS 2.x/3.x) configured to auto-boot straight into the game (or `C:\AUTO\` for AUTO-booting titles), packaged with a `README.TXT`.
- Verify the standalone `.vhd` by cold-booting it in Hatari with `--gemdos-drive skip --acsi 0=<game>.vhd`.

## General Rules

- Never modify anything under `originals/`.
- Keep games in `games/in_progress/<slug>/` until the user explicitly declares them ready to promote to `games/done/<slug>/`.
- Always include a discreet `enhanced by dad_prg vX.Y` credit on the title screen so patched releases are clearly distinguished from originals.
