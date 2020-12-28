#-------------------------------------------------------------------------------
# Name:        Double Zero video driver
# Purpose:     Set registers of TC358778XBG chip and A026EAN01.0 screen via i2c.
# Author:      Jonathan Roybal
# Created:     02/02/2018
# Copyright:   (c) Lo-Fi-Fo-Fum Technology LLC, 2018
# License:     Released under Creative Commons 4.0 nc-by-sa license.
#              https://www.creativecommons.org
#-------------------------------------------------------------------------------
#! /usr/bin/python3
import smbus2, time, math, binascii, array
a            = 0x0e                                ## i2c address of TC358778XBG
b            = smbus2.SMBus(3)                     ## use bitbanged i2c device 3
hActive      = 800                                 ## Horizontal resolution, px
hFrontPorch  = 4                                   ## Horiz. front porch, pixels
hSyncWidth   = 68                                  ## Horiz. sync pulse width px
hBackPorch   = 72                                  ## Horiz. back porch, pixels
hSkew        = 0                                   ## Accounts for overhead
vActive      = 1280                                ## Vertical resolution, lines
vFrontPorch  = 6                                   ## Vert. front porch, lines
vSyncWidth   = 1                                   ## Vert. sync pulse width, ln
vBackPorch   = 2                                   ## Vert. back porch, lines
colorDepth   = 24                                  ## Bits per pixel
frameRate    = 60                                  ## Frames per second
mipiLanes    = 4                                   ## # MIPI lanes used
vSyncDelay   = 3*0x06                              ## RGB to MIPI delay, bytes
pixelClock   = 73008960 ##67546000                 ## Incoming RGB pixel clock.
Hertz        = 404340000*2                         ## Target PLL frequency.
##Hertz        = 498400000                           ## Target PLL frequency.

class PLL:                                         ## PLL settings
    ## This section is used to calculate the values needed for the MIPI bit
    ## clock, and the PLL feedback and input dividers needed to generate it on
    ## TC358778XBG. We want the divider values which give the smallest possible
    ## error from the target frequency.
    pllClock     = Hertz
    if (pllClock < 1000000000):
        divisorExp=3-int(math.log((pllClock/62500000),2)) ## w/ pllClock > 62.5MHz
    else:
        divisorExp = 0
    FBDplus1     = (10**8)*(2**divisorExp)*pllClock/(pixelClock/4) ## w/ PRD = 0
    error        = [abs((FBDplus1-(10**8)*round(FBDplus1/10**8))/FBDplus1)]
    FBD  =  PRD  = 0
    for i in range (1,15):
        FBD1xPRD1= FBDplus1*(i+1)
        error.append(abs((FBD1xPRD1-(10**8)*round(FBD1xPRD1/10**8))/FBD1xPRD1))
    errmin   = min(error)
    for i in range (16):
        FtoP     = FBDplus1*(i+1)
        FBDtest  = ((FtoP-(10**8)*round(FtoP/(10**8)))/FtoP)
        if ((FBDtest == errmin) and ((FtoP/10**8) < 512)):
            FBD  = int(FtoP/(10**8))
            PRD  = i
    pllClock = int((FBD+1)*(pixelClock/4)/((2**divisorExp)*(PRD+1))+1)
    byteClkFrq   = int(pllClock/4)
    byteClk      = 0.01*((10**11)/byteClkFrq)      ## 2 bits per DDR clock cycle
    bitClockFrq  = int(pllClock*2)
    bitClock     = 0.01*((10**11)/bitClockFrq)
    ctl1     = PRD*16 + int(FBD/256)
    ctl2     = FBD - (256*int(FBD/256))
    ctl3     = divisorExp*4
    ############################################################################
