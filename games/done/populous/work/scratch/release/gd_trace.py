import sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent / "machines")]
from mm import start
h = start("ste", "gemdos", sys.argv[1], extra=["--trace", "gemdos"])
try:
    time.sleep(16); h.key("space", 0.5); time.sleep(30)
    lg = open(h.logpath).read()
    print("\n".join(l[:150] for l in lg.splitlines() if "Crawio" not in l and "repeats" not in l and "PNG" not in l and "Cconws" not in l)[-3000:])
finally:
    h.close()
