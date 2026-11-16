cd "$(dirname "$0")"
for sn in ste1m_race_start ste1m_race_grid; do
 for mhz in 8 16 32; do for v in A T; do
  python3 exp_tick.py $v $sn.sav $mhz 600 36 2>&1 | tail -1 | python3 -c "import sys,json;r=json.loads(sys.stdin.read());print('%s %s %2d MHz: pass/s %.3f VBL/pass %.3f pos/s %.2f sw/s %.3f'%(r['variant'],r['snap'][:-4],r['mhz'],r['pass_per_s'],r['vbl_per_pass'],r['pos_per_s'],r['sw_per_s']))"
 done; done
done
