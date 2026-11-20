cd "$(dirname "$0")/../.."
for cfg in "ste 1024 1.62" "ste 4096 1.62" "megaste 4096 2.06" "st 1024 1.04" "tt 4096 3.06"; do set -- $cfg
 echo "=== $1 $2 TOS $3"
 python3 tools/msr_boot_test.py --machine $1 --mem $2 --tos $3 --game build/mt_default --peek b2700 b8f00 2>&1 | grep -E "RESULT|PEEK|Error|Traceback" 
done
