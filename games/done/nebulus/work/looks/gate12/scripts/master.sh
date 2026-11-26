#!/bin/bash
cd /tmp/ng12hd/nb; L=/tmp/ng12hd/logs
while [ ! -f $L/ste/done ]; do sleep 20; done
./chainE.sh megaste > $L/chainE_mega.out 2>&1
./chainE.sh st > $L/chainE_st.out 2>&1
./chainC.sh > $L/chainC.out 2>&1
./chainL.sh > $L/chainL.out 2>&1
echo all > $L/master.done
