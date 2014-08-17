from doitpy.pyflakes import Pyflakes


DOIT_CONFIG = {'default_tasks': ['pyflakes', 'doctest']}


def task_pyflakes():
    yield Pyflakes().tasks('*.py')
    yield Pyflakes().tasks('regurgitator/**/*.py')


def task_test():
    for module in ['regurgitator/asdl2html.py']:
        yield {
            'basename': 'doctest',
            'name': module,
            'file_dep': [module],
            'actions': ['py.test --doctest-modules --color=yes ' + module],
            'verbosity': 2,
            }




def task_asdl():
    return {'actions': ['python regurgitator/asdl2html.py python2.asdl > %(targets)s'],
            'file_dep': ['python2.asdl', 'regurgitator/asdl2html.py'],
            'targets': ['_output/python-asdl.html'],
            }

import glob

SAMPLES = glob.glob("samples/*.py")
def task_ast():
    for sample in SAMPLES:
        target = "_output/%s.html" % sample[8:-3]
        yield {'name': sample,
               'actions':["python regurgitator/ast2html.py %s > %s" % (sample, target)],
               'file_dep': ['regurgitator/ast2html.py', sample],
               'targets': [target]
               }
