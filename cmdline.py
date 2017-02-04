from ADC import sensor
import pigpio
from wsinitd import init_scale
from wsinloopd import get_reading as getread
from time import sleep

def sample(hx):
	empty = 0
	while empty < 1:
		count, mode, inp = hx.get_reading()
		if type(c) == type(None):
			print 'empty reading'
		else:
			empty = 1
			print 'good reading'
	return inp

def get_mc(x1,y1,x2,y2):
	m = (y1-y2)/(x1-x2)
	c = y1 - (m*x1)
	return (m,c)

#get readings
counter = 0
(hx, m, c) = init_scale()

while True:
        inp = sample(hx)
        if type(inp) != type(None):
        	mass = (inp - c)/m
        else:
        	mass = 0
        print('\n time elapsed (s): %s \t mass (g): %s \t raw: %s' %(counter, mass, inp))
        counter += 1
        sleep(1)
