"""super pretty print of python source-code's AST"""

import platform
import ast
import json
import argparse

import jinja2

from .ast_util import file2ast


# load ASDL based on python version
python_version = platform.python_version().split('.')
# FIXME harcoded version
# put json files inside package
with open('_output/python33.asdl.json') as fp:
    MAP = json.load(fp)


class AstField(object):
    """There are 3 basic kinds of AST fields
     * TypeField - contains a basic type (not an AST node/element)
     * NodeField - contains a single AST element
     * ListField - contains a list of AST elements
    """
    pass

class TypeField(AstField):
    def __init__(self, value, path, lines):
        self._value = value
        self.path = path
    def to_text(self):
        return repr(self._value)
    def to_html(self):
        if isinstance(self._value,str):
            #TODO escape HTML from docstrings
            str_value = repr(self._value.replace('\n', '\n<br/>'))
        else:
            str_value = repr(self._value)
        return '<span class="final">%s</span>' % str_value
    def to_map(self):
        return ["%s => %s" % (self.path, repr(self._value))]

class NodeField(AstField):
    def __init__(self, value, path, lines, parent):
        self._value = AstNode(value, path, lines, parent)
        self.path = path
    def to_text(self):
        return self._value.to_text()
    def to_html(self):
        return self._value.to_html()
    def to_map(self):
        ll = ["%s (%s)" % (self.path, self._value.node.__class__.__name__)]
        ll.extend(self._value.to_map())
        return ll

class ListField(AstField):
    def __init__(self, value, path, lines, parent):
        self._value = [AstNode(n, "%s[%d]" % (path,i), lines, parent) for i,n in enumerate(value)]
        self.path = path
    def to_text(self):
        return "[%s]" % ", ".join((n.to_text() for n in self._value))
    def to_html(self):
        t_head = '<table class="field_list">'
        t_body = "".join(("<tr><td>%s</td></tr>" % n.to_html() for n in self._value))
        t_foot = '</table>'
        return t_head + t_body + t_foot
    def to_map(self):
        ll = ["%s []" % self.path]
        for n in self._value:
            ll.append("%s (%s)" % (n.path, n.node.__class__.__name__))
            ll.extend(n.to_map())
        return ll




class AstNode(object):
    """friendly AST class

    @ivar node: stdlib AST node
    @ivar path: python variable's "path" to this node
    @ivar lines: node location on file
    @ivar class_: AST type
    @ivar attrs
    @ivar fields: dict of AstField
    """

    @staticmethod
    def tree(filename):
        """build whole AST from a module"""
        ct = file2ast(filename)
        with open(filename, 'r') as fp:
            lines = fp.readlines()
            return AstNode(ct, '', lines, None)


    def __init__(self, node, path, lines, parent):
        self.node = node
        self.path = path
        self.lines = lines
        self.parent = parent
        self.class_ = node.__class__.__name__
        self.line_nums = set()

        # normalize values when using python2.5
        # on python2.5 node might not have _attributes, ...
        if not hasattr(node, '_attributes'):
            node._attributes = []
        # ... _fields is None instead of []
        if node._fields is None:
            node._fields = []
        # end - python2.5

        self.attrs = [(name, getattr(node, name)) for name in node._attributes]
        self.fields = {}
        for name in node._fields: # _fields is a tuple of str
            value = getattr(node, name)
            f_path = "%s.%s" % (self.path, name)
            if isinstance(value, ast.AST):
                self.fields[name] = NodeField(value, f_path, lines, self)
            elif isinstance(value, list):
                self.fields[name] = ListField(value, f_path, lines, self)
            else:
                self.fields[name] = TypeField(value, f_path, lines)


    def to_html(self):
        """return HTML string for node
          - set line_nums of node
        """
        class_info = MAP[self.class_]
        category = class_info['category']

        # add line number of this node to the contatining statement
        if self.attrs:
            curent = self
            while True:
                if MAP[curent.class_]['category'] != "stmt":
                    if curent.parent:
                        curent = curent.parent
                        continue
                    else:
                        break
                else:
                    curent.line_nums.add(self.attrs[0][1])
                    break

        # special case for triple quotes multiple line string
        if category == 'stmt' and self.attrs and self.attrs[1][1] == -1:
            # start from last line
            triple_quote_line = self.attrs[0][1]
            # move up if line contains only terminating triple quotes
            if len(self.lines[triple_quote_line-1].strip()) == 3:
                triple_quote_line -= 1
                self.line_nums.add(triple_quote_line)
            # move up until it finds starting triple quotes
            while not self.lines[triple_quote_line-1].strip().startswith('"""'):
                triple_quote_line -= 1
                self.line_nums.add(triple_quote_line)

        attrs = ["%s" % v for k,v in self.attrs]
        return self.node_template.module.node(self, class_info, category, attrs)



    def to_text(self):
        """dumps node info in plain text
        @returns string
        """
        attrs = ["%s=%s" % (k, v) for k,v in self.attrs]
        fields = ["%s=%s" % (k, v.to_text()) for k,v in self.fields.items()]
        return "%s(%s)" % (self.class_, ", ".join(attrs + fields))

    def to_map(self):
        items = []
        for f in self.fields.values():
            items.extend(f.to_map())
        return items



#####################################33




def ast2html(filename, tree):
    """pretty print ast in HTML"""
    jinja_env = jinja2.Environment(
        loader=jinja2.PackageLoader('pyreg', 'templates'),
        undefined=jinja2.StrictUndefined,
        trim_blocks=True)
    template = jinja_env.get_template("ast.html")
    AstNode.node_template = jinja_env.get_template("ast_node.html")
    print(template.render(filename=filename, tree=tree))



def ast_view(args=None):
    """command line program to convert python module into AST data"""
    description = """
Super pretty-printer for python modules's AST(abstract syntax tree)."""

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-f', '--format', dest='format', metavar='FORMAT',
        choices=('html', 'map', 'txt'), default='html',
        help='output format one of [%(choices)s], default=%(default)s')
    parser.add_argument(
        'py_file', metavar='MODULE', nargs=1,
        help='python module')

    args = parser.parse_args(args)
    tree = AstNode.tree(args.py_file[0])
    if args.format == 'html':
        ast2html(args.py_file[0], tree)
    elif args.format == 'map':
        for x in tree.to_map():
            print(x)
    elif args.format == 'txt':
        print((tree.to_text()))


if __name__ == "__main__":
    ast_view()
