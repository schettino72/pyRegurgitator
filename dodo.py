import os
import glob

from doitpy.pyflakes import Pyflakes
from doitpy import pypi

DOIT_CONFIG = {'default_tasks': ['pyflakes', 'doctest']}


def task_pyflakes():
    yield Pyflakes().tasks('*.py')
    yield Pyflakes().tasks('pyreg/**/*.py')


def task_test():
    """run tests"""
    for module in ['pyreg/asdlview.py']:
        yield {
            'basename': 'doctest',
            'name': module,
            'file_dep': [module],
            'actions': ['py.test --doctest-modules --color=yes ' + module],
            'verbosity': 2,
            }



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


def xml_text(xml_file, target):
    """return text content of a XML tree"""
    import xml.etree.ElementTree as ET
    root = ET.parse(xml_file)
    reslist = list(root.iter())
    with open(target, 'w') as fp:
        for element in reslist:
            if element.text:
                fp.write(element.text)


SAMPLES = glob.glob("samples/*.py")
def task_ast():
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
            'basename': 'ast2xml',
            'name': sample,
            'actions':["astview --format=xml {} > {}".format(sample, xml)],
            'file_dep': ['pyreg/astview.py', sample],
            'targets': [xml]
            }

        gen_py = "_output/%s.py" % sample[8:-3]
        yield {
            'basename': 'xml2py',
            'name': sample,
            'actions':[(xml_text, (xml, gen_py))],
            'file_dep': ['pyreg/astview.py', xml],
            'targets': [gen_py]
            }


############################

def _update_dict(d, **kwargs):
    """little helper to modify and return a dict in one line"""
    d.update(kwargs)
    return d

def task_pypi():
    pkg = pypi.PyPi()
    yield pkg.manifest_git()
    yield _update_dict(pkg.sdist(), task_dep=['asdl_json'])
