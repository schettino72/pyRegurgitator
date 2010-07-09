"""create HTML for a project tree file"""

import subprocess
import os

import jinja2

# build folder
BUILD = 'html'


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
    def __init__(self, path):
        self.path = path
        self.folders = []
        self.files = []

    def __repr__(self):
        return "Folder(%s)" % self.path

    def dump(self):
        return ("Folder(%s){\n  folders=[%s]\n  files=[%s]}" %
                (self.path, ", ".join(self.folders), ", ".join(self.files)))


class Project(object):
    def __init__(self, root_path):
        self.root_path = root_path
        self.files = {}
        self.folders = {}

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
            if folder not in self.folders:
                self.folders[folder] = Folder(folder)
            self.folders[folder].files.append(path)

        # add sub-folders
        for folder in self.folders.iterkeys():
            if folder == '':
                continue # skip root folder
            parts = folder.rsplit('/')
            if len(parts) == 1:
                self.folders[''].folders.append(folder)
            else:
                self.folders[parts[0]].folders.append(parts[1])




 # <link rel="stylesheet" href="_static/pygments.css" type="text/css">
 #    <script type="text/javascript">
 #    </script>
 #    <script type="text/javascript" src="_static/jquery.js"></script>

    def html(self):
        """create HTML"""
        template = jinja_env.get_template("home.html")
        return template.render(project=self)




if __name__ == "__main__":
    jinja_env = jinja2.Environment(
        loader=jinja2.PackageLoader('regurgitator.project', 'templates'),
        undefined=jinja2.StrictUndefined,
        trim_blocks=True)

    proj = Project("/home/eduardo/src/pyregurgitator")
    proj.load_project_files()
    print proj.folders.keys()
    print proj.folders['']
    print proj.folders[''].dump()
    print
    print proj.html()
