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
