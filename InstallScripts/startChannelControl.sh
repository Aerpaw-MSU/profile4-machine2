#!/bin/bash

export WORKAREA=/root/Workarea

cd $WORKAREA/CHEM

screen -S control -dm \
       /bin/bash -c "python3 ./channelControl.py --manifest 2nodes1F1P.json | tee control.log"


