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
    return [iD, data, fname, hx, window, m, c]


def main():
    iD, data, fname, hx, window, m, c = ws_init()
    tick = 0

    # Initializing, sleep for 3 seconds in test, 3 min in prod
    for x in range(0, 3):
        sleep(1)  # 3 * 60)
        window.update()

    window.nametowidget("init").grid_remove()

    prev_avg = 100000
    prev_valid_avg = 1000000
    processed = 0
    avg_array = np.zeros(60)
    prev_valid_index = 1

    i = 59

    AVG = 50
    STD = 14
    LASTN = 60
    DIFF_MIN = -10
    DIFF_MAX = 10000

    table_data = []
    reading = lp.get_reading(hx, m, c)
    data.append((str(datetime.now())[:-7], 0, processed))
    lp.generate_table(table_data, window.nametowidget("table"))

    db.add_pi(iD)  # adds pi code to database

    while nt.reset == 0:
        print
        "reset: " + str(nt.reset) + "\n"
        # record every interval (1 second for test, 20 for prod)
        timestamp = datetime.now()
        reading = lp.get_reading(hx, m, c)

        # qc every 6 seconds for prod, 3 second for test


        if tick % 1 == 0 and tick > 0 and len(data) > LASTN:
            last_sixty = [x[1] for x in data[-59:]]
            last_sixty.append(reading)
            print(last_sixty)
            avg = np.mean(last_sixty)
            std = np.std(last_sixty)
            i = i + 1
            avg_array.append(avg)

            if avg > AVG and std < STD and DIFF_MIN < avg - prev_avg < DIFF_MAX:

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



                else:
                    processed += avg - prev_avg

                prev_valid_avg = avg
                prev_valid_index = i

            prev_avg = avg

        time = str(timestamp)[:-7]
        raw = reading  # round(reading, 3)
        processed = round(processed, 3)

        # update table every (hour (3 * 60 seconds) for prod, every 6 seconds for test)
        if tick % 6 == 0 and tick > 0:
            table_data.append((time[11:], ' ' + str(raw), ' ' + str(processed)))
            lp.generate_table(table_data, window.nametowidget("table"))

        lp.save_data(time, str(raw), str(processed), fname)
        data.append((timestamp, raw, processed))

        times = (datetime.now() - datetime.fromtimestamp(0)).total_seconds()

        db.add_data((times, raw, processed, iD))

        window.update()
        tick += 1
        print
        "tick++\n"
        # one second for test, 20 seconds for prod
        sleep(3)

    nt.quit(window)


while True:
    nt.set_reset()
    main()




