import time 
import datetime
import os
import RPi.GPIO as GPIO
from thread import *
#import SimpleHTTPServer
#import SocketServer
#import Adafruit_GPIO.SPI as SPI
#import Adafruit_MAX31855.MAX31855 as MAX31855
import threading
import logging
import paho.mqtt.client as mqtt
import json

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# TCP Connection Settings
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

# there are two topics with two sub-topics each. Each sub-topic has a name, of which describes who is PUBLISHING to that topic
# for example, the ESB pi publishes valve states on TOPIC_2 ("Valve_States/Servers") and the Client publishes commands on
# TOPIC_1 ("Valve_States/Clients")

print ("\nLaunch Control Server Initialized.")

HOST = "192.168.1.128"
TOPIC_1 = "Valve_States/Clients"
TOPIC_2 = "Valve_States/Servers"
TOPIC_3 = "Buttons/Servers"

print (("Please connect client software to: %s at port: %d \n") % (HOST, 1883))
print ("Waiting to establish connection........ \n")

def on_connect(client, userdata, flags, rc):
	print("Connected with result code "+str(rc))
	print ("Connection established.")
	#print ('Connection address: ',addr)
	#logger.debug("Connection established at {}".format(time.asctime())) #find what the ip is
	print ("Awaiting commands... \n")
	error = rc
	client.subscribe(TOPIC_1)
	return error

def on_disconnect(client, userdata,rc=0):
	print("Connection Lost.")
	client.loop_stop()

def on_message(client, userdata, msg):
	calldata(str(msg.payload))
	if str(msg.payload) == "Read_Valves":
		callvalves(str(msg.payload))

client = mqtt.Client("server",True)
client.on_connect = on_connect
client.on_message = on_message
#client.on_publish = on_publish
client.on_disconnect = on_disconnect
client.connect(HOST, 1883, 60)



#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Feedback Logging Setup
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

#setting up the logging program
#all of the logging events will be put into a text file wherever the location is specified
#the location can be specified by setting the "filename" equal to "anyname.log"
#if the logging filname is kept the same, the logging events will be put in the same file, adding to past events.


logname = time.strftime("LC_ServerLog(%H_%M_%S).log",time.localtime())
logger = logging.getLogger("")                                                                 
logging.basicConfig(filename=logname, level=logging.DEBUG)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Pin Setup
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

# All pins are set to use the broadcom numbering scheme on the raspberry pi
# Refer to this wiring standard when setting up or changing pins

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

ign1 = 18        # 18 is for the first ignitor
ign2 = 27        # 27 is for the second ignitor
vnts = 22        # 22 is the pin setup for the vents
main = 23        # 23 is the pin setup for the main valves
bstr = 24         # 24 is for the HACK HD camera actuation
PoE_1 = 20		 # 20 is the PoE for Data Acquisition 1
PoE_2 = 21		 # 21 is the PoE for Data Acquisition 2	

GPIO.setup(ign1,GPIO.OUT)
GPIO.setup(ign2,GPIO.OUT)
GPIO.setup(vnts,GPIO.OUT)
GPIO.setup(main,GPIO.OUT) 
GPIO.setup(bstr,GPIO.OUT) 
GPIO.setup(PoE_1,GPIO.OUT)
GPIO.setup(PoE_2,GPIO.OUT)

# set all pin outputs to false initially so that they do not
# actuate anything upon the program starting

GPIO.output(ign1, GPIO.input(ign1))
GPIO.output(ign2,GPIO.input(ign2))
GPIO.output(vnts,GPIO.input(vnts))
GPIO.output(main,GPIO.input(main))
GPIO.output(bstr,GPIO.input(bstr))
GPIO.output(PoE_1,GPIO.input(PoE_1))
GPIO.output(PoE_2,GPIO.input(PoE_2))

b_wire = 17      # 17 is the pin for the breakwire
r_main = 13      # 13 is the pin for the main valve reed switch
r_LOX = 19       # 19 is the pin for the LOX reed switch
r_kero = 26      # 26 is the pin for the kero reed switch

GPIO.setup(b_wire,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)     # this pin is setup to control the breakwire
GPIO.setup(r_main,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)     # setup for the main fuel feedback signal
GPIO.setup(r_LOX,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)      # setup for the LOX feedback signal
GPIO.setup(r_kero,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)     # setup for the Kerosene feedback signal

