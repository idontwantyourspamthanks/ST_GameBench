"""docs gate: submenu names (Campaigns, level, campaign entry menus), T/E no-ops in the editor, Delete/C clear, Return/Space repeat, Name..., Options page hint"""
import sys; sys.path.insert(0, '/tmp/ng12fl/s')
exec(open('/tmp/ng12fl/s/rt.py').read().split("DOC = {}\ntry:")[0])
try:
    print('floppy title', bool(h.boot_to_title(timeout=500, space_at=25 if MEM > 1024 else 20)), flush=True); time.sleep(3)
    for i in range(14):
        h.shot(OUT + f'opt{i}.png'); time.sleep(2.5)
    h.debug(f'loadbin /tmp/ng12fl/w_rt_ste_out/saved.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
    h.key('F10', hold=0.5); time.sleep(2.5)
    pick('Campaigns >'); P('campaigns list: %r' % names()); pick('<new campaign>', 1.5); P('after <new campaign>: %r' % names())
    pick(0, 1.5); P('after <add entry>: %r' % names())
    h.key('Left', hold=0.2); time.sleep(1.2); P('Left 1: %r' % names()); h.shot(OUT + 'left1.png')
    try:
        pick(0, 1.5); P('campaign menu: %r' % names()); h.shot(OUT + 'camp_menu.png')
        pick('Edit entries', 1.5); P('entries list: %r' % names()); pick(0, 1.2); P('entry menu: %r' % names()); h.shot(OUT + 'entry_menu.png')
    except Exception as e: P('campaign submenu walk failed: %r' % e)
    for _ in range(5): h.key('Left', hold=0.2); time.sleep(1.0)
    P('main menu again: %r' % names())
    pick('Levels'); P('levels list: %r' % names()); pick(0, 1.2); P('level menu: %r' % names()); h.shot(OUT + 'level_menu.png')
    pick('Edit', 1.5)
    g = gridnow(); cx, cy = W(h, RS + 20), W(h, RS + 22)
    at(8, 5); K('p'); a = col(8, 5, 1)[0]; K('t'); K('e'); b = col(8, 5, 1)[0]; chk('T and E do nothing in the editor map', (a, b, W(h, RS + 20), W(h, RS + 22)), (0x80, 0x80, 8, 5))
    K('Delete'); chk('Delete clears', col(8, 5, 1)[0], 0); K('p'); K('c'); chk('C clears', col(8, 5, 1)[0], 0)
    at(9, 5); K('l'); at(10, 5); K('Return'); at(11, 5); K('space'); chk('L then Return, Space repeat the ledge', col(9, 5, 1) + col(10, 5, 1) + col(11, 5, 1), [0x81] * 3)
    at(4, 8); K('s'); v = col(4, 8, 1)[0]; K('s'); w = col(4, 8, 1)[0]; P('stone ball S then S again on the same enemy: %#x -> %#x' % (v, w)); h.shot(OUT + 'enemy_s.png')
    fire(1.2); pick('Level >', 1.0); pick('Name...', 1.2); h.shot(OUT + 'name.png'); P('name prompt hint status: %r' % msgnow()); ensure_map()
except Exception as ex:
    import traceback; traceback.print_exc(); chk('exception in the script', repr(ex)[:200], 'none')
finally:
    h.close(); time.sleep(1)
print('FAILS', fails)
