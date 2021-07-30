#!/bin/bash

screen -S iperf3 -dm bash -c "iperf3 -s | ts '[%Y-%m-%d %H:%M:%.S]' > iperf3.log"
