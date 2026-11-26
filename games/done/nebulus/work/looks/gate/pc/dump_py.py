import sys, json
sys.path.insert(0, '/tmp/looksgate/games/in_progress/nebulus/work/editor')
import ovl
out = {}
for f in sys.argv[1:]:
    raw = open(f, 'rb').read(); lv, camps = ovl.parse(raw)
    p = ovl.LV0; recs = []
    for l in lv:
        recs.append(dict(mission=l['mission'], tower=l['tower'], rows=l['rows'], time_bcd=l['time'], name=l['name'], colours=l['flags'] >> 4, enemy_set=l['flags'] & 15,
                         grid=l['grid'], record=raw[p:p + l['size']].hex())); p += l['size']
    out[f.split('/')[-1]] = dict(levels=recs, playlists=[dict(name=n, entries=[dict(type='original', mission=((x >> 3) & 7) + 1, tower=(x & 7) + 1) if x & 0x80 else dict(type='custom', index=x) for x in e]) for n, e in camps])
print(json.dumps(out, sort_keys=True))
