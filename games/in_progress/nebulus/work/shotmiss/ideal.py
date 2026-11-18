import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
D = open('/tmp/shot_play_enemy.bin','rb').read()
SHOT_TAB = D[0x3b7c6:0x3b7c6+16]
def sgn(v, m): v &= (m - 1); return v - m if v >= m // 2 else v
def ideal_hit(sx, sy, cx, cy, tab=SHOT_TAB):
    """what sub_03b7d6 intends for the shot box vs a creature (table indexed by dy+7, dy = shot.y-creature.y in -7..8)"""
    dx = sgn(sx - cx, 128); dy = sgn(sy - cy, 1024)
    if not (-3 <= dx <= 2): return False
    if not (-7 <= dy <= 7): return False
    return bool(tab[dy + 7] >> (dx + 3) & 1)
def garbage_hit(sx, sy, cx, cy, code=D):
    dx = sgn(sx - cx, 128); dy = sgn(sy - cy, 1024)
    if not (-3 <= dx <= 2): return False
    if not (-7 <= dy <= 7): return False
    idx = ((dy & 0x3ff) + 7) & 0xffff
    return bool(code[0x3b7c6 + idx] >> (dx + 3) & 1)
