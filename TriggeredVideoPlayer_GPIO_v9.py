#Copyright Jesse Stevens @ Cake Industries 12/9/19
#icing@cake.net.au www.cake.net.au
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.

#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#####################################################################
# BRAND NEW UDP PACKET TRIGGERED VIDEO PLAYER:
# -Removed console clearing from here, better to run on external shell script
# -Listens for A or B to trigger video 1 or 2 in order
# -Plays holding video whilst waiting to be triggered
# -Returns to main holding video after playing triggered videos
# -Listens on all interfaces on UDP port 5005
# -Ensure the packets you send are encoded to byte in utf-8 encoding
#####################################################################

import RPi.GPIO as GPIO
import sys
import os
import subprocess
import psutil
import time
import threading
import socket
import random

##############################################################
# Shutdwn GPIO-Button
##############################################################
# load Librarys
from gpiozero import Button
from subprocess import check_call
from signal import pause

# define function
def shutdown():
    # Shutdown
    check_call(['sudo', 'poweroff'])

# Initialize GPIO21 as Button (Input)
shutdown_btn = Button(21, hold_time=2)

# Call function if Button is pressed
shutdown_btn.when_held = shutdown

##############################################################
# GPIO Pin in/out setup
##############################################################
GPIO.setmode(GPIO.BCM)

#Here we're using GPIO 17 and 18 as triggers, but these can be changed
#Be careful which pins you use, and do some reading on their functions
gpio1 = 17
gpio2 = 18

