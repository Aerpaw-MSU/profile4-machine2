
#!/bin/bash

ping -i 0.2 -c 20 172.17.0.1 |  ts '[%Y-%m-%d %H:%M:%.S]' | tee pingResultsEPC.txt
