#!/usr/bin/env python3
from dronekit import connect, VehicleMode, LocationGlobalRelative, LocationGlobal, Command
from pymavlink import mavutil
from threading import Lock, Thread, Event
import json
import argparse
import numpy as np
import math
import signal
import logging
import time
import sys,os
import pickle
from socket import *

UAVs = 3 # How many UAVs we're controlling
stillUpdatingChannel = True
channelUpdateRate = 1 # how often to recompute the channel in Hz
transmissionRange = 200 # in meters
CHANNEL_UPDATE_PORT = 4999  # update channel matrix through this default port
BASE_UAV_PORT = 14550 # add the logical node number for each UAV (14551 for node 1)
exit = Event()

##### setup logging ####
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('channelSimulator')



######## Read the configuration  ##############
def getConfiguration(configFile):
    try:
        with open(configFile) as json_data_file:
            configList = json.load(json_data_file)
        return configList
    except IOError as e:
        logger.error('Error reading ' + configFile)
        logger.error(e)
        return
    except ValueError as e:
        logger.error('Error parsing ' + configFile)
        logger.error(e)
        return
    except Exception as e:
        logger.error('Unexpected error parsing ' + configFile + ':' + str(sys.exc_info()[0]))
        logger.error(e)
        return
    logger.info('Parsed inputs')


def allArmable(vehicle): # returns true only if all vehicles are armable
    allArmable=True
    for i in range(0,UAVs):
        allArmable = allArmable and vehicle[i].is_armable
    return allArmable

def channelModelDisk(distance):
    # for now a simple disk model
    if distance < transmissionRange:
        return 1
    else:
        return 2 # two means multiply with zero for now - needs fixing (should be zero)


def channelModelFading(distance):
    # ever so slightly more realistic
    # Used this:
    # https://hal.archives-ouvertes.fr/hal-01418637/file/IET_ELetters_2016.pdf
    # for the values below it has about 45% success rate at 400m

    receiverThreshold = 0.00001
    alpha = 2.    # path loss coefficient (freespace!)
    d0 = 1.       # reference disance
    gamma0 = 1.   # power at d0

    pSuccess = math.exp(-receiverThreshold*pow(distance/d0,alpha)/(2*gamma0))
    return pSuccess


def initializeAllLocations(configList):
    # This returns all current locations from the configuration file (already converted to a list)
    locations = [];
    for index,configElement in enumerate(configList):
        lat = configElement['Latitude'];
        lon = configElement['Longitude'];
        alt = configElement['Altitude'];
        newLocation = LocationGlobal(lat,lon,alt);
        locations.append(newLocation);

    return locations


def connectAllVehicles(configList):
    # This returns all current locations from the configuration file (already converted to a list)
    vehicles = [];
    for index,configElement in enumerate(configList):
        if configElement['Type']=="UAV":
            port = BASE_UAV_PORT+configElement['LogicalNodeNumber']
            connectionString = ':'+str(port)
            print("Connecting to: "+connectionString)
            vehicles.append(connect(connectionString, wait_ready=True,heartbeat_timeout=300))
#            vehicles.append(connectionString)
        else:
            vehicles.append(None)

    return vehicles


def updateLocations(allLocations,vehicles):
    # This returns all current locations from the configuration file (already converted to a list)

    newLocations=[];
    assert len(allLocations)==len(vehicles)
            # , "Different size vector for locations and vehicles"+len(locations)+"!="+len(vehicles));

    for i in range(len(vehicles)):
        if vehicles[i] == None:  #meaning it's a fixed node
            newLocations.append(allLocations[i])
        else:
            newLocations.append(vehicles[i].location.global_frame)

    return newLocations;


def computePairwiseDistances(allLocations):
    # This returns all pairwise distances given the locations

    numberOfNodes = len(allLocations)
    distances = [[0 for col in range(0,numberOfNodes)] for row in range(0,numberOfNodes)]

    for i in range(0,numberOfNodes): 
        for j in range(0,numberOfNodes):
            if (i != j):
                distances[i][j]= get_distance_metres(allLocations[i],allLocations[j])

    return distances;


