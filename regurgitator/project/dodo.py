import glob

from doit.tools import create_folder

output_folder = "_html"
templates = glob.glob('templates/*.html')

def task_regurgitator_map():
    return {'actions': [(create_folder, (output_folder,)),
                        'pymap ../..'],
            'file_dep': ['tree.py']  + templates,
            'targets': [output_folder + '/index.html'],
            'clean': ['rm -rf %s' % output_folder],
            }


# TODO
# - module page
# - list of first level imports on module page
# - integrate with doit
# - package page include import graph
# - module page - list of all imports at any level


# OTHER
# - include link to trac
