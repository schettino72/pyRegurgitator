
import argparse
from tokenize import tokenize
import token as Token
import xml.etree.ElementTree as ET
from xml.dom.minidom import getDOMImplementation
import logging as log

from .astview import AstNode


#log.basicConfig(level=log.DEBUG)


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


    ###########################################################
    # Expr
    ###########################################################

    def maybe_par_expr(self, parent, ast_node):
        """deal with optional "()" around an expression"""
        have_parenthesis = False

        # Figure out if expression has parenthis or not.
        # assume multiline string expressions wont be wrapped in ()
        if ast_node.column != -1 and ast_node.class_ != 'Tuple':
            token = self.tokens.find(self.line, self.column)
            if token.exact_type == Token.LPAR:
                have_parenthesis = True
            else:
                # if an expr has extra parameters sometimes the start
                # column does not include the parenthesis, so here
                # we also check the previous token
                token = self.tokens.previous()
                if token.exact_type == Token.LPAR:
                    have_parenthesis = True

        # add left parenthesis.
        if have_parenthesis:
            start_token = self.tokens.pos
            par_count = 0
            while self.tokens.current().exact_type == Token.LPAR:
                par_count += 1
                self.tokens.next()
            text = self.tokens.previous_text(start_exact_type=Token.LPAR)
            parent.appendChild(DOM.createTextNode(text))

        # add the expr node itself
        parent.appendChild(ast_node.to_xml())

        # add the right parenthesis
        if have_parenthesis:
            self.tokens.find_close_par(start_token)
            self.tokens.next()
            text = self.tokens.previous_text(
                max_start=par_count,
                end_exact_type=Token.RPAR, end_space=False)
            print(repr(text))
            parent.appendChild(DOM.createTextNode(text))


    def c_Expr(self):
        ele = Element('Expr')
        self.maybe_par_expr(ele, self.fields['value'].value)
        return ele

    ###########################################################
    # expr
    ###########################################################

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
                self.tokens.pos -= 1
                break

            # check if next string is on a different line
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


    def c_Name(self):
        ele = Element('Name', text=self.fields['id'].value)
        ele.setAttribute('name', self.fields['id'].value)
        ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        return ele


    def c_BinOp(self):
        op = self.fields['op'].value
        orig_pos = self.tokens.pos
        self.tokens.find(self.fields['right'].value.line,
                         self.fields['right'].value.column)
        op_text = self.tokens.previous_text(end_exact_type=Token.PLUS)
        self.tokens.pos = orig_pos
        ele = Element(self.class_)
        ele.appendChild(self.fields['left'].value.to_xml())
        ele.appendChild(Element(op.class_, text=op_text))
        self.fields['right'].value.maybe_par_expr(ele, self.fields['right'].value)
        return ele

    ###########################################################
    # stmt
    ###########################################################

    def c_Assign(self):
        targets = Element('targets', childs=self.fields['targets'].to_xml())
        equal = self._before_field('value')
        return Element(self.class_, childs= [
                targets,
                DOM.createTextNode(equal),
                self.fields['value'].to_xml(),
                ])



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
        #log.debug('NEXT %s %s', self.pos, self.list[self.pos])
        return self.list[self.pos]

    def previous(self):
        """return token given by self.pos"""
        self.pos -= 1
        return self.list[self.pos]

    def token_iter(self):
        yield self.current()
        while True:
            yield self.next()

    def find(self, line, col):
        """find token given line and column"""
        log.debug('find %s %s', line, col)
        for token in self.token_iter():
            if token.start[0] == line and token.start[1] == col:
                log.debug('FOUND %s', token)
                return token

    def find_string(self, line, col):
        """find string token with given position

        multiline strings return last line and column == -1
        """
        if col == -1:
            for token in self.token_iter():
                if token.end[0] == line:
                    return token
        else:
            return self.find(line, col)


    def find_close_par(self, start_pos):
        """token with closing parenthesis from current position"""
        self.pos = start_pos
        num_open = 0
        for token in self.token_iter():
            if token.type == Token.OP:
                if token.exact_type == Token.RPAR:
                    num_open -= 1
                elif token.exact_type == Token.LPAR:
                    num_open += 1
            if num_open == 0:
                return token


    def previous_text(self, end_pos=None,
                      start_exact_type=None, max_start=None,
                      end_exact_type=None, end_space=True):
        """get all text that preceeds a node.

         - includes spance, operators and delimiters
         - if `end_exact_type` is used go back and don't get
           text until one token after end_exact_type.
           This is used to handle extra "()" around AST expr nodes.
        """
        end_pos = end_pos if end_pos is not None else self.pos
        text = ''
        # Control if we are looking for starting end_pos,
        # once it is found, stop checking end_exact_type
        searching_end = end_exact_type is not None
        matched_start = 0
        while True:
            cur_col = self.list[end_pos].start[1]
            end_pos -= 1
            token = self.list[end_pos]
            if searching_end:
                if token.exact_type != end_exact_type:
                    continue
                else:
                    searching_end = False
                    self.pos = end_pos
                    if not end_space:
                        cur_col = token.end[1]
            spaces = ' ' * (cur_col - token.end[1])

            match = False
            if max_start and matched_start >= max_start:
                pass
            elif start_exact_type:
                if token.exact_type == start_exact_type:
                    match = True
                else:
                    # ignore leading spaces when matching for a start of
                    # an exact type
                    spaces = ''
            elif token.type == Token.OP:
                match = True

            if match:
                matched_start += 1
                text = token.string + spaces + text
            else:
                return spaces + text


def py2xml(filename):
    """convert ast to srcML"""
    AstNodeX.load_map()
    ast_root = AstNodeX.tree(filename)
    with open(filename, 'rb') as fp:
        AstNodeX.tokens = SrcToken(fp)
    root = ast_root.to_xml()
    return root.toxml()


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