# setup for the thermocouple
# these pins should not change, recommended pins that should be used are set

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Sensor Reading
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

def Thermo_read():

	# This function contains a simple C to F converter function as well as the loop to 
	# reed the temperatures and to send it off as data over the TCP connection

	def c_to_f(c):

		return c * 9.0 / 5.0 + 32.0

	while True:		

		temp = sensor.readTempC()
		internal = sensor.readInternalC()
		Temperature = c_to_f(temp)

		return Temperature

def Breakwire_read():

	# Breakwire input is read here. If the input is true, this means that the connection 
	# is intact and that the breakwire has not been broken yet.
	# The state of the breakwire is sent over the TCP connection

	if GPIO.input(b_wire) == True:
		bwire = "Intact"
		#print "sent b_wire status"
		logger.debug("sent b_wire status of {} at {}".format(str(bwire), time.asctime()))
	elif GPIO.input(b_wire) == False:
		bwire = "Broken"
		#print "Sent b_wire status of {}".format(bwire)
		logger.debug("Sent b_wire status of {} at {}".format(str(bwire), time.asctime()))
	return bwire

def Main_Valve_Sensor():

	# Function that reads the magnetic reed switch on board the rocket at the main fuel valves

	if GPIO.input(r_main) == True:
		main_status = "Open"
		#print "main is open: sending status"
		logger.debug("main is open: sending main_status at {}".format(time.asctime()))
		#print "Sent status of {}".format(main_status)
		logger.debug("Sent main_status(open) of {} at {}".format(str(main_status), time.asctime()))
	elif GPIO.input(r_main) == False:
		main_status = "Closed"
		#print "main is closed: sending status"
		logger.debug("main is closed: sending main_status at {}".format(time.asctime()))
		#print "Sent status of {}".format(main_status)
		logger.debug("Sent main_status(closed) of {} at {}".format(str(main_status), time.asctime()))
	return main_status

def LOX_Valve_Sensor():

	# Function that reads the magnetic reed switch on board the rocket at the LOX valve

	if GPIO.input(r_LOX) == True:
		LOX_status = "Open"
		logger.debug("Sent LOX_status(open) of {} at {}".format(str(LOX_status), time.asctime()))
	elif GPIO.input(r_LOX) == False:
		LOX_status = "Closed"
		logger.debug("Sent LOX_status(closed) of {} at {}".format(str(LOX_status), time.asctime()))
	return LOX_status

def Kero_Valve_Sensor():

	# Function that reads the magnetic reed switch on board the rocket at the Kerosene valve

	if GPIO.input(r_kero) == True:
		kero_status = "Open"
		logger.debug("Sent: kero_status(open) of {} at {}".format(str(kero_status), time.asctime()))
	elif GPIO.input(r_kero) == False:
		kero_status = "Closed"
		logger.debug("Sent kero_status(closed) of {} at {}".format(str(kero_status), time.asctime()))
	return kero_status


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Relay and Communication
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

# All of the functions for actuating are pretty straight forward and appropriately
# named. These functions set the correct pins to high or low depending on the state at
# which we request them to be turned to. Abort controls multiple pins because this state
# requires us to close the main valve and turn the ignitor signal off while opening the 
# vents

def PoE_Switch_On():
	GPIO.output(PoE_1,True)
	GPIO.output(PoE_2,True)
	client.publish(TOPIC_3,"Switching power to onboard control.")
	return

def PoE_Switch_Off():
	GPIO.output(PoE_1,False)
	GPIO.output(PoE_2,False)
	client.publish(TOPIC_3,"Switching power to launch control system.")
	return

def boosters_lit():

	GPIO.output(bstr,True)
	client.publish(TOPIC_3,"Boosters Lit")
	return

def boosters_off():

	GPIO.output(bstr,False)
	client.publish(TOPIC_3,"Boosters Off")
	return

def ignitor_one_on():

	# Ignitor one has default control over both ignitors. To change this, comment out the the line of 
	# GPIO.output(27,True)

	GPIO.output(ign1,True)
	client.publish(TOPIC_3,"Ignitor 1 Lit")
	return

