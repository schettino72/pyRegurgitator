"""create HTML for a project tree file"""

import subprocess
import os

import jinja2

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
    def __init__(self, root_path, path):
        parts = path.split('/')
        self.name = parts[-1]
        self.path = path
        self.ref = '.'.join(parts)
        self.ast = None

        try:
            docstring = None
            self.ast = file2ast(os.path.join(root_path, path))
            docstring = ast.get_docstring(self.ast)
        except Exception, e:
            print "pymap (ERROR) %s" % e

        # module docstring
        if docstring:
            self.desc = docstring.split('\n')[0]
        else:
            self.desc = ''

        # imports
        class ImportsFinder(ast.NodeVisitor):
            def __init__(self):
                ast.NodeVisitor.__init__(self)
                self.imports = []

            def visit_Import(self, node):
                names = [(n.name, n.asname) for n in node.names]
                self.imports.append([None, names, None])
                ast.NodeVisitor.generic_visit(self, node)

            def visit_ImportFrom(self, node):
                names = [(n.name, n.asname) for n in node.names]
                self.imports.append([node.module, names, node.level])
                ast.NodeVisitor.generic_visit(self, node)

        self.imports = []
        if self.ast:
            finder = ImportsFinder()
            finder.visit(self.ast)
            self.imports = ([(m[0], m[1]) for m in finder.imports])

    def parent_list(self):
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

    def load_project_files(self):
        file_list = get_tracked_files_hg(self.root_path)

        # initialize files
        for path in file_list:
            print "pymap: init file: %s " % path
            # ignore non-python files
            if path.endswith(".py"):
                self.files[path] = File(self.root_path, path)

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
