""" PY -> XML -> PY checker
convert all files from cpython/Lib to xml and back to python
"""

import pathlib

PATH = '/home/eduardo/work/third_party/cpython/Lib'

def task_regurgitate():
    """generate HTML for AST of sample modules"""
    for sample in pathlib.Path(PATH).glob('**/*.py'):
        orig_py = str(sample)
        rel_path = str(sample.relative_to(PATH))

        xml = "_output/%s.xml" % rel_path
        yield {
            'basename': 'py2xml',
            'name': rel_path,
            'actions':[
                "mkdir -p {}".format(pathlib.Path(xml).parent),
                "py2xml {} > {}".format(orig_py, xml)],
            'file_dep': ['pyreg/py2xml.py', orig_py],
            'targets': [xml]
            }

        gen_py = "_output/%s" % rel_path
        yield {
            'basename': 'xml2py',
            'name': rel_path,
            'actions':["py2xml --reverse {} > {}".format(xml, gen_py)],
            'file_dep': [xml],
            'targets': [gen_py]
            }

        yield {
            'basename': 'roundtrip',
            'name': rel_path,
            'actions':['diff {} {}'.format(orig_py, gen_py)],
            'file_dep': [orig_py, gen_py],
            }
