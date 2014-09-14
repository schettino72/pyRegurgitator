pyRegurgitator - Tools for analysing python code
===================================================


Tools
=======

asdlview
-----------

`asdlview` generates a HTML page with python's ASDL info.

It can also create a JSON file with the ASDL information
(used by the `astview` tool).

Link XXX


astview
----------

`astview` generates a HTML page with a python module's AST info.

It can also dumps the AST in text format.

Link XXX


py2xml (*Experimental*)
-------------------------

`py2xml` convert python code to XML.

All source-code text include white-space and comments are preserved.
The XML can be converted back to python creating the exact same source.

The goal is to use the XML for querying / analysis of the code.
Perform some transformation/refactoring in the code, and then
convert it back to python.

As of release 0.2, `py2xml` creates a XML preserving all formating.
But not much tough was given in creating a XML for easy querying and
transformation (it mostly follows the AST nodes).
So the XML format will change completely in future releases.


Project Details
===============

- Project management on github - https://github.com/schettino72/pyRegurgitator/


license
=======

The MIT License
Copyright (c) 2010-2014 Eduardo Naufel Schettino

see LICENSE file


developers / contributors
==========================

- Eduardo Naufel Schettino


install
=======

::

 $ pip install pyRegurgitator

or download and::

 $ python setup.py install


tests
=======

To run the tests::

  $ py.test
