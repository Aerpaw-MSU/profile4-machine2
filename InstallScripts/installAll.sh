#!/bin/bash
#
# This script should install all the necessary scripts for  
# the CH-EM-VM container in preparation for starting

set -e
# In principle this makes the script return immediatly with an error code
# if command fails (returns a non zero code)

# Pull the AERPAW repository
cd /root

WORKAREA=/root/Workarea
REPO=/root/AERPAW-Dev

# Link the scripts
ln -s $REPO/DCS/Emulation/emul_wireless_channel/InstallScripts $WORKAREA/InstallScripts

# Link in the Channel Emulator
ln -s $REPO/DCS/Emulation/emul_wireless_channel/CHEM $WORKAREA/CHEM

# Install the rest of dependencies
apt install -y net-tools iputils-ping nano iperf3 iperf inetutils-traceroute traceroute usbutils iproute2 isc-dhcp-client emacs python3 python3-pip screen emacs25

pip3 install dronekit python-pytun pymavlink pyserial zmq keyboard numpy



