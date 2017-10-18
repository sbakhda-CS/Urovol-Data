import wsinitd as nt
from time import sleep

def sample(hx):
	empty = 0
	while empty < 1:
		(count, mode, inp) = hx.get_reading()
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
(hx, m, c) = nt.init_scale()
print('scale must be empty in the next 10 seconds...')
sleep(10)

print('getting zero reading...')
mass_0 = sample(hx)
print('\nadd 500g in the next 10 seconds...')
sleep(10)

print('getting 500 reading...')
mass_500 = sample(hx)
print('\nadd 1000g in the next 10 seconds...')
sleep(10)

print('getting 1000 reading...')
mass_1000 = sample(hx)

#get mc values
(m1,c1) = get_mc(0.0,mass_0,500.0,mass_500) #for 0 - 500 line
(m2,c2) = get_mc(500.0,mass_500,1000.0,mass_1000) #for 500 - 1000 line
(m3,c3) = get_mc(0.0,mass_0,1000.0,mass_1000) #for 0 - 1000 line

#get averages
m = (m1+m2+m3)/3.0
c = (c1+c2+c3)/3.0

print ('\ngradient = %s \noffset = %s' %(m,c))
target = open('calib.txt', 'w')
target.write(str(m))
target.write('\n'+str(c))
target.close()


