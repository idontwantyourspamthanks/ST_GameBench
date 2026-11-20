import sys, time
sys.argv = ["gate.py", "finish", "--machine", "ste", "--mem", "2048", "--tag", "explore"]
exec(open("gate.py").read().split("try:\n    {\"finish\"")[0])
h = new(file="c3.trk"); time.sleep(2)
menu_open(); load_from(1); time.sleep(1.5); h.keypress(0x1c)
t0 = time.time(); k = 0; done = False
while time.time() - t0 < 300:
    time.sleep(5)
    if race_up() and mem(h, 0x1024, 1)[0] == 0:
        h.debug("w $6105 $01", 0.3)
    elif mem(h, 0x1024, 1)[0] == 0xff and not done:
        done = True; h.debug("w $6105 $00", 0.3); t1 = time.time(); log("race over at", h.vbl())
    elif not race_up() and not done:
        h.keypress(57)
    if done:
        k += 1; shot(f"x{k:02d}"); log(k, "vbl", h.vbl(), "$1021", mem(h, 0x1021, 1).hex(), "$102c", mem(h, 0x102c, 2).hex(), "$23c0", mem(h, 0x23c0, 4).hex())
        if k == 2: h.debug("w $d486 $4e $b9 $00 $00 $d1 $38", 0.3); time.sleep(1); click_at(170, 211); shot("after_goto"); log("CLICK with the mouse query restored")
        if k >= 3: h.keypress(57); log("SPACE")
        if k >= 6: break
h.close()