#We're pulling up voltage on these, so short to ground to trigger:
GPIO.setup(gpio1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(gpio2, GPIO.IN, pull_up_down=GPIO.PUD_UP) 

#Make sure your switches are pretty clean and your switching is simple
#The debounce amount below (in milliseconds) makes sure we don't get twitchy results
#from electrical noise or bad contacts. Increase this if you find multiple 
#triggers are happening. Better yet, use small capacitors to help the switch
#This is intended for momentary trigger switches, not state-based switches
gpiobounce = 100

###############################################################
# file locations for media
###############################################################
startmovie = ("/home/pi/video/start.mp4")
movie1 = ("/home/pi/video/video1.mp4")
movie2 = ("/home/pi/video/video2.mp4")
movie3 = ("/home/pi/video/video3.mp4")
movie4 = ("/home/pi/video/video4.mp4")
movie5 = ("/home/pi/video/video5.mp4")
movie6 = ("/home/pi/video/video6.mp4")
movie7 = ("/home/pi/video/video7.mp4")
movie8 = ("/home/pi/video/video8.mp4")
movie9 = ("/home/pi/video/video9.mp4")
movie10 = ("/home/pi/video/video10.mp4")
movie11 = ("/home/pi/video/video11.mp4")
movie12 = ("/home/pi/video/video12.mp4")

##################################################################
#variables for making sure we only trigger each video player once:
##################################################################
needtostart = 1
running = 0
mode = 0
gpio1status = 0
gpio2status = 0
modenew = 0

################################################################################
#Redirecting console output to null so we don't litter the window with feedback
################################################################################
FNULL = open(os.devnull,'w')

#####################################################################
# threaded callbacks for interrupt driven button triggers
# also: resets so buttons must be release and pressed to re-trigger
#####################################################################
def pressedgpio1(channel):
    global needtostart
    global mode
    global gpio1status
    #check that the button was previously release before re-triggering
    #remember, voltage low (zero) means pressed, due to our pull-ups
    if (gpio1status == 0 and GPIO.input(gpio1) == 0):
        print("GPIO#1 triggered")
        mode = 1
        needtostart = 1
        gpio1status = 1
    #the button was previously pressed, but is now released, let's reset
    #remember, voltage high (1) means released, due to our pull-ups
    elif (gpio1status == 1 and GPIO.input(gpio1) == 1):
        print("GPIO#1 released and reset")
        gpio1status = 0
    #button is still being held down from last time, do nothing
    elif (gpio1status == 1 and GPIO.input(gpio1) == 0):
        print("GPIO#1 still held down, not triggered")

def pressedgpio2(channel):
    global needtostart
    global mode
    global gpio2status
    #check that the button was previously release before re-triggering
    #remember, voltage low (zero) means pressed, due to our pull-ups
    if (gpio2status == 0 and GPIO.input(gpio2) == 0):
        print("GPIO#2 triggered")
        mode = 2
        needtostart = 1
        gpio2status = 1
    #the button was previously pressed, but is now released, let's reset
    #remember, voltage high (1) means released, due to our pull-ups
    elif (gpio2status == 1 and GPIO.input(gpio2) == 1):
        print("GPIO#2 released and reset")
        gpio2status = 0
    #button is still being held down from last time, do nothing
    elif (gpio2status == 1 and GPIO.input(gpio2) == 0):
        print("GPIO#2 still held down, not triggered")

#########################################################################
# Definition of callback functions to physical button mapping
#########################################################################
#Interrupt driven callbacks with 100ms debounce in case of electrical noise
#Short to ground to trigger, release to reset (rise/fall detected in callbacks):
GPIO.add_event_detect(gpio1, GPIO.BOTH, callback=pressedgpio1, bouncetime=gpiobounce)
GPIO.add_event_detect(gpio2, GPIO.BOTH, callback=pressedgpio2, bouncetime=gpiobounce)

#########################################################################
#Main looping
#########################################################################
try:

	while True:
		###################################################################
		#Base looping video
		###################################################################
		if (mode == 0):
			if (needtostart == 1):
				needtostart = 0
				#for troubleshooting: uncomment
				print("Starting main holding video")
				m = subprocess.Popen(['omxplayer', '-b', '--no-osd', startmovie], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to start video (for killing logic)
				running = 0

			else:
				#Not needed on base loop, but in case of crash
				#Check for end of video
				if m.poll() is not None:
					#Relaunch the process to start again
					modenew = random.randint(1,12)
					mode = modenew
					print("modenew = " + str(modenew))
					needtostart = 1
					m.kill()

		###################################################################
		#Triggered video 1
		###################################################################
		elif (mode == 1):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1 (restarting it)")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()

				#for troubleshooting: uncomment
				print("Starting first triggered video")
				needtostart = 0
				a = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie1], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 1 (for killing logic)
				running = 1
			else:
				#End checking:
				#if process has quit
				if a.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					a.kill()

		###################################################################
		#Triggered video 2
		###################################################################
		elif (mode == 2):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3 (Restarting it)")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()
				#for troubleshooting: uncomment
				print("Starting second triggered video")
				needtostart = 0
				b = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie2], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 2 (for killing logic)
				running = 2
			else:
				#End checking:
				#if process has quit
				if b.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					b.kill()

		###################################################################
		#Triggered video 3
		###################################################################
		elif (mode == 3):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2 (Restarting it)")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()
				#for troubleshooting: uncomment
				print("Starting third triggered video")
				needtostart = 0
				c = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie3], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 3 (for killing logic)
				running = 3
			else:
				#End checking:
				#if process has quit
				if c.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					c.kill()

		###################################################################
		#Triggered video 4
		###################################################################
		elif (mode == 4):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4 (Restarting it)")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()
				#for troubleshooting: uncomment
				print("Starting fourth triggered video")
				needtostart = 0
				d = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie4], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 4 (for killing logic)
				running = 4
			else:
				#End checking:
				#if process has quit
				if d.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					d.kill()

		###################################################################
		#Triggered video 5
		###################################################################
		elif (mode == 5):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5 (Restarting it)")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()
				#for troubleshooting: uncomment
				print("Starting fifth triggered video")
				needtostart = 0
				e = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie5], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 5 (for killing logic)
				running = 5
			else:
				#End checking:
				#if process has quit
				if e.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					e.kill()

		###################################################################
		#Triggered video 6
		###################################################################
		elif (mode == 6):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6 (Restarting it)")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()
				#for troubleshooting: uncomment
				print("Starting sixth triggered video")
				needtostart = 0
				f = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie6], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 6 (for killing logic)
				running = 6
			else:
				#End checking:
				#if process has quit
				if f.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					f.kill()

		###################################################################
		#Triggered video 7
		###################################################################
		elif (mode == 7):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7 (Restarting it)")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()
				#for troubleshooting: uncomment
				print("Starting seventh triggered video")
				needtostart = 0
				g = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie7], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 7 (for killing logic)
				running = 7
			else:
				#End checking:
				#if process has quit
				if g.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					g.kill()

		###################################################################
		#Triggered video 8
		###################################################################
		elif (mode == 8):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8 (Restarting it)")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()
				#for troubleshooting: uncomment
				print("Starting eighth triggered video")
				needtostart = 0
				h = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie8], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 8 (for killing logic)
				running = 8
			else:
				#End checking:
				#if process has quit
				if h.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					h.kill()

		###################################################################
		#Triggered video 9
		###################################################################
		elif (mode == 9):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9 (Restarting it)")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()
				#for troubleshooting: uncomment
				print("Starting ninth triggered video")
				needtostart = 0
				i = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie9], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 9 (for killing logic)
				running = 9
			else:
				#End checking:
				#if process has quit
				if i.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					i.kill()					

		###################################################################
		#Triggered video 10
		###################################################################
		elif (mode == 10):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10 (Restarting it)")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()
				#for troubleshooting: uncomment
				print("Starting tenth triggered video")
				needtostart = 0
				j = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie10], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 10 (for killing logic)
				running = 10
			else:
				#End checking:
				#if process has quit
				if j.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					j.kill()

		###################################################################
		#Triggered video 11
		###################################################################
		elif (mode == 11):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11 (Restarting it)")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()
				#for troubleshooting: uncomment
				print("Starting eleventh triggered video")
				needtostart = 0
				k = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie11], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 11 (for killing logic)
				running = 11
			else:
				#End checking:
				#if process has quit
				if k.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					k.kill()

		###################################################################
		#Triggered video 12
		###################################################################
		elif (mode == 12):
			if (needtostart == 1):
				#kill off other videos first
				if (running == 0):
					print("Killing start video")
					m.stdin.write(b'q')
					# m.stdin.flush()
					#Let's sink the boot in
					m.kill()
				elif (running == 1):
					print("Killing video 1")
					a.stdin.write(b'q')
					a.stdin.flush()
					#Let's sink the boot in
					a.kill()
				elif (running == 2):
					print("Killing video 2")
					b.stdin.write(b'q')
					b.stdin.flush()
					#Let's sink the boot in
					b.kill()
				elif (running == 3):
					print("Killing video 3")
					c.stdin.write(b'q')
					c.stdin.flush()
					#Let's sink the boot in
					c.kill()
				elif (running == 4):
					print("Killing video 4")
					d.stdin.write(b'q')
					d.stdin.flush()
					#Let's sink the boot in
					d.kill()
				elif (running == 5):
					print("Killing video 5")
					e.stdin.write(b'q')
					e.stdin.flush()
					#Let's sink the boot in
					e.kill()
				elif (running == 6):
					print("Killing video 6")
					f.stdin.write(b'q')
					f.stdin.flush()
					#Let's sink the boot in
					f.kill()
				elif (running == 7):
					print("Killing video 7")
					g.stdin.write(b'q')
					g.stdin.flush()
					#Let's sink the boot in
					g.kill()
				elif (running == 8):
					print("Killing video 8")
					h.stdin.write(b'q')
					h.stdin.flush()
					#Let's sink the boot in
					h.kill()
				elif (running == 9):
					print("Killing video 9")
					i.stdin.write(b'q')
					i.stdin.flush()
					#Let's sink the boot in
					i.kill()
				elif (running == 10):
					print("Killing video 10")
					j.stdin.write(b'q')
					j.stdin.flush()
					#Let's sink the boot in
					j.kill()
				elif (running == 11):
					print("Killing video 11")
					k.stdin.write(b'q')
					k.stdin.flush()
					#Let's sink the boot in
					k.kill()
				elif (running == 12):
					print("Killing video 12 (Restarting it)")
					l.stdin.write(b'q')
					l.stdin.flush()
					#Let's sink the boot in
					l.kill()
				#for troubleshooting: uncomment
				print("Starting twelfth triggered video")
				needtostart = 0
				l = subprocess.Popen(['omxplayer', '-b', '--no-osd', movie12], stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE, close_fds=True)
				#Set the current running to video 12 (for killing logic)
				running = 12
			else:
				#End checking:
				#if process has quit
				if l.poll() is not None:
					#go back to start video/holding frame
					mode = 0
					needtostart = 1
				#return back to start
				if (needtostart == 1):
					mode = 0
					l.kill()


		#give the loop some breathing space (eases up on resources, but delays response by 100ms)
		time.sleep(0.1)

#when killed, get rid of players and any other stuff that needs doing
finally:
	#make sure all players are killed fully off
	os.system('killall omxplayer.bin')
	os.system('killall omxplayer')
	#turn the blinking cursor back on in the terminal
	#os.system("setterm -cursor on > /dev/tty1")
	print("Quitting, Goodbye!")
