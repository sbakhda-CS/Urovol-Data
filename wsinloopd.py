#import matplotlib
#matplotlib.use('TkAgg')
#import matplotlib.pyplot as plt

#from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
#from matplotlib.figure import Figure

import numpy as np
from subprocess import call
import Tkinter as tk
import mlbox as mlb
#import tktable as tktable
import random
from datetime import datetime

def get_reading(hx, m, c):
    """Returns mass reading from strain gauge"""
    empty = 0
    while empty < 1:
        count, mode, inp = hx.get_reading()
        if type(inp) == type(None):
            print 'empty reading'
            #print inp
            empty = 0
        else:
            empty = 1
            print 'good reading'
    print inp
    if type(inp) != type(None):
        mass = (inp - c)/m
    return mass 

def save_data(time, vol, last, new, cumul, status, fname):
    """Saves data to file"""
    string = time+', '+str(vol)+', '+str(last)+', '+str(new)+', '+str(cumul)+', '+status+'\n'
    print "save_data: "+string+"\n"
    f=open(fname,'a')
    f.write(string)
    f.close()

def generate_table(table_data, table):
    for slave in table.pack_slaves():
        slave.destroy()

    scrollbar = tk.Scrollbar(table, orient=tk.VERTICAL)

    mlbox = mlb.MultiListbox(table, (('Date Time', 12), ('New (mL)', 6), ('Cumulative (mL)', 6), ('Status', 4)))
    for item in table_data:
        mlbox.insert(0, item)
    mlbox.pack(expand=tk.YES,fill=tk.BOTH)

