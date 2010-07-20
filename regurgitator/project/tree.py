"""create HTML for a project tree file"""

import subprocess
import os

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


class Folder(object):
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.folders = []
        self.files = []

    def __repr__(self):
        return "Folder(%s)" % self.path

    def dump(self):
        return ("Folder(%s){\n  folders=[%s]\n  files=[%s]}" %
                (self.path, ", ".join(self.folders), ", ".join(self.files)))


class Project(object):
    """
    @ivar output: (str) folder where HTML files will be created
    """
    root_folder_name = '(root)'

    def __init__(self, name, root_path, output="_html"):
        self.name = name
        self.root_path = root_path
        self.files = {}
        self.folders = {}
        self.output = output
        self.output_path = os.path.abspath(os.path.join(
                os.path.curdir, self.output))

    def load_project_files(self):
        file_list = get_tracked_files_hg(self.root_path)

        # initialize files
        for path in file_list:
            # ignore non-python files
            if path.endswith(".py"):
                self.files[path] = None

        # initialize folders
        for path in self.files:
            folder, file_ = os.path.split(path)
            if folder:
                name = folder
            else:
                name = self.root_folder_name
            if folder not in self.folders:
                self.folders[folder] = Folder(name, folder)
            self.folders[folder].files.append(path)

        # add sub-folders
        for folder in self.folders.iterkeys():
            if not folder:
                continue # skip root folder
            parts = folder.rsplit('/', 1)
            if len(parts) == 1:
                self.folders[''].folders.append(folder)
            else:
                self.folders[parts[0]].folders.append(parts[1])




 # <link rel="stylesheet" href="_static/pygments.css" type="text/css">
 #    <script type="text/javascript">
 #    </script>
 #    <script type="text/javascript" src="_static/jquery.js"></script>

    def html(self, jinja_env):
        """create HTML pages"""

        # index page
        index = open(os.path.join(self.output, "index.html"), 'w')
        template = jinja_env.get_template("index.html")
        index.write(template.render(project=self))
        index.close()

        # folder pages
        template = jinja_env.get_template("folder.html")
        for f_name, folder in self.folders.iteritems():
            page_path = os.path.join(self.output, "%s.html" % folder.name)
            # FIXME do not use sub-folders. use only relative paths on HTML links
            if not os.path.exists(os.path.dirname(page_path)):
                os.makedirs(os.path.dirname(page_path))
            f_page = open(page_path, 'w')
            # TODO add breadcrumbs
            f_page.write(template.render(project=self, folder=folder))
            f_page.close()


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
