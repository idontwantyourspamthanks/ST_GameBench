"""poptick.py ab with pop_tt_ptr added to the --release set of both runs (it is a TT/Falcon-only site: the STE live image must not contain it)."""
import sys
from pathlib import Path
GAME = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous")
sys.path.insert(0, str(GAME / "tools"))
import poptick as pt
pt.RELEASE.extend(["pop_tt_ptr", "pop_tt_ptr2"])
sys.argv = ["poptick.py"] + sys.argv[1:]
sys.exit(pt.main())
