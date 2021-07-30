#!/bin/bash
source .profile
./cleanup.sh
./startMachine1.sh $1 $2	
sleep 5

if [[ $1 == "TESTBED" && $2 == "PING" ]]
  then
  sleep 15
  cd Tests/
  ./startPingTestbed.sh
  elif [[ $1 == "TESTBED" && $2 == "IPERF" ]]
  then
  sleep 15
  cd Tests/
  ./startIperfTestbed.sh
  elif [[ $1 == "ZMQ" && $2 == "PING" ]]
  then
  sleep 15
  cd Tests/
  ./startPingZmq.sh
  elif [[ $1 == "ZMQ" && $2 == "IPERF" ]]
  then
  sleep 15
  cd Tests/
  ./startIperfZmq.sh
  elif [[ $1 == "ZCHEM" && $2 == "PING" ]]
  then
  sleep 15
  elif [[ $1 == "ZCHEM" && $2 == "IPERF" ]]
  then
  sleep 15
fi
