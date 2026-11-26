for t in 3 4 6 2; do
  PRE=0.3 python3 ride2.py /tmp/lp/ste_p_t$t.sav t${t}_e1q 24 1 > /tmp/lp/b2_t$t.out 2>&1
  python3 ana.py /tmp/lp/tr_t${t}_e1q/log.txt | tail -4 > /tmp/lp/b2_t$t.ana
done
echo done > /tmp/lp/b2.done
