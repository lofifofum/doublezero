#-------------------------------------------------------------------------------
# Name:        AudioDriver
# Purpose:     Set registers of LM49450 audio chip via i2c the for Double Zero
#              peripheral board for Raspberry Pi. Includes loop to adjust
#              registers in response to settings changes.
#
# Author:      Jonathan Roybal
#
# Created:     03/02/2018
# Copyright:   (c) Jonathan Roybal 2018
# Licence:     Released under Creative Commons 4.0 nc-by-sa license.
#              https://www.creativecommons.org
#-------------------------------------------------------------------------------

import smbus
import time
a    = 0x7D                                         ## Per LM45450 specs.
b    = smbus.SMBus(3)                               ## i2c dev 3 (bitbanged)
dBH  = -15                                          ## Default headphone volume.
dBS  = -15                                          ## Default speaker volume.
muted          = false                              ## State var: if outpt muted
equalized      = false                              ## State var: if eq on
movieMode      = false                              ## State var: if freq=48kHz
u,v,w,x,y,z    = 0x00,0x00,0x00,0x00,0x00,0x00      ## Equalizer defaults.
defaults       = [0x49,0x21,0x21,0x00,0x00,0x00,0x00,0x09,0x09]
lastEql        = [u,v,w,x,y,z]
defaults.extend(lastEql)

class Register:                                     ## Register read/write fx
    def read(regAddrs):
        result = hex(b.i2c_smbus_read_byte_data(a,regAddrs))
        return result
    def write(regAddr,byteVal):
        b.i2c_smbus_write_byte_data(a,regAddr,byteVal)
class Volume:                                       ## Mute and volume functions
    def headphone(dBh):                             ## Controls headphone volume
        if dBh < -57:                               ## given decibels desired.
            HP = 0x1F&int(0)                        ## HP is a 5 bit register.
        elif dBh < -24:
            HP = 0x1F&int(6.5 + (0.288675*sqrt(-16*dBh - 405)))
        elif dBh < -13.5:
            HP = 0x1F&int(4 + ((dBh + 30)/3))
        elif dBh > 18:
            dBh = 18
            HP = 0x1F&int(((dBh + 15)*(2/3)) + 9)
        else:
            HP = 0x1F&int(((dBh + 15)*(2/3)) + 9)
        Register.write(0x07,HP)
        dBH = dBh
    def speaker(dBs):                               ## Controls speaker volume
        if dBs < -42:                               ## given decibels desired.
            LS = 0x1F&int(0)                        ## LS is a 5 bit register.
        elif dBs < -18:
            LS = 0x1F&int(6.5 + ((sqrt(-16*dBs - 309))/(2*sqrt(3))))
        elif dBs < -7.5:
            LS = 0x1F&int(6 + ((dBs + 18)/3))
        elif dBs > 24:
            dBs = 24
            LS = 0x1F&int(((dBs + 9)*(2/3)) + 9)
        else:
            LS = 0x1F&int(((dBs + 9)*(2/3)) + 9)
        Register.write(0x08,LS)
        dBS = dBs
    def mute(mute):                                 ## Sets/clears bit 2 of 0x00
        if mute == true:
            Register.write(0x00,((0xFB&(Register.read(0x00)))|0x04))
        else:
            Register.write(0x00,(0xFB&(Register.read(0x00))))
class EQ:                                           ## EQ lvl, EQ & freq on/off
        def switch(equalize):                       ## Sets/clears bit 4 of 0x00
            if equalize == true:
                Register.write(0x00,((0xEF&(Register.read(0x00)))|0x10))
            else:
                Register.write(0x00,(0xEF&Register.read(0x00)))
        def level(band,lvl):                        ## Sets eq by band and level
             Register.write(0x09+band,lvl)
        def freq(movie):                            ## Sets regs for 44.1/48kHz
            if movie == false:                      ## Next line sets b5,6 = 0,1
                Register.write(0x00,((0x9F&(Register.read(0x00)))|0x40))
                Register.write(0x01,0x21)           ## Sets clock divisor = 17
                Register.write(0x02,0x21)           ## Sets chargepump dv = 17
            else:                                   ## Next line sets b5.6 = 0,0
                Register.write(0x00,((0x9F&(Register.read(0x00)))|0x00))
                Register.write(0x01,0x0F)           ## Sets clock divisor = 8
                Register.write(0x01,0x49)           ## Sets chargepump dv = 37

def mainLoop():                                     ## Separated for convenience
    while True:
        mute = inBool1                              ## T: mute on F: mute off
        equalize = inBool2                          ## T: eq on   F: eq off
        movie = inBool3                             ## T: f=48kHz F: f=44.1kHz
        dBh = hpVolIn
        dBs = spVolIn
        eqLevels = bytearray([u,v,w,x,y,z])         ## where u:z are input vars
        if (mute != muted):
            Volume.mute(mute)
            muted = mute
        elif (dBh != dBH):
            Volume.headphone(dBh)
        elif (dBs != dBS):
            Volume.speaker(dBs)
        elif (equalize != equalized):
            EQ.switch(equalize)
            equalized = equalize
        elif (eqLevels != lastEql):
            for i,level in enumerate(EQLevels):
                EQ.level(i,level)
            lastEql = eqLevels
        elif (movie != movieMode):
            EQ.freq(movie)
            movie = moviemode
        sleep(0.1)

def main():
    for i,val in enumerate(defaults):
        Register.write(0x0F&i,val)
##    mainLoop()