class DPHY:                                        ## MIPI-DPHY layer settings
    ## This section adjusts the capacitors and delay used for each physical
    ## MIPI lane. These are not calculated, but tuned based on evaluation.
    clCap    = 0x0 ## Output capacitor.  0:0pF, 1:2.8pF, 2:3.2pF, 3:3.6pF
    clCur    = 0x0 ## Added current out. 0:+0%, 1:+25%I, 2:+50%I, 3:+50%I
    clDel    = 0x0 ## Output delay x~25ps.
    d0Cap    = 0x0 ## Output capacitor.  0:0pF, 1:2.8pF, 2:3.2pF, 3:3.6pF
    d0Cur    = 0x0 ## Added current out. 0:+0%, 1:+25%I, 2:+50%I, 3:+50%I
    d0Del    = 0x0 ## Output delay x~25ps.
    d1Cap    = 0x0 ## Output capacitor.  0:0pF, 1:2.8pF, 2:3.2pF, 3:3.6pF
    d1Cur    = 0x0 ## Added current out. 0:+0%, 1:+25%I, 2:+50%I, 3:+50%I
    d1Del    = 0x0 ## Output delay x~25ps.
    d2Cap    = 0x0 ## Output capacitor.  0:0pF, 1:2.8pF, 2:3.2pF, 3:3.6pF
    d2Cur    = 0x0 ## Added current out. 0:+0%, 1:+25%I, 2:+50%I, 3:+50%I
    d2Del    = 0x0 ## Output delay x~25ps.
    d3Cap    = 0x0 ## Output capacitor.  0:0pF, 1:2.8pF, 2:3.2pF, 3:3.6pF
    d3Cur    = 0x0 ## Added current out. 0:+0%, 1:+25%I, 2:+50%I, 3:+50%I
    d3Del    = 0x0 ## Output delay x~25ps.
    ############################################################################
class PPI:                                         ## MIPI-PPI layer settings
    ## This section is used to program the PPI layer of the MIPI interface. The
    ## below values are calculated per the MIPI D-PHY datasheet, and indicate
    ## the number of MIPI byte clock cycles the counter will increment. For
    ## variables where a range of acceptable values is possible, we take the
    ## average of the two extrema and round it down. Variable naming follows
    ## that in the TC358778XBG register map.
    HSByteClk= PLL.byteClk
    lineInit = int((100000/HSByteClk)/256) + 1
    LPTxTime = int(50/HSByteClk)                      ##checked
    tClkPrep = int((int(38/HSByteClk) + int((95/HSByteClk)-1))/2)
    tClkZero = int((300/HSByteClk)+1) - tClkPrep
    tClkTrail= int((int((60/HSByteClk)+0.75)+int(0.5+(105/HSByteClk)))/2)
    tHSPrep  = int((int((40/HSByteClk)+0.5)+int(-0.25+(85/HSByteClk)))/2)
    tHSZero  = int((145/HSByteClk) + 0.75) - tHSPrep ## Add 1.75 for PHY delay
##    tHSZero  = int((145/HSByteClk) + 0.75)
    tWakeUp  = int(1 + ((1000000/((LPTxTime+1)*HSByteClk))/256))
    tClkPost = int(7 + (60/HSByteClk))
    tHSTrail = int((int(0.5+(60/HSByteClk))+int(0.5+(105/HSByteClk)))/2)
    ClkCont  = 0                                   ## Enables continuous clock
    ############################################################################
class DSI:                                         ## MIPI-DSI layer settings
    ## This section contains boolean values for the logical components of
    ## the MIPI DSI implementation - that is, data sequence and error handling.
    PrTimeoutEn  = 1                               ## Enables PR timeout
    TaTimeoutEn  = 1                               ## Enables TA timeout
    LrxTimeoutEn = 1                               ## Enables LRx timeout
    HtxTimeoutEn = 1                               ## Enables HSTx timeout
    ContentionDis= 0                               ## Disables contention detect
    EccDisable   = 0                               ## Disables ECC check
    HSTxMode     = 1                               ## Enables HSTx mode
    CRCDisable   = 0                               ## Disables CRC check
    HSClkContinue= 0                               ## Enables continuous HSClock
    EoTPacketDis = 0                               ## Disables auto EoT packet
    d1       = 2*PrTimeoutEn + TaTimeoutEn
    d2       = 8*LrxTimeoutEn + 4*HtxTimeoutEn + 2*ContentionDis + EccDisable
    d3       = 8*HSTxMode + 4*CRCDisable + 2*HSClkContinue
    d4       = 2*(mipiLanes-1) + EoTPacketDis
    byte1    = 16*d1 + d2
    byte2    = 16*d3 + d4
    lanes    = mipiLanes - 1
    ############################################################################
