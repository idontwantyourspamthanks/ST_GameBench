"""boot_to_game with --trace gemdos; save the Fopen/Fseek/Fread/Fclose lines of the GAME-phase service."""
import sys, time, re
from pathlib import Path
sys.path.insert(0,'tools')
from mw2harness import Hatari
name, game, mem = sys.argv[1], sys.argv[2], int(sys.argv[3])
h = Hatari(snapshot=None, memsize_kb=mem, game_dir=Path(game), machine='megaste',
           tos=Path('tos/TOS_2_06.img').resolve(), extra=['--trace', 'gemdos'])
try:
    h.boot_to_game('M')
    time.sleep(2)
    t = h._logtext()
    Path(f'work/bigram/{name}_gemdos.txt').write_text(t)
    print(name, 'log lines', len(t.splitlines()))
finally:
    h.close()
