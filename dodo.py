import os
import glob

from doitpy.pyflakes import Pyflakes


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
    for fn in glob.glob('asdl/*.asdl'):
        name = os.path.basename(fn)
        target = '_output/{}.html'.format(name)
        yield {
            'name': name + '.html',
            'actions': [cmd_html.format(fn, target)],
            'file_dep': ['pyreg/asdlview.py', 'pyreg/templates/asdl.html', fn],
            'targets': [target],
            }

        target = '_output/{}.json'.format(name)
        yield {
            'name': name + '.json',
            'actions': [cmd_json.format(fn, target)],
            'file_dep': ['pyreg/asdlview.py', 'pyreg/templates/ast.html',
                         'pyreg/templates/ast_node.html', fn],
            'targets': [target],
            }


SAMPLES = glob.glob("samples/*.py")
def task_ast():
    """generate HTML for AST of sample modules"""
    for sample in SAMPLES:
        target = "_output/%s.html" % sample[8:-3]
        yield {'name': sample,
               'actions':["astview {} > {}".format(sample, target)],
               'file_dep': ['pyreg/astview.py', sample],
               'targets': [target]
               }
