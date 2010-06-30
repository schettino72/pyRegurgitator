from __future__ import with_statement

a = 5
a += 3
b = 7
exec('a+b', locals(), globals())

try:
    print a
except Exception, exp:
    print b
else:
    print 6
finally:
    print a+b

while False:
    print "x"

with 5 as f:
    print f

g = [f*f for f in range(10) if x < 5]

True and False

def myg():
    yield 5
    f = yield 7

if True:
    6

if True:
    7
elif False:
    9
else:
    10

j = 4 if None else 6

a = lambda x:x*2

v = [1,2,3]

v[1:3:2]

(i for i in (1,2,3))
