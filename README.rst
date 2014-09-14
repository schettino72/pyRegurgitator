================
pyRegurgitator
================

Tools for analysing python code.

http://bitbucket.org/schettino72/pyregurgitator/


Features (done)
================

* asdl2html => reference table of python's ASDL

* ast2html => super pretty print of python source-code's AST


Install
=========

$ python setup.py install


Usage
=======

As of version 0.1 the only tool available is `ast2html`

ast2html
----------

$ ast2html my_python_module.py

see http://bitbucket.org/schettino72/pyregurgitator/raw/tip/doc/ast_sample.html for a sample output.


Roadmap (TODO)
===============

* project_map I  => display folder/package structure

* project_map II => include import/dependency information

* project_map III => import/dependency checker

* AST -> get all defined names in a module (or another scope)

* doc-tool

* refactoring tool



License
=========

The MIT License, see. LICENSE.txt
