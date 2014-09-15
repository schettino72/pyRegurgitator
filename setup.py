#! /usr/bin/env python

from setuptools import setup

# use README file as long_description
with open('README.rst') as readme:
    long_description = readme.read()


setup(name = 'pyRegurgitator',
      description = 'pyRegurgitator - Tools for analysing python code',
      version = '0.2.1',
      license = 'MIT',
      author = 'Eduardo Naufel Schettino',
      author_email = 'schettino72@gmail.com',
      url = 'http://pythonhosted.org/pyRegurgitator',
      classifiers = ['Development Status :: 3 - Alpha',
                     'Environment :: Console',
                     'Intended Audience :: Developers',
                     'License :: OSI Approved :: MIT License',
                     'Natural Language :: English',
                     'Operating System :: OS Independent',
                     'Operating System :: POSIX',
                     'Programming Language :: Python :: 3.4',
                     'Topic :: Software Development',
                     ],

      packages = ['pyreg'],
      package_data = {'': ['asdl/*', 'templates/*', ]},
      install_requires = ['jinja2'],
      long_description = long_description,
      entry_points = {
        'console_scripts': [
            'asdlview = pyreg.asdlview:asdl_view',
            'astview = pyreg.astview:ast_view',
            'py2xml = pyreg.py2xml:main',
            ]
        },
      )

