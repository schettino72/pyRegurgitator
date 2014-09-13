""" PY -> XML -> PY checker
convert all files from cpython/Lib to xml and back to python
"""

import pathlib

PATH = '/home/eduardo/work/third_party/cpython/Lib'

IGNORE = {
    # IGNORE
    'test/badsyntax_3131.py',
    'test/bad_coding.py',
    'test/bad_coding2.py',
    'test/badsyntax_pep3120.py',
    'test/test_pep3131.py', # get an ERRORTOKEN

    # WONT FIX - not unicode
    'sqlite3/test/hooks.py',
    'sqlite3/test/types.py',
    'sqlite3/test/regression.py',
    'sqlite3/test/factory.py',
    'sqlite3/test/userfunctions.py',
    'sqlite3/test/dbapi.py',
    'sqlite3/test/transactions.py',
    'test/encoded_modules/module_iso_8859_1.py',
    'test/encoded_modules/module_koi8_r.py',
    'test/test_source_encoding.py',
    'test/coding20731.py',

    # WONT FIX - use 2 parenthesis around expression
    'test/test_itertools.py',
    'plat-sunos5/IN.py',
    'plat-sunos5/STROPTS.py',
    'tkinter/test/test_ttk/test_functions.py',
    'idlelib/configHelpSourceEdit.py',
    'idlelib/keybindingDialog.py',
    'cpy/plat-aix4/IN.py',
    'plat-aix4/IN.py',

    # WONT FIX - contains page break
    'test/test_isinstance.py',
    'test/test_email/test_asian_codecs.py',
    'test/test_email/torture_test.py',
    }

def task_regurgitate():
    """generate HTML for AST of sample modules"""
    for sample in pathlib.Path(PATH).glob('**/*.py'):
        orig_py = str(sample)
        rel_path = str(sample.relative_to(PATH))
        out_path = "_output/cpy"

        if rel_path.startswith('lib2to3/tests/data'):
            continue # contains python2 code
        if rel_path.startswith('email'):
            continue # many files with page break
        if rel_path in IGNORE:
            continue

        xml = out_path + "/%s.xml" % rel_path
        yield {
            'basename': 'py2xml',
            'name': rel_path,
            'actions':[
                "mkdir -p {}".format(pathlib.Path(xml).parent),
                "py2xml {} > {}".format(orig_py, xml)],
            'file_dep': [#'pyreg/py2xml.py',
                         orig_py],
            'targets': [xml]
            }

        gen_py = out_path + "/%s" % rel_path
        yield {
            'basename': 'xml2py',
            'name': rel_path,
            'actions':["py2xml --reverse {} > {}".format(xml, gen_py)],
            'file_dep': [xml],
            'targets': [gen_py]
            }

        yield {
            'basename': 'roundtrip',
            'name': rel_path,
            'actions':['diff {} {}'.format(orig_py, gen_py)],
            'file_dep': [orig_py, gen_py],
            }
