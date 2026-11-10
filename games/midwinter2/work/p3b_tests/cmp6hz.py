"""Group-end equality, option A vs partial B, any pair of t6 pickles (t6.py output names t6_<which>_<hd><tag>.pkl in /tmp/p3b):
    python3 cmp6hz.py A_tag B_tag     e.g. A=Anew B=B2new: python3 cmp6hz.py Anew_768_N60 B2new_768_N60
Rows of B with PH == 5 are the group ends; row 0 of each is the sampling start and skipped (as cmp6.py)."""
import pickle, sys
a, b = sys.argv[1], sys.argv[2]
A = pickle.load(open(f'/tmp/p3b/t6_{a}.pkl', 'rb')); B = pickle.load(open(f'/tmp/p3b/t6_{b}.pkl', 'rb'))
Ag = A[1:]; Bg = [x for x in B[1:] if x['PH'] == 5]
keys = ['X', 'Y', 'H', 'clk', 'cd', 'alt', 'blk', 'spd', 'bank', 'type']
bad = 0
for k in range(min(len(Ag), len(Bg))):
    d = [x for x in keys if Ag[k][x] != Bg[k][x]]
    bad += bool(d)
    if d or k < 3:
        print(k + 1, [Ag[k][x] for x in keys], [Bg[k][x] for x in keys], 'EQ' if not d else 'DIFF ' + ','.join(d))
print(a, b, 'groups', min(len(Ag), len(Bg)), 'mismatching', bad)
