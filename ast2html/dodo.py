

def task_asdl():
    return {'actions': ['python asdl2html.py > %(targets)s'],
            'dependencies': ['python.asdl', 'asdl2html.py'],
            'targets': ['python-asdl.html'],
            }

SAMPLES = ['sample.py', 'sample2.py']
def task_ast():
    for sample in SAMPLES:
        target = "%s.html" % sample
        yield {'name': sample,
               'actions':["python ast2html.py %s > %s" % (sample, target)],
               'dependencies': ['ast2html.py', sample],
               'targets': [target]
               }
