
#!/bin/bash

ping -i 0.2 -c 20 172.16.0.2 |  ts '[%Y-%m-%d %H:%M:%.S]' | tee pingResultsEPC.txt
