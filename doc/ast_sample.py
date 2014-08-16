import sys

max_something = 5

class MyClass(object):
    spam = "egg"

    def do_x(a,b=None):
        my_sum = max_something + a
        print(my_sum)
        return b is None
