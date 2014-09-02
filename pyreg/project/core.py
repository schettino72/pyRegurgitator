"""create HTML for a project tree file"""

import subprocess
import os
import time
import ast

import jinja2



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


def get_tracked_files_git(path):
    """get all files being tracked by GIT

    @param path: (str) repository root directory
    @return: (list -str) relative file paths
    """
    output = subprocess.check_output(
        ['git', 'ls-tree', '--name-only', '-r', '--full-tree', 'HEAD', path],
        universal_newlines=True)
    return [f.strip() for f in output.splitlines()]




class File(object):
    """Represents a python file"""
    def __init__(self, path):
        """
        @param ast_node: if not given
        """
        parts = path.split('/')
        self.name = parts[-1]
        self.path = path
        self.ref = '.'.join(parts)

        self.ast = None
        self.desc = None
        self.imports = None


    def __lt__(self, other):
        return self.path < other.path

    def get_ast(self, root_path):
        """get module's ast node"""
        file_path = os.path.join(root_path, self.path)
        try:
            with open(file_path, 'r') as fp:
                self.ast = ast.parse(fp.read(), file_path)
        except Exception as exception:
            print("pymap error creating AST for %s." % file_path)
            print(str(exception))


    def get_docstring(self):
        """get module docstring"""
        if not self.ast:
            self.desc = ''
            return

        docstring = ast.get_docstring(self.ast)
        if docstring:
            self.desc = docstring.split('\n')[0]
        else:
            self.desc = ''


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
                """callback for 'import' statement"""
                self.imports.extend((None, n.name, n.asname, None)
                                    for n in node.names)
                ast.NodeVisitor.generic_visit(self, node)

            def visit_ImportFrom(self, node):
                """callback for 'import from' statement"""
                self.imports.extend((node.module, n.name, n.asname, node.level)
                                    for n in node.names)
                ast.NodeVisitor.generic_visit(self, node)

        if not self.ast:
            return []
        finder = ImportsFinder()
        finder.visit(self.ast)
        self.imports = finder.imports


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
    """Represents a folder on file-system

    @ivar name: (str) folder name (only part after last '/')
    @ivar path: (str) '/' separate folder path
    @ivar ref: (str) "." separated folder path

    # Project is responsible for setting this
    @ivar folders: (list of Folder)
    @ivar files: (list of File)
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

    def __lt__(self, other):
        return self.path < other.path

    def dump(self):
        """return str with information of all folder content"""
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
        self.jinja_env = jinja2.Environment(
            loader=jinja2.PackageLoader('regurgitator.project', 'templates'),
            undefined=jinja2.StrictUndefined,
            trim_blocks=True)

        # initialization of project files/folders
        file_list = get_tracked_files_git(self.root_path)
        self._init_files(file_list)
        self._init_folders()


    def _init_files(self, file_list):
        """create File objects (put on self.files)"""
        for path in file_list:
            #print "pymap: init file: %s " % path
            # ignore non-python files
            if path.endswith(".py"):
                self.files[path] = File(path)


    def _init_folders(self):
        """create and initialize Folder objects (put on self.folders)"""
        # initialize folders
        # get all folders that contain "tracked" files
        for path in self.files:
            #print "pymap: processing file: %s " % path
            folder = os.path.split(path)[0]
            if folder not in self.folders:
                new_folder = Folder(folder)
                self.folders[folder] = Folder(folder) #XXX create folder again?
                # make sure all fold ancestors are added
                for folder_path in new_folder.parent_list()[:-1]:
                    if folder_path not in self.folders:
                        self.folders[folder_path] = Folder(folder_path)
            # add file to folder
            self.folders[folder].files.append(self.files[path])

        # add sub-folders (this must be done after all Folder are created)
        for folder in list(self.folders.keys()):
            #print "pymap: init folder: %s " % folder
            if not folder:
                continue # skip root folder
            parts = folder.rsplit('/', 1)
            if len(parts) == 1:
                # root folder
                self.folders[''].folders.append(self.folders[folder])
            else:
                self.folders[parts[0]].folders.append(self.folders[folder])


    def html_file_path(self, file_obj):
        """get file path where html file will be created"""
        return os.path.join(self.output, "%s.html" % file_obj.ref)


    ## generate HTML methods

    # FIXME remove ".html" from pages
    def html(self):
        """create HTML pages"""
        self.html_index()

        folder_template = self.jinja_env.get_template("folder.html")
        for folder_obj in self.folders.values():
            self.html_folder(folder_template, folder_obj)

        file_template = self.jinja_env.get_template("file.html")
        for file_obj in self.files.values():
            self.html_file(file_template, file_obj)

    def html_index(self):
        """create HTML for index page"""
        template = self.jinja_env.get_template("index.html")
        index = open(os.path.join(self.output, "index.html"), 'w')
        index.write(template.render(project=self))
        index.close()

    def html_folder(self, template, folder_obj):
        """create HTML for folder pages"""
        page_path = os.path.join(self.output, "%s.html" % folder_obj.ref)
        f_page = open(page_path, 'w')
        if folder_obj.ref == "_root_folder":
            base_path = ''
        else:
            base_path = folder_obj.ref + '.'
        # print "pymap: generate template for ", folder
        parents = [self.folders[p] for p in folder_obj.parent_list()]
        f_page.write(template.render(project=self, base_link=base_path,
                                     folder=folder_obj, parents=parents))
        f_page.close()

    def html_file(self, template, file_obj):
        """create HTML for file pages"""
        parents = [self.folders[p] for p in file_obj.parent_list()]

        page_path = self.html_file_path(file_obj)
        file_page = open(page_path, 'w')
        file_page.write(template.render(project=self, file_obj=file_obj,
                                        parents=parents))
        file_page.close()




def create_project_map(project_path):
    """create all HTML for a project"""
    # list with timestamps to measure speed of every step
    start = []

    # setup
    root_path = os.path.abspath(project_path)
    project_name = root_path.split('/')[-1]

    start.append(time.time())

    print("========>  go")
    proj = Project(project_name, root_path)
    print("========>  get files", time.time() - start[0])

    for pyfile in proj.files.values():
        pyfile.get_ast(proj.root_path)
    print("========>  ast", time.time() - start[0])

    list(map(File.get_imports, iter(proj.files.values())))
    print("========>  imports", time.time() - start[0])

    list(map(File.get_docstring, iter(proj.files.values())))
    print("========>  docstring", time.time() - start[0])

    proj.html()
    print("========>  html", time.time() - start[0])

