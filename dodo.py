import os
import glob
import pathlib

from doitpy.pyflakes import Pyflakes
from doitpy.coverage import Coverage, PythonPackage
from doitpy import pypi



DOIT_CONFIG = {'default_tasks': ['pyflakes', 'test']}


def task_pyflakes():
    yield Pyflakes().tasks('*.py')
    yield Pyflakes().tasks('pyreg/**/*.py')

def task_test():
    """run tests"""
    yield {
        'name': 'unit',
        'actions': ['py.test tests'],
        'verbosity': 2,
        }

    for module in ['pyreg/asdlview.py']:
        yield {
            'name': 'doctest:' + module,
            'file_dep': [module],
            'actions': ['py.test --doctest-modules --color=yes ' + module],
            'verbosity': 2,
            }

def task_coverage():
    """show coverage for all modules including tests"""
    cov = Coverage([PythonPackage('pyreg', 'tests')])
    yield cov.all()
    yield cov.src()
    yield cov.by_module()




def _update_dict(d, **kwargs):
    """little helper to modify and return a dict in one line"""
    d.update(kwargs)
    return d

def task_pypi():
    pkg = pypi.PyPi()
    yield pkg.manifest_git()
    yield _update_dict(pkg.sdist(), task_dep=['asdl_json'])


#################################################

def task_asdl():
    """generate HTML and JSON for python ASDL"""
    cmd_html = 'asdlview {} > {}'
    cmd_json = 'asdlview --format json {} > {}'
    for fn in glob.glob('pyreg/asdl/*.asdl'):
        name = os.path.basename(fn)
        target = '_output/{}.html'.format(name)
        yield {
            'basename': 'asdl_html',
            'name': name + '.html',
            'actions': [cmd_html.format(fn, target)],
            'file_dep': ['pyreg/asdlview.py', 'pyreg/templates/asdl.html', fn],
            'targets': [target],
            }

        target = 'pyreg/asdl/{}.json'.format(name)
        yield {
            'basename': 'asdl_json',
            'name': name + '.json',
            'actions': [cmd_json.format(fn, target)],
            'file_dep': ['pyreg/asdlview.py', 'pyreg/templates/ast.html',
                         'pyreg/templates/ast_node.html', fn],
            'targets': [target],
            }


SAMPLES = glob.glob("samples/*.py")
def task_regurgitate():
    """generate HTML for AST of sample modules"""
    for sample in SAMPLES:
        html = "_output/%s.html" % sample[8:-3]
        yield {
            'basename': 'ast2html',
            'name': sample,
            'actions':["astview {} > {}".format(sample, html)],
            'file_dep': ['pyreg/astview.py', sample],
            'targets': [html]
            }

        xml = "_output/%s.xml" % sample[8:-3]
        yield {
            'basename': 'py2xml',
            'name': sample,
            'actions':["py2xml {} > {}".format(sample, xml)],
            'file_dep': ['pyreg/py2xml.py', sample],
            'targets': [xml]
            }

        gen_py = "_output/%s.py" % sample[8:-3]
        yield {
            'basename': 'xml2py',
            'name': sample,
            'actions':["py2xml --reverse {} > {}".format(xml, gen_py)],
            'file_dep': ['pyreg/py2xml.py', xml],
            'targets': [gen_py]
            }

        yield {
            'basename': 'check',
            'name': sample,
            'actions':['diff {} {}'.format(sample, gen_py)],
            'file_dep': [sample, gen_py],
            }


def task_roundtrip():
    """check roundtrip PY -> XML -> PY on all python stdlib files"""

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
        'plat-aix4/IN.py',

        # WONT FIX - contains page break
        'test/test_isinstance.py',
        'test/test_email/test_asian_codecs.py',
        'test/test_email/torture_test.py',
        }

#    for sample in pathlib.Path(PATH).glob('**/*.py'):
    for sample in pathlib.Path(PATH).glob('*.py'):
        orig_py = str(sample)
        rel_path = str(sample.relative_to(PATH))

        if rel_path.startswith('lib2to3/tests/data'):
            continue # contains python2 code
        if rel_path.startswith('email'):
            continue # many files with page break
        if rel_path in IGNORE:
            continue

        yield {
            'name': rel_path,
            'actions':[
                "py2xml --check {}".format(orig_py)],
            'file_dep': [#'pyreg/py2xml.py',
                         orig_py],
            }
