"""Creates a pymap for a project

It divides page creations into sub-tasks to execute only what is not up-to-date.
"""

import os

from doit.tools import create_folder

from .project.core import Project

OUTPUT_FOLDER = "_html"
PROJECT_PATH = '/home/eduardo/src/pyregurgitator'
ROOT_PATH = os.path.abspath(PROJECT_PATH)
PROJECT_NAME = ROOT_PATH.split('/')[-1]

# Project instance -> this should be create within a task but doit doesnt
# support the creation of tasks dynamically
PROJ = Project(PROJECT_NAME, ROOT_PATH)

def task_html():
    # index page
    yield {'name': 'index',
           'actions': [(create_folder, (OUTPUT_FOLDER,)),
                       (PROJ.html_index,)],
           'file_dep': [False], # always execute (FIXME -> use some proper dep)
           }


    # folder pages
    folder_template = PROJ.jinja_env.get_template("folder.html")
    for folder_obj in PROJ.folders.values():
        yield{'name': 'folder-%s' % folder_obj.ref,
              'actions': [(PROJ.html_folder, (folder_template, folder_obj))],
              # FIXME use task result where task get files+folders from folder_obj
              'file_dep': [False],
              }


    # file pages
    file_template = PROJ.jinja_env.get_template("file.html")
    for file_obj in PROJ.files.values():
        yield{'name': 'file-%s' % file_obj.ref,
              'actions': [(file_obj.get_ast, [ROOT_PATH]),
                          (file_obj.get_docstring,),
                          (file_obj.get_imports,),
                          (PROJ.html_file, (file_template, file_obj))],
              'file_dep': [os.path.join(ROOT_PATH, file_obj.path)],
              'targets': [PROJ.html_file_path(file_obj)],
              }

