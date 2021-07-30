# zchem demos

## zmq_tun demo
### Dependencies
pip3 install python-pytun zmq
### Run
In the Tests/ directory run the following commands
`docker-compose --file docker-compose-tun-demo.yml build`
`docker-compose --file docker-compose-tun-demo.yml up`
These will build and run three docker containers. The first is a server node running the `zchem.py` script.
The other two nodes are running the script `zmq_tun.py` located in `AERPAW-Dev/AHN/E-VM/ACN_base_images_config/NetworkLevelEmulationAdaptation`
This script creates a tun interface at `10.0.0.2` and `10.0.0.3` in the two client nodes respectively and connects their interfaces to the zchem server script.

These scripts are automatically run and all the command line parameters are configured in the docker-compose.yaml file.

To test it is working properly you can
`docker exec -it tests_node_1_1 /bin/bash`
or
`docker exec -it tests_node_2_1 /bin/bash`
and once you are in the container try to ping the tun interface of the other client docker node. (`ping 10.0.0.3` if you are in node 1)

### zmq
All zmq sockets are setup as PAIR sockets. I'm not sure what type of connection srsUE uses, but if it uses something other than PAIR zchem.py will need to be updated.

## SRS demo
### Dependencies
pip3 install python-pytun zmq

If the Dockerfile used the base docker image `nmullane/srs_node` or another docker image with zmq and srsLTE configure than the entire srs demo can be run in the next secion.

Otherwise you will need to do the following setup steps inside both `tests_node_1_1` and `tests_node_2_1` docker containers.

#### SRS Setup
```bash
# general dependencies
apt-get install build-essential cmake libfftw3-dev libmbedtls-dev libboost-program-options-dev libconfig++-dev libsctp-dev

# this isn't a script just copy and paste what is needed
apt-get install libzmq3-dev #if you dont do this, SRS will install but the commands afterwards will not work
git clone https://github.com/srsRAN/srsRAN.git
cd srsRAN
git checkout release_20_10_1
mkdir build
cd build
cmake ../
make -j xxx #replace xxx with number of CPU cores
make install
ldconfig
srsran_install_configs.sh user

# above installs SRS. do this on both nodes


# On node 1 Terminal 1
srsepc

# On node 1 Terminal 2, you may need to play around with the port numbers depending on your setup
srsenb --rf.device_name=zmq --rf.device_args="fail_on_disconnect=true,tx_port=tcp://*:5001,rx_port=tcp://172.17.0.2:5101,id=enb,base_srate=23.04e6"

# On node 2
srsue --rf.device_name=zmq --rf.device_args="tx_port=tcp://*:5002,rx_port=tcp://172.17.0.2:5102,id=ue,base_srate=23.04e6"
```

### Run
In the Tests/ directory run the following commands
`docker-compose --file docker-compose-srs-demo.yml build`
`docker-compose --file docker-compose-srs-demo.yml up`
#### Launch zchem
On the docker container `tests_server_1`, kill the running instance of zchem. Due to the lockstep request reply architecture, zchem needs to be launched after srsenb and srsue nodes.
##### Node 1:
`srsepc`
and
``bash
srsenb --rf.device_name=zmq --rf.device_args="fail_on_disconnect=true,tx_port=tcp://*:5101,rx_port=tcp://172.17.0.2:5001,id=enb,base_srate=23.04e6"
``

##### Node 2:
``bash
srsue --rf.device_name=zmq --rf.device_args="tx_port=tcp://*:5102,rx_port=tcp://172.17.0.2:5002,id=ue,base_srate=23.04e6"
``
##### Server:
launch zchem with `-t req_rep`, and channelSimulator with 2 nodes.

