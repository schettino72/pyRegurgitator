.. pyRegurgitator documentation master file, created by
   sphinx-quickstart on Mon Sep 15 01:44:58 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

pyRegurgitator - Tools for analysing python code
====================================================

Development on github: https://github.com/schettino72/pyRegurgitator/

PyPI: https://pypi.python.org/pypi/pyRegurgitator

Supported versions: Python 3.4 only


Tools
=========


asdlview
-----------

`asdlview` generates a HTML page with python's ASDL info.

It can also create a JSON file with the ASDL information
(used by the `astview` tool).

.. code-block:: console

  $ asdlview python34.asdl > python34.asdl.html

See :download:`python 34 ASDL <./_sample/python34.asdl.html>`.

astview
----------

`astview` generates a HTML page with a python module's AST info.

It can also dumps the AST in text format.


.. code-block:: console

  $ astview sample.py > sample.py.html

See :download:`sample AST HTML <./_sample/sample.py.html>`.


py2xml (*Experimental*)
-------------------------

`py2xml` convert python code to XML.


All source-code text, including white-space and comments, are preserved.
The XML can be converted back to python creating the exact same source.

The design was inspired by `srcML <http://www.srcml.org/>`_.
In order to get the original source code you just need to remove
all XML tags.

The goal is to use the XML for querying / analysis of the code.
And to perform code transformation/refactoring, and then
convert it back to python.

Why use XML instead of AST? AST does not preserve comments and
source code formatting. There are many available tools to manipulate
XML. XML is nice format for query and transformation - just do not use XSLT ;)


.. warning::

  As of release 0.2, `py2xml` creates a XML preserving all formating.
  But not much tough was given in creating a XML for easy querying and
  transformation (it mostly follows the AST nodes).
  So, expect the XML format to completely change in future releases.


Example
^^^^^^^^^^^^^

A simple python module...

.. literalinclude:: sample.py


Converting to XML:

.. code-block:: console

  $ py2xml sample.py > sample.py.xml


.. literalinclude:: _sample/sample.py.xml
   :language: xml


The XML can be converted back to source using the command line:

.. code-block:: console

  $ py2xml --reverse sample.py.xml > new_sample.py


Example - query
^^^^^^^^^^^^^^^^^^^^^

Example to print out all classes and their method names.

.. literalinclude:: query_class.py

Results in:

.. literalinclude:: _sample/query_result.txt


Example - transform
^^^^^^^^^^^^^^^^^^^^^^

In this example the variable `__version__` is programmatically
set to a new value.
Then the modified code is written back to plain python code.

.. literalinclude:: change_version.py

Results in:

.. literalinclude:: _sample/new_sample.py
   :language: python


Note how we just set the text of new content without creating XML nodes
for a `tuple` structure. Since the conversion from XML to python is done
just by removing the XML tags, and we won't do any other transformation
we can just insert the new python code text!


Implementation and known limitations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The implementation uses a combination of the python modules `ast` and `tokenize`.
Together they give all information necessary, code structure and formatting.

The current implementation fails to convert the python code to XML
in the following situations:

 - if the source code uses an encoding different than ascii or unicode

 - source contains page-breaks (tokenize module does not handle
   page-break)

 - expressions wrapped in 2 or more parenthesis. This is tricky to handle
   correctly, specially because of bugs in the AST column offset information.
   2 parenthesis is useless and seldom used in practice, so we just advise users
   to remove the extra parenthesis.

From the command line you can check if `py2xml` is capable of a lose-less
round-trip (python -> XML -> python) using the `--check` option.
No output means it is OK, otherwise you get an error or a diff.

.. code-block:: console

  $ py2xml --check my_module.py
