#-------------------------------------------------------------------------------
# Name:        VideoDriver
# Purpose:     Set registers of TC358778XBG RBG to MIPI DSI chip and A026EAN01.0
#              MIPI DSI screen via i2c for the Double Zero peripheral board for
#              Raspberry Pi. Includes loop for short DCS commands after setup.
#
# Author:      Jonathan Roybal
#
# Created:     02/02/2018
# Copyright:   (c) Jonathan Roybal 2018
# Licence:     Released under Creative Commons 4.0 nc-by-sa license.
#              https://www.creativecommons.org
#-------------------------------------------------------------------------------

import smbus2
import time
import binascii
a    = 0x0e                                        ## Per TC358778XBG specs
b    = smbus2.SMBus(3)                             ## i2c dev 3 (bitbanged)

def main():
    b.write_byte_data(a,0x00,0x00)
    I = bytearray([0x00,0x01])
    str1 = "      0   2   4   6   8   A   C   E   "
    str2 = "      0   2   4   6   8   A   C   E  "
    for i in I:
        for u in range(6):
            s1 = binascii.hexlify(bytearray(b.read_i2c_block_data(a,i,0x10)))
            s2 = '0x'+'%03X' % ((16*i)+(u))
            if (u == 0):
                s4 = [s2,s1]
            else:
                s4.extend([s2,s1])
        for v in range(5):
	        block9 = bytearray(b.read_i2c_block_data(a,i,0x10))
	        blockA = bytearray(b.read_i2c_block_data(a,i,0x10))
        if (i == 0):
            s3 = s4
    J = bytearray([0x02,0x04])
    for j in J:
        for w in range(6):
            s5 = binascii.hexlify(bytearray(b.read_i2c_block_data(a,j,0x10)))
            s6 = '0x'+'%03X' % ((16*j)+(w))
            if (w == 0):
                s8 = [s6,s5]
            else:
                s8.extend([s6,s5])
        for x in range(5):
	        block9 = bytearray(b.read_i2c_block_data(a,j,0x10))
	        blockA = bytearray(b.read_i2c_block_data(a,j,0x10))
        if (j == 2):
            s7 = s8
    K = bytearray([0x05,0x06])
    for k in K:
        for y in range(6):
            s9 = binascii.hexlify(bytearray(b.read_i2c_block_data(a,k,0x10)))
            sa = '0x'+'%03X' % ((16*k)+(y))
            if (y == 0):
                sc = [sa,s9]
            else:
                sc.extend([sa,s9])
        for z in range(5):
	        block9 = bytearray(b.read_i2c_block_data(a,k,0x10))
	        blockA = bytearray(b.read_i2c_block_data(a,k,0x10))
        if (k == 5):
            sb = sc
    for l in range(6):
        print s3[2*l],s3[2*l+1],s4[2*l],s4[2*l+1]
    print str1,str2
    for m in range(6):
        print s7[2*m],s7[2*m+1],s8[2*m],s8[2*m+1]
    print str1,str2
    for n in range(6):
        print sb[2*n],sb[2*n+1],sc[2*n],sc[2*n+1]
#print hex(2*j),binascii.hexlify(block1),binascii.hexlify(block2)
#print(hex(z))
    pass

if __name__ == '__main__':
    main()
