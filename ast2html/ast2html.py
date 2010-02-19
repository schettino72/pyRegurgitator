import myast as ast


def file2ast(file_name):
    fp = open(file_name, 'r')
    text = fp.read()
    fp.close()
    return ast.parse(text, file_name)


def get_ast_data(node):
    assert isinstance(node, ast.AST)
    data = {}
    data['class'] = node.__class__.__name__
    data['attributes'] = list((name, getattr(node, name)) for name in node._attributes)
    data['single'] = [] # node
    data['childs'] = [] # *node
    data['terminal'] = [] # type
    for field_name in node._fields:
        field = getattr(node, field_name)
        if isinstance(field, ast.AST):
            data['single'].append([field_name, get_ast_data(field)])
        elif isinstance(field, list):
            node_list = [get_ast_data(n) for n in field]
            data['childs'].append([field_name, node_list])
        else:
            data['terminal'].append((field_name, repr(field)))
    return data


def node2txt(node):
    def print_node(d):
        # expand child nodes
        for ch in d['childs']:
            ch[1] = "[%s]" % ", ".join((print_node(n) for n in ch[1]))
        for si in d['single']:
            si[1] = print_node(si[1])
        all = d['attributes'] + d['terminal'] + d['single'] + d['childs']
        content = " ,".join(("%s=%s" % (a[0],a[1]) for a in all))
        return "%s(%s)" % (d['class'], content)
    data = get_ast_data(node)
    return print_node(data)


def node2html(node):
    def print_node(d):
        for ch in d['childs']:
            ch[1] = "\n".join((print_node(n) for n in ch[1]))
        for si in d['single']:
            si[1] = print_node(si[1])
        all = d['terminal'] + d['single'] + d['childs']
        nh = "<div> %s => %s </div>"
        att = ", ".join(("%s=%s" % (a[0],a[1]) for a in d['attributes']))
        content = "\n".join((nh % (a[0],a[1]) for a in all))
        return "<div>%s (%s)<div>%s</div></div>" % (d['class'], att, content)
    data = get_ast_data(node)
    return print_node(data)


if __name__ == "__main__":
    ct = file2ast('sample.py')
    #print node2txt(ct)
    print '<html><body>'
    print node2html(ct)
    print '</body></html>'

