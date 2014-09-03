
import argparse
from tokenize import tokenize
import token as Token
import xml.etree.ElementTree as ET
from xml.dom.minidom import getDOMImplementation

from .astview import AstNode

impl = getDOMImplementation()
DOM = impl.createDocument(None, None, None)
def Element(tag_name, childs=None, text=None):
    ele = DOM.createElement(tag_name)
    if childs:
        for node in childs:
            ele.appendChild(node)
    if text:
        ele.appendChild(DOM.createTextNode(text))
    return ele


class AstNodeX(AstNode):
    """add capability to AstNode be convert to XML"""

    def _before_field(self, field_name):
        """return text before a field in the node"""
        field = self.fields[field_name]
        self.tokens.find(field.line(), field.column())
        return self.tokens.previous_text()


    def to_xml(self):
        # apply converter based on node class_
        converter = getattr(self, 'c_'+self.class_, None)
        if converter:
            return converter()

        # default converter
        class_info = self.MAP[self.class_]
        field_nodes = []
        for field_name in class_info['order']:
            field = self.fields[field_name]
            ele = Element(field_name, childs=field.to_xml())
            field_nodes.append(ele)
        return Element(self.class_, childs=field_nodes)


    def c_Expr(self):
        # parenthesis handling applies to all `expr` fields
        # not only to the `Expr` class
        ele = Element(self.class_)
        expr_value = self.fields['value'].value
        have_parenthesis = False
        # assume multiline string expressions wont be wrapped in ()
        if expr_value.column != -1 and expr_value.class_ != 'Tuple':
            token = self.tokens.find(self.line, self.column)
            have_parenthesis = token.type == Token.OP
        if have_parenthesis:
            start_token = self.tokens.pos
            while self.tokens.current().exact_type == Token.LPAR:
                self.tokens.next()
            ele.appendChild(DOM.createTextNode(self.tokens.previous_text()))
        ele.appendChild(expr_value.to_xml())
        if have_parenthesis:
            self.tokens.find_close_par(start_token)
            self.tokens.next()
            ele.appendChild(DOM.createTextNode(self.tokens.previous_text()))
        return ele

    def c_Num(self):
        return Element('Num', text=str(self.fields['n'].value))

    def c_Str(self):
        ele = Element('Str')
        token = self.tokens.find_string(self.attrs[0][1], self.attrs[1][1])
        while True:
            ele_s = Element('s', text=token.string)
            ele.appendChild(ele_s)
            # check if next token is a string (implicit concatenation)
            next_token = self.tokens.next()
            if next_token.type != Token.STRING:
                break

            # check next string is on a different line
            prev_space = ''
            if token.end[0] != next_token.start[0]:
                prev_space = token.line[token.end[1]:]
            # add space before next string concatenated
            space = DOM.createTextNode(
                prev_space + self.tokens.previous_text())
            ele.appendChild(space)
            token = next_token
        return ele

    def c_Tuple(self):
        ele = Element('Tuple')
        ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        for item in self.fields['elts'].value:
            self.tokens.find(item.line, item.column)
            text = self.tokens.previous_text()
            delimiter = DOM.createTextNode(text)
            ele.appendChild(delimiter)
            ele.appendChild(item.to_xml())
        next_token = self.tokens.next()
        text = (self.tokens.previous_text() +
                next_token.string)
        ele.appendChild(DOM.createTextNode(text))
        return ele

    def c_Add(self):
        return Element('Add')

    def c_BinOp(self):
        op = self.fields['op'].to_xml()
        op.appendChild(DOM.createTextNode(self._before_field('right')))
        return Element(self.class_, childs =[
                self.fields['left'].to_xml(),
                op,
                self.fields['right'].to_xml(),
                ])

    def c_Assign(self):
        targets = Element('targets', childs=self.fields['targets'].to_xml())
        equal = self._before_field('value')
        return Element(self.class_, childs= [
                targets,
                DOM.createTextNode(equal),
                self.fields['value'].to_xml(),
                ])

    def c_Name(self):
        ele = Element('Name', text=self.fields['id'].value)
        ele.setAttribute('name', self.fields['id'].value)
        ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        return ele



class SrcToken:
    """helper to read tokenized python source

    Token is named tuple with field names:
    type string start end line exact_type
    """
    def __init__(self, fp):
        self.pos = 0 # current position of analised tokens
        self.list = list(tokenize(fp.readline))

    def current(self):
        return self.list[self.pos]

    def next(self):
        """return token given by self.pos"""
        self.pos += 1
        return self.list[self.pos]

    def find(self, line, col):
        """find token given line and column"""
        while True:
            token = self.list[self.pos]
            #print(self.pos, line, col, token.start)
            if token.start[0] == line and token.start[1] == col:
                return token
            self.pos += 1

    def find_string(self, line, col):
        """find string token with given position

        multiline strings return last line and column == -1
        """
        if col == -1:
            while True:
                token = self.list[self.pos]
                if token.end[0] == line:
                    return token
                self.pos += 1
        else:
            return self.find(line, col)


    def find_close_par(self, start_pos):
        """token with closing parenthesis from current position"""
        self.pos = start_pos
        num_open = 0
        while True:
            token = self.list[self.pos]
            if token.type == Token.OP:
                if token.exact_type == Token.RPAR:
                    num_open -= 1
                elif token.exact_type == Token.LPAR:
                    num_open += 1
            if num_open == 0:
                return token
            self.pos += 1


    def previous_text(self, end_pos=None):
        """get all text that preceeds a node.

         - includes spance, operators and delimiters
        """
        end_pos = end_pos if end_pos is not None else self.pos
        text = ''
        cur_col = self.list[end_pos].start[1]
        while True:
            end_pos -= 1
            token = self.list[end_pos]
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
    ast_root = AstNodeX.tree(filename)
    with open(filename, 'rb') as fp:
        AstNodeX.tokens = SrcToken(fp)
    root = ast_root.to_xml()
    return root.toxml()
    #return ET.tostring(ast_root.to_xml(), encoding='unicode')


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
