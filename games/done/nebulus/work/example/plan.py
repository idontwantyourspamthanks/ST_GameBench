"""Input plans for the three example levels, derived from the same geometry as work/editor/mk_example.py.
Joystick cell values (what the real keys send with --joy1 keys): $08 right, $04 left, $01 up, $02 down, $80 fire, $00 neutral.
Positions are the frog's x ($33a16, 8 units per column, column c is x = 8c+4 at its centre, supported x = 8c+1..8c+8, mod 128)."""
import sys
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
import mk_example as M

R, FIRE, UP = 0x08, 0x80, 0x01
def wall(col): return (8 * col - 3) % 128          # x of the frog standing against the wall of a ledge that starts in column col

def stairs(treads, risers, door_col, first=None):
    """walk right; at the wall of every 2-row riser press fire (the jump); on the top tread walk under the door and press Up"""
    ev = [dict(cell=R)]
    for k, rs in enumerate(risers):
        if rs == 2:
            ev += [dict(cond='x=%d&st=0' % wall(treads[k + 1][1]), cell=R | FIRE), dict(cond='st=1', cell=R)]
    xd = (8 * door_col + 4) % 128
    ev += [dict(cond='x=%d&st=0' % xd, cell=0x00), dict(cond='st=0&x=%d' % xd, cell=UP)]
    return ev

def spiral():
    tr = M.spiral_treads(); rs = M.SPIRAL_RISERS
    r, c, w = tr[-1]
    return stairs(tr, rs, c + 1)


def lifts():
    ev = [dict(cell=R)]
    ev += [dict(cond='x=44&st=0', cell=0), dict(cond='x=44&st=0', cell=UP), dict(cond='st=6', cell=0)]        # lift 1 (col 5): Up, ride 10 rows
    ev += [dict(cond='st=0&y>=48&x=44', cell=R)]                                                               # at the top: walk right onto the landing
    ev += [dict(cond='x=100&st=0', cell=0), dict(cond='x=100&st=0', cell=UP), dict(cond='st=6', cell=0)]      # lift 2 (col 12): ONE tap of Up = ride stops at the stop (row 18)
    ev += [dict(cond='st=0&y>=76', cell=UP), dict(cond='st=6', cell=0)]                                         # Up again: on to the end (row 25)
    ev += [dict(cond='st=0&y>=104', cell=R)]                                                                    # step off to the right, walk to the exit column 2
    ev += [dict(cond='x=20&st=0', cell=0), dict(cond='x=20&st=0', cell=UP)]
    return ev

def blocks():
    ev = [dict(cell=R)]
    ev += [dict(cond='x=45&st=0', cell=0), dict(cond='x=45&st=0', cell=FIRE), dict(cond='st=5', cell=0)]      # shot 1: first blue block
    ev += [dict(cond='st=0', cell=FIRE), dict(cond='st=5', cell=0)]                                            # shot 2: second block
    ev += [dict(cond='st=0', cell=R)]
    treads = M.BLOCK_TREADS; risers = [1, 2, 1, 2, 1]
    tr = [(2, 2, 8)] + treads
    for k, rs in enumerate(risers[1:], start=1):                                                               # risers k: tr[k] -> tr[k+1]
        pass
    for k in range(1, len(tr) - 1):
        if tr[k + 1][0] - tr[k][0] == 2:
            ev += [dict(cond='x=%d&st=0' % wall(tr[k + 1][1]), cell=R | FIRE), dict(cond='st=1', cell=R)]
    r, c, w = tr[-1]
    xd = (8 * (c + 2) + 4) % 128
    ev += [dict(cond='x=%d&st=0' % xd, cell=0), dict(cond='x=%d&st=0' % xd, cell=UP)]
    return ev
