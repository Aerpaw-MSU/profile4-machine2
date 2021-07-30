#!/usr/bin/env python
import json
import argparse
import select
import random
import logging
import signal
import time
import sys,os
import pickle
from threading import Event
from socket import *
sys.path.insert(2, '../MessageDefinitions/')


channel = None
exit = Event()

##### setup logging ####
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('channelSimulator')


######## Wait for a key  ##################
def wait_key():
    ''' Wait for a key press on the console and return it. '''
    result = None
    if os.name == 'nt':
        import msvcrt
        result = msvcrt.getch()
    else:
        import termios
        fd = sys.stdin.fileno()

        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)

        try:
            result = sys.stdin.read(1)
        except IOError:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)

    return result

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

def signal_handler(signal, frame):
    sys.exit()

# function changing the channel, playing the configuration and passing the Channel matrix to GCHEM
def playConfig(configList,CHANNEL_UPDATE_PORT,ipaddress):
    global channel

    try:
        txSocket = socket(AF_INET,SOCK_DGRAM)                                           
    except Exception as error:
        print('Cannot open channel update channel:',error)
    
    for index,configElement in enumerate(configList):
        channel = configElement['Channel']
        try:  # getting backwards compatible (if TimeDelay is missing)
            timeDelay = configElement['TimeDelay']
        except:
            timeDelay = 0

        try:  # getting backwards compatible (if TimeDelay is missing)
            description = configElement['Description']
        except:
            description = ''
        print(channel) #Printing the channel matrix we are passing         
        #Here we are sending the channel to GCHEM
        payload = pickle.dumps(channel)

        try:
            txSocket.sendto(payload,(ipaddress, CHANNEL_UPDATE_PORT))
        except Exception as error:
            print('Cannot send channel weights:',error)
    
        logger.info('At configuration element: '+str(index+1)       
                    +' '+description)

        if (index == len(configList)- 1): # last element, no need to wait
            break
        
        if (timeDelay <=0): # wait for a key enter
            print('Press a key to step over...')
            wait_key()
        else: # wait for timeDelay seconds
            time.sleep(timeDelay)
            #exit.wait(timeDelay) # interruptable version of sleep

    txSocket.close()
    logger.info('No more changes in the channel')

def main():
    global channel

    #Handle the command line arguments
    #Default is scenario.json
    parser = argparse.ArgumentParser(description='Optional config file')
    parser.add_argument('-s','--scenario', metavar='configFile',
                        type=argparse.FileType('r'),
                        nargs=1,
                        default = 'scenario.json',
                        help='The .json configuration file for the channel')

    parser.add_argument('-d','--debug', dest='debug', action='store_const',
                    const='debug', default='info',
                    help='Enable debug level for the logger')
    parser.add_argument('-p','--channelSimulatorPort',help='port number', type=int, default=4999)
    parser.add_argument('-i','--ipaddress', help='ip address', type=str, default='127.0.0.1')

    args = parser.parse_args()
    if type(args.scenario) == type([]):                                     
        configFile = args.scenario[0].name
    else:
        configFile = args.scenario.name
        
    if args.debug=='debug':
        logger.setLevel(logging.DEBUG)

    signal.signal(signal.SIGINT,signal_handler)
    
    # Read and parse the configuration file
    configList = getConfiguration(configFile)

    # Playing the configuration and passing the channel matrix to gchem.py              
    playConfig(configList,args.channelSimulatorPort,args.ipaddress)
    
    if (configList == None):
        logger.critical('Exiting due to bad configuration file');
        sys.exit()

    while (channel == None):
        time.sleep(1) # wait for the channel to get initialized
                      # by the play thread
    

if __name__ == "__main__":
    # execute only if run as a script
    main()
