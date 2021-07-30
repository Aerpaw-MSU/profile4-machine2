#!/bin/bash
export PYTHONPATH=/AERPAWBLOCKS/
pkill screen
#docker container kill $(docker ps -q)
pkill python3
pkill iperf3
sleep 5
ip link delete tun0
ip link delete srs_spgw_sgi
ip link delete tun