class VOUT:                                        ## MIPI video layer settings
    ## This section calculates MIPI DSI video output timings for TC358778XBG to
    ## the specifications required by A026EAN01.0 screen.
    eventMode= 1                                   ## Bool sync event (vs pulse)
##    ByteMulti= PLL.byteClkFrq*mipiLanes/pixelClock
    ByteMulti= colorDepth/8
    if (eventMode == 1):
        vSyncWidth = vBackPorch + vFrontPorch
        hSyncWidth = hBackPorch + hFrontPorch
    VSW1     = int((vSyncWidth)/256)
    VSW2     = int((vSyncWidth)) - VSW1*256
    VBP1     = int(vBackPorch/256)
    VBP2     = int(vBackPorch)  - VBP1*256
    VAL1     = int(vActive/256)
    VAL2     = int(vActive)    - VAL1*256
    HSW1     = int(hSyncWidth*ByteMulti/256)
    HSW2     = int(hSyncWidth*ByteMulti)-HSW1*256
    HBP1     = int(hBackPorch*ByteMulti/256)
    HBP2     = int(hBackPorch*ByteMulti) - HBP1*256
    HAL1     = int(hActive*3/256)
    HAL2     = int(hActive*3) - HAL1*256
    VSD1     = int(vSyncDelay/256)
    VSD2     = vSyncDelay - VSD1*256
    ############################################################################
