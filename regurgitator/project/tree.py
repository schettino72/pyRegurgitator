"""create HTML for a project tree file"""

import subprocess
import os
import sys
import cPickle as pickle

import jinja2
from doit import task, cmds

from regurgitator.ast_util import file2ast
from regurgitator import myast as ast


def get_tracked_files_hg(path):
    """get all files being tracked by HG

    @param path: (str) repository root directory
    @return: (list -str) relative file paths
    """
    output = subprocess.Popen(
        ["hg", "status", "--no-status", "--clean", "--modified", "--added",
         "--repository", path],
        stdout=subprocess.PIPE).communicate()[0]
    return [f.strip() for f in output.splitlines()]



class File(object):
    def __init__(self, path, ast_node):
        """
        @param ast_node: if not given
        """
        parts = path.split('/')
        self.name = parts[-1]
        self.path = path
        self.ref = '.'.join(parts)
        self.ast = ast_node

        self.desc = self.get_docstring()
        self.imports = self.get_imports()


    def get_docstring(self):
        """get module docstring"""
        if not self.ast:
            return ''

        docstring = ast.get_docstring(self.ast)
        if docstring:
            return docstring.split('\n')[0]
        else:
            return ''


    def get_imports(self):
        """get list of imports from module"""

        class ImportsFinder(ast.NodeVisitor):
            """find all imports
            @ivar imports: (list - tuple) (module, name, asname, level)
            """
            def __init__(self):
                ast.NodeVisitor.__init__(self)
                self.imports = []

            def visit_Import(self, node):
                self.imports.extend((None, n.name, n.asname, None)
                                    for n in node.names)
                ast.NodeVisitor.generic_visit(self, node)

            def visit_ImportFrom(self, node):
                self.imports.extend((node.module, n.name, n.asname, node.level)
                                    for n in node.names)
                ast.NodeVisitor.generic_visit(self, node)

        if not self.ast:
            return []
        finder = ImportsFinder()
        finder.visit(self.ast)
        return finder.imports


    def parent_list(self):
        """return list of parent folders "/" separated

        >>> my_file = File('top_p/sub_p1/myfile')
        >>> my_file.parent_list()
        ['', 'top_p', 'top_p/sub_p1']
        """
        parents = ['']
        current = []
        for part in self.path.split('/')[:-1]:
            current.append(part)
            parents.append("/".join(current))
        return parents



class Folder(object):
    """
    @ivar name: (str) folder name (only part after last '/')
    @ivar path: (str) '/' separate folder path
    @ivar ref: (str) "." separated folder path
    """
    def __init__(self, path):
        """
        @param path(str): relative path to the root of the project.
                          should NOT start with '/'
        """
        parts = path.split('/')
        self.path = path
        if not path:
            self.name = "(root)"
            self.ref = "_root_folder"
        else:
            self.name = parts[-1]
            self.ref = '.'.join(parts)
        self.folders = []
        self.files = []


    def parent_list(self):
        """return list of parent folders "/" separated

        >>> my_folder = Folder('top_p/sub_p1/sub_p2')
        >>> my_folder.parent_list()
        ['', 'top_p', 'top_p/sub_p1', 'top_p/sub_p1/sub_p2']
        """

        parents = ['']
        if self.ref == '_root_folder':
            return parents

        current = []
        for part in self.path.split('/'):
            current.append(part)
            parents.append("/".join(current))
        return parents


    def __repr__(self):
        return "Folder(%s)" % self.path


    def dump(self):
        return ("Folder(%s){\n  folders=[%s]\n  files=[%s]}" %
                (self.path, ", ".join(self.folders), ", ".join(self.files)))


def save_ast(in_module, out_path):
    mod_ast = file2ast(in_module)
    out = open(out_path, 'w')
    pickle.dump(mod_ast, out)
    out.close()


