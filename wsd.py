import wsinloopd as lp
import wsinitd as nt
from time import sleep
import numpy as np
from datetime import datetime
import RPi.GPIO as GPIO
import database as db
TOUCH_SWITCH = 24

def ws_init():
    # Initalization:
    iD = nt.gen_id()  # Patient ID
    data = []  # List for data structure
    fname = nt.init_file(iD)  # File for syncing to wifi
    (hx, m, c) = nt.init_scale()  # hx object for data readings
    window = nt.init_disp(iD)  # Display window

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TOUCH_SWITCH, GPIO.IN)

    # Return initialized instances
    return [iD, data, fname, hx, window, m, c]


def main():
    iD, data, fname, hx, window, m, c = ws_init()
    tick = 0

    print "init done"

    # Initializing, sleep for 3 seconds in test, 3 min in prod
    for x in range(0, 3):
        sleep(1)  # 3 * 60)
        window.update()

    window.nametowidget("init").grid_remove()

    AVG = 50
    STD = 14
    LASTN = 60
    DIFF_MIN = -10
    DIFF_MAX = 10000

    prev_avg = 100000
    prev_valid_avg = 100000
    prev_valid_index = 0
    i = 0

    avg_array = [100000]

    processed = 0
    new = 0
    cumul = 0
    last = 0
    table_data = []
    reading = lp.get_reading(hx, m, c)  # reading = mass registered by strain gauge
    data.append((str(datetime.now())[:-7], 0, last, new, cumul,
                 "init"))  # data added includes: datetime, raw, last volume, new (change), cumulative
    lp.generate_table(table_data, window.nametowidget("table"))  # adds data to table on screen

    db.add_pi(iD)  # adds pi code to database

    # avg_collect = []
    # avg_collect.append(0)

    pressed_array = []
    print "entering while loop"
    while nt.reset == 0:
        print
        "reset: " + str(nt.reset) + "\n"
        # record every interval (1 second for test, 20 for prod)
        timestamp = datetime.now()
        reading = lp.get_reading(hx, m, c)

        # new data processing every 1 second

        if tick % 1 == 0 and tick > 0:
            last_n = [x[1] for x in data[-(LASTN - 1):]]
            last_n.append(reading)  # add new volume to list of readings
            print(last_n)

            avg = np.mean(last_n)  # new proposed volume is the mean of the last six
            std = np.std(last_n)  # standard deviation of last six readings

            avg_array.append(avg)

            i += 1

            if len(avg_array) > LASTN and avg > AVG and std < STD and DIFF_MIN < avg - prev_avg < DIFF_MAX:
                # if parameters are met, timepoint becomes new processed data point


                if (avg - prev_valid_avg) > 10:

                    processed += avg - prev_valid_avg

                elif avg < (0.9 * prev_valid_avg) and avg > 200:

                    marker = 0

                    if (i - prev_valid_index) > 300:
                        binary_array = np.zeros(i - 300 - prev_valid_index + 2)
                        for k in range(prev_valid_index, (i - 298)):
                            test_array = avg_array[k:k + 300]
                            for j in range(0, 300):
                                if test_array[j] > 20:
                                    binary_array[k - prev_valid_index] = 1

                        for m in range(0, len(binary_array)):
                            if binary_array[m] == 0:
                                marker = 1

                    if marker == 1:
                        processed += avg - 200

                    else:
                        processed += avg - prev_avg



                # find difference between average of most recent six points (1-6) and average of the set before that (0-5)
                # add difference to previous processed point to get new processed data point (cumulative volume)

                else:
                    processed += avg - prev_avg

                prev_valid_avg = avg
                prev_valid_index = i


                # prev_avg = avg

            # if processed < 0: #if the new processed point is negative
            #    processed = 0 #set processed back to zero

            prev_avg = avg  # for the next iteration, this average becomes the "previous average" relative to the next timepoint

            # difference will always be taken with respect to previous average, regardless of whether that point fell within parameters

        time = str(timestamp)[:-7]
        vol = reading  # round(reading, 3)
        processed = round(processed, 3)
        new = round(new, 3)
        cumul = round(processed, 3)


        # update table every (hour (3 * 60 seconds) for prod, every 6 seconds for test)
        if tick % 6 == 0 and tick > 0:
            table_data.append((time[11:], ' ' + str(new), ' ' + str(cumul), ' ' + status))
            lp.generate_table(table_data, window.nametowidget("table"))

        lp.save_data(time, str(vol), str(last), str(new), str(cumul), status, fname)

        data.append((timestamp, vol, last, new, cumul, status))

        times = (datetime.now() - datetime.fromtimestamp(0)).total_seconds()

        status = "init array"

        pressed_array.append(not GPIO.input(TOUCH_SWITCH))
        if len(pressed_array) == 11:
            pressed_array.pop(0)
            for pressed in pressed_array:
                if not pressed:
                    status = "not pressed"
                    break
            else:
                status = "pressed"

        db.add_data((times, vol, last, new, cumul, status, iD))


        window.update()
        tick += 1
        print
        "tick++\n"
        sleep(3)

    nt.quit(window)


while True:
    nt.set_reset()
    main()




