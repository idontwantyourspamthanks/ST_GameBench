for t in 1 2 3 4 5 8; do
  PRE=0.3 python3 ride2.py /tmp/lp/ste_q_t$t.sav q${t}_e1 24 1 > /tmp/lp/b3_t$t.out 2>&1
  python3 ana.py /tmp/lp/tr_q${t}_e1/log.txt | tail -4 > /tmp/lp/b3_t$t.ana
done
echo done > /tmp/lp/b3.done
