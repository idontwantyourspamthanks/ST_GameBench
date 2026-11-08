#!/usr/bin/env python3
"""One cold-boot test cell for Midwinter 1 builds.

    python3 tools/mw1cell.py NAME MACHINE TOS MEM_KB GAME_DIR [--live PREFIX] [--team]

Cold boots GAME_DIR (a build/ copy or the original game dir), waits for the Game Options screen
(exact match of work/ref/options_play.png), then:
  * prints the marker ($B2FF8: MWPO / MWPF / 0000 for an unpatched game),
  * with --live PREFIX (the .img/.json written by `mw1patch.py live`): compares the payload
    $B3000.. with the built image and every site's RAM bytes with its `new` bytes,
  * saves a screenshot,
  * with --team: clicks PLAY and waits for THE TEAM screen (work/ref/team_title.png), then
    repeats marker/payload/site checks and saves another screenshot.
Raw lines go to stdout and to /tmp/mw1cell_NAME.log.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mw1harness import MW1, TOS, REF  # noqa: E402

TEAM_BOX = (320, 50, 510, 90)


def main():
    a = sys.argv[1:]
    name, machine, tos, mem, game = a[:5]
    live = a[a.index("--live") + 1] if "--live" in a else None
    team = "--team" in a
    out = Path("/tmp") / f"mw1cell_{name}"
    out.mkdir(exist_ok=True)
    log = open(f"/tmp/mw1cell_{name}.log", "w")

    def L(*x):
        s = " ".join(str(v) for v in x)
        print(s, flush=True)
        log.write(s + "\n")

    img = spec = None
    if live:
        img = Path(live + ".img").read_bytes()
        spec = json.loads(Path(live + ".json").read_text())
    h = MW1(game_dir=Path(game).resolve(), snapshot=None, machine=machine, tos=TOS[tos], memsize_kb=int(mem))
    try:
        L("cell", name, machine, "TOS", tos, mem, "KB", game)

        def checks(stage):
            m = h.debug("m $b2ff8 4").strip().splitlines()[-1]
            L(f"[{stage}] marker:", m)
            if img is not None:
                p = out / f"{stage}_payload.bin"
                h.debug(f"savebin {p} $b3000 {len(img)}", wait=2)
                ram = p.read_bytes()
                diff = [i for i in range(len(img)) if ram[i] != img[i]]
                L(f"[{stage}] payload $B3000..+${len(img):x} vs built image: {len(diff)} bytes differ")
                for s in spec["sites"]:
                    ln = len(s["new"]) // 2
                    q = out / f"{stage}_site.bin"
                    h.debug(f"savebin {q} ${s['addr']:x} {ln}", wait=1)
                    b = q.read_bytes()
                    L(f"[{stage}] site ${s['addr']:06x} [{s['name']}] RAM {b.hex()}  new {s['new']}  orig {s['orig']}  ->",
                      "PATCHED" if b.hex() == s["new"] else ("ORIGINAL" if b.hex() == s["orig"] else "OTHER"))

        ok = h.boot_to_options()
        L("Game Options screen reached:", ok)
        if not ok:
            h.shot(str(out / "fail.png"))
            return 1
        h.shot(str(out / "options.png"))
        checks("options")
        if team:
            h.goto(415, 385)
            h.click()
            ok = False
            t = time.time()
            while time.time() - t < 60:
                if h.matches(REF / "team_title.png", TEAM_BOX):
                    ok = True
                    break
                time.sleep(2)
            L("THE TEAM screen reached:", ok)
            h.shot(str(out / "team.png"))
            checks("team")
            return 0 if ok else 1
        return 0
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main())
