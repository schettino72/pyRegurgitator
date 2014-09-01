"""asdl2html - generate HTML file from asdl

This was coded only to be able to convert python's ASDL.
I have not studied ASDL specification so the parsing is probably incomplete!
It uses a quick & dirty (inneficient and naive) parsing, but it did the job :)

Python code is represented as a `tree`.
Each `node` of the tree is an instance of a node `Type`.
Each type belongs to a Category.
Each Type define `attributes` and `fields`.
Attributes describe which properties a node of that type has.
Fields describe the quantity and the category of child nodes.
"""

import json
import argparse

import jinja2



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

        # first line contains list of built-in types
        for name in asdl_lines[0].split(','):
            type_name = name.split(' ')[-1]
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
            # might be named or not.
            # If not named use cat_name as type_name.
            type_name = types[0].split('(')[0].strip() or cat_name
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

class ASDL2JSON(ASDL):
    """output ASDL in JSON format"""
    def render(self):
        types = {}
        for asdl_type in self.types.values():
            types[asdl_type.name] = self.type_dict(asdl_type)
        print(json.dumps(types, sort_keys=True, indent=4))

    @staticmethod
    def type_dict(asdl_type):
        order = []
        fields = {}
        for f in asdl_type.fields:
            order.append(f.name)
            fields[f.name] = {'cat':f.cat_name, 'q':f.qualifier}

        return {
            'category': asdl_type.cat_name,
            'order': order,
            'fields': fields,
            }


class ASDL2HTML(ASDL):
    """extend ASDL with methods to generate a HTML page"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.css = {} # map category to a CSS color
        self.jinja_env = jinja2.Environment(
            loader=jinja2.PackageLoader('pyreg', 'templates'),
            undefined=jinja2.StrictUndefined,
            trim_blocks=True)

        # divide categories into groups
        self.builtin_types = []
        self.product_types = [] # the name "product" comes from ASDL spec
        self.sum_cats = []
        for cat in self.cats.values():
            if cat.cat_name in ('mod', 'stmt', 'expr'):
                continue
            if cat.builtin:
                self.builtin_types.append(cat.types[0])
            elif len(cat.types) == 1:
                self.product_types.append(cat.types[0])
            else:
                self.sum_cats.append(cat.cat_name)
        self.product_types.sort()
        self.builtin_types.sort()
        self.sum_cats.sort()


        palette_soft = ['#CFD0D2', '#E9D4A7', '#C1D18A', '#B296C7',
                       '#55BEED', '#F384AE', '#F1753F']
        palette_strong = ['#FFE617', '#E8272F', '#E5185D',
                          '#5F3577', '#238ACC', '#143B86', '#799155',
                          '#09811C', '#C05C20', '#474D4D',
                          '#003F2E', '#FDB717', '#EF4638']
        palette_all = palette_soft + palette_strong

        # set color for builtins
        for cat_name in self.builtin_types:
            rules = '{{background-color:{}; border: 2px solid black;}}'
            self.css[cat_name] = rules.format(palette_soft.pop())

        # all categories that have a sigle type but are not built-ins
        # set color for builtins
        for cat_name in self.product_types + self.sum_cats:
            rules = '{{background-color:{};}}'
            self.css[cat_name] = rules.format(palette_all.pop())


    def get_group(self, name):
        """get a group of types to be displayed together in the HTML"""
        if name == 'builtin':
            return '', self.builtin_types
        if name == 'product_types':
            return '', self.product_types
        cat = self.cats[name]
        return cat.cat_name, cat.types


    def render(self):
        template = self.jinja_env.get_template("asdl.html")
        cols = {1: ["mod", "stmt", "expr"],
                2: self.sum_cats + ["product_types", "builtin"]}
        print(template.render(asdl=self, category_colors=self.css,
                              columns=cols))



def asdl_view(args=None):
    """command line program to convert ASDL into HTML, JSON"""
    parser = argparse.ArgumentParser(description='ASDL viewer')
    parser.add_argument(
        '-f', '--format', dest='format', metavar='FORMAT',
        choices=('html', 'json'), default='html',
        help='output format one of [%(choices)s], default=%(default)s')
    parser.add_argument(
        'asdl_file', metavar='ASDL', nargs=1,
        help='ASDL file')

    args = parser.parse_args(args)
    if args.format == 'html':
        ASDL2HTML(args.asdl_file[0]).render()
    elif args.format == 'json':
        ASDL2JSON(args.asdl_file[0]).render()


if __name__ == "__main__":
    asdl_view()
