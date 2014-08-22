import os
import glob

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



#################################################

def task_asdl():
    cmd_html = 'python regurgitator/asdl2html.py {} > {}'
    cmd_json = 'python regurgitator/asdl2html.py --format json {} > {}'
    for fn in glob.glob('asdl/*.asdl'):
        name = os.path.basename(fn)
        target = '_output/{}.html'.format(name)
        yield {
            'name': name + '.html',
            'actions': [cmd_html.format(fn, target)],
            'file_dep': ['regurgitator/asdl2html.py', fn],
            'targets': [target],
            }

        target = '_output/{}.json'.format(name)
        yield {
            'name': name + '.json',
            'actions': [cmd_json.format(fn, target)],
            'file_dep': ['regurgitator/asdl2html.py', fn],
            'targets': [target],
            }


SAMPLES = glob.glob("samples/*.py")
def task_ast():
    for sample in SAMPLES:
        target = "_output/%s.html" % sample[8:-3]
        yield {'name': sample,
               'actions':["python regurgitator/ast2html.py %s > %s" % (sample, target)],
               'file_dep': ['regurgitator/ast2html.py', sample],
               'targets': [target]
               }
