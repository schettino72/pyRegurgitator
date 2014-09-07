
import argparse
from tokenize import tokenize
import tokenize as Token
import xml.etree.ElementTree as ET
from xml.dom.minidom import getDOMImplementation
import logging as log

from .astview import AstNode


#log.basicConfig(level=log.DEBUG)


impl = getDOMImplementation()
DOM = impl.createDocument(None, None, None)
DOM.Text = DOM.createTextNode
def Element(tag_name, childs=None, text=None):
    ele = DOM.createElement(tag_name)
    if childs:
        for node in childs:
            ele.appendChild(node)
    if text:
        ele.appendChild(DOM.Text(text))
    return ele


class AstNodeX(AstNode):
    """add capability to AstNode be convert to XML"""

    def _before_field(self, field_name):
        """return text before a field in the node"""
        field = self.fields[field_name]
        self.tokens.find(field.line(), field.column())
        return self.tokens.previous_text()


    def to_xml(self, parent=None):
        # hack for root node
        if parent == None:
            parent = Element(self.class_)

        # apply converter based on node class_
        converter = getattr(self, 'c_' + self.class_, None)
        if converter:
            try:
                return converter(parent)
            except Exception:
                print('Error on {}'.format(self))
                raise

        log.warn("**** unimplemented coverter %s", self.class_)
        # default converter
        class_info = self.MAP[self.class_]
        for field_name in class_info['order']:
            field = self.fields[field_name]
            if isinstance(field.value, list):
                for v in field.value:
                    v.to_xml(parent)
            else:
                field.value.to_xml(parent)
        return parent # XXX should not return anything


    ###########################################################
    # Expr
    ###########################################################

    def maybe_par_expr(self, parent, ast_node):
        """deal with optional "()" around an expression"""
        have_parenthesis = False

        # get token
        token = self.tokens.find(self.line, self.column)

        # Figure out if expression has parenthis or not.
        # assume tuples wont have it
        if ast_node.column != -1 and ast_node.class_ != 'Tuple':
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
            text = self.tokens.previous_text(
                start_exact_type=Token.LPAR)
            parent.appendChild(DOM.Text(text))

        # add the expr node itself
        ast_node.to_xml(parent)

        # add the right parenthesis
        if have_parenthesis:
            self.tokens.find_close_par(start_token)
            self.tokens.next()
            text = self.tokens.previous_text(
                max_start=par_count,
                end_exact_type=Token.RPAR, end_space=False)
            parent.appendChild(DOM.Text(text))
            self.tokens.start_limit = self.tokens.pos


    def c_Expr(self, parent):
        self.prepend_previous(parent)
        ele = Element('Expr')
        self.maybe_par_expr(ele, self.fields['value'].value)
        parent.appendChild(ele)


    ###########################################################
    # expr
    ###########################################################

    def c_Num(self, parent):
        parent.appendChild(Element('Num', text=str(self.fields['n'].value)))

    def c_Str(self, parent):
        ele = Element('Str')
        token = self.tokens.find(self.attrs[0][1], self.attrs[1][1])
        while True:
            ele_s = Element('s', text=token.string)
            ele.appendChild(ele_s)
            # check if next token is a string (implicit concatenation)
            next_token = self.tokens.next()
            if next_token.type != Token.STRING:
                self.tokens.pos -= 1
                break
            # add space before next string concatenated
            ele.appendChild(DOM.Text(self.tokens.previous_text()))
            token = next_token
        parent.appendChild(ele)


    def c_Tuple(self, parent):
        ele = Element('Tuple')
        ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        for item in self.fields['elts'].value:
            self.tokens.find(item.line, item.column)
            text = self.tokens.previous_text()
            delimiter = DOM.Text(text)
            ele.appendChild(delimiter)
            item.to_xml(ele)
        next_token = self.tokens.next()
        text = (self.tokens.previous_text() +
                next_token.string)
        ele.appendChild(DOM.Text(text))
        self.tokens.start_limit = self.tokens.pos
        parent.appendChild(ele)


    def c_Name(self, parent):
        ele = Element('Name', text=self.fields['id'].value)
        ele.setAttribute('name', self.fields['id'].value)
        ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        parent.appendChild(ele)


    def c_BinOp(self, parent):
        op = self.fields['op'].value
        orig_pos = self.tokens.pos
        self.tokens.find(self.fields['right'].value.line,
                         self.fields['right'].value.column)
        op_text = self.tokens.previous_text(end_exact_type=Token.PLUS)
        self.tokens.pos = orig_pos
        ele = Element(self.class_)
        self.fields['left'].value.to_xml(ele)
        ele.appendChild(Element(op.class_, text=op_text))
        self.fields['right'].value.maybe_par_expr(
            ele, self.fields['right'].value)
        parent.appendChild(ele)


    def c_Call(self, parent):
        ele = Element('Call')

        # func
        ele_func = Element('func')
        self.fields['func'].value.to_xml(ele_func)
        ele.appendChild(ele_func)

        # current parent, keeps track on where previous_text should be inserted
        cur_parent = ele

        # args
        args = self.fields['args'].value
        if args:
            ele_args = Element('args')
            for arg in self.fields['args'].value:
                arg.prepend_previous(cur_parent)
                arg.to_xml(ele_args)
                cur_parent = ele_args
            ele.appendChild(ele_args)

        # close parent
        self.tokens.next(exact_type=Token.RPAR)
        self.tokens.start_limit = self.tokens.pos
        ele.appendChild(DOM.Text(self.tokens.previous_text() + ')'))

        parent.appendChild(ele)


    ###########################################################
    # stmt
    ###########################################################

    def prepend_previous(self, parent, include_op=True):
        """helper to prepend space, new line comments between stmt/expr"""
        self.tokens.find(self.line, self.column)
        leftmost = self.tokens.pos
        leading_text = self.tokens.previous_text(end_pos=leftmost,
                                                 include_op=include_op)
        parent.appendChild(DOM.Text(leading_text))


    def _c_field_list(self, parent, field_name):
        """must a field list that contains line, number information"""
        ele = Element(field_name)
        for item in self.fields[field_name].value:
            item.to_xml(ele)
        parent.appendChild(ele)


    def c_Pass(self, parent):
        self.prepend_previous(parent)
        parent.appendChild(Element('Pass', text='pass'))

    def c_Assign(self, parent):
        self.prepend_previous(parent)
        targets = Element('targets')
        for child in self.fields['targets'].value:
            child.to_xml(targets)
        equal = self._before_field('value')
        ele = Element('Assign', childs= [
                targets,
                DOM.Text(equal),
                ])
        self.fields['value'].value.to_xml(ele)
        parent.appendChild(ele)


    def _c_import_names(self, ele):
        for child in self.fields['names'].value:
            # consume token NAME 'import' on first item...
            # ... or token COMMA for remaining items
            self.tokens.next()
            alias = Element('alias')
            alias.appendChild(DOM.Text(self.tokens.previous_text()))

            # add name
            name = Element('name', text=child.fields['name'].value)
            self.tokens.next() # consume token NAME '<imported-name>'
            alias.appendChild(name)

            # check if optional asname is present
            asname = child.fields.get('asname', None)
            if asname.value:
                while self.tokens.current().exact_type == Token.DOT:
                    self.tokens.next() # dot
                    self.tokens.next() # name
                text = self.tokens.previous_text()
                self.tokens.next() # consume token NAME 'as'
                text += 'as' + self.tokens.previous_text()
                self.tokens.next() # consume token NAME '<asname>'
                alias.appendChild(DOM.Text(text))
                alias.appendChild(Element('asname', text=asname.value))

            ele.appendChild(alias)


    def c_Import(self, parent):
        self.prepend_previous(parent)
        ele = Element('Import', text='import')
        self._c_import_names(ele)
        parent.appendChild(ele)

    def c_ImportFrom(self, parent):
        self.prepend_previous(parent)

        # from <module>
        self.tokens.next() # consume token NAME 'from'
        from_text = 'from'
        from_text += self.tokens.previous_text()
        # get level dots
        while self.tokens.current().exact_type == Token.DOT:
            from_text += '.'
            self.tokens.next() # dot
        ele = Element('ImportFrom', text=from_text)
        # get module name
        ele.appendChild(Element('module', text=self.fields['module'].value))
        if self.tokens.current().string != 'import':
            self.tokens.next() # consume token NAME <module>
            while self.tokens.current().exact_type == Token.DOT:
                self.tokens.next() # dot
                self.tokens.next() # name
        import_prev_space = self.tokens.previous_text(include_op=False)
        ele.appendChild(DOM.Text(import_prev_space + 'import'))

        # names
        names = Element('names')
        self._c_import_names(names)
        ele.appendChild(names)

        # level
        ele.setAttribute('level', str(self.fields['level'].value))

        # append to parent
        parent.appendChild(ele)

    def c_Return(self, parent):
        self.prepend_previous(parent)
        self.tokens.next() # consume NAME `return`
        ele = Element('Return', text='return' + self.tokens.previous_text())
        self.fields['value'].value.to_xml(ele)
        parent.appendChild(ele)

    def c_FunctionDef(self, parent):
        self.prepend_previous(parent)
        ele = Element('FunctionDef', text='def')

        # name
        name = self.fields['name'].value
        ele.setAttribute('name', name)
        self.tokens.next() # consume name
        ele.appendChild(DOM.Text(self.tokens.previous_text() + name))

        # arguments
        arguments = self.fields['args'].value
        self.tokens.next() # consume LPAR
        start_arguments_text = self.tokens.previous_text() + '('
        self.tokens.start_limit = self.tokens.pos
        arguments_ele = Element('arguments', text=start_arguments_text)

        args = arguments.fields['args'].value
        if args:
            f_defaults = arguments.fields['defaults'].value
            defaults = ([None] * (len(args) - len(f_defaults))) + f_defaults
            args_ele = Element('args')
            for arg, default in zip(args, defaults):
                self.tokens.next() # consume LPAR / COMMA
                args_ele.appendChild(DOM.Text(self.tokens.previous_text()))
                arg_ele = Element('arg')
                arg_ele.setAttribute('name', arg.fields['arg'].value)
                arg_ele.appendChild(DOM.Text(arg.fields['arg'].value))
                self.tokens.next() # consume NAME
                if default:
                    self.tokens.find(default.line, default.column)
                    text = self.tokens.previous_text()
                    default_ele = Element('default', text=text)
                    default.to_xml(default_ele)
                    arg_ele.appendChild(default_ele)
                    # FIXME how to find end of expression?
                    self.tokens.next()

                args_ele.appendChild(arg_ele)
            arguments_ele.appendChild(args_ele)

        # close parent + colon
        self.tokens.next(exact_type=Token.COLON)
        self.tokens.start_limit = self.tokens.pos
        end_arguments_text = self.tokens.previous_text()
        if len(arguments_ele.childNodes) == 1:
            end_arguments_text = end_arguments_text[len(start_arguments_text):]
        arguments_ele.appendChild(DOM.Text(end_arguments_text + ':'))
        ele.appendChild(arguments_ele)

        # body
        self._c_field_list(ele, 'body')

        parent.appendChild(ele)


