"""Example module to test pyRegurgitator"""

__version__ = (0, 1, 0)


class Foo:
    def hi(self):
        print('Hi, this is Foo')

    @staticmethod
    def add_4(num):
        return 4 + num


class Bar(Foo):
    def bar(self):
        print('foobar')
