#!/bin/bash

screen -S iperf3 -dm bash -c "iperf3 -c 172.17.0.1 | ts '[%Y-%m-%d %H:%M:%.S]' > iperf3.log"