class SrcToken:
    """helper to read tokenized python source

    Token is named tuple with field names:
    type string start end line exact_type
    """
    def __init__(self, fp):
        # current position of analised tokens
        # ignore first element (encoding token)
        self.pos = 1
        self.list = list(tokenize(fp.readline))
        # save a Token that was already included in the XML
        # and must not be included again
        self.start_limit = None

    def current(self):
        return self.list[self.pos]

    def next(self, exact_type=None):
        """return token given by self.pos"""
        if exact_type:
            while self.list[self.pos].exact_type != exact_type:
                self.pos += 1
        else:
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
        if col == -1:
            return self.find_multiline_string(line, col)
        for token in self.token_iter():
            if token.start[0] == line and token.start[1] == col:
                log.debug('FOUND %s', token)
                return token

    def find_multiline_string(self, line, col):
        """find string token with given position

        multiline strings return last line and column == -1
        """
        for token in self.token_iter():
            if token.end[0] == line:
                return token


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


    def previous_text(self, end_pos=None, include_op=True,
                      start_exact_type=None, max_start=None,
                      end_exact_type=None, end_space=True):
        """get all text that preceeds a node.

         - includes spance, operators and delimiters
         - if `end_exact_type` is used go back and don't get
           text until one token after end_exact_type.
           This is used to handle extra "()" around AST expr nodes.
        """
        # XXX this function is too complex dealing with many different
        # situations. split use-cases into different functions?

        # set tokens that are considered as "text"
        # not used if start_exact_type is specified
        include_previous = [Token.NEWLINE, Token.NL, Token.COMMENT, Token.COMMA,
                            Token.INDENT, Token.DEDENT]
        if include_op:
            include_previous.append(Token.OP)

        end_pos = end_pos if end_pos is not None else self.pos
        text = ''
        # Control if we are looking for starting end_pos,
        # once it is found, stop checking end_exact_type
        searching_end = end_exact_type is not None
        matched_start = 0
        while True:
            # calculate the spaces betwen 2 tokens
            # <token>____<cur>
            current = self.list[end_pos]
            current_col = current.start[1]
            end_pos -= 1
            token = self.list[end_pos]
            if searching_end:
                if token.exact_type != end_exact_type:
                    continue
                else:
                    searching_end = False
                    self.pos = end_pos
                    if not end_space:
                        current_col = token.end[1]
            if current.start[0] == token.end[0]:
                # same line, just add spaces
                spaces = ' ' * (current_col - token.end[1])
            elif current.type == Token.ENDMARKER:
                spaces = ''
            else:
                spaces = token.line[token.end[1]:] + ' ' * current_col


            # `match` defines if token is of the type we were looking for
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
            elif token.type in include_previous:
                if end_pos != self.start_limit:
                    match = True
                else:
                    self.start_limit = None

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

    # add remaining text at the end of the file
    ast_root.tokens.pos = len(ast_root.tokens.list) - 1
    last_text = ast_root.tokens.previous_text()
    root.appendChild(DOM.Text(last_text))

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