class Reg:                                         ## Register values to write.
    ## For TC358778XBG, the chip automatically increments the register address
    ## +1 for every byte received, so for adjacent sets of registers, we can
    ## simply send all the registers' values in order, starting from the first.
    ##
    ## Also, for all Reg(n) variables, the first byte is the second half of the
    ## register address into which the array is written. This allows us to use
    ## 16-bit register addresses with the standard smbus2 Python library above
    ## by putting the first byte as the address in the function call, then the
    ## second byte as the first "data" byte; the chip will assume the first
    ## two bytes after the 7-bit i2c address and 1 read/write bit are the target
    ## register address. Transfers are limited to 32 bytes at a time for
    ## stability. See info on the register of interest in TC358778XBG specs for
    ## interpretation of the input values.
    one  =[
          [0x02,
          0x00,0x00,0x00,0x04,VOUT.VSD1,VOUT.VSD2,
          0x00,0x4c],                              ## 4 16 bit registers
          [0x0E,       ## Bottom value keeps PLL off until it has time to lock.
          0x00,0x00,0x00,0xF9,0x00,0x00,0x00,0x06,
          PLL.ctl1,PLL.ctl2,PLL.ctl3,0x03],        ## 6 16 bit registers
          [0x50,
          0x00,0x2E]                               ## 1 16 bit register
          ]
    ## Per TC358778XBG specs, for a 32-bit value, we must write in the order
    ## [bits 15-0][bits 31-16] in order for the data to properly align with
    ## the chip's internal automatic address incrementing.
    two  =[
          [0x00,
          DPHY.clCap,(16*DPHY.clDel+DPHY.clCur),0x00,0x00,
          DPHY.d0Cap,(16*DPHY.d0Del+DPHY.d0Cur),0x00,0x00,
          DPHY.d1Cap,(16*DPHY.d1Del+DPHY.d1Cur),0x00,0x00,
          DPHY.d2Cap,(16*DPHY.d2Del+DPHY.d2Cur),0x00,0x00,
          DPHY.d3Cap,(16*DPHY.d3Del+DPHY.d3Cur),0x00,0x00],## 5 32 bit registers
          [0x40,
          0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
          0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
          0x00,0x00,0x00,0x00]                     ## 5 32 bit registers
          ]
    three=[
          [0x10,
          PPI.lineInit,0x00,0x00,0x00,
          0x00,PPI.LPTxTime,0x00,0x00,
          PPI.tClkZero,PPI.tClkPrep,0x00,0x00,
          0x00,PPI.tClkTrail,0x00,0x00,
          PPI.tHSZero,PPI.tHSPrep,0x00,0x00,
          PPI.tWakeUp,0x00,0x00,0x00],             ## 6 32 bit registers
          [0x28,
          0x00,PPI.tClkPost,0x00,0x00,
          0x00,PPI.tHSTrail,0x00,0x00,
          0x00,0x10,0x00,0x00,
          0x00,0x1F,0x00,0x00,
          0x00,PPI.ClkCont,0x00,0x00,
          0x00,0x03,0x00,0x0B]                     ## 6 32 bit registers
          ]
    four =[[0x18,0x00,0x01,0x00,0x00]]             ## 1 32 bit registers
    five =[
          [0x00,DSI.byte1,DSI.byte2,0xA3,0x00],[0x00,0x00,0x0F,0xA6,0x04],
          [0x00,0X00,0x00,0xAE,0x00],[0x00,0x00,0x00,0xAF,0x00],
          [0x00,0x2F,0x58,0xB1,0x1A],[0x00,0x2F,0x58,0xB2,0x1A],
          [0x00,0x03,0xB7,0xB4,0x00],[0x00,0x03,0xB7,0xB5,0x00],
          [0x00,0x82,0x01,0xC3,0x00]               ## 8 32 bit registers
          ]                                        ## last clears default bits.
                                                   ## See TC sec on reg 0x0500.
    six  =[                                        ## Screen register settings
          [0x01,0xFF], ## COMMAND2 page0: Power/MTP/Gamma setting
          [0x01,0xFB], ## Don't reload settings from MTP/default
          [0x48,0x00], ## Sets display to 800x1280
          [0x33,0x01], ## set charge pump freq
          [0x53,0x02], ## set charge pump freq
          [0x55,0x03], ## set charge pump freq
          [0x55,0x04], ## set charge pump freq
          [0x33,0x05], ## set AVDD=6V/AVEE=-6V
          [0x22,0x06], ## set AVDD/AVEE output level
          [0x56,0x08], ## 0x56 2XAVDD , 0x66 2xAVDD-VCL
          [0x8F,0x09], ## VGL 0X8A=-7V 0x8F=-8V 0X90=-8.2V
          [0x97,0x0B], ## GVDD   0xAF=4.3V 0xA7=4.2V 0X9F=4.1V	0X5F=3.3V
          [0x97,0x0C], ## GVDDN	0X97=4V	 0XBF=4.5V 0XCF=4.7V
          [0x2F,0x0D], ##
          [0x24,0x0E], ## VGH 0X18=7.3V 0x1A=7.5V ,0x1F=8V,0x24=8.5V
          [0x7F,0x11], ## VCOM DC 0x70, 0X7F, for typ
          [0x03,0x12], ## SET VCOMDC3
          [0x73,0x36], ## Enable gate EQ
          [0x04,0x0F],
##          [0x00,0xFF],
          [0xEE,0xFF], ## COMMAND3
          [0x01,0xFB], ## Don't reload settings from MTP/default
          [0xAD,0x04],                         ######## 44 bytes
##          [0x50,0x12], ## set VDD level
##          [0x02,0x13], ## set VDD level
##          [0x60,0x6A], ## set SRAM timing
          [0x00,0xFF],
          [0x05,0xFF], ## COMMAND2 page4: LTPS Display Timing
          [0x01,0xFB], ## Don't reload settings from MTP/default
          [0x00,0x01],
          [0x8C,0x02],
          [0x8C,0x03],
          [0x8C,0x04],
          [0x30,0x05],
          [0x33,0x06],
          [0x01,0x07],
          [0x00,0x08],
          [0x46,0x09],
          [0x46,0x0A],
          [0x0B,0x0D], ## set MUX rising position
          [0x1D,0x0E], ## set MUX high period
          [0x08,0x0F], ## set MUX non-overlap
          [0x53,0x10], ## set MUX non-overlap
          [0x00,0x11],
          [0x00,0x12],
          [0x01,0x14], ## set XCLK/CLK position
          [0x00,0x15],
          [0x05,0x16],
          [0x04,0x17], ## EQ off: 0x00, EQ on: 0x04
          [0x7F,0x19],
          [0xFF,0x1A],
          [0x0F,0x1B],
          [0x00,0x1C],
          [0x00,0x1D],
          [0x00,0x1E],
          [0x07,0x1F],
          [0x00,0x20],
          [0x02,0x21], ## set display control ### (orientation)
      ##    [0x00,0x21], ## set display control
          [0x55,0x22],
          [0x0D,0x23], ## Sub-pixel/pixel column inversion: 0x0D/0x4D
          [0x00,0x6C], ## Sub-pixel/pixel column inversion: 0x00/0x03
          [0x00,0x6D], ## Sub-pixel/pixel column inversion: 0x00/0x03
          [0x02,0x2D],
          [0x02,0x83], ## set dummy line
          [0x58,0x9E], ## XDON_XDONB_extend
          [0x58,0x9F],
          [0x41,0xA0], ## AUO_TYPE H466 (A) 0x01, H426 (B) 0x41
          [0x10,0xA2],
          [0x0A,0xBB], ## set FP line number
          [0x0A,0xBC], ## set BP line number
          [0x01,0x28],
          [0x02,0x2F],
          [0x08,0x32],
          [0xB8,0x33],
          [0x02,0x36],
          [0x00,0x37],
          [0x00,0x43],
          [0x21,0x4B],
          [0x03,0x4C],
          [0x21,0x50],
          [0x03,0x51],
          [0x21,0x58],
          [0x03,0x59],
          [0x21,0x5D],
          [0x03,0x5E],
          [0x04,0xFF], ## COMMAND2 page3: PWM
          [0x01,0xFB],
          [0x03,0x0A], ## PWM 28.63 kHz
          [0x00,0xFF], ## COMMAND1
          [0x01,0xFB], ## Don't reload default/MTP settings
          [0x07,0x51], ## PWM setting. Set as brightness%/100 = (x+1)/256
          [0x2C,0x53], ## Enable content-adaptive brightness control
          [0x03,0x55],
          [0x00,0x5E],
          [0x03,0xC2], ## Via RAM and internal clock 0x08/ bypass RAM 0x03
          [DSI.lanes,0xBA],
          [0x00,0xBC],
          [0x00,0x35]  ## Screen tearing effect on
          ]                               ## Per A026EAN01.0 specs
    seven=[0x20,
          0x00,VOUT.eventMode,
          VOUT.VSW1,VOUT.VSW2,VOUT.VBP1,VOUT.VBP2,
          VOUT.VAL1,VOUT.VAL2,VOUT.HSW1,VOUT.HSW2,
          VOUT.HBP1,VOUT.HBP2,VOUT.HAL1,VOUT.HAL2] ## 7 16 bit registers.
                                                   ## Per TC358778XBG specs
    nine =[                                        ## color lookup table
          [0x04,0x00,0x0C,0x08,0x14,0x10,0x1C,0x18],
          [0x24,0x20,0x2C,0x28,0x34,0x30,0x3C,0x38],
          [0x45,0x41,0x4D,0x49,0x55,0x51,0x5D,0x59],
          [0x65,0x61,0x6D,0x69,0x75,0x71,0x7D,0x79],
          [0x86,0x82,0x8E,0x88,0x96,0x92,0x9E,0x9A],
          [0xA6,0xA2,0xAE,0xA8,0xB6,0xB2,0xBE,0xBA],
          [0xC7,0xC3,0xCF,0xC9,0xD7,0xD3,0xDF,0xDB],
          [0xE7,0xE3,0xEF,0xE9,0xF7,0xF3,0xFF,0xFB], ## 64 bytes - R
          [0x04,0x00,0x0C,0x08,0x14,0x10,0x1C,0x18],
          [0x24,0x20,0x2C,0x28,0x34,0x30,0x3C,0x38],
          [0x45,0x41,0x4D,0x49,0x55,0x51,0x5D,0x59],
          [0x65,0x61,0x6D,0x69,0x75,0x71,0x7D,0x79],
          [0x86,0x82,0x8E,0x8A,0x96,0x92,0x9E,0x9A],
          [0xA6,0xA2,0xAE,0xAA,0xB6,0xB2,0xBE,0xBA],
          [0xC7,0xC3,0xCF,0xCB,0xD7,0xD3,0xDF,0xDB],
          [0xE7,0xE3,0xEF,0xEB,0xF7,0xF3,0xFF,0xFB], ## 128 bytes - G
          [0x04,0x00,0x0C,0x08,0x14,0x10,0x1C,0x18],
          [0x24,0x20,0x2C,0x28,0x34,0x30,0x3C,0x38],
          [0x45,0x41,0x4D,0x49,0x55,0x51,0x5D,0x59],
          [0x65,0x61,0x6D,0x69,0x75,0x71,0x7D,0x79],
          [0x86,0x82,0x8E,0x8A,0x96,0x92,0x9E,0x9A],
          [0xA6,0xA2,0xAE,0xAA,0xB6,0xB2,0xBE,0xBA],
          [0xC7,0xC3,0xCF,0xCB,0xD7,0xD3,0xDF,0xDB],
          [0xE7,0xE3,0xEF,0xEB,0xF7,0xF3,0xFF,0xFB], ## 192 bytes - B
          ]                                        ## Per MIPI DSI specs, 18>24b
    ############################################################################

