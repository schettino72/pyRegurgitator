import glob

from doit.tools import create_folder

OUTPUT_FOLDER = "_html"
TEMPLATES = glob.glob('templates/*.html')

def task_regurgitator_map():
    """creates a project map for pyRegurgitator"""
    return {'actions': [(create_folder, (OUTPUT_FOLDER,)),
                        'pymap ../..'],
            'file_dep': ['tree.py']  + TEMPLATES,
            'targets': [OUTPUT_FOLDER + '/index.html'],
            'clean': ['rm -rf %s' % OUTPUT_FOLDER],
            }


# TODO
# what is faster?
#     .py => ast
#     pickle load ast from file
#
# - integrate with doit
# - link on import list (identify project modules)
# - package page include import graph
# - module page - list of all imports at any level


# OTHER
# - include link to trac
