#www.stuffaboutcode.com
#Raspberry Pi, Minecraft - hide and seek

#GPIO controls added by Bertrand Le Roy, Nwazet http://nwazet.com

#import the minecraft.py module from the minecraft directory
import minecraft.minecraft as minecraft
#import minecraft block module
import minecraft.block as block
#import time, so delays can be used
import time
#import random module to create random number
import random
#import math module to use square root function
import math
# https://code.google.com/p/raspberry-gpio-python/
import RPi.GPIO as GPIO
# http://tjjr.fi/sw/python-uinput/
import uinput

#function to round players float position to integer position
def roundVec3(vec3):
    return minecraft.Vec3(int(vec3.x), int(vec3.y), int(vec3.z))

def distanceBetweenPoints(point1, point2):
    xd = point2.x - point1.x
    yd = point2.y - point1.y
    zd = point2.z - point1.z
    return math.sqrt((xd*xd) + (yd*yd) + (zd*zd))

#Button interrupt handlers
def button_changed(channel):
    global keyboard, mouse, mouseInertia
    if channel == BUTTON_FORWARD:
        keyboard.emit(uinput.KEY_W, 0 if GPIO.input(channel) else 1)
    elif channel == BUTTON_BACK:
        keyboard.emit(uinput.KEY_S, 0 if GPIO.input(channel) else 1)
    elif channel == BUTTON_RIGHT:
        if GPIO.input(channel):
            mouseInertia = 0
        else:
            mouse.emit(uinput.REL_X, 50)
            mouseInertia = 50
    elif channel == BUTTON_LEFT:
        if GPIO.input(channel):
            mouseInertia = 0
        else:
            mouse.emit(uinput.REL_X, -50)
            mouseInertia = -50
    elif channel == BUTTON_JUMP:
        keyboard.emit(uinput.KEY_SPACE, 0 if GPIO.input(channel) else 1)

if __name__ == "__main__":

    #Connect to minecraft by creating the minecraft object
    # - minecraft needs to be running and in a game
    global mc
    mc = minecraft.Minecraft.create()

    #Keyboard
    keys = (uinput.KEY_W, uinput.KEY_A, uinput.KEY_S, uinput.KEY_D, uinput.KEY_SPACE)
    global keyboard
    keyboard = uinput.Device(keys)

    #Mouse
    mouseFreedom = (uinput.REL_X, uinput.REL_Y, uinput.BTN_LEFT, uinput.BTN_RIGHT)
    global mouse
    mouse = uinput.Device(mouseFreedom)
    global mouseInertia
    mouseInertia = 0

    #Button and LED constants
    BUTTON_RIGHT = 11
    BUTTON_LEFT = 15
    BUTTON_FORWARD = 13
    BUTTON_BACK = 19
    BUTTON_JUMP = 16
    LED_PROXIMITY = 12
    LED_COLDER = 18
    LED_WARMER = 22
    LED_HAPPY = 21

    #Init GPIO
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    GPIO.setup(LED_PROXIMITY, GPIO.OUT)
    pwm = GPIO.PWM(LED_PROXIMITY, 50)
    GPIO.setup(LED_COLDER, GPIO.OUT)
    GPIO.setup(LED_WARMER, GPIO.OUT)
    GPIO.setup(LED_HAPPY, GPIO.OUT)
    GPIO.setup(BUTTON_RIGHT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_FORWARD, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_BACK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_LEFT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(BUTTON_JUMP, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(BUTTON_RIGHT, GPIO.BOTH, callback=button_changed)
    GPIO.add_event_detect(BUTTON_FORWARD, GPIO.BOTH, callback=button_changed)
    GPIO.add_event_detect(BUTTON_BACK, GPIO.BOTH, callback=button_changed)
    GPIO.add_event_detect(BUTTON_LEFT, GPIO.BOTH, callback=button_changed)
    GPIO.add_event_detect(BUTTON_JUMP, GPIO.BOTH, callback=button_changed)

    #Post a message to the minecraft chat window
    mc.postToChat("Minecraft Hide & Seek")

    while True:
        #Find the players position
        playerPos = mc.player.getPos()

        #Create random position, our hidden block will go there
        x = int(random.randrange(-127, 127))
        z = int(random.randrange(-127, 127))
        y = 127
        #Drop the block right above the ground
        while mc.getBlock(x, y - 1, z) == block.AIR:
            y = y - 1
        randomBlockPos = minecraft.Vec3(x, y, z)

        #Create hidden diamond block
        mc.setBlock(x, y, z, block.GOLD_BLOCK)
        mc.postToChat("A treasure has been hidden - go find!" + str(mc.getBlock(x, y, z)))

        #Start hide and seek
        seeking = True
        lastPlayerPos = playerPos
        lastDistanceFromBlock = distanceBetweenPoints(randomBlockPos, lastPlayerPos)
        timeStarted = time.time()
        while (seeking == True):
            #perpetuate mouse inertia as long as button wasn't released
            if mouseInertia != 0:
                mouse.emit(uinput.REL_X, mouseInertia)
            #Get players position
            playerPos = mc.player.getPos()
            #Has the player moved
            if lastPlayerPos != playerPos:
                #print "lastDistanceFromBlock = " + str(lastDistanceFromBlock)
                distanceFromBlock = distanceBetweenPoints(randomBlockPos, playerPos)
                #print "distanceFromBlock = " + str(distanceFromBlock)
                if distanceFromBlock < 2:
                    #found it!
                    seeking = False
                else:
                    pwm.start(max(50 - distanceFromBlock, 0) * 2)
                    if distanceFromBlock < lastDistanceFromBlock:
                        #mc.postToChat("Warmer " + str(int(distanceFromBlock)) + " blocks away")
                        GPIO.output(LED_WARMER, GPIO.HIGH)
                        GPIO.output(LED_COLDER, GPIO.LOW)
                    if distanceFromBlock > lastDistanceFromBlock:
                        #mc.postToChat("Colder " + str(int(distanceFromBlock)) + " blocks away")
                        GPIO.output(LED_COLDER, GPIO.HIGH)
                        GPIO.output(LED_WARMER, GPIO.LOW)

                lastDistanceFromBlock = distanceFromBlock

            time.sleep(0.05)

        timeTaken = time.time() - timeStarted

        #Start happy dance
        GPIO.output(LED_HAPPY, GPIO.HIGH)
        mc.postToChat("Well done - " + str(int(timeTaken)) + " seconds to find the treasure")

        #Remove the treasure
        mc.setBlock(x, y, z, block.AIR)

        #Wait for player to hit jump
        while GPIO.input(BUTTON_JUMP):
            time.sleep(0.2)

        #Stop happy dance
        GPIO.output(LED_HAPPY, GPIO.LOW)
        GPIO.output(LED_COLDER, GPIO.LOW)
        GPIO.output(LED_WARMER, GPIO.LOW)
        pwm.stop()
