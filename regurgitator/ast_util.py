"""AST utility functions"""

from regurgitator import myast as ast

def file2ast(file_name):
    """get ast-tree from file_name"""
    fp = open(file_name, 'r')
    text = fp.read()
    fp.close()
    return ast.parse(text, file_name)