def ignitor_one_off():

	# Ignitor one has default control over both ignitors. To change this, comment out the the line of 
	# GPIO.output(27,False)

	GPIO.output(ign1,False)
	client.publish(TOPIC_3,"Ignitor 1 Off")
	return

def ignitor_two_on():

	GPIO.output(ign2,True)
	client.publish(TOPIC_3,"Ignitor 2 Lit")
	return

def ignitor_two_off():

	GPIO.output(ign2,False)
	client.publish(TOPIC_3,"Ignitor 2 Off")
	return

def main_open():

	GPIO.output(main,True)
	client.publish(TOPIC_3,"Main Valve Opened")
	return

def main_close():

	GPIO.output(main,False)
	client.publish(TOPIC_3,"Main Valve Closed")
	return

def vent_open():

	GPIO.output(vnts,False)
	client.publish(TOPIC_3,"Vents Opened")
	return

def vent_close():

	GPIO.output(vnts,True)
	client.publish(TOPIC_3,"Vents Closed")
	return

def launch():

	GPIO.output(main,True)
	GPIO.output(bstr,True)
	client.publish(TOPIC_3,"Launch!")
	return

def abort():

	GPIO.output(ign1,False)
	GPIO.output(bstr,False)
	GPIO.output(main,False)
	GPIO.output(vnts,True)
	client.publish(TOPIC_3,"Launch Aborted")
	return

def sensors():
	bstatus = Breakwire_read()
	mstatus = Main_Valve_Sensor()
	lstatus = LOX_Valve_Sensor()
	kstatus = Kero_Valve_Sensor()

	package = "{'bstatus':'%s','mstatus':'%s','lstatus':'%s','kstatus':'%s'}" % (bstatus,mstatus,lstatus,kstatus)

	client.publish(TOPIC_2, package)
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Main Loop
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

# Our main loop is the listener or the TCP connection. It listens for 'data' and 
# uses this data to analyze what is being requested on the Launch Control Client. Data
# that is receieved requesting valve or ignitor actuation simply jumps into the correct
# function listed above. If sensor information is requested, new threads are started that
# use the target function specified to send sensor information back to the client software.


def calldata(data):

	if 'boosters_lit' in data:
		print ("Received data: ",data)
		boosters_lit()

	elif 'boosters_off' in data:
		print ("Received data: ", data)
		boosters_off()
	
	elif 'rocket_power' in data:
		print ("Received data: ", data)
		PoE_Switch_On()

	elif 'esb_power' in data:
		print ("Received data: ", data)
		PoE_Switch_Off()
	
	elif 'ign1_on' in data:
		print ("Received data: ", data)
		ignitor_one_on()
	
	elif 'ign1_off' in data:
		print ("Received data: ", data)
		ignitor_one_off()

	elif 'ign2_on' in data:
		print ("Received data: ", data)
		ignitor_two_on()
	
	elif 'ign2_off' in data:
		print ("Received data: ", data)
		ignitor_two_off()
	
	elif 'vents_open' in data:
		print ("Received data: ", data)
		vent_open()

	elif 'vents_close' in data:
		print ("Received data: ", data)
		vent_close()
	
	elif 'main_open' in data:
		print ("Received data: ", data)
		main_open()

	elif 'main_close' in data:
		print ("Received data: ", data)
		main_close()

	elif 'launch' in data:
		print ("Received data: ", data)
		launch()

	elif 'abort' in data:
		print ("Received data: ", data)
		abort()

def callvalves(data):
		
	if 'temp_status' in data:
		thermo_trd = threading.Thread(target=Thermo_read())
		thermo_trd.start()
		
	elif 'bwire_status' in data:
		bwire_trd = threading.Thread(target=Breakwire_read())
		bwire_trd.start()

	elif 'main_status' in data:
		r_main_trd = threading.Thread(target=Main_Valve_Sensor())
		r_main_trd.start()

	elif 'kero_status' in data:
		r_kero_trd = threading.Thread(target=Kero_Valve_Sensor())
		r_kero_trd.start()

	elif 'LOX_status' in data:
		r_LOX_trd = threading.Thread(target=LOX_Valve_Sensor())
		r_LOX_trd.start()

	sensors()

client.loop_forever()
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# End Script
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
