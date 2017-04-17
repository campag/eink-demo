#!/usr/bin/env python

import thread
import string
import time
import sys

from datetime import datetime
from subprocess import call
from PIL import Image
from PIL import ImageDraw, ImageFont
from papirus import Papirus

update_status=0   #used as flag:
                  #bit0 set: we have a data packet to draw in buffer
                  #bit1 set: we have finished updating the e-ink display
                  #bit2 set: do a partial update, not full (clear for 1st frame -> full update).

epd = Papirus()

SCREEN_WIDTH = epd.size[0]
SCREEN_HEIGHT =  epd.size[1]

SCREEN_WIDTH-=1
SCREEN_HEIGHT-=1

FONTFILE = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

SIZE_MED = int(SCREEN_HEIGHT/4)  #24
FONT_MED = ImageFont.truetype(FONTFILE, SIZE_MED)
CHRW_MED = FONT_MED.getsize("0")[0]

WHITE = 1
BLACK = 0

image = Image.new('1', epd.size, WHITE)
draw = ImageDraw.Draw(image)

def epd_draw(lagtime, packet_num):
    global display_status, t0to60, ft0to60, lt0to60

    #Clear drawing
    draw.rectangle([(0,0), (SCREEN_WIDTH, SCREEN_HEIGHT)], fill=WHITE, outline=WHITE)

    #draw radar
    draw.ellipse([((SCREEN_WIDTH-SCREEN_HEIGHT)/2,0),(SCREEN_HEIGHT+(SCREEN_WIDTH-SCREEN_HEIGHT)/2, SCREEN_HEIGHT)], outline=BLACK)
    draw.pieslice([((SCREEN_WIDTH-SCREEN_HEIGHT)/2,0),(SCREEN_HEIGHT+(SCREEN_WIDTH-SCREEN_HEIGHT)/2, SCREEN_HEIGHT)], 10*packet_num-2, 10*packet_num+2, fill=BLACK)

    #seconds counter
    now = datetime.today()
    draw.text((SCREEN_WIDTH/2-1.0*CHRW_MED, SCREEN_HEIGHT/2-1.5*SIZE_MED), '{s:02d}'.format(s=now.second) + "s", fill=BLACK, font=FONT_MED)

    #fps
    fps10x=10000/lagtime
    draw.text((SCREEN_WIDTH/2-3.0*CHRW_MED, SCREEN_HEIGHT/2-0.5*SIZE_MED), "%3dfps" %fps10x, fill=BLACK, font=FONT_MED)
    draw.text((SCREEN_WIDTH/2-1.4*CHRW_MED, SCREEN_HEIGHT/2-0.5*SIZE_MED), ".", fill=BLACK, font=FONT_MED)

    #cycle time
    draw.text((SCREEN_WIDTH/2-2.5*CHRW_MED, SCREEN_HEIGHT/2+0.5*SIZE_MED), "%3dms" %lagtime, fill=BLACK, font=FONT_MED)

    #swap rendered image to epd image buffer
    epd.display(image)

    return

def epd_update(packet_num):
    global update_status

    epd.partial_update()

    #flag that we have rendered data, ready for display
    update_status|=2

    return

#main entry

#edit the fake temperature value to change the frame rate, or
#'echo 25 > /dev/epd/temperature' in another console whilst running.
#fastest is with temperature set to 50, but ghosting is evident.
#lower the value for blacker updates, with less ghosting.
#temp:   50, 48, 42, 38, 35, 32, 30, 28, 27, 26...
#factor:  2,  3,  4,  5,  6,  7,  8,  9, 10, 11...

call(["echo 50 > /dev/epd/temperature"], shell=True)


epd.clear()
counter=0
#set to initial non-zero value 
frametime=80
#ensure we enter the loop busy, to avoid a 1st frametime measurement error
thread.start_new_thread(epd_update, (counter,))

try:
    while (True):
        prev=datetime.now()

        epd_draw(frametime,counter)

        while update_status&2 == 0: #wait for last update to finish if necessary
            time.sleep(0.001)
        update_status&=~2
        thread.start_new_thread(epd_update, (counter,))

        curr=datetime.now()
        frametime=(curr-prev).seconds*1000 + (curr - prev).microseconds/1000

        counter += 1

except KeyboardInterrupt:
    print "Clearing panel for long term storage"
    epd.clear()
    epd.clear()
    sys.exit('\nKeyboard interrupt')