class Dcs():                                       ## DSI read/write functions
    def CMD(self,l):
        e = [0x10,0x00]
        e.extend(l)
        E = bytearray(e)
        b.write_i2c_block_data(a,0x06,[0x02,0x10,0x05])
        b.write_i2c_block_data(a,0x06,E)
        b.write_i2c_block_data(a,0x06,[0x00,0x00,0x01])
        time.sleep(0.01)
    def WRITE(self,k):
        f = [0x10]
        f.extend(k)
        F = bytearray(f)
        b.write_i2c_block_data(a,0x06,[0x02,0x10,0x15])
        b.write_i2c_block_data(a,0x06,F)
        b.write_i2c_block_data(a,0x06,[0x00,0x00,0x01])
        time.sleep(0.001)
    def GENERIC(self,j):
        g = [0x10]
        g.extend(j)
        G = bytearray(g)
        b.write_i2c_block_data(a,0x06,[0x02,0x10,0x23])
        b.write_i2c_block_data(a,0x06,G)
        b.write_i2c_block_data(a,0x06,[0x00,0x00,0x01])
        time.sleep(0.001)
    def LONG(self,i):
        h =[0x10]
        h.extend(i)
        H = bytearray(h)
        b.write_i2c_block_data(a,0x06,[0x02,0x40,0x39])
        b.write_i2c_block_data(a,0x06,[0x04,0x00,(len(i))])
        b.write_i2c_block_data(a,0x06,H)
        b.write_i2c_block_data(a,0x06,[0x00,0x00,0x01])
        b.write_i2c_block_data(a,0x06,[0x04,0x00,0x00])
        b.write_i2c_block_data(a,0x06,[0x12,0x00,0x00,0x00,0x00,0x00,0x00])
        time.sleep(0.001)
