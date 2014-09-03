
import argparse
from tokenize import tokenize
import token as Token
import xml.etree.ElementTree as ET


from .astview import AstNode




class AstNodeX(AstNode):
    """add capability to AstNode be convert to XML"""

    def ff(self, fields):
        """return xml string from list of child nodes"""
        ele = ET.Element(self.class_)
        ele.extend(fields)
        return ele

    def _before_field(self, field_name):
        """return text before a field in the node"""
        field = self.fields[field_name]
        self.tokens.find(field.line(), field.column())
        return self.tokens.previous_text(self.tokens.pos)


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

    def c_Num(self):
        ele = ET.Element('Num')
        ele.text = str(self.fields['n'].value)
        return ele

    def c_Str(self):
        ele = ET.Element('Str')
        token = self.tokens.find_string(self.attrs[0][1], self.attrs[1][1])
        while True:
            ele_s = ET.Element('s')
            ele_s.text = token.string
            ele.append(ele_s)
            # check if next token is a string (implicit concatenation)
            self.tokens.pos += 1
            next_token = self.tokens.tokens[self.tokens.pos]
            if next_token.type != Token.STRING:
                break

            # check next string is on a different line
            prev_space = ''
            if token.end[0] != next_token.start[0]:
                prev_space = token.line[token.end[1]:]
            # add space before next string concatenated
            space = ET.Element('space')
            space.text = prev_space + self.tokens.previous_text(self.tokens.pos)
            ele.append(space)
            token = next_token
        return ele

    def c_Add(self):
        return ET.Element('Add')

    def c_BinOp(self):
        op = self.fields['op'].to_xml()
        op.text = self._before_field('right')
        return self.ff([self.fields['left'].to_xml(),
                op,
                self.fields['right'].to_xml(),
                ])

    def c_Assign(self):
        targets = ET.Element('targets')
        targets.extend(self.fields['targets'].to_xml())
        equal = ET.Element('delimiter')
        equal.text = self._before_field('value')
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

    def find_string(self, line, col):
        """find token with given position

        multiline strings return last line and column == -1
        """
        if col == -1:
            while True:
                token = self.tokens[self.pos]
                if token.end[0] == line:
                    return token
                self.pos += 1
        else:
            return self.find(line, col)

    def previous_text(self, end_pos):
        """get all text that preceeds a node.

         - includes spance, operators and delimiters
        """
        text = ''
        cur_col = self.tokens[end_pos].start[1]
        while True:
            end_pos -= 1
            token = self.tokens[end_pos]
            spaces = ' ' * (cur_col - token.end[1])
            text = spaces + text
            if token.type == Token.OP:
                text = token.string + text
            else:
                return text
            cur_col = token.start[1]


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



def main(args=None): # pragma: no cover
    """command line program for py2xml"""
    description = """convert python module to XML representation"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        'py_file', metavar='MODULE', nargs=1,
        help='python module')

    args = parser.parse_args(args)
    print(py2xml(args.py_file[0]))

if __name__ == "__main__": # pragma: no cover
    main()
