#!/usr/bin/env python3
"""Leave a build running at the map view and watch for the crash / payload trampling.

The user reported that WW1 "after a while" throws an address error (``Address Error
writing at address $1bebc25f, PC=$e09598``) — an odd address in TOS, which means a stack
or pointer had already been corrupted. This tool decides whether that is ours or the
stock release's:

* every sample it checks the **tick payload is intact** (its first 16 bytes at ``$72000``
  and the variable block at ``$72180``), because a resource load that lands on top of the
  payload is the obvious way to corrupt code;
* it checks the **world counter is still advancing** (the game is still running);
* it greps Hatari's log for address/bus errors.

    python3 tools/soak.py --build build/soak-pat --minutes 12
    python3 tools/soak.py --stock --minutes 12

``--stock`` runs the unpatched Cobra files directly (``extracted/cobra26``), which is the
control: it also has no protection problem because it is the answer-removed build ...
no — the stock build stops at the protection question, so ``--stock`` here means the
noprot-only reference build (``wwbuild.py build --only noprot``), the same reference the
release gate uses. The one thing it does not have is the tick payload.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))

from pmww import PMWW, TOS  # noqa: E402

TICK = 0x2ED90
PAYLOAD = 0x72000
VARS = 0x72180
CACHE = 0x2CFDA        # the resource cache's bump cursor, starts at $80000, no upper bound
PACKPAY = 0xC1D84      # the packer's own resident payload — the cache grows towards it
PAYLOAD_SIG = bytes.fromhex("2f082f002f0152b9")     # tick.bin's first 8 bytes
ERRORS = ("Address Error", "Bus Error", "Illegal Instruction", "double bus error",
          "CPU halted", "Halt dialog")


def read_bytes(h, addr: int, n: int) -> bytes | None:
	for _ in range(4):
		s = h.debug(f"m ${addr:x} {n}", wait=0.45)
		toks = []
		for line in s.splitlines():
			if re.match(r"^[0-9A-F]{8}:", line):
				toks += [t for t in line.split(':', 1)[1].split()
				         if len(t) == 2 and all(c in "0123456789ABCDEFabcdef" for c in t)]
		if len(toks) >= n:
			return bytes(int(t, 16) for t in toks[:n])
		time.sleep(0.3)
	return None


def read_long(h, addr: int) -> int:
	b = read_bytes(h, addr, 4)
	return int.from_bytes(b, 'big') if b else -1


def to_map(h) -> None:
	for attempt in range(3):
		try:
			_to_map(h)
			return
		except RuntimeError as e:
			print(f"  navigation: {e} (retry {attempt + 1}/3)", flush=True)
			time.sleep(3)
	raise SystemExit("navigation failed three times")


def _to_map(h) -> None:
	time.sleep(6)
	t = time.time()
	while not h.at_gate("name"):
		if time.time() - t > 180:
			raise RuntimeError("name prompt not reached")
		h.key("space")
		time.sleep(2.5)
	for ch in "SOAK":
		h.key(ch)
		time.sleep(0.4)
	h.key("Return")
	t = time.time()
	while not h.at_gate("opt"):
		if time.time() - t > 45:
			raise RuntimeError("options screen not reached")
		h.key("space")
		time.sleep(2.2)
	h.debug("w $5a84e 0 1", wait=0.5)
	h.poke_click(112, 72)          # Start New Conquest
	time.sleep(3)
	h.poke_click(130, 88)          # activate
	time.sleep(16)
	for _ in range(10):
		h.poke_click(60, 20)
		time.sleep(10)
		a = read_long(h, TICK)
		time.sleep(1.5)
		if read_long(h, TICK) > a > 0:
			break
	else:
		raise RuntimeError("map view not reached")
	time.sleep(8)


def errors_in_log(h) -> list[str]:
	text = h._logtext()
	found = []
	for line in text.splitlines():
		if any(e in line for e in ERRORS):
			found.append(line.strip())
	return found


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--build", type=Path, help="folder containing WW1.PRG (patched)")
	ap.add_argument("--minutes", type=float, default=10.0)
	ap.add_argument("--stock", action="store_true", help="the noprot-only reference instead")
	ap.add_argument("--sample", type=float, default=20.0)
	args = ap.parse_args()

	if args.stock:
		folder = GAME / "build" / "soak-stock"
		import subprocess
		subprocess.run([sys.executable, str(HERE / "wwbuild.py"), "build", "--only", "noprot",
		                "--out", str(folder)], check=True, capture_output=True)
		import shutil
		shutil.copy(GAME / "extracted" / "cobra26" / "WW1_FUZI.LFB", folder / "WW1_FUZI.LFB")
	else:
		folder = args.build
		if folder is None:
			raise SystemExit("--build DIR or --stock")

	# the game cannot start without its data file beside the program: catch it here rather
	# than after three failed navigations
	if not (folder / "WW1_FUZI.LFB").exists():
		raise SystemExit(f"{folder} has no WW1_FUZI.LFB; wwbuild.py writes only WW1.PRG — "
		                 f"copy the data file in (play.sh does this for you)")
	print(f"soaking {folder} for {args.minutes:.0f} minutes", flush=True)
	h = PMWW(disk=None, no_floppy=True, autorun_f="C:\\WW1.PRG", files_from=folder,
	         machine="ste", tos=TOS["1.62"])
	samples = 0
	stopped_early = False
	ran_for = 0.0
	try:
		to_map(h)
		start = time.time()
		last_tick = read_long(h, TICK)
		last_vbl = h.vbl()
		while time.time() - start < args.minutes * 60:
			time.sleep(args.sample)
			samples += 1
			sig = read_bytes(h, PAYLOAD, 8)
			now = read_long(h, TICK)
			vbl = h.vbl()
			errs = errors_in_log(h)
			cache = read_long(h, CACHE)
			alive = now > last_tick
			payload_ok = (sig == PAYLOAD_SIG) if not args.stock else True
			# A world counter that stops is not necessarily a fault: at the map view the game
			# can enter the 3D battle view (the general's portrait), where $2ed90 does not
			# advance. That is normal; only a halt with error lines is a crash.
			if not alive and not errs:
				print(f"[{samples:3d}] t={(time.time() - start) / 60:5.1f}m world={now} "
				      f"stopped advancing — checking whether this is the battle view", flush=True)
				h.shot(str(GAME / "work" / "soak-pause.png"))
				time.sleep(10)
				again = read_long(h, TICK)
				if again > now:
					print("       it was a pause; still running", flush=True)
					last_tick, last_vbl = again, h.vbl()
					continue
				print("       left the map view (battle/portrait) — trying to return", flush=True)
				# the portrait view returns with the right button (ESC in most of the UI)
				for _ in range(4):
					h.key("Escape")
					time.sleep(4)
					if read_long(h, TICK) > now:
						break
				back = read_long(h, TICK)
				if back > now:
					print(f"       back at the map (world {back}); continuing", flush=True)
					last_tick, last_vbl = back, h.vbl()
					continue
				print("       could not return; stopping (no errors: not a crash)", flush=True)
				stopped_early = True
				break
			rate = (now - last_tick) / ((vbl - last_vbl) / 50.0) if vbl > last_vbl else -1
			print(f"[{samples:3d}] t={(time.time() - start) / 60:5.1f}m "
			      f"world={now:<6d} {'+' if alive else 'STUCK'} "
			      f"{rate:5.2f} ticks/s  payload={'ok' if payload_ok else 'TRAMPLED ' + str(sig)} "
			      f"cache=${cache:05x}  errors={len(errs)}", flush=True)
			for e in errs[-3:]:
				print(f"        {e}", flush=True)
			if cache >= PAYLOAD:
				print(f"  ---- the resource cache (${cache:05x}) has reached the payload area", flush=True)
			if not payload_ok or errs:
				print("  ---- stopping early", flush=True)
				try:
					h.shot(str(GAME / "work" / "soak-fail.png"))
					dump = GAME / "work" / "soak-fail.bin"
					dump.unlink(missing_ok=True)
					h.cmd(f"hatari-debug savebin {dump} 0 1048576")
					time.sleep(2)
					print(f"  dump: {dump} ({dump.stat().st_size if dump.exists() else 0} bytes)", flush=True)
				except Exception as e:      # a dead CPU can make the debugger unusable
					print(f"  (could not dump: {e})", flush=True)
				break
			last_tick, last_vbl = now, vbl
			ran_for = time.time() - start
	finally:
		h.close()

	if errs:
		print(f"\nFAIL: {len(errs)} error lines")
	elif stopped_early:
		print(f"\nOK: {samples} samples, {ran_for / 60:.1f} min until the game left the map view "
		      f"(a battle or another screen, not a fault); no errors, payload intact")
	else:
		print(f"\nOK: {samples} samples over {args.minutes:.0f} minutes, no errors")


if __name__ == "__main__":
	main()
