"""asdl2html - generate HTML file from asdl

This was coded only to be able to convert python's ASDL.
I have not studied ASDL specification so the parsing is probably incomplete!
It uses a quick & dirty (inneficient and naive) parsing, but it did the job :)
I did cheat making sure constructors are define in a single line.
"""

ASDL_TYPES = ['identifier', 'int', 'string', 'object', 'bool']
LANG_TYPES_STR = 'python_types'

class Param(object):
    """Node's Param"""
    def __init__(self, _type, name):
        self.type = _type.strip()
        self.name = name.strip()
        if self.type[-1] in "*?":
            self.name = self.type[-1] + self.name
            self.type = self.type[:-1]

class Node(object):
    def __init__(self, name, cluster, params):
        self.name = name
        self.cluster = cluster
        self.params = []
        for par in params:
            if not par:
                continue
            parts = par.strip().split(' ')
            self.params.append(Param(*parts))

class Cluster(object):
    def __init__(self, name, attributes):
        self.name = name
        self.attributes = attributes
        self.nodes = []



############### ASDL parsing

def get_braces_content(data):
    """extract data from within comma separated, round-braces string
    return list of strings
    """
    left_brace = data.split('(')
    if len(left_brace) > 1:
        return left_brace[1].split(')')[0].split(',')
    return []


def get_asdl_definitions(asdl_file_name):
    """Read an ASDL file and returns a list
    with definitions (just the unprocessed strings)
    """
    # 0 - read the file
    asdl_file = open(asdl_file_name, 'r')
    asdl = asdl_file.readlines()
    asdl_file.close()

    # 1 - remove comments
    asdl = [line.split('--')[0] for line in asdl]

    # 2 - get content part. Everything between {}. just handle one {}
    left_brace = "".join(asdl).split('{')
    assert len(left_brace) == 2
    right_brace = left_brace[1].split('}')
    assert len(right_brace) == 2
    content = right_brace[0]

    # 3 - break content into definitions
    definitions = []
    def_id = -1
    for line in content.splitlines(1):
        if not line.strip(): # ignore blank lines
            continue
        #print "--->", line
        if "=" in line:
            definitions.append('')
            def_id += 1
        definitions[def_id] += line

    return definitions



def get_asdl_nodes(definitions):
    """get nodes and clusters from asdl definitions
    returns pair of dicts (clusters, nodes)
    """
    clusters = {}
    nodes = {}

    # break left(name) and right(constructors) side of a definition
    for defi in definitions:
        # extract definition name
        _left, _right = defi.split('=')
        defi_name = _left.strip()
        right = '|' + _right # to identify constructors

        # read lines, extract constructors & attributes
        attrs = []
        constructors = []
        for full_line in right.splitlines():
            line = full_line.strip()
            if line[0] in '|':
                constructors.extend([c.strip() for c in line[1:].split('|')])
            elif line.strip().startswith('attributes'):
                attrs = get_braces_content(line)

        # if just one constructor, it is not a class but a type
        if len(constructors) == 1:
            if LANG_TYPES_STR not in clusters:
                clusters[LANG_TYPES_STR] = Cluster(LANG_TYPES_STR, [])
            nodes[defi_name] = Node(defi_name, LANG_TYPES_STR,
                                    get_braces_content(constructors[0]))
        # iterate over constructors
        else:
            clusters[defi_name] = Cluster(defi_name, attrs)
            for cons in constructors:
                name = cons.split('(')[0].strip()
                nodes[name] = Node(name, defi_name,
                                   get_braces_content(cons))
    return clusters, nodes



#
# HTML stuff
def node2html(node):
    class_ = node.cluster
    if class_ in ["basic_types", "python_types"]:
        class_ = node.name
    print(('<div class="node %s">' % class_))
    print(('<div class="class">%s</div>' % node.name))
    for param in node.params:
        print(('<span class="param %s">%s</span>' % (param.type, param.name)))
    print ('</div>')



def main(file_name):
    # get clusters and nodes from asdl files
    definitions = get_asdl_definitions(file_name)
    clusters, nodes = get_asdl_nodes(definitions)

    # add cluster with basic types
    clusters['basic_types'] = Cluster("basic_types", [])
    # add basic nodes
    nodes.update([(name, Node(name, "basic_types", [])) for name in ASDL_TYPES])


#     for c in clusters.itervalues():
#         print c.name
#     for n in nodes.itervalues():
#         print n.name, "\b",
#     print


    # calculate cluster nodes.
    for n in nodes.values():
        clusters[n.cluster].nodes.append(n)


    # HTML
    head = """
<style type="text/css">
body{
background-color:#b0c4de;
}

.mod{background-color:#555555;}
.stmt{background-color:#ff8800;}
.expr{background-color:#995522;}
.expr_context{background-color:#cc0000;}
.slice{background-color:#663322;}
.boolop{background-color:#ffcc99;}
.operator{background-color:#ff66ff;}
.unaryop{background-color:#ffff33}
.cmpop{background-color:ff6666}

.bool{background-color:#ffffff}
.identifier{background-color:cccccc}
.int{background-color:#888888}
.object{background-color:#555555}
.string{background-color:#333333}


.alias{background-color:#00CCff}
.arguments{background-color:#0099CC}
.comprehension{background-color:#009999}
.excepthandler{background-color:#009966}
.keyword{background-color:#006600}


.cluster{
clear: both;
}

.node{
border: 1px solid #90a4be;
margin: 2px;
float: left;
padding: 3px;
}

.param{
border:1px dashed black;
padding: 2px;
font-size:small;
}

.col1{
position: absolute;
width: 48%;
}

.col2{
position: absolute;
width: 48%;
left: 50%;
}

</style>
"""
    print(('<html><head>%s</head><body>' % head))

    cols = {1: ["mod", "stmt", "python_types", "basic_types"],
            2: ["expr", "slice", "expr_context", "operator",
                "boolop", "cmpop", "unaryop"],
            }
    for col in [1, 2]:
        print(('<div class="col%s">' % col))
        for clu_name in cols[col]:
            clu = clusters[clu_name]
            title = clu.name
            if title in ["basic_types", "python_types"]:
                title = ""
            print(('<div class="cluster %s"><span>%s</span><div>' %
                   (clu.name, title)))
            for n in sorted(clu.nodes, key=lambda x:x.name):
                node2html(n)
            print ('</div></div>')
        print ('</div>')


    print ("</body></html>")

if __name__ == "__main__":
    main('python.asdl')
