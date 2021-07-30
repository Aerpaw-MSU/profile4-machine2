#!/bin/bash

# MODE is either TESTBED,ZMQ,or ZCHEM
MODE=$1

TX_GAIN=70
RX_GAIN=40
EARFCN=2900
N_PRB=100


if [ $MODE == "TESTBED" ]
  then
  mkdir /dev/net
  mknod /dev/net/tun c 10 200
  ip tuntap add mode tun srs_spgw_sgi	
  screen -S run -dm bash -c "./ofdm_rx_b210_tuntap_with_tx.py | ts '[%Y-%m-%d %H:%M:%.S]' > testbed.log" 
  screen -S setip -dm bash -c "ifconfig tap2 192.168.0.1"
  
elif [ $MODE == "ZMQ" ]
then
  
  
  screen -S run -dm bash -c "./ofdm_zmq.py | ts '[%Y-%m-%d %H:%M:%.S]' > zmq.log"
  screen -S setip -dm bash -c "ifconfig tap2 172.17.0.1"
 

 
elif [ $MODE == "ZCHEM" ]
then


 cd CHEM/TESTS/
 screen -S docker -dm bash -c "docker-compose up"
 sleep 10
# screen -S ping -dm bash -c "
 docker exec -it tests_node_1_1 ping -w 60 172.17.0.3 | ts '[%Y-%m-%d %H:%M:%.S]' > zchemping1.log
 sleep 70
 pkill screen
#screen -S copy -dm bash -c "docker cp tests_node_1_1:/home/scripts/zchemping.log /"
#screen -S copy -dm bash -c "docker cp tests_node_2_1:/home/scripts/zchemping1.log /"

else
  echo "No mode specified"


fi