class Project(object):
    """
    @ivar output: (str) folder where HTML files will be created
    """

    def __init__(self, name, root_path, output="_html"):
        self.name = name
        self.root_path = root_path
        self.files = {}
        self.folders = {}
        self.output = output


    def init_files_doit(self, file_list):
        # compile module's ast
        ast_tasks = []
        for path in file_list:
            print "pymap: ast file: %s " % path
            # ignore non-python files
            if path.endswith(".py"):
                abs_path = os.path.join(self.root_path, path)

                target = "_ast/" + path.replace('/', '.') + ".ast"
                this_task = None
                this_task = task.Task(
                    "ast:%s" % abs_path, # name
                    [(save_ast, (abs_path, target))], # actions
                    [abs_path], # file_dep
                    [target], # targets
                    )
                ast_tasks.append((path, this_task))

        cmds.doit_run(".reg_doit.db", (i[1] for i in ast_tasks), sys.stdout,
                      continue_=True)

        # initialize files
        mod_ast_list = []
        for path, ast_task in ast_tasks:
            print "pymap: load ast file: %s " % path
            try:
                ast_file = open(ast_task.targets[0], 'r')
                mod_ast_list.append((path, pickle.load(ast_file)))
                ast_file.close()
            except Exception, e:
                print "pymap (ERROR) %s" % e
                mod_ast = None

        # initialize files
        for path, mod_ast in mod_ast_list:
            print "pymap: process ast file: %s " % path
            self.files[path] = File(path, mod_ast)


    def init_files(self, file_list):
        for path in file_list:
            print "pymap: init file: %s " % path
            # ignore non-python files
            if path.endswith(".py"):
                try:
                    this_ast = file2ast(os.path.join(self.root_path, path))
                except Exception, e:
                    print "pymap (ERROR) %s" % e
                self.files[path] = File(path, this_ast)


    def load_project_files(self):
        file_list = get_tracked_files_hg(self.root_path)
        self.init_files(file_list)


        # initialize folders
        for path in self.files:
            print "pymap: processing file: %s " % path
            folder, file_ = os.path.split(path)
            if folder not in self.folders:
                new_folder = Folder(folder)
                self.folders[folder] = Folder(folder)
                for folder_path in new_folder.parent_list()[:-1]:
                    if folder_path not in self.folders:
                        self.folders[folder_path] = Folder(folder_path)
            self.folders[folder].files.append(self.files[path])

        # add sub-folders
        for folder in self.folders.keys():
            print "pymap: init folder: %s " % folder
            if not folder:
                continue # skip root folder
            parts = folder.rsplit('/', 1)
            if len(parts) == 1:
                self.folders[''].folders.append(self.folders[folder])
            else:
                self.folders[parts[0]].folders.append(self.folders[folder])




 # <link rel="stylesheet" href="_static/pygments.css" type="text/css">
 #    <script type="text/javascript">
 #    </script>
 #    <script type="text/javascript" src="_static/jquery.js"></script>


    def _html_index(self, template):
        """create HTML for index page"""
        index = open(os.path.join(self.output, "index.html"), 'w')
        index.write(template.render(project=self))
        index.close()

    def _html_folder(self, template):
        """create HTML for folder pages"""
        for f_name, folder in self.folders.iteritems():
            page_path = os.path.join(self.output, "%s.html" % folder.ref)
            f_page = open(page_path, 'w')
            if folder.ref == "_root_folder":
                base_path = ''
            else:
                base_path = folder.ref + '.'
            print "pymap: generate template for ", folder
            parents = [self.folders[p] for p in folder.parent_list()]
            f_page.write(template.render(project=self, base_link=base_path,
                                         folder=folder, parents=parents))
            f_page.close()

    def _html_file(self, template):
        """create HTML for file pages"""
        for file_obj in self.files.itervalues():
            parents = [self.folders[p] for p in file_obj.parent_list()]

            page_path = os.path.join(self.output, "%s.html" % file_obj.ref)
            file_page = open(page_path, 'w')
            file_page.write(template.render(project=self, file_obj=file_obj,
                                            parents=parents))
            file_page.close()

        pass

    def html(self, jinja_env):
        """create HTML pages"""
        self._html_index(jinja_env.get_template("index.html"))
        self._html_folder(jinja_env.get_template("folder.html"))
        self._html_file(jinja_env.get_template("file.html"))



def create_project_map(project_path):
    """ """
    root_path = os.path.abspath(project_path)
    project_name = root_path.split('/')[-1]
    jinja_env = jinja2.Environment(
        loader=jinja2.PackageLoader('regurgitator.project', 'templates'),
        undefined=jinja2.StrictUndefined,
        trim_blocks=True)
    proj = Project(project_name, root_path)
    proj.load_project_files()
    print proj.html(jinja_env)



if __name__ == "__main__":
    create_project_map("/home/eduardo/src/pyregurgitator")
