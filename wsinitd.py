#from hx711 import HX711
from ADC import sensor
import matplotlib.pyplot as plt
import numpy as np
import os
from random import choice, random
import string
import Tkinter as tk
import pigpio

path ='/home/pi/urovol/data/'
reset = 0

def gen_id(): 
    """Generates unique patient iD"""
    exist = True
    while exist:
        iD = choice(string.ascii_letters[26:]) + choice(string.ascii_letters[26:]) + str(int(random()*10)) + str(int(random()*10)) +choice(string.ascii_letters[26:]) + choice(string.ascii_letters[26:])
        exist = os.path.exists(path+iD+'.csv')
    return iD

def init_file(iD): 
    """Initializes the data file iD.csv"""
    fname = path+iD+'.csv'
    f = open(fname,'w')
    f.write('time, raw volume, last valid volume, new volume, cumulative volume, status\n')
    f.close()
    return fname

def init_scale():
    """Initializes the strain gauge"""
    pi = pigpio.pi()
    hx = sensor(pi, DATA=15, CLOCK=14, mode=1)
    calib = open('calib.txt','r')
    m = float(calib.readline())
    c = float(calib.readline())
    calib.close()
    return (hx, m, c)

def quit(root):
    root.destroy()

def show_graph(root):
    table = root.nametowidget("table")
    graph = root.nametowidget("graph")
    table.grid_remove()
    graph.grid()

def show_table(root):
    table = root.nametowidget("table")
    graph = root.nametowidget("graph")
    graph.grid_remove()
    table.grid()

def new_patient():
    print "reset function"
    global reset
    reset = 1

def set_reset():
    global reset
    reset = 0

def init_disp(ID):
    """Displays the patient iD initially"""

    pad = 30

    root = tk.Tk()

    # BUTTONS
    tk.Button(root, text='NEW PATIENT', bg = "red", font='-size 12', height=1, command=lambda:new_patient()).grid(rowspan=2,column=0)

    # PATIENT ID
    tk.Label(root, text='PATIENT',font='-size 15').grid(row=0, column=1)
    tk.Label(root, text=ID,font='-weight bold -size 20').grid(row=1, column=1)
    root.columnconfigure(1, weight=1)

    # INITIALIZE
    tk.Label(root, name="init", text = 'INITIALIZING', font='-size 15').grid(row=2, column=1)

    # TABLE/GRAPH PANES
    tk.Frame(root, name="table").grid(row=3, columnspan=3, sticky=tk.N+tk.S+tk.W+tk.E, padx=pad, pady=pad)
    tk.Frame(root, name="graph").grid(row=3, columnspan=3, sticky=tk.N+tk.S+tk.W+tk.E, padx=pad, pady=pad)
    root.rowconfigure(3, weight=1)

    
    # default to graph view
    show_table(root)

    root.wm_title(ID)
    root.attributes('-fullscreen', True)
    root.update()

    return root
	


