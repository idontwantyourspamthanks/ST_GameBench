for t in 8 4 6 5 3 2 1 7; do
  PRE=0.2 python3 ride2.py /tmp/lp/ste_s_t$t.sav s${t}_e1 24 1 > /tmp/lp/b4_t$t.out 2>&1
  python3 ana.py /tmp/lp/tr_s${t}_e1/log.txt | tail -4 > /tmp/lp/b4_t$t.ana
done
echo done > /tmp/lp/b4.done