DCS = Dcs()
class Screen():                                    ## Common DSI 0param commands
    def on(self):
        DCS.CMD([0x29])
    def off(self):
        DCS.CMD([0x28])
    def sleep(self):
        DCS.CMD([0x10])
    def wake(self):
        DCS.CMD([0x11])
    def idle(self):
        DCS.CMD([0x39])
    def stopIdle(self):
        DCS.CMD([0x38])
    def reset(self):
        DCS.CMD([0x01])
    def tearOn(self):
        DCS.CMD([0x35])
screen = Screen()
class Step():                                      ## Steps. Numbers match Reg.x
    def GlobalReg(self):                           #1. global registers (0x00xx)
        for i in Reg.one:
            I = bytearray(i)
            b.write_i2c_block_data(a,0x00,I)
        hsync = bytearray([0x32,0x00,0x00])
        b.write_i2c_block_data(a,0x00,hsync)       ## Sets hsync active low
        time.sleep(0.005)
        b.write_i2c_block_data(a,0x00,[0x18,PLL.ctl3,0x13])
    def PHYReg(self):                              #2. PHY registers (0x01xx)
        for i in Reg.two:
            I = bytearray(i)
            b.write_i2c_block_data(a,0x01,I)
    def PPIReg(self):                              #3. PPI registers (0x02xx)
        for i in Reg.three:
            I = bytearray(i)
            b.write_i2c_block_data(a,0x02,I)
    ## Set 0x0204 = 0x00000001 after setting 0x02xx registers.
        b.write_i2c_block_data(a,0x02,[0x04,0x00,0x01,0x00,0x00])
    def TXReg(self):                               #4. TX registers (0x05xx)
        for i in Reg.four:
            I = bytearray(i)
            b.write_i2c_block_data(a,0x05,I)
    def ErrorReg(self):                            #5. DSI error handling
        for j in Reg.five:
            G = bytearray(j)
            b.write_i2c_block_data(a,0x05,G)
            time.sleep(0.1)
        b.write_i2c_block_data(a,0x00,bytearray([0x08,0x00,0x4e]))
    def ScreenReg(self):                           #6. Screen registers (DSI)
        time.sleep(0.02)
        screen.wake()
        time.sleep(0.1)
        scr1 =[[0xEE,0xFF],[0x08,0x26]]
        for k in scr1:
            DCS.WRITE(k)
        time.sleep(0.001)
        scr2 =[[0x00,0x26],[0x00,0xFF]]
        for k in scr2:
            DCS.WRITE(k)
        time.sleep(0.01)
        b.write_i2c_block_data(a,0x00,bytearray([0x14,0x00,0x00]))
        time.sleep(0.00001)
        b.write_i2c_block_data(a,0x00,bytearray([0x14,0x00,0x06]))
        time.sleep(0.02)
        screen.wake()
        time.sleep(0.1)
        for k in Reg.six:
            DCS.WRITE(k)
        RGB=[0x4b,0x3B,vFrontPorch/2,vBackPorch/2,hFrontPorch,hBackPorch]
        DCS.LONG(RGB)
        time.sleep(0.1)
        screen.wake()
        time.sleep(0.1)
        screen.on()
        time.sleep(0.1)
        DCS.WRITE([0x77,0x3A])
    def LookupTable(self):                         #7. Color lookup table (DSI)
        b.write_i2c_block_data(a,0x00,bytearray([0x08,0x00,0x01]))
        b.write_i2c_block_data(a,0x00,bytearray([0x50,0x00,0x39]))
        b.write_i2c_block_data(a,0x00,bytearray([0x22,0x03,0xFC]))
        b.write_i2c_block_data(a,0x00,bytearray([0xE0,0x80,0x00]))
        for k in Reg.nine:
            DCS.LONG(k)
        b.write_i2c_block_data(a,0x00,bytearray([0xE0,0xE0,0x00]))
        b.write_i2c_block_data(a,0x00,bytearray([0xE0,0x20,0x00]))
        b.write_i2c_block_data(a,0x00,bytearray([0xE0,0x00,0x00]))
        b.write_i2c_block_data(a,0x00,bytearray([0x08,0x00,0x4f]))
        b.write_i2c_block_data(a,0x00,bytearray([0x50,0x00,0x2E]))
        time.sleep(0.1)
        DCS.LONG([0x59,0x1D],[0x00,0x80])
    def DSITXReg(self):                            #8. TX registers (0x06xx)
        I = bytearray(Reg.seven)
        b.write_i2c_block_data(a,0x06,I)
        b.write_i2c_block_data(a,0x00,bytearray([0x04,0x00,0x44]))
        b.write_i2c_block_data(a,0x00,bytearray([0x08,0x00,0x4f]))
step = Step()
def main():
    step.GlobalReg()
    step.PHYReg()
    step.PPIReg()
    step.TXReg()
    step.ErrorReg()
    step.ScreenReg()
    step.DSITXReg()
    print "MIPI clock:",0.000001*PLL.pllClock,"MHz"," ","Byte clock:",0.000001*PLL.byteClkFrq,"MHz"," ","HSByteClkP:",PPI.HSByteClk,"ns"
    pass
if __name__ == '__main__':
    main()
