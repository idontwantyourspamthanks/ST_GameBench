#!/usr/bin/env python3
"""Development wrapper: huntpatch.py with a private `sav_` prefix range (the lead adds the real one to PREFIX_RANGES).
    python3 tools/huntsave_build.py build --only <names> --out build/sav_game ...   (same arguments as huntpatch.py)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import huntpatch as hp
hp.PREFIX_RANGES.setdefault("sav_", (0xAE500, 0xAEFFF))
hp.main()
