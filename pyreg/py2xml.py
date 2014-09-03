
import argparse
from tokenize import tokenize
import xml.etree.ElementTree as ET


from .astview import AstNode


class AstNodeX(AstNode):
    """add capability to AstNode be convert to XML"""

    def ff(self, fields):
        """return xml string from list of child nodes"""
        ele = ET.Element(self.class_)
        ele.extend(fields)
        return ele

    def to_xml(self):
        # apply converter based on node class_
        converter = getattr(self, 'c_'+self.class_, None)
        if converter:
            return converter()

        # default converter
        class_info = self.MAP[self.class_]
        field_nodes = []
        for field_name in class_info['order']:
            ele = ET.Element(field_name)
            field = self.fields[field_name]
            ele.extend(field.to_xml())
            field_nodes.append(ele)
        return self.ff(field_nodes)

    def c_Expr(self):
        return self.ff([self.fields['value'].to_xml()])

    def c_Assign(self):
        targets = ET.Element('targets')
        targets.extend(self.fields['targets'].to_xml())
        equal = ET.Element('AssignOp')
        equal.text= ' = '
        return self.ff([
                targets,
                equal,
                self.fields['value'].to_xml(),
                ])


    def c_Name(self):
        ele = ET.Element('Name')
        ele.set('name', self.fields['id'].value)
        ele.set('ctx', self.fields['ctx'].value.class_)
        ele.text = self.fields['id'].value
        return ele

    def c_Num(self):
        ele = ET.Element('Num')
        ele.text = str(self.fields['n'].value)
        return ele

    def c_Str(self):
        tmpl = "<Str>{delimiter}{val}{delimiter}</Str>"
        # FIXME why sometimes the col_offset is -1 with line to the end of
        # the string ? to indicate a docstring
        if self.attrs[1][1] == -1:
            delimiter = "'''"
        else:
            token = self.tokens.find(self.attrs[0][1], self.attrs[1][1])
            delimiter = token.string[0]
            # check for triple-quote
            if token.string[0] == token.string[1]:
                delimiter *= 3
        return tmpl.format(delimiter=delimiter, val=self.fields['s'].value)

    def c_Add(self):
        ele = ET.Element('Add')
        ele.text = ' + '
        return ele

    def c_BinOp(self):
        return self.ff([
                self.fields['left'].to_xml(),
                self.fields['op'].to_xml(),
                self.fields['right'].to_xml(),
                ])


class SrcToken:
    """helper to read tokenized python source"""
    def __init__(self, fp):
        self.pos = 0 # current position of analised tokens
        self.tokens = list(tokenize(fp.readline))

    # token is named tuple with field names:
    # type string start end line exact_type
    def find(self, line, col):
        while True:
            token = self.tokens[self.pos]
            #print(self.pos, line, col, token.start)
            if token.start[0] == line and token.start[1] == col:
                return token
            self.pos += 1


def py2xml(filename):
    """convert ast to srcML"""
    AstNodeX.load_map()
    tree = AstNodeX.tree(filename)
    with open(filename, 'rb') as fp:
        AstNodeX.tokens = SrcToken(fp)
    return ET.tostring(tree.to_xml(), encoding='unicode')


def xml2py(xml):
    """convert XML back to python

    To convert back just get all text from all nodes.
    """
    root = ET.fromstring(xml)
    return ET.tostring(root, encoding='unicode', method='text')



def main(args=None):
    """command line program for py2xml"""
    description = """convert python module to XML representation"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        'py_file', metavar='MODULE', nargs=1,
        help='python module')

    args = parser.parse_args(args)
    print(py2xml(args.py_file[0]))

if __name__ == "__main__":
    main()