def computeChannel(distances):
    # This returns the channel matrix given all pairwise distances
    # in the channel matrix:
    #   0 means no forwarding at all (no signal)
    #   1 means 100% forwarding
    #   2 means forwarding after multiplying with zero (zeroed signal)

    numberOfNodes = len(distances)
    channel = [[0 for col in range(0,numberOfNodes)] for row in range(0,numberOfNodes)]

    for i in range(0,numberOfNodes): 
        for j in range(0,numberOfNodes):
            if (i != j):
                channel[i][j] = channelModelDisk(distances[i][j])
#                channel[i][j] = channelModelFading(distances[i][j])

    return channel;





def channelUpdate(allLocations,vehicles):

    # This will get the locations of the UAVs and compute the wireless channel
    global stillUpdatingChannel
    try:
        txSocket = socket(AF_INET,SOCK_DGRAM)
    except Exception as error:
        #print('Cannot open channel update channel:',error)
        logger.error('Cannot open channel update channel:',error)

    while stillUpdatingChannel:

        # here we get all updated locations (only updated for the vehicles)
        allLocations = updateLocations(allLocations, vehicles);

        # computer pair-wise distances
        distances   = computePairwiseDistances(allLocations);

        # compute the channel
        channel = computeChannel(distances);

        #Here we send the channel to GCHEM
        payload = pickle.dumps(channel)
        #print(np.matrix(channel))
        try:
            txSocket.sendto(payload,('', CHANNEL_UPDATE_PORT))
        except Exception as error:
            logger.error('Cannot send channel weights:',error)

        # For debugging purposes:
        #logger.debug('Distances:')
        #logger.debug(np.matrix(distances))
        #logger.debug('Channel:')
        #logger.debug(np.matrix(channel))
        # print('Distances:')
        # print(np.matrix(distances))
        # print('Channel:')
        # print(np.matrix(channel))

        # repeat 
        time.sleep(1./channelUpdateRate)

    print('Done updating')
    txSocket.close()

######### Catch and handle Ctrl+C  ###############
def signal_handler(signal, frame):
    global stillUpdatingChannel
    stillUpdatingChannel = False # kill the thread on Ctrl+C
    print('Handling Ctrl+C')
    exit.set()




def get_distance_metres(aLocation1, aLocation2):
    """
    Returns the ground distance in metres between two LocationGlobal objects.
    This method is an approximation, and will not be accurate over large distances and close to the 
    earth's poles. It comes from the ArduPilot test code: 
    https://github.com/diydrones/ardupilot/blob/master/Tools/autotest/common.py
    """
    dlat = aLocation2.lat - aLocation1.lat
    dlong = aLocation2.lon - aLocation1.lon
    return math.sqrt((dlat*dlat) + (dlong*dlong)) * 1.113195e5




def main():

    global stillUpdatingChannel;

    # Setup the interrupt handler
    signal.signal(signal.SIGINT,signal_handler)


    # Parse the arguments
    parser = argparse.ArgumentParser(description='Optional config file')
    parser.add_argument('-m','--manifest', metavar='configFile',
                        type=argparse.FileType('r'),
                        nargs=1,
                        default = 'manifest.json',
                        help='The .json configuration file for the nodes being emulated')
    parser.add_argument('-d','--debug', dest='debug', action='store_const',
                    const='debug', default='info',
                    help='Enable debug level for the logger')
    parser.add_argument('-p','--channelEmulatorPort',help='port number', type=int, default=CHANNEL_UPDATE_PORT)

    args = parser.parse_args()
    if args.debug=='debug':
        logger.setLevel(logging.DEBUG)
    elif args.debug=='info':
        logger.setLevel(logging.INFO)

    if type(args.manifest) == type([]):                                     
        configFile = args.manifest[0].name
    else:
        configFile = args.manifest.name

    # Read and parse the configuration file
    configList = getConfiguration(configFile)


    if (configList == None):
        logger.critical('Exiting due to bad configuration file');
        sys.exit()

    allLocations = initializeAllLocations(configList)
    vehicles = connectAllVehicles(configList)

#    print(vehicles)


    print('All initialized, channel updating started')

    # Start the channel computation thread
    thread = Thread(target = channelUpdate, args = (allLocations, vehicles,))
    thread.start()

    print('Press enter to exit')
    input()
    stillUpdatingChannel = False # stop the thread
    thread.join()
    logger.info('Done')

if __name__ == "__main__":
    # execute only if run as a script
    main()

    
