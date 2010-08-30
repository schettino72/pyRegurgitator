"""doit rules"""

import os

from doit.tools import create_folder

from regurgitator.project import tree

output_folder = "_html"
project_path = '/home/eduardo/src/pyregurgitator'
root_path = os.path.abspath(project_path)
project_name = root_path.split('/')[-1]

proj = tree.Project(project_name, root_path)

def task_html():
    # index page
    yield {'name': 'index',
           'actions': [(create_folder, (output_folder,)),
                       (proj.html_index,)],
           'file_dep': [False], # always execute (FIXME -> use some proper dep)
           }


    # folder pages
    folder_template = proj.jinja_env.get_template("folder.html")
    for folder_obj in proj.folders.itervalues():
        yield{'name': 'folder-%s' % folder_obj.ref,
              'actions': [(proj.html_folder, (folder_template, folder_obj))],
              # FIXME use task result where task get files+folders from folder_obj
              'file_dep': [False],
              }


    # file pages
    file_template = proj.jinja_env.get_template("file.html")
    for file_obj in proj.files.itervalues():
        yield{'name': 'file-%s' % file_obj.ref,
              'actions': [(file_obj.get_ast, [root_path]),
                          (file_obj.get_docstring,),
                          (file_obj.get_imports,),
                          (proj.html_file, (file_template, file_obj))],
              'file_dep': [os.path.join(root_path, file_obj.path)],
              }

