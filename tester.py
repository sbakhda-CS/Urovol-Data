from ADC import sensor
from time import sleep
import pigpio

pi = pigpio.pi()
hx = sensor(pi, DATA=15, CLOCK=14, mode=1)
#try mode 0 (128 bit) and 1 (64 bit) next

while True:
	count, mode, inp = hx.get_reading()
	input = hx.get_reading()
	
	print '\n'
	
	#see what data type it gets when read individually
	print str(count)+' (count) is type '+str(type(count))
	print str(mode)+' (mode) is type '+str(type(mode))
	print str(inp)+' (inp) is type '+str(type(inp))
	
	#see what data type it gets when read as an array
	print str(input)+'(array) is type'+str(type(input))
	print str(input[0])+' (array count) is type '+str(type(input[0]))
	print str(input[1])+' (array mode) is type '+str(type(input[1]))
	print str(input[2])+' (array inp) is type '+str(type(input[2]))		
	
	#try doing arithmetic with value
	#adj = (inp + 167609.0)/219.48
	#print('\n raw_input: %s', %inp)
	#print('mass: %s', %adj)
	sleep(5)
	
