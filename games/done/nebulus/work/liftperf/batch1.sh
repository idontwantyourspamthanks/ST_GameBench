for t in 1 3 4 6 7 8; do
  python3 ride2.py /tmp/lp/ste_p_t$t.sav t${t}_e1 24 1 > /tmp/lp/b1_t$t.out 2>&1
  python3 ana.py /tmp/lp/tr_t${t}_e1/log.txt | tail -4 > /tmp/lp/b1_t$t.ana
done
echo done > /tmp/lp/b1.done
