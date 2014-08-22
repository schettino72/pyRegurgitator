"""super pretty print of python source-code's AST"""

import platform
import ast
import json

from regurgitator.ast_util import file2ast


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

    def to_text(self):
        """dumps node info in plain text
        @returns string
        """
        attrs = ["%s=%s" % (k, v) for k,v in self.attrs]
        fields = ["%s=%s" % (k, v.to_text()) for k,v in self.fields.items()]
        return "%s(%s)" % (self.class_, ", ".join(attrs + fields))


    def to_html(self):
        """dumps node in HTML
        @returns string
        """
        class_info = MAP[self.class_]
        category = class_info['category']
        attrs = ("%s" % v for k,v in self.attrs)

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


        # build HTML
        n_head = ('<div class="%s node_tbl"><table><th colspan="10">' +
                  '<span class="node_type">%s</span> ' +
                  '<span class="att">(%s)</span></th>')
        n_sourcecode = '<tr class="code"><td colspan="10"><pre>%s: %s</pre></td></tr>'
        n_stmts_head = '</table><table>'
        n_stmts = '<tr><td class="field_name">%s</td><td>%s</td></tr>'
        n_close = '</table><div>'

        fields_html = []
        for field_name in class_info['order']:
            field_html = self.fields[field_name].to_html()
            fields_html.append(n_stmts % (field_name, field_html))

        html = n_head % (category , self.class_, ", ".join(attrs))
        if category == 'stmt':
            for line_num in sorted(self.line_nums):
                html += n_sourcecode % (line_num, self.lines[line_num - 1])
        html += n_stmts_head + "\n".join(fields_html)
        html += n_close
        return html

    def to_map(self):
        items = []
        for f in self.fields.values():
            items.extend(f.to_map())
        return items



#####################################33



def file2lines(file_name):
    """get list of lines from file_name"""
    fp = open(file_name, 'r')
    lines = fp.readlines()
    fp.close()
    return lines


def ast2txt(filename):
    """dump file as plain text (same output as ast.dump)"""
    ct = file2ast(filename)
    lines = file2lines(filename)
    tree = AstNode(ct, '', lines, None)

    print((tree.to_text()))
    #print "----------------"
    #print ast.dump(ct, include_attributes=True)



def ast2map(filename):
    """display variable path to node"""
    ct = file2ast(filename)
    lines = file2lines(filename)
    tree = AstNode(ct, '', lines, None)

    # map
    for x in tree.to_map():
        print(x)


def ast2html(filename):
    """pretty print ast in HTML"""
    ct = file2ast(filename)
    lines = file2lines(filename)
    tree = AstNode(ct, '', lines, None)

    style = """
* {font-size:small;}
.att{font-size:x-small;}
.node_tbl{border: 1px solid #66B;}
.node_tbl th{text-align:left;}
.node_tbl td{vertical-align:top;}
.stmt{border-top: 2px solid #ff8800;}
.mod{border: hidden;}
.field_list{border: 2px solid #eef;}
.field_name{background-color:#eef;}
.node_type{background-color:#99B;}
.final{background-color:#A88;}
.code{background-color:#ff8800;}
pre{font-size:13px;margin-bottom:0;}
"""
    print('<html><head><style type="text/css">%s</style></head>' % style)
    print('<body><h4>%s</h4>' % filename)
    print(tree.to_html())
    print('</body></html>')


if __name__ == "__main__":
    import sys
    filename = sys.argv[1]
    #ast2txt(filename)
    #ast2map(filename)
    ast2html(filename)
