#!/usr/bin/env python3
"""Powermonger WW1: the command-icon grid (the 1990 game's design, the WW1's tables).

The game hit-tests the perspective command icons with two line tables (near-vertical
separators at $13bde, near-horizontal at $13c58); the cell code is column + 16*row, found
exactly as the 1990 game's tools/pmtt_grid.py does:

    col: for each vertical line (x0,y0,x1,y1):
             q = (x-x0) * (y1-y0) / (x1-x0)          (signed 16-bit, word result)
             col++;  continue while (y-y0) < q
    row: for each horizontal line:
             q = ...
             cell += 16;  continue while (y-y0) > q

The code cell is looked up in the 24-entry table at $1a89a: the entry index = the icon id
(the same ids as the 1990 game). Live-verified cell codes (work/dumps/grid_t1/t2.bin,
mapview.sav): (285,168)=$da -> id 4 Get Men, (250,165)=$d9 -> id 10 Derank,
(202,181)=$d7 -> id 3 Get Food, (245,189)=$e8 -> id 6 Attack, (300,150)=$db -> id 8 Equip,
(100,150)=$94 -> id 20 Neutral posture.
"""

from __future__ import annotations

# the two tables from work/dumps/grid_t1.bin / grid_t2.bin ($13bde / $13c58)
VERTICAL = [
	(23, 95, 24, 199), (63, 93, 64, 199), (74, 91, 88, 199), (91, 89, 125, 199),
	(107, 88, 160, 199), (122, 86, 198, 199), (138, 85, 231, 199), (151, 83, 268, 199),
	(164, 82, 302, 199), (177, 80, 319, 184), (189, 79, 319, 162), (204, 77, 319, 145),
	(216, 77, 319, 131), (230, 76, 319, 122), (238, 74, 319, 113),
]
HORIZONTAL = [
	(237, 74, 1, 99), (244, 77, 1, 106), (252, 82, 1, 114), (260, 85, 1, 122),
	(270, 90, 1, 128), (280, 93, 1, 136), (290, 98, 1, 145), (300, 104, 1, 156),
	(315, 111, 1, 168), (319, 119, 1, 182), (319, 131, 1, 199), (319, 143, 90, 199),
	(319, 160, 170, 199), (319, 182, 258, 199),
]
# the action table $1a89a: index = icon id -> cell code
ACTION_CELLS = [0x00, 0xEA, 0xC4, 0xD7, 0xDA, 0xB4, 0xE8, 0xE9, 0xDB, 0xD5, 0xD9, 0x00,
                0xD6, 0xD8, 0xB3, 0xA3, 0x93, 0x00, 0x00, 0xA4, 0x94, 0x84, 0xC3, 0x83]


def _wrap16(v: int) -> int:
	"""68300 word result."""
	v &= 0xFFFF
	return v - 0x10000 if v & 0x8000 else v


def cell_code(x: int, y: int) -> int | None:
	"""The game's cell code for a screen point (None outside the tables' zone)."""
	cell = 0
	for x0, y0, x1, y1 in VERTICAL:
		if x1 == x0:
			return None
		q = _wrap16(((x - x0) * (y1 - y0)) // (x1 - x0))
		cell += 1
		if not (y - y0) < q:
			break
	for x0, y0, x1, y1 in HORIZONTAL:
		if x1 == x0:
			return None
		q = _wrap16(((x - x0) * (y1 - y0)) // (x1 - x0))
		cell += 0x10
		if not (y - y0) > q:
			break
	return cell


def icon_id(x: int, y: int) -> int | None:
	"""The icon id under a screen point (None = no icon / blank cell)."""
	cell = cell_code(x, y)
	if cell is None or cell not in ACTION_CELLS:
		return None
	return ACTION_CELLS.index(cell)


def icon_cells() -> dict[int, list[tuple[int, int]]]:
	"""Every screen pixel (inside the icon zone) grouped by icon id."""
	out: dict[int, list[tuple[int, int]]] = {}
	for y in range(120, 200):
		for x in range(64, 320):
			cell = cell_code(x, y)
			if cell in ACTION_CELLS:
				out.setdefault(ACTION_CELLS.index(cell), []).append((x, y))
	return out


def icon_centres() -> dict[int, tuple[int, int]]:
	return {i: (sum(p[0] for p in ps) // len(ps), sum(p[1] for p in ps) // len(ps))
	        for i, ps in icon_cells().items()}


# the 1990 command names (work/done/powermonger work/notes/tooltip.md section 1.2; the
# user's manual: the WW1 has the same icons in the same places doing the same job)
NAMES = {
	1: "Send Captain", 2: "Transfer Men", 3: "Get Food", 4: "Get Men", 5: "Go Home",
	6: "Attack", 7: "Invent", 8: "Equip", 9: "Drop Food", 10: "Derank", 12: "Drop Items",
	13: "Supply Food", 14: "Trade", 15: "Alliance", 16: "Spy", 19: "Aggressive",
	20: "Neutral", 21: "Passive", 22: "Query", 23: "Option",
}

if __name__ == "__main__":
	# self-test against the live-verified readings
	checks = {(285, 168): 4, (275, 163): 4, (250, 165): 10, (202, 181): 3,
	          (245, 189): 6, (300, 150): 8, (100, 150): 20}
	ok = True
	for (x, y), want in checks.items():
		got = icon_id(x, y)
		print(f"({x},{y}): icon {got} (want {want}){'  MISMATCH' if got != want else ''}")
		ok &= got == want
	print("oracle:", "PASS" if ok else "FAIL")
	print("icon centres (id: x,y  name):")
	for i, (x, y) in sorted(icon_centres().items()):
		print(f"  {i:2d}: ({x:3d},{y:3d})  {NAMES.get(i, '?')}")
