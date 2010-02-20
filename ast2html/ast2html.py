import myast as ast


def file2ast(file_name):
    fp = open(file_name, 'r')
    text = fp.read()
    fp.close()
    return ast.parse(text, file_name)


class AstNode(object):
    """friendly AST class"""

    class AstField(object):
        pass

    class TypeField(AstField):
        def __init__(self, value):
            self._value = value
        def to_text(self):
            return repr(self._value)
        def to_html(self):
            return repr(self._value)

    class NodeField(AstField):
        def __init__(self, value):
            self._value = AstNode(value)
        def to_text(self):
            return self._value.to_text()
        def to_html(self):
            return self._value.to_html()

    class ListField(AstField):
        def __init__(self, value):
            self._value = [AstNode(n) for n in value]
        def to_text(self):
            return "[%s]" % ", ".join((n.to_text() for n in self._value))
        def to_html(self):
            return "".join((n.to_html() for n in self._value))

    def __init__(self, node):
        self.class_ = node.__class__.__name__
        self.attrs = [(name, getattr(node, name)) for name in node._attributes]
        self.fields = {}
        for name in node._fields:
            value = getattr(node, name)
            if isinstance(value, ast.AST):
                self.fields[name] = self.NodeField(value)
            elif isinstance(value, list):
                self.fields[name] = self.ListField(value)
            else:
                self.fields[name] = self.TypeField(value)

    def to_text(self):
        attrs = ["%s=%s" % (k, v) for k,v in self.attrs]
        fields = ["%s=%s" % (k, v.to_text()) for k,v in self.fields.iteritems()]
        return "%s(%s)" % (self.class_, ", ".join(attrs + fields))

    def to_html(self):
        attrs = ("%s=%s" % (k, v) for k,v in self.attrs)
        field_t = "<div> %s => %s </div>"
        fields = (field_t % (k, v.to_html()) for k,v in self.fields.iteritems())
        node_t = "<div>%s (%s)<div>%s</div></div>"
        return node_t % (self.class_, ", ".join(attrs), "\n".join(fields))


if __name__ == "__main__":
    ct = file2ast('sample.py')
    tree = AstNode(ct)

    #
    #print tree.to_text()
    #print "----------------"
    #print ast.dump(ct, include_attributes=True)


    print '<html><body>'
    print tree.to_html()
    print '</body></html>'

