import asdl2html

def task_asdl():
    return {'actions': ['python asdl2html.py > %(targets)s'],
            'dependencies': ['python.asdl', 'asdl2html.py'],
            'targets': ['python-asdl.html'],
            }
