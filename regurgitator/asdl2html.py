"""asdl2html - generate HTML file from asdl

This was coded only to be able to convert python's ASDL.
I have not studied ASDL specification so the parsing is probably incomplete!
It uses a quick & dirty (inneficient and naive) parsing, but it did the job :)

Python code is represented as a `tree`.
Each `node` of the tree is an instance of a node `Type`.
Each type belong a Category.
Each Type define `attributes` and `fields`.
Attributes describe which properties a node of that type has.
Fields describe the quantity and the category of child nodes.
"""

import sys

LANG_TYPES_STR = 'python_types'


class Field:
    """Type's Field

    qualifier represent the quantity of child nodes for this field
      * 0 to N
      ? 0 or 1
    """
    def __init__(self, name, cat_name):
        self.name = name.strip() # the field name
        # extract qualifier from cat_name string
        cat_name = cat_name.strip()
        if cat_name[-1] in "*?":
            self.qualifier = cat_name[-1]
            self.cat_name = cat_name[:-1]
        else:
            self.cat_name = cat_name
            self.qualifier = ''


class Type:
    """A node type in an AST"""
    def __init__(self, name, cat_name, fields, attributes):
        """:param str fields: unparsed field definition"""
        self.name = name
        self.cat_name = cat_name
        self.fields = [] # list of Field
        # atributes saved as string unparsed. currently not used
        self.attributes = attributes
        for par in fields:
            if not par:
                continue
            parts = par.strip().split(' ')
            self.fields.append(Field(parts[1], parts[0]))

    def __lt__(self, other):
        return self.name < other.name


class Category:
    """Category is an Abstract Type that may have more than derived Type"""
    def __init__(self, cat_name, types, builtin=False):
        self.cat_name = cat_name
        self.types = types # list os strings
        self.builtin = builtin


class ASDL:
    """parse an asdl file
    """
    def __init__(self, file_name):
        self.cats = {}
        self.types = {}

        # 0 - read the file
        with open(file_name, 'r') as asdl_file:
            asdl_lines = asdl_file.readlines()

        ASDL_TYPES = ['identifier', 'int', 'string', 'object', 'bool']
        for name in ASDL_TYPES:
            type_name = name
            self.cats[name] = Category(name, [type_name], builtin=True)
            self.types[type_name] = Type(type_name, name, '', '')

        # split content into a list of definitions
        definitions = self.get_asdl_definitions(asdl_lines)

        # prase and set self.clusters, self.types
        for definition in definitions:
            self.parse_definition(definition)


    @staticmethod
    def get_asdl_definitions(asdl_lines):
        """Read an ASDL file and returns a list
        with definitions (just the unprocessed strings)
        """
        # 1 - remove comments
        asdl_no_comments = [line.split('--')[0] for line in asdl_lines]

        # 2 - get content part. Everything between {}. just handle one {}
        left_brace = "".join(asdl_no_comments).split('{')
        assert len(left_brace) == 2
        right_brace = left_brace[1].split('}')
        assert len(right_brace) == 2
        content = right_brace[0]

        # 3 - break content into definitions
        # a definition is something like
        #
        # xxx = yyy
        #     | zzz
        #
        # a definition is over when another line with a `=` is found
        definitions = []
        current = None
        for line in content.splitlines(1):
            if not line.strip(): # ignore blank lines
                continue
            #print "--->", line
            if "=" in line:
                if current is not None:
                    definitions.append(current)
                current = ''
            current += line
        definitions.append(current)

        return definitions



    def parse_definition(self, defi):
        """parse a definition. A definition contains one Category and its types.
        """
        # break left(cat_name) and right(constructors) side of a definition
        # extract definition cat_name
        _left, _right = defi.split('=')
        cat_name = _left.strip()
        right_parts = _right.split('attributes')
        assert len(right_parts) < 3

        # get attributes - not all definitions contain attributes
        if len(right_parts) == 2:
            attrs = self.get_braces_content(right_parts[1])
        else:
            attrs = []

        # read lines, extract constructors & attributes
        types = [c.strip() for c in right_parts[0].split('|')]

        # if just one type in definition
        if len(types) == 1:
            # in the ASDL types from categories that have only one type
            # are not named.
            type_name = cat_name
            type_names = [type_name]
            field_list = self.get_braces_content(types[0])
            self.types[type_name] = Type(type_name, cat_name, field_list, attrs)
        # iterate over constructors
        else:
            type_names = []
            for cons in types: # for each constructor
                name = cons.split('(')[0].strip()
                type_names.append(name)
                field_list = self.get_braces_content(cons)
                self.types[name] = Type(name, cat_name, field_list, attrs)

        # create category
        self.cats[cat_name] = Category(cat_name, type_names)


    @staticmethod
    def get_braces_content(data):
        """extract data from within comma separated, round-braces string
        return list of strings

        >>> ASDL.get_braces_content('(a,b,c)')
        ['a', 'b', 'c']
        """
        left_brace = data.split('(')
        if len(left_brace) > 1:
            return left_brace[1].split(')')[0].split(',')
        return []




################################################################


class ASDL2HTML(ASDL):
    """extend ASDL with methods to generate a HTML page"""

    @staticmethod
    def render_type(ntype):
        class_ = ntype.cat_name
        print('<div class="type {}">'.format(class_))
        print('<div>{}</div>'.format(ntype.name))
        # render fields
        for field in ntype.fields:
            print('<span class="field {}">{}{}</span>'.format(
                    field.cat_name, field.qualifier, field.name))
        print('</div>')


    def get_builtin(self):
        items = []
        for c in self.cats.values():
            if c.builtin:
                items.append(c.types[0])
        return items

    def get_product_types(self):
        # all categories that have a sigle type but are not built-ins
        items = []
        for c in self.cats.values():
            if not c.builtin and len(c.types)==1:
                items.append(c.types[0])
        return items

    def get_group(self, name):
        if name == 'builtin':
            return '', self.get_builtin()
        if name == 'product_types':
            return '', self.get_product_types()
        cat = self.cats[name]
        return cat.cat_name, cat.types

    def render_body(self):
        cols = {1: ["mod", "stmt", "product_types", "builtin"],
                2: ["expr", "slice", "expr_context", "operator",
                    "boolop", "cmpop", "unaryop"],
                }

        for col in [1, 2]:
            print('<div class="col{}">'.format(col))
            for group in cols[col]:
                name, types = self.get_group(group)
                print(('<div class="category %s"><span>%s</span><div>' %
                       (name, name)))
                for ntype in sorted(types):
                    self.render_type(self.types[ntype])
                print ('</div></div>')
            print ('</div>')


    def render(self):
        print('<html><head>{}</head><body>'.format(HTML_HEAD))
        self.render_body()
        print ("</body></html>")


# HTML
HTML_HEAD = """
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


.category{
clear: both;
}

.type{
border: 1px solid #90a4be;
margin: 2px;
float: left;
padding: 3px;
}

.field{
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




if __name__ == "__main__":
    ASDL2HTML(sys.argv[1]).render()
