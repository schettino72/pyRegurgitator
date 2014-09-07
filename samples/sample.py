"""multiple
line  xixixi
docstring
"""

from time import time, mktime

mm = 5 + \
    9

ss = """se " # middle of expression
line2"""

# comment top level
a = 2
b = 5
t = a + b
print(t) # comment after statement


def xxxx(a,b,c=5):
    """single"""
    return (a*b-c)

dd = [23,
      45,
      67]

t=7;y=8

def nothing():
    """multiple
    with identation"""
    time()
    # comment at func level
    ascitime()
