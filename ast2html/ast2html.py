import myast as ast


MAP = {'Assert':
           {'category':'stmt',
            'order':('test','msg')},
       'Assign':
           {'category':'stmt',
            'order':('targets','value')},
       'AugAssign':
           {'category':'stmt',
            'order':('target','op','value')},
       'Break':
           {'category':'stmt'},
       'ClassDef':
           {'category':'stmt',
            'order':('name','bases','decorator_list')},
       'Continue':
           {'category':'stmt'},
       'Delete':
           {'category':'stmt'},
       'Exec':
           {'category':'stmt',
            'order':('locals','globals')},
       'Expr':
           {'category':'stmt'},
       'For':
           {'category':'stmt',
            'order':('target','iter')},
       'FunctionDef':
           {'category':'stmt',
            'order':('name','args','decorator_list')},
       'Global':
           {'category':'stmt'},
       'If':
           {'category':'stmt'},
       'Import':
           {'category':'stmt'},
       'ImportFrom':
           {'category':'stmt',
            'order':('module', 'names', 'level')},
       'Pass':
           {'category':'stmt'},
       'Print':
           {'category':'stmt',
            'order':('values','dest','nl')},
       'Raise':
           {'category':'stmt',
            'order':('inst','type','tback')},
       'Return':
           {'category':'stmt'},
       'TryExcept':
           {'category':'stmt'},
       'TryFinally':
           {'category':'stmt'},
       'While':
           {'category':'stmt'},
       'With':
           {'category':'stmt',
            'order':('context_expr','optional_vars')},

       'Module':
           {'category':'mod'},

       # 21
       'alias':
           {'order':('name','asname')},
       'arguments':
           {'order':('args', 'defaults','vararg','kwarg')},
       'Attribute':
           {'order':('value','attr','ctx')},
       'BinOp':
           {'order':('op','left','right')},
       'BoolOp':
           {'order':('op','values')},
       'Call':
           {'order':('func','args','keywords','starargs','kwargs')},
       'Compare':
           {'order':('ops','left','comparators')},
       'comprehension':
           {'order':('target','iter','ifs')},
       'Dict':
           {'order':('keys','values')},
       'excepthandler':
           {'order':('type','name')},
       'GeneratorExp':
           {'order':('elt', 'generators')},
       'keyword':
           {'order':('arg','value')},
       'List':
           {'order':('elts','ctx')},
       'ListComp':
           {'order':('elt', 'generators')},
       'Name':
           {'order':('id','ctx')},
       'Slice':
           {'order':('lower','upper','step')},
       'Subscript':
           {'order':('value','slice','ctx')},
       'Tuple':
           {'order':('elts','ctx')},
       'UnaryOp':
           {'order':('op','operand')},
       }


class AstNode(object):
    """friendly AST class

    @ivar node: stdlib AST node
    @ivar path: python variable's "path" to this node
    @ivar lines: node location on file
    @ivar class_: AST type
    @ivar attrs
    @ivar fields
    """

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
        def __init__(self, value, path, lines):
            self._value = AstNode(value, path, lines)
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
        def __init__(self, value, path, lines):
            self._value = [AstNode(n, "%s[%d]" % (path,i), lines) for i,n in enumerate(value)]
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


    def __init__(self, node, path, lines):
        self.node = node
        self.path = path
        self.lines = lines
        self.class_ = node.__class__.__name__
        self.attrs = [(name, getattr(node, name)) for name in node._attributes]
        self.fields = {}
        for name in node._fields:
            value = getattr(node, name)
            f_path = "%s.%s" % (self.path, name)
            if isinstance(value, ast.AST):
                self.fields[name] = self.NodeField(value, f_path, lines)
            elif isinstance(value, list):
                self.fields[name] = self.ListField(value, f_path, lines)
            else:
                self.fields[name] = self.TypeField(value, f_path, lines)

    def to_text(self):
        """dumps node info in plain text
        @returns string
        """
        attrs = ["%s=%s" % (k, v) for k,v in self.attrs]
        fields = ["%s=%s" % (k, v.to_text()) for k,v in self.fields.iteritems()]
        return "%s(%s)" % (self.class_, ", ".join(attrs + fields))

    def to_html(self):
        """dumps node in HTML
        @returns string
        """
        class_info = MAP.get(self.class_, {})
        category = class_info.get('category', "")
        attrs = ("%s" % v for k,v in self.attrs)

        # divide fields into 2 groups: stmt_list & non_stmt
        stmt_list = {}
        non_stmt = {}
        for k,v in self.fields.iteritems():
            if k in ('body', 'handlers', 'orelse', 'finalbody'):
                stmt_list[k] = v
            else:
                non_stmt[k] = v

        # build HTML
        n_head = ('<div class="%s node_tbl"><table><th colspan="10">' +
                  '<span class="node_type">%s</span> ' +
                  '<span class="att">(%s)</span></th>')
        n_sourcecode = '<tr class="code"><td colspan="10">%s: %s</td></tr>'
        n_ns_head = '<tr class="field_name"><td>%s</td></tr>'
        n_ns_body = '<tr><td>%s</td></tr>'
        n_stmts_head = '</table><table>'
        n_stmts = '<tr><td class="field_name">%s</td><td>%s</td></tr>'
        n_close = '</table><div>'

        field_names = [k for k in class_info.get('order', non_stmt.keys())]
        fields = [non_stmt[v].to_html() for v in field_names]
        # sorted because by lucky correct order is the same as alphabetical order
        stmts = [n_stmts% (k,v.to_html()) for k,v in sorted(stmt_list.iteritems())]

        html = n_head % (category , self.class_, ", ".join(attrs))
        if category == 'stmt':
            line_num = self.attrs[0][1]
            html += n_sourcecode % (line_num, self.lines[line_num - 1])
        html += n_ns_head % '</td>\n<td>'.join(field_names)
        html += n_ns_body % "</td>\n<td>".join(fields)
        html += n_stmts_head + "\n".join(stmts)
        html += n_close
        return html

    def to_map(self):
        items = []
        for f in self.fields.itervalues():
            items.extend(f.to_map())
        return items



#####################################33



def file2ast(file_name):
    """get ast-tree from file_name"""
    fp = open(file_name, 'r')
    text = fp.read()
    fp.close()
    return ast.parse(text, file_name)

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
    tree = AstNode(ct, '', lines)

    print tree.to_text()
    #print "----------------"
    #print ast.dump(ct, include_attributes=True)



def ast2map(filename):
    """display variable path to node"""
    ct = file2ast(filename)
    lines = file2lines(filename)
    tree = AstNode(ct, '', lines)

    # map
    for x in tree.to_map():
        print x


def ast2html(filename):
    """pretty print ast in HTML"""
    ct = file2ast(filename)
    lines = file2lines(filename)
    tree = AstNode(ct, '', lines)

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
"""
    print '<html><head><style type="text/css">%s</style></head>' % style
    print '<body><h4>%s</h4>' % filename
    print tree.to_html()
    print '</body></html>'


if __name__ == "__main__":
    import sys
    filename = sys.argv[1]
    #ast2txt(filename)
    #ast2map(filename)
    ast2html(filename)
