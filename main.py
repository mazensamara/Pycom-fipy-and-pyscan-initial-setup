# Copyright (c) 2020, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
# See https://docs.pycom.io for more information regarding library specif


import machine
import struct
import time
import pycom
import socket
import ubinascii
from pycoproc_1 import Pycoproc
from LIS2HH12 import LIS2HH12
from LTR329ALS01 import LTR329ALS01
from MFRC630 import MFRC630
from network import WLAN
from machine import RTC


# Make sure heartbeat is disabled before setting RGB LED
pycom.heartbeat(False)
pycom.rgbled(0x0000FF) # Blue

RGB_BRIGHTNESS = 0x8

RGB_RED = (RGB_BRIGHTNESS << 16)
RGB_GREEN = (RGB_BRIGHTNESS << 8)
RGB_BLUE = (RGB_BRIGHTNESS)

# Connect to wifi to get time
wlan = WLAN(mode=WLAN.STA)
wlan.connect(ssid='YOUR SSID', auth=(WLAN.WPA2, 'YOUR PASSWORD'))
while not wlan.isconnected():
    machine.idle()
time.sleep(1)
print('\n')
print("WiFi connected succesfully to :")
print(wlan.ifconfig()) # Print IP configuration
pycom.rgbled(0x0000FF) # Blue
time.sleep(5)


# setup rtc
rtc = machine.RTC()
rtc.ntp_sync("pool.ntp.org")
time.sleep(0.75)
print('\nRTC Set from NTP to UTC:', rtc.now())
time.timezone(-14200)
print('Adjusted from UTC to EST timezone', time.localtime(), '\n')
print("Local time: ", time.localtime())
a = rtc.synced()
print('RTC is synced to "pool.ntp.org": ', a)

#add your card UID here
VALID_CARDS = [[0x43, 0x95, 0xDD, 0xF8],
               [0x43, 0x95, 0xDD, 0xF9],
               [0x46, 0x5A, 0xEB, 0x7D, 0x8A, 0x08, 0x04]]


# This is the default key for an unencrypted MiFare card
CARDkey = [ 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF ]
DECODE_CARD = False

pyscan = Pycoproc(Pycoproc.PYSCAN)
py = Pycoproc(Pycoproc.PYSCAN)

nfc = MFRC630(py) # NFC and card reader
ltr329als01 = LTR329ALS01() # Digital Ambient Light Sensor
lis2hh12 = LIS2HH12() # 3-Axis Accelerometer

# Initialise the MFRC630 with some settings
nfc.mfrc630_cmd_init()

while True:
    # Read the values from the sensors
    print('\nScanning for cards')
    # Send REQA for ISO14443A card type
    atqa = nfc.mfrc630_iso14443a_WUPA_REQA(nfc.MFRC630_ISO14443_CMD_REQA)
    if (atqa != 0):
        # A card has been detected, read UID
        print('A card has been detected, reading its UID ...')
        uid = bytearray(10)
        uid_len = nfc.mfrc630_iso14443a_select(uid)
        print('UID has length {}'.format(uid_len))
        if (uid_len > 0):
            # A valid UID has been detected, print details
            counter += 1
            print("%d\tUID [%d]: %s" % (counter, uid_len, nfc.format_block(uid, uid_len)))
            if DECODE_CARD:
                # Try to authenticate with CARD key
                nfc.mfrc630_cmd_load_key(CARDkey)
                for sector in range(0, 16):
                    if (nfc.mfrc630_MF_auth(uid, nfc.MFRC630_MF_AUTH_KEY_A, sector * 4)):
                        pycom.rgbled(RGB_GREEN)
                        # Authentication was sucessful, read card data
                        readbuf = bytearray(16)
                        for b in range(0, 4):
                            f_sect = sector * 4 + b
                            len = nfc.mfrc630_MF_read_block(f_sect, readbuf)
                            print("\t\tSector %s: Block: %s: %s" % (nfc.format_block([sector], 1), nfc.format_block([b], 1), nfc.format_block(readbuf, len)))
                    else:
                        print("Authentication denied for sector %s!" % nfc.format_block([sector], 1))
                        pycom.rgbled(RGB_RED)
                # It is necessary to call mfrc630_MF_deauth after authentication
                # Although this is also handled by the reset / init cycle
                nfc.mfrc630_MF_deauth()
            else:
                #check if card uid is listed in VALID_CARDS
                if (check_uid(list(uid), uid_len)) > 0:
                    print('Card is listed, turn LED green')
                    pycom.rgbled(RGB_GREEN)
                    if(pybytes_enabled):
                        pybytes.send_signal(1, ('Card is listed', uid))
                else:
                    print('Card is not listed, turn LED red')
                    pycom.rgbled(RGB_RED)
                    if(pybytes_enabled):
                        pybytes.send_signal(1, ('Unauthorized card detected', uid))

    else:
        pycom.rgbled(RGB_BLUE)
        time.sleep(5)
    # We could go into power saving mode here... to be investigated
    print('\nNo card detected !!!')
    nfc.mfrc630_cmd_reset()
    time.sleep(2)
    # Re-Initialise the MFRC630 with settings as these got wiped during reset
    nfc.mfrc630_cmd_init()
    
    # Read the values from the sensors
    acceleration = lis2hh12.acceleration()
    acceleration_x = lis2hh12.acceleration_x()
    acceleration_y = lis2hh12.acceleration_y()
    acceleration_z = lis2hh12.acceleration_z()
    voltage = pyscan.read_battery_voltage()
    light = ltr329als01.light()[0]
    lux = ltr329als01.lux()
    roll = lis2hh12.roll()
    pitch = lis2hh12.pitch()
    # Debug sensor values
    print('\nvoltage: {}, lumen: {}, lux: {}, roll: {}, pitch: {}, acceleration: {}'.format(voltage, light, lux, roll, pitch, acceleration))
    print('\nacceleration x: {}, acceleration y: {}, acceleration z: {}'.format(acceleration_x, acceleration_y, acceleration_z))
    print('\n')
    print("Sleeping for 3 secs")
    print("\nLocal time: ", time.localtime()) # Print local time
    print("\nIp configuration: ", wlan.ifconfig()) # Print IP configuration
    pycom.rgbled(0xFFFF00) # Yellow
    time.sleep(3)

