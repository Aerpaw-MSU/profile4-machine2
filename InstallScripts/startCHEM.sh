#!/bin/bash

MODE=${1-IQ_EMULATION}
WORKAREA=/root/Workarea
# Entire address prefix of the XE(E-VM) containers to connect to
# XE(E-VM, X3) = 192.168.153.65
ADDR_PREFIX=192.168.153.
FIRST_SUFFIX=65
FIRST_PORT=5001

cd $WORKAREA/CHEM

if [ $MODE = "IQ_EMULATION" ]
then
    SOCKET_TYPE=req_rep
elif [ $MODE = "PL_EMULATION" ]
then
    SOCKET_TYPE=pair
else
    echo "No mode specified"
fi


#
#To do: make zchem read the number of nodes from an argument
# rather than the json file (or better, yet, the manifest once settled on)
#

screen -S zchem -dm \
       python3 ./zchem.py -t $SOCKET_TYPE \
       --scenario num_nodes.json \
       --addr_prefix $ADDR_PREFIX \
       --first_suffix $FIRST_SUFFIX \
       --first_port $FIRST_PORT 

# Redirect not working (likely it's redirecting screen instead of python3)
#
#       > >(tee -a zchemOut.log) 2> >(tee -a zchemErr.log >&2)
