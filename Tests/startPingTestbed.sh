
#!/bin/bash

ping -i 0.2 -c 20 192.168.0.1 |  ts '[%Y-%m-%d %H:%M:%.S]' | tee pingResultsEPC.txt
