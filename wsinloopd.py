import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import Tkinter as tk
import mlbox as mlb
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

def generate_graph(graph_data, graph):

    intervals = 30*6 # 30 minutes * 6 ten second intervals?
    M30_data = [x[1] for x in graph_data[-(intervals):]]
    M30_time = [(intervals)-(datetime.now()-x[0]).total_seconds() for x in graph_data[-(intervals):]]
    fig = plt.figure(1)
    fig.suptitle('Volume in the past 30 minutes', fontsize=20)
    plt.plot(M30_time, M30_data)
    axes = plt.gca()
    axes.set_xlim([0, intervals])
    axes.set_ylim([0, 1])
    plt.ylabel('Volume in mL')
    #plt.xlabel('Number of 10 s intervals')
    plt.close(fig)

    for slave in graph.pack_slaves():
        if slave.winfo_exists():
            slave.destroy()

    canvas = FigureCanvasTkAgg(fig, master=graph)
    plot_widget = canvas.get_tk_widget()
    plot_widget.pack(side=tk.RIGHT, expand=1)

    volume_total = graph_data[-1][1] - graph_data[0][1]
    volume_30 = M30_data[-1] - M30_data[0]

    numbers = tk.Frame(graph, name="numbers")
    numbers.pack(side=tk.LEFT)
    tk.Label(numbers, text='Volume accumulated in 30 minutes:', font='-size 25').pack(anchor='center')
    tk.Label(numbers, text="%.3f"%volume_30, font='-weight bold -size 50').pack(anchor='center')
    
    tk.Label(numbers, text='Volume accumulated total:', font='-size 25').pack(anchor='center')
    tk.Label(numbers, text="%.3f"%volume_total, font='-weight bold -size 50').pack(anchor='center')



