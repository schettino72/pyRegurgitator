

def task_regurgitator_map():
    return {'actions': ['pymap ../.. > %(targets)s'],
            'targets': ['self_pymap.html'],
            'file_dep': ['tree.py', 'templates/index.html'],
            }
