import Tkinter as tk
import tkFont
import os
from time import time
import threading
from ADC import sensor 
import pigpio
from random import choice, random
import string
from datetime import datetime
import pytz
import numpy as np
import database as db


class App():
    def __init__(self):
        self.root = tk.Tk()
    	self.path ='/home/pi/urovol/data/'
        self.root.attributes("-fullscreen", True)
        self.init_frames()
        self.init_styles()
        self.init_cover_screen()
        self.init_live_screen()
        self.init_new_screen()
        self.init_id_select_screen()
        self.init_calib_screen()
        self.init_id_enter_screen()
        self.raise_frame(self.fr0)
        self.root.mainloop()

    def begin(self):
    	self.go_btn.grid_forget()
    	self.splash_logo.grid(row=3, column=1, columnspan=4)
        def scanning():
            self.check_network()
        t = threading.Thread(target=scanning)
        t.start()

    def init_frames(self):
        """Initializes all frames in the GUI"""
        self.fr0 = tk.Frame(self.root) #cover screen
        self.fr1 = tk.Frame(self.root) #live screen
        self.fr2 = tk.Frame(self.root) #new patient/bag screen
        self.fr3 = tk.Frame(self.root) #id select screen
        self.fr4 = tk.Frame(self.root) #calibration screen
        self.fr5 = tk.Frame(self.root) #enter ID screen
        self.frame_ls = [self.fr0, self.fr1, self.fr2, self.fr3, self.fr4, self.fr5]
        for frame in self.frame_ls:
            frame.grid(row=0, column=0, sticky='news')
            frame.configure(bg='#FFFFFF')


    def init_styles(self):
        """Initializes all styles in the GUI"""
        #window styles
        self.root.title('urOvol')
        self.root.configure(bg='#FFFFFF')
        self.root.geometry('{}x{}'.format(480, 320))
        self.fn0 = tkFont.Font(family='segoe ui', size=11)
        self.fn1 = tkFont.Font(family='segoe ui', size=8)
        self.fn2 = tkFont.Font(family='segoe ui', size=16)


    def init_cover_screen(self):
        """Initializes the cover screen"""
        #declare widgets
        self.mbox0 = tk.Label(self.fr0, text='urOvol', font=self.fn0, bg='#FFFFFF')
        self.exit0 = tk.Button(self.fr0, text=  u"\u25C0"+' EXIT', font=self.fn0, bg='#FFFFFF', height='3', command=lambda:self._quit())
        self.wifi_sym = tk.Label(self.fr0, text='network', font=self.fn1, bg='#FFFFFF', fg='#FF0000')
        self.scale_sym = tk.Label(self.fr0, text='scale', font=self.fn1, bg='#FFFFFF', fg='#FF0000')
        self.calib_btn = tk.Button(self.fr0, text='SET '+u"\u25BC", font=self.fn0, bg='#FFFFFF', height='3', state='disabled')
        self.splash_logo = tk.Label(self.fr0, text='urOvol', font=self.fn2, bg='#FFFFFF', height='3')
    	self.move_on_btn = tk.Button(self.fr0, text='CONTINUE '+u"\u25B6", font=self.fn2, bg='#FFFFFF', height='3', command=lambda:self.raise_frame(self.fr3))
    	self.retry_btn = tk.Button(self.fr0, text='RETRY '+u"\u25B6", font=self.fn2, bg='#FFFFFF', height='3', command=lambda:self.check_network())
    	self.go_btn = tk.Button(self.fr0, text='BEGIN '+u"\u25B6", font=self.fn2, bg='#FFFFFF', height='3', command=lambda:self.begin())
        self.foot0 = tk.Label(self.fr0, text='Copyright '+ u'\xa9' + ' 2017. All rights reserved.', font=self.fn1, bg='#FFFFFF')

        #apply spacing
        self.fr0.columnconfigure(0,pad=80)
        self.fr0.columnconfigure(1,pad=20)
        self.fr0.columnconfigure(2,pad=20)
        self.fr0.columnconfigure(3,pad=20)
        self.fr0.columnconfigure(4,pad=20)
        self.fr0.columnconfigure(5,pad=80)
        self.fr0.rowconfigure(3, pad=20)

        #grid widgets
        self.exit0.grid(row=0, column=0, sticky='NW')
        self.mbox0.grid(row=2, column=1, columnspan=4)
        self.wifi_sym.grid(row=1, column=0, sticky='NW')
        self.scale_sym.grid(row=2, column=0, sticky='NW')
        self.go_btn.grid(row=3, column=1, columnspan=4)
        self.calib_btn.grid(row=6, column=0, sticky='SW')
        self.foot0.grid(row=7, column=1, columnspan=4)


    def init_live_screen(self):
        """Initializes the live screen"""

        #declare widgets
        self.new_btn = tk.Button(self.fr1, text='NEW '+u"\u25B6", font=self.fn0, bg='#FFFFFF', height='3', command=lambda:self.raise_frame(self.fr2))
        self.id_disp = tk.Label(self.fr1, text='PATIENT#', font=self.fn2, bg='#FFFFFF')
        self.exit1 = tk.Button(self.fr1, text=  u"\u25C0"+' EXIT', font=self.fn0, bg='#FFFFFF', height='3', command=lambda:self._quit())
        self.live_timer = tk.Label(self.fr1, text='00:00', font=self.fn0, bg='#FFFFFF', relief='raised', width='12', height='2')
        self.live_vol = tk.Label(self.fr1, text='0000 mL', font=self.fn0, bg='#FFFFFF', relief='raised', width='12', height='2')
        self.table_head = tk.Label(self.fr1, text='Accumulated', font=self.fn1, bg='#FFFFFF')
        self.time1 = tk.Label(self.fr1, text='', font=self.fn0, bg='#FFFFFF', relief='raised', width='12', height='2')
        self.time2 = tk.Label(self.fr1, text='', font=self.fn0, bg='#FFFFFF', relief='raised', width='12', height='2')
        self.time3 = tk.Label(self.fr1, text='', font=self.fn0, bg='#FFFFFF', relief='raised', width='12', height='2')
        self.vol1 = tk.Label(self.fr1, text='', font=self.fn0, bg='#FFFFFF', relief='raised', width='12', height='2')
        self.vol2 = tk.Label(self.fr1, text='', font=self.fn0, bg='#FFFFFF', relief='raised', width='12', height='2')
        self.vol3 = tk.Label(self.fr1, text='', font=self.fn0, bg='#FFFFFF', relief='raised', width='12', height='2')
        self.scrl_up = tk.Button(self.fr1, text=u"\u25B2", font=self.fn0, bg='#FFFFFF', state='disabled')
        self.scrl_dn = tk.Button(self.fr1, text=u"\u25BC", font=self.fn0, bg='#FFFFFF', state='disabled')
        self.foot1 = tk.Label(self.fr1, text='Copyright '+ u'\xa9' + ' 2017. All rights reserved.', font=self.fn1, bg='#FFFFFF')
    
        #apply spacing
        self.fr1.columnconfigure(0,pad=20)
        self.fr1.columnconfigure(4,pad=20)
        self.fr1.rowconfigure(3,pad=15)
        self.fr1.rowconfigure(7, pad=15)
    
        #grid widgets
        self.exit1.grid(row=0, column=0, sticky='NW')
        self.id_disp.grid(row=1, column=1, columnspan=2)
        self.new_btn.grid(row=0, column=4, sticky='NE')
        self.live_timer.grid(row=2, column=1)
        self.live_vol.grid(row=2, column=2)
        self.table_head.grid(row=3, column=1, columnspan=2, sticky='S')
        self.time1.grid(row=4, column=1)
        self.time2.grid(row=5, column=1)
        self.time3.grid(row=6, column=1)
        self.vol1.grid(row=4, column=2)
        self.vol2.grid(row=5, column=2)
        self.vol3.grid(row=6, column=2)
        self.scrl_up.grid(row=4, column=3)
        self.scrl_dn.grid(row=6, column=3)
        self.foot1.grid(row=7, column=1, columnspan=3, sticky='S')


    def init_new_screen(self):
        """Initializes new patient select screen"""
        self.new0 = tk.Button(self.fr2, text='NEW PATIENT '+ u"\u25B6", font=self.fn0, bg='#FFFFFF', command=lambda:self.refresh())
        self.new1 = tk.Button(self.fr2, text='NEW BAG '+ u"\u25B6", font=self.fn0, bg='#FFFFFF', state='disabled')
        self.back2 = tk.Button(self.fr2, text=  u"\u25C0"+' BACK', font=self.fn0, bg='#FFFFFF', command=lambda:self.raise_frame(self.fr1))
        
        self.new0.grid(row=0, column=0, sticky='NEWS')
        self.new1.grid(row=1, column=0, sticky='NEWS')
        self.back2.grid(row=2, column=0, sticky='NEWS')
        
        self.fr2.rowconfigure(0, pad=70)
        self.fr2.rowconfigure(1, pad=70)
        self.fr2.rowconfigure(2, pad=70)
        
        self.fr2.columnconfigure(0, pad=350)


    def init_id_select_screen(self):
        """Initializes ID selection screen"""
        self.idopt1 = tk.Button(self.fr3, text='ASSIGN ID '+ u"\u25B6", font=self.fn0, bg='#FFFFFF', command=lambda:self.move_on())
        self.idopt2 = tk.Button(self.fr3, text='ENTER ID '+ u"\u25B6", font=self.fn0, bg='#FFFFFF', command=lambda:self.raise_frame(self.fr5))
        self.back3 = tk.Button(self.fr3, text=  u"\u25C0"+' BACK', font=self.fn0, bg='#FFFFFF', command=lambda:self.raise_frame(self.fr0))
        
        self.idopt1.grid(row=0, column=0, sticky='NEWS')
        self.idopt2.grid(row=1, column=0, sticky='NEWS')
        self.back3.grid(row=2, column=0, sticky='NEWS')
        
        self.fr3.rowconfigure(0, pad=70)
        self.fr3.rowconfigure(1, pad=70)
        self.fr3.rowconfigure(2, pad=70)
        
        self.fr3.columnconfigure(0, pad=350)

    def init_calib_screen(self):
        """Initializes calibration screen"""
        tk.Label(self.fr4, text='Calibration Screen').grid(row=0, column=0)
        tk.Button(self.fr4, text = 'Next', command=lambda:self.raise_frame(self.fr0)).grid(row=1, column=0)  

    def init_id_enter_screen(self):
        """Initializes ID entry screen"""
        self.box = tk.Entry(self.fr5, font=self.fn2, bg='#FFFFFF')
        self.pinfrm = tk.Frame(self.fr5, bd=1, width=50, height=50, bg='#323232', relief='flat')
        self.pin7 = tk.Button(self.pinfrm, bg='#FFFFFF', width=5, font=self.fn2, command=lambda:self.add_text('7'))
        self.pin8 = tk.Button(self.pinfrm, bg='#FFFFFF', width=5, font=self.fn2, command=lambda:self.add_text('8'))
        self.pin9 = tk.Button(self.pinfrm, bg='#FFFFFF', width=5, font=self.fn2, command=lambda:self.add_text('9'))
        self.pin4 = tk.Button(self.pinfrm, bg='#FFFFFF', width=5, font=self.fn2, command=lambda:self.add_text('4'))
        self.pin5 = tk.Button(self.pinfrm, bg='#FFFFFF', width=5, font=self.fn2, command=lambda:self.add_text('5'))
        self.pin6 = tk.Button(self.pinfrm, bg='#FFFFFF', width=5, font=self.fn2, command=lambda:self.add_text('6'))
        self.pin1 = tk.Button(self.pinfrm, bg='#FFFFFF', width=5, font=self.fn2, command=lambda:self.add_text('1'))
        self.pin2 = tk.Button(self.pinfrm, bg='#FFFFFF', width=5, font=self.fn2, command=lambda:self.add_text('2'))
        self.pin3 = tk.Button(self.pinfrm, bg='#FFFFFF', width=5, font=self.fn2, command=lambda:self.add_text('3'))
        self.pin0 = tk.Button(self.pinfrm, bg='#FFFFFF', width=5, font=self.fn2, command=lambda:self.add_text('0'))
        self.pindel = tk.Button(self.pinfrm, bg='#FFFFFF', font=self.fn2, command=lambda:self.backspace())
        self.pinpeep = tk.Button(self.pinfrm, bg='#FFFFFF', font=self.fn2)
        self.pinbtn = np.array([(self.pin1, self.pin2, self.pin3), (self.pin4, self.pin5, self.pin6), (self.pin7, self.pin8, self.pin9), (self.pinpeep, self.pin0, self.pindel)])
        self.pintxt = np.array([('1', '2', '3'), ('4','5','6'), ('7','8','9'), ('','0', u'\u232B')])
        for i in range(0,4):
            for j in range(0,3):
                self.pinbtn[i,j].config(text=self.pintxt[i,j])
                self.pinbtn[i,j].grid(row=i, column=j, ipady=3, sticky='NESW')
        self.box.grid(row=1, column=1, columnspan=3, sticky='NEWS', ipady=8)
        self.pinfrm.grid(row=2, column=1, columnspan=3)
        
        self.fr5.rowconfigure(1, pad=20)
        self.fr5.columnconfigure(1, pad=40)
        self.back5 = tk.Button(self.fr5, text=  u"\u25C0"+' BACK', font=self.fn0, bg='#FFFFFF', height='3', command=lambda:self.raise_frame(self.fr3))
        self.back5.grid(row=0, column=0)
        self.go5 = tk.Button(self.fr5, text='CONTINUE '+u"\u25B6", font=self.fn0, bg='#FFFFFF', height='3', state='disabled', command=lambda:self.enterid())
        self.go5.grid(row=0, column=4)

    def add_text(self, text):
        try:
            stringi = self.root.focus_get().get()
            if text == '.' and len(stringi)==0:
                text = '0.'
            if stringi == '-':
                text = '0.'
            self.root.focus_get().insert('end',text)
        except:
            pass
            
    def backspace(self):
        try:
            current = self.root.focus_get()
            position = current.index('insert')
            stringi = current.get()
            if len(string) > 0 and position>0:
                new = stringi[:position-1] + stringi[position:]
                current.delete(0,'end')
                current.insert('end', new)
                current.icursor(position-1)
        except:
            pass
                        
    def check_network(self):
        """Checks if urovol.com can be reached"""
        self.mbox0.configure(text='connecting to urovol.com', fg='#000000')

        def net_connect():
            start = time()
            done = False
            while done == False:
                hostname = "urovol.com"
                response = os.system("ping -c 1 " + hostname)
                if response == 0:
                    self.network = True
                    done = True
                else:
                    self.network = False
                if time()-start > 5:
                    done = True
            if self.network == True:
                self.wifi_sym.configure(fg='#00FF00')
                self.mbox0.configure(text='checking scale')
                self.check_scale()
            else:
                self.mbox0.configure(text='error: could not connect', fg='#FF0000')
        v = threading.Thread(target=net_connect)
        v.start()


    def check_scale(self):
        """Initializes and checks scale"""
        self.mbox0.configure(text='checking scale...please wait')
        self.scale = False
        self.mass = None
        self.timeout = False
        self.init_scale()

        def checking():
            self.get_reading()

        u = threading.Thread(target=checking)
        u.start()

        start = time()
        while self.scale == False and self.timeout == False:
            if type(self.mass) == type(None):
                self.scale = False
            else:
                self.scale = True
            if time()-start > 10:
                self.timeout = True
        
        if self.scale == True:
            self.mbox0.configure(text='urOvol\nPlace bag on hook.')
            self.scale_sym.configure(fg='#00FF00')
            self.splash_logo.grid_forget()
            self.move_on_btn.grid(row=3, column=1, columnspan=4)
        else:
            self.mbox0.configure(text='error: problem with scale.', fg='#FF0000')
            self.retry_btn.grid(row=3, column=1, columnspan=4)


    def init_scale(self):
        """Initializes the strain gauge"""
        self.pi = pigpio.pi()
        self.hx = sensor(self.pi, DATA=15, CLOCK=14, mode=1)
        self.calib = open('calib.txt','r')
        self.m = float(self.calib.readline())
        self.c = float(self.calib.readline())
        self.calib.close()


    def refresh(self):
        self.interval_records = []
        clear = [self.time1, self.time2, self.time3, self.vol1, self.vol2, self.vol3]
        for entry in clear:
            entry.configure(text='')
        self.gen_id()
        self.id_disp.configure(text=self.iD)
        self.init_file()
        self.counter = 0 #for updates
        self.interval_start_time = datetime.now(pytz.timezone('US/Eastern'))
        self.time1.configure(text=str(self.interval_start_time)[11:-16])
        self.vol1.configure(text='0.0')
        self.interval_data = []
        self.all_data = []
        self.get_reading() 
        self.offset = self.mass
        self.last = 0
        self.new = 0
        self.cumul = 0
        self.interval_records = [(str(self.interval_start_time)[11:-16], '00.0')]   
        self.raise_frame(self.fr1)
    
              
    def move_on(self):
        """Continues to the live screen"""
        self.raise_frame(self.fr1)
        self.gen_id()
        self.id_disp.configure(text=self.iD)
        self.init_file()
        self.counter = 0 #for updates
        self.interval_start_time = datetime.now(pytz.timezone('US/Eastern'))
        self.time1.configure(text=str(self.interval_start_time)[11:-16])
        self.vol1.configure(text='0.0')
        self.interval_data = []
        self.all_data = []
        self.get_reading()
        self.offset = self.mass
        self.last = 0
        self.new = 0
        self.cumul = 0
        self.interval_records = [(str(self.interval_start_time)[11:-16], '00.0')]
        self.update_display()


    def get_reading(self):
        """Returns mass reading from strain gauge"""
        empty = 0
        while empty < 1:
            count, mode, inp = self.hx.get_reading()
            if type(inp) == type(None):
                print 'empty reading'
                #print inp
                empty = 0
            else:
                empty = 1
                print 'good reading'
        if type(inp) != type(None):
            self.mass = round(((inp - self.c)/self.m),0)
        print self.mass
    

    def gen_id(self): 
        """Generates unique patient iD"""
        exist = True
        while exist:
            self.iD = choice(string.ascii_letters[26:]) + choice(string.ascii_letters[26:]) + choice(string.ascii_letters[26:]) + str(int(random()*10)) + str(int(random()*10)) +choice(string.ascii_letters[26:]) + choice(string.ascii_letters[26:]) + choice(string.ascii_letters[26:])
            exist = os.path.exists(self.path+self.iD+'.csv')
        db.add_pi(self.iD)


    def init_file(self): 
        """Initializes the data file iD.csv"""
        self.fname = self.path+self.iD+'.csv'
        f = open(self.fname,'w')
        f.write('time, raw volume, status, new volume, cumulative volume\n')
        f.close()


    def get_data(self):
        """Gets the raw mass and time"""
        self.get_reading()
        self.raw=self.mass
        self.time = datetime.now(pytz.timezone('US/Eastern'))


    def adjust_live_display(self):
        """Adjusts the live volume reading and countdown timer"""
        self.interval_elapsed = str(self.time-self.interval_start_time)[2:-7]
        self.live_timer.configure(text=self.interval_elapsed)
        self.live_vol.configure(text=str(self.raw-self.offset))


    def validity_check(self):
        """Validity check every 20 seconds"""
        self.tag = 'raw'
        if self.counter%20==0 and self.counter>20:
            avg = np.mean(np.array(self.all_data[-9:])[:,1])
            std = np.std(np.array(self.all_data[-9:])[:,1])
            if avg > 100 and std < 10:
                self.tag = 'valid'
                self.change = self.raw - self.last
            if self.change > 0:
                self.new += self.change
                self.cumul += self.change
            else:
                self.new += 0
                self.cumul += 0
        else:
            self.tag = 'reject'
        self.save_data()
        #db.add_data(self.time, self.raw, 0, self.new, self.cumul, self.tag, self.iD)



    def make_new_interval(self):
        """create new interval every 600 seconds (10 minutes)"""
        if self.counter%600==0 and self.counter>0:
            #get cumulative and reset counter
            self.last_interval_cumulative = round(self.new,0)
            self.last = self.last_interval_cumulative
            self.new = 0
            #reset array and time
            self.interval_data = []     
            self.interval_start_time = datetime.now(pytz.timezone('US/Eastern'))
            self.repaint_list()
            if len(self.interval_records) > 3:
                self.scrl_up.configure(command=lambda:self.scroll_up)
                self.scrl_dn.configure(command=lambda:self.scroll_down)                 

 
    def repaint_list(self):
        """Refreshes values in table"""
        #update table
        self.interval_records.append((str(self.interval_start_time)[11:-16],str(self.last_interval_cumulative)))
        if len(self.interval_records)>0:
            self.time1.configure(text=self.interval_records[-1][0])
            self.vol1.configure(text=self.interval_records[-1][1])
        if len(self.interval_records)>1:
            self.time2.configure(text=self.interval_records[-2][0])
            self.vol2.configure(text=self.interval_records[-2][1])
        if len(self.interval_records)>2:
            self.time3.configure(text=self.interval_records[-3][0])
            self.vol3.configure(text=self.interval_records[-3][1])     


    def scroll_up(self):
        """Scrolls up in table"""
        self.interval_records.insert(0,self.interval_records[-1])
        self.interval_records.pop(-1)
        self.repaint_list()


    def scroll_down(self):
        """Scrolls down in table"""
        self.interval_records.append(self.interval_records.pop(0))
        self.repaint_list()
        
                    
    def update_arrays(self):
        """Updates the arrays"""
        #add to arrays
        self.tick = (self.time, self.raw, 0, self.new, self.cumul, self.tag, self.iD)
        self.interval_data.append(self.tick)
        self.all_data.append(self.tick)
        db.add_data(self.all_data)
        #limit length of all data array
        if self.counter > 10000:
            self.all_data.pop(0)


    def save_data(self):
        """Saves data to file"""
        string = str(self.time)+', '+str(self.raw)+', '+str(self.tag)+', '+str(self.new)+', '+str(self.cumul)+'\n'
        f=open(self.fname,'a')
        f.write(string)
        f.close()   
        
        
    def update_display(self):
        """Gets readings and updates the live screen"""
        self.counter += 1 #1 second between each update
        self.get_data()
        self.adjust_live_display()
        self.validity_check()
        self.make_new_interval()
        self.update_arrays()
        self.root.after(1000, self.update_display)



    def shutdown(self):
        command = "/usr/bin/sudo /sbin/shutdown now"
        import subprocess
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output = process.communicate()[0]
        print output

    def _quit(self): 
        """Quits the GUI"""
        self.root.quit()
        self.root.destroy()
        #self.shutdown()


    def raise_frame(self, frame): 
        """Displays another frame"""
        frame.tkraise()


app=App()
