"""Lotus exemplar harness: floppy boot in Hatari via tools/stharness.Hatari (wrapper strips --harddrive)."""
import sys, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[4]
sys.path.insert(0, str(BENCH / 'tools'))
import stharness
from stharness import Hatari, TOS
DISK = BENCH / 'games/exemplars/2d-racing/lotus_esprit_turbo_challenge_ste_1_0_[thomas_jonathan].st'
os.environ['LOTUS_DISK'] = str(DISK)
_orig = stharness.hatari_bin
stharness.hatari_bin = lambda machine: str(HERE / 'hatari_flop.sh')

EMPTY = HERE / 'emptyhd'
EMPTY.mkdir(exist_ok=True)

class Lotus(Hatari):
    def __init__(self, snapshot=None, machine='ste', memsize_kb=1024, tos=None, extra=None):
        super().__init__(game_dir=str(EMPTY), snapshot=snapshot, machine=machine, tos=tos,
                         memsize_kb=memsize_kb, autorun='', extra=extra or [])
