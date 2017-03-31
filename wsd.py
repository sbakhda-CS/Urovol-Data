import wsinloopd as lp
import wsinitd as nt
from time import sleep
import numpy as np
import Tkinter as tk
from datetime import datetime
import RPi.GPIO as GPIO
import database as db

def ws_init():

    # Initalization: 
    #   Patient ID
    #   List for data structure
    #   File for syncing to wifi
    #   hx object for data readings
    #   Display window

    iD = nt.gen_id()
    data = []
    fname = nt.init_file(iD)
    (hx, m, c) = nt.init_scale()
    window = nt.init_disp(iD)

    # Return initialized instances
    return [iD,data,fname,hx,window,m,c]

def main():
    iD, data, fname, hx, window,m,c = ws_init()
    tick = 0

    # Initializing, sleep for 3 seconds in test, 3 min in prod
    for x in range(0, 3):
        sleep(1) # 3 * 60)
        window.update()
        
    window.nametowidget("init").grid_remove()

    last = 100000 # initially large, so new will be negative and the first stable reading will be set as the 0 
    new = 0
    cumul = 0
    table_data = []
    reading = lp.get_reading(hx,m,c)
    data.append((str(datetime.now())[:-7], 0, last, new, cumul, "init"))
    lp.generate_table(table_data, window.nametowidget("table"))

    db.add_pi(iD)  # adds pi code to database

    while nt.reset == 0: 
        print "reset: "+str(nt.reset)+"\n"
        # record every interval (1 second for test, 20 for prod)
        timestamp = datetime.now()
        reading = lp.get_reading(hx,m,c)
        status = "raw"


        # qc every 6 seconds for prod, 3 second for test
        if tick % 3 == 0 and tick > 0:
            last_six = [x[1] for x in data[-5:]]
            last_six.append(reading)
            print (last_six)
            avg = np.mean(last_six)
            std = np.std(last_six)
            if avg > 50 and std < 9: # change back to 50 later
                last = avg
                new = avg - data[-1][2]
                if new > 0:
                    cumul += new
                else:
                    new = 0
                status = "valid"
            else:
                status = "rejected"

            #lp.generate_graph(data, window.nametowidget("graph"))

        time = str(timestamp)[:-7]
        vol = reading #round(reading, 3)
        last = round(last, 3)
        new = round(new, 3)
        cumul = round(cumul, 3)

        # update table every (hour (3 * 60 seconds) for prod, every 6 seconds for test)
        if tick % 6 == 0 and tick > 0:
            table_data.append((time[11:], ' '+str(new), ' '+str(cumul), ' '+status))
            lp.generate_table(table_data, window.nametowidget("table"))

        lp.save_data(time, str(vol), str(last), str(new), str(cumul), status, fname)
        data.append((timestamp, vol, last, new, cumul, status))

        times = (datetime.now() - datetime.fromtimestamp(0)).total_seconds()

        db.add_data((times, vol, last, new, cumul, status, iD))

        window.update()
        tick += 1
        print "tick++\n"
        # one second for test, 20 seconds for prod
        sleep(3)

    nt.quit(window)

while True:
    nt.set_reset()
    main()




