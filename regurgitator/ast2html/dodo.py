import glob

def task_asdl():
    return {'actions': ['python asdl2html.py > %(targets)s'],
            'file_dep': ['python.asdl', 'asdl2html.py'],
            'targets': ['python-asdl.html'],
            }

SAMPLES = glob.glob("samples/*.py")
def task_ast():
    for sample in SAMPLES:
        target = "%s.html" % sample[:-3]
        yield {'name': sample,
               'actions':["python ast2html.py %s > %s" % (sample, target)],
               'file_dep': ['ast2html.py', sample],
               'targets': [target]
               }
