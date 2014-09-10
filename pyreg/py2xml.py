
import argparse
from tokenize import tokenize
import tokenize as Token
import xml.etree.ElementTree as ET
from xml.dom.minidom import getDOMImplementation, Text
import logging as log

from .astview import AstNode


############# monkey-patch minidom.Text so it doesnt escape "
def _monkey_writexml(self, writer, indent="", addindent="", newl=""):
    data = "%s%s%s" % (indent, self.data, newl)
    if data:
        data = data.replace("&", "&amp;").replace("<", "&lt;"). \
                    replace(">", "&gt;")
        writer.write(data)
Text.writexml = _monkey_writexml
##############################################################


#log.basicConfig(level=log.DEBUG)


# create DOM Document
impl = getDOMImplementation()
DOM = impl.createDocument(None, None, None)
DOM.Text = DOM.createTextNode
def Element(tag_name, text=None):
    ele = DOM.createElement(tag_name)
    if text:
        ele.appendChild(DOM.Text(text))
    return ele


class AstNodeX(AstNode):
    """add capability to AstNode be convert to XML"""

    def to_xml(self, parent=None):
        # hack for root node
        if parent == None:
            parent = Element(self.class_)

        # apply converter based on node class_
        converter = getattr(self, 'c_' + self.class_, None)
        if converter:
            try:
                return converter(parent)
            except Exception: # pragma: no cover
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
    # expr
    ###########################################################

    def expr_wrapper(func):
        """deals with optional "()" around expressions"""
        def _build_expr(self, parent):
            has_PAR = False
            if self.tokens.next().exact_type == Token.LPAR:
                has_PAR = True
                token = self.tokens.pop()
                text = '(' + self.tokens.space_right()
                parent.appendChild(DOM.Text(text))
            func(self, parent)
            if has_PAR:
                token = self.tokens.pop()
                assert token.exact_type == Token.RPAR
                text = self.tokens.prev_space() + ')'
                parent.appendChild(DOM.Text(text))
        return _build_expr


    def _c_delimiter(self, ele, delimiters):
        while self.tokens.next().exact_type in delimiters:
            token = self.tokens.pop()
            text = self.tokens.prev_space() + token.string
            ele.appendChild(DOM.Text(text))


    def _c_comma_delimitted(self, ele, items):
        """convert a COMMA separated list of items

        with optional end in COMMA"""
        for index, item in enumerate(items):
            if index:
                ele.appendChild(DOM.Text(self.tokens.space_right()))
            item.to_xml(ele)
            self._c_delimiter(ele, (Token.COMMA, Token.NL))


    @expr_wrapper
    def c_Num(self, parent):
        parent.appendChild(Element('Num', text=str(self.fields['n'].value)))
        assert self.tokens.pop().type == Token.NUMBER

    @expr_wrapper
    def c_Str(self, parent):
        ele = Element('Str')
        token = self.tokens.pop()
        while True:
            assert token.type == Token.STRING
            ele_s = Element('s', text=token.string)
            ele.appendChild(ele_s)
            # check if next token is a string (implicit concatenation)
            next_token = self.tokens.next()
            if next_token.type != Token.STRING:
                break
            # add space before next string concatenated
            token = self.tokens.pop()
            ele.appendChild(DOM.Text(self.tokens.prev_space()))
        parent.appendChild(ele)


    @expr_wrapper
    def c_Tuple(self, parent):
        ele = Element('Tuple')
        ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        self._c_comma_delimitted(ele, self.fields['elts'].value)
        parent.appendChild(ele)


    @expr_wrapper
    def c_List(self, parent):
        ele = Element('List')
        ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        assert self.tokens.pop().exact_type == Token.LSQB
        ele.appendChild(DOM.Text('[' + self.tokens.space_right()))
        self._c_comma_delimitted(ele, self.fields['elts'].value)

        # close text
        assert self.tokens.pop().exact_type == Token.RSQB
        if self.fields['elts'].value:
            close_text = self.tokens.prev_space() + ']'
        else:
            close_text = ']'
        ele.appendChild(DOM.Text(close_text))

        parent.appendChild(ele)


    @expr_wrapper
    def c_Dict(self, parent):
        ele = Element('Dict')
        parent.appendChild(ele)

        assert self.tokens.pop().exact_type == Token.LBRACE
        ele.appendChild(DOM.Text('{' + self.tokens.space_right()))
        for key, value in zip(self.fields['keys'].value,
                              self.fields['values'].value):
            ele.appendChild(DOM.Text(self.tokens.space_right()))
            item_ele = Element('item')
            ele.appendChild(item_ele)

            key.to_xml(item_ele)
            self._c_delimiter(item_ele, (Token.COLON, Token.NL))
            item_ele.appendChild(DOM.Text(self.tokens.space_right()))
            value.to_xml(item_ele)
            # optional comma
            self._c_delimiter(ele, (Token.COMMA, Token.NL))

        # close text
        assert self.tokens.pop().exact_type == Token.RBRACE
        if self.fields['keys'].value:
            close_text = self.tokens.prev_space() + '}'
        else:
            close_text = '}'
        ele.appendChild(DOM.Text(close_text))



    @expr_wrapper
    def c_Name(self, parent):
        assert self.tokens.pop().type == Token.NAME
        ele = Element('Name', text=self.fields['id'].value)
        ele.setAttribute('name', self.fields['id'].value)
        ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        parent.appendChild(ele)


    @expr_wrapper
    def c_NameConstant(self, parent):
        assert self.tokens.pop().type == Token.NAME
        ele = Element('NameConstant', text=self.tokens.current.string)
        parent.appendChild(ele)


    @expr_wrapper
    def c_Attribute(self, parent):
        attribute_ele = Element('Attribute')
        attribute_ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        # value
        value_ele = Element('value')
        self.fields['value'].value.to_xml(value_ele)
        attribute_ele.appendChild(value_ele)
        # dot
        assert self.tokens.pop().exact_type == Token.DOT
        attribute_ele.appendChild(DOM.Text('.'))
        # attr name
        assert self.tokens.pop().type == Token.NAME
        attr_ele = Element('attr', text=self.tokens.current.string)
        attribute_ele.appendChild(attr_ele)
        parent.appendChild(attribute_ele)


    TOKEN_MAP = {
        'Add': Token.PLUS,
        'Mult': Token.STAR,
        'Sub': Token.MINUS,
        'Mod': Token.PERCENT,
        }

    @expr_wrapper
    def c_BinOp(self, parent):
        ele = Element(self.class_)
        self.fields['left'].value.to_xml(ele)
        # operator
        op = self.fields['op'].value
        op_token = self.TOKEN_MAP[op.class_]
        assert self.tokens.pop().exact_type == op_token, self.tokens.current
        op_text = self.tokens.text_prev2next()
        ele.appendChild(Element(op.class_, text=op_text))
        # right value
        self.fields['right'].value.to_xml(ele)
        parent.appendChild(ele)

    @expr_wrapper
    def c_BoolOp(self, parent):
        ele = Element(self.class_)
        ele.setAttribute('op', self.fields['op'].value.class_)

        for index, value in enumerate(self.fields['values'].value):
            if index:
                # prepend operator text to all values but first one
                assert self.tokens.pop().type == Token.NAME
                ele.appendChild(DOM.Text(self.tokens.text_prev2next()))
            ele_value = Element('value')
            value.to_xml(ele_value)
            ele.appendChild(ele_value)
        parent.appendChild(ele)

    @expr_wrapper
    def c_UnaryOp(self, parent):
        self.tokens.pop().type == Token.NAME
        op_text = self.tokens.current.string + self.tokens.space_right()
        ele = Element(self.class_, text=op_text)
        ele.setAttribute('op', self.fields['op'].value.class_)
        self.fields['operand'].value.to_xml(ele)
        parent.appendChild(ele)


    @expr_wrapper
    def c_Compare(self, parent):
        ele = Element(self.class_)

        ele_left = Element('value')
        self.fields['left'].value.to_xml(ele_left)
        ele.appendChild(ele_left)

        for op, value in zip(self.fields['ops'].value,
                             self.fields['comparators'].value):
            assert self.tokens.pop().type == Token.OP
            ele_op = Element('cmpop', text=self.tokens.text_prev2next())
            ele.appendChild(ele_op)
            # value
            ele_value = Element('value')
            value.to_xml(ele_value)
            ele.appendChild(ele_value)
        parent.appendChild(ele)


    @expr_wrapper
    def c_Call(self, parent):
        ele = Element('Call')

        # func
        ele_func = Element('func')
        self.fields['func'].value.to_xml(ele_func)
        ele.appendChild(ele_func)

        assert self.tokens.pop().exact_type == Token.LPAR
        ele.appendChild(DOM.Text(self.tokens.text_prev2next()))

        # args
        args = self.fields['args'].value
        if args:
            ele_args = Element('args')
            self._c_comma_delimitted(ele_args, args)
            ele.appendChild(ele_args)

        keywords = self.fields['keywords'].value
        if keywords:
            ele_keywords = Element('keywords')
            ele.appendChild(ele_keywords)
            for keyword in keywords:
                ele_keyword = Element('keyword')
                ele_keywords.appendChild(ele_keyword)
                # arg
                assert self.tokens.pop().type == Token.NAME
                ele_arg = Element('arg', text=keyword.fields['arg'].value)
                ele_keyword.appendChild(ele_arg)
                # equal
                assert self.tokens.pop().exact_type == Token.EQUAL
                ele_keyword.appendChild(DOM.Text(self.tokens.text_prev2next()))
                # value
                ele_val = Element('value')
                keyword.fields['value'].value.to_xml(ele_val)
                ele_keyword.appendChild(ele_val)
                # optional comma
                self._c_delimiter(ele_keywords, (Token.COMMA, Token.NL))

        assert self.tokens.pop().exact_type == Token.RPAR
        ele.appendChild(DOM.Text(self.tokens.prev_space() + ')'))
        parent.appendChild(ele)


    ###########################################################
    # stmt
    ###########################################################

    def _c_field_list(self, parent, field_name):
        """must a field list that contains line, number information"""
        ele = Element(field_name)
        for item in self.fields[field_name].value:
            item.to_xml(ele)
        parent.appendChild(ele)


    def c_Expr(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        ele = Element('Expr')
        self.fields['value'].value.to_xml(ele)
        parent.appendChild(ele)


    def c_Pass(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().type == Token.NAME
        parent.appendChild(Element(self.class_,
                                   text=self.tokens.current.string))
    c_Break = c_Pass
    c_Continue = c_Pass


    def c_Assert(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().string == 'assert'
        assert_text = 'assert' + self.tokens.space_right()
        assert_ele = Element('Assert', text=assert_text)
        # test expr
        test_ele = Element('test')
        self.fields['test'].value.to_xml(test_ele)
        assert_ele.appendChild(test_ele)
        # msg
        msg = self.fields['msg'].value
        if msg:
            assert self.tokens.pop().exact_type == Token.COMMA
            assert_ele.appendChild(DOM.Text(self.tokens.text_prev2next()))
            msg_ele = Element('msg')
            msg.to_xml(msg_ele)
            assert_ele.appendChild(msg_ele)
        parent.appendChild(assert_ele)


    def c_Assign(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        ele = Element('Assign')
        # targets
        targets = Element('targets')
        self._c_comma_delimitted(targets, self.fields['targets'].value)
        ele.appendChild(targets)
        # op `=`
        assert self.tokens.pop().exact_type == Token.EQUAL
        ele.appendChild(DOM.Text(self.tokens.text_prev2next()))
        # value
        self.fields['value'].value.to_xml(ele)
        parent.appendChild(ele)


    def _c_import_names(self, ele):
        for child in self.fields['names'].value:
            alias = Element('alias', text=self.tokens.space_right())

            # add name
            self.tokens.pop_dotted_name()
            name_ele = Element('name', text=child.fields['name'].value)
            alias.appendChild(name_ele)

            # check if optional asname is present
            asname = child.fields.get('asname', None)
            if asname.value:
                assert self.tokens.pop().string == 'as'
                alias.appendChild(DOM.Text(self.tokens.text_prev2next()))
                assert self.tokens.pop().type == Token.NAME
                alias.appendChild(Element('asname', text=asname.value))
            ele.appendChild(alias)

            if self.tokens.next().exact_type == Token.COMMA:
                self.tokens.pop()
                text = self.tokens.prev_space() + ','
                ele.appendChild(DOM.Text(text))



    def c_Import(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().string == 'import'
        ele = Element('Import', text='import')
        self._c_import_names(ele)
        parent.appendChild(ele)

    def c_ImportFrom(self, parent):
        self.tokens.write_non_ast_tokens(parent)

        # from <module>
        assert self.tokens.pop().string == 'from'
        ele = Element('ImportFrom')
        from_text = 'from' + self.tokens.space_right()
        # get level dots
        while self.tokens.next().exact_type == Token.DOT:
            from_text += '.'
            self.tokens.pop() # dot
        ele.appendChild(DOM.Text(from_text))

        # get module name
        module_text = ''
        if self.tokens.next().string != 'import':
            module_text += self.tokens.pop_dotted_name()
        ele.appendChild(Element('module', text=module_text))

        # import keyword
        assert self.tokens.pop().string == 'import'
        ele.appendChild(DOM.Text(self.tokens.prev_space() + 'import'))

        # names
        names = Element('names')
        self._c_import_names(names)
        ele.appendChild(names)
        # level
        ele.setAttribute('level', str(self.fields['level'].value))
        # append to parent
        parent.appendChild(ele)


    def c_Return(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().string == 'return'
        ele = Element('Return', text='return' + self.tokens.space_right())
        self.fields['value'].value.to_xml(ele)
        parent.appendChild(ele)

    def c_FunctionDef(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        ele = Element('FunctionDef', text='def')
        assert self.tokens.pop().type == Token.NAME

        # name
        assert self.tokens.pop().type == Token.NAME
        name = self.fields['name'].value
        ele.setAttribute('name', name)
        text = self.tokens.prev_space() + name
        ele.appendChild(DOM.Text(text))

        # arguments
        arguments = self.fields['args'].value
        assert self.tokens.pop().exact_type == Token.LPAR
        start_arguments_text = self.tokens.prev_space() + '('
        arguments_ele = Element('arguments', text=start_arguments_text)

        args = arguments.fields['args'].value
        if args:
            f_defaults = arguments.fields['defaults'].value
            defaults = ([None] * (len(args) - len(f_defaults))) + f_defaults
            args_ele = Element('args')
            for arg, default in zip(args, defaults):
                assert self.tokens.pop().type == Token.NAME
                args_ele.appendChild(DOM.Text(self.tokens.prev_space()))
                arg_ele = Element('arg')
                arg_ele.setAttribute('name', arg.fields['arg'].value)
                arg_ele.appendChild(DOM.Text(arg.fields['arg'].value))
                if default:
                    assert self.tokens.pop().exact_type == Token.EQUAL
                    default_ele = Element('default')
                    equal_text = self.tokens.text_prev2next()
                    default_ele.appendChild(DOM.Text(equal_text))
                    default.to_xml(default_ele)
                    arg_ele.appendChild(default_ele)

                args_ele.appendChild(arg_ele)
                if self.tokens.next().exact_type == Token.COMMA:
                    self.tokens.pop()
                    text = self.tokens.prev_space() + ','
                    args_ele.appendChild(DOM.Text(text))

            arguments_ele.appendChild(args_ele)

        # close parent + colon
        assert self.tokens.pop().exact_type == Token.RPAR
        close_args_text = self.tokens.prev_space() + ')'
        assert self.tokens.pop().exact_type == Token.COLON
        close_args_text += self.tokens.prev_space() + ':'
        arguments_ele.appendChild(DOM.Text(close_args_text))
        ele.appendChild(arguments_ele)

        # body
        self._c_field_list(ele, 'body')
        parent.appendChild(ele)


    def c_ClassDef(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        ele = Element('ClassDef', text='class')
        assert self.tokens.pop().type == Token.NAME

        # name
        assert self.tokens.pop().type == Token.NAME
        name = self.fields['name'].value
        ele.setAttribute('name', name)
        text = self.tokens.prev_space() + name
        ele.appendChild(DOM.Text(text))

        # arguments
        assert self.tokens.pop().exact_type == Token.LPAR
        start_arguments_text = self.tokens.text_prev2next()
        arguments_ele = Element('arguments', text=start_arguments_text)

        bases = self.fields['bases'].value
        if bases:
            bases_ele = Element('bases')
            self._c_comma_delimitted(bases_ele, bases)
            arguments_ele.appendChild(bases_ele)

        # close arguments
        assert self.tokens.pop().exact_type == Token.RPAR
        arguments_ele.appendChild(DOM.Text(')'))
        assert self.tokens.pop().exact_type == Token.COLON
        arguments_ele.appendChild(DOM.Text(self.tokens.prev_space() + ':'))
        ele.appendChild(arguments_ele)

        # body
        self._c_field_list(ele, 'body')
        parent.appendChild(ele)

    def c_While(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().type == Token.NAME
        while_text = self.tokens.current.string + self.tokens.space_right()
        ele = Element(self.class_, text=while_text)
        # test expr
        test_ele = Element('test')
        self.fields['test'].value.to_xml(test_ele)
        ele.appendChild(test_ele)
        # colon
        assert self.tokens.pop().exact_type == Token.COLON
        ele.appendChild(DOM.Text(self.tokens.prev_space() + ':'))
        # body
        self._c_field_list(ele, 'body')
        parent.appendChild(ele)

    c_If = c_While


    def c_Raise(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().string == 'raise'
        ele = Element('Raise', text='raise')
        ele.appendChild(DOM.Text(self.tokens.space_right()))
        ele_exc = Element('exc')
        self.fields['exc'].value.to_xml(ele_exc)
        ele.appendChild(ele_exc)
        parent.appendChild(ele)



class SrcToken:
    """helper to read tokenized python source

    Token is named tuple with field names:
    type string start end line exact_type
    """
    def __init__(self, fp):
        self.list = list(reversed(list(tokenize(fp.readline))))
        self.current = None
        self.previous = None
        self.pop() # ignore encoding

    def pop(self):
        self.previous = self.current
        self.current = self.list[-1]
        return self.list.pop()

    def next(self):
        return self.list[-1]

    def pop_dotted_name(self):
        name = self.pop().string
        while self.next().exact_type == Token.DOT:
            self.pop()
            name += '.' + self.pop().string
        return name


    @staticmethod
    def calc_space(from_token, to_token):
        if from_token.end[0] == to_token.start[0]:
            # same line, just add spaces
            return ' ' * (to_token.start[1] - from_token.end[1])
        elif to_token.type == Token.ENDMARKER:
            return ''
        else:
            # previous token is a previous line
            # add end of previous line more spaces leading to current token
            return from_token.line[from_token.end[1]:] + ' ' * to_token.start[1]

    def text_prev2next(self):
        text = self.calc_space(self.previous, self.current)
        text += self.current.string
        text += self.calc_space(self.current, self.next())
        return text

    def prev_space(self):
        return self.calc_space(self.previous, self.current)

    def space_right(self):
        return self.calc_space(self.current, self.next())


    NON_AST_TOKENS = set([
        Token.SEMI,
        Token.NEWLINE, Token.NL,
        Token.COMMENT,
        Token.INDENT, Token.DEDENT,
        ])
    def write_non_ast_tokens(self, parent_ele):
        token = None
        text = ''
        while self.next().exact_type in self.NON_AST_TOKENS:
            token = self.pop()
            text += self.prev_space() + token.string
        if token:
            text += self.space_right()
        parent_ele.appendChild(DOM.Text(text))


def py2xml(filename):
    """convert ast to srcML"""
    AstNodeX.load_map()
    ast_root = AstNodeX.tree(filename)
    with open(filename, 'rb') as fp:
        AstNodeX.tokens = SrcToken(fp)
    root = ast_root.to_xml()

    # add remaining text at the end of the file
    ast_root.tokens.write_non_ast_tokens(root)

    # write XML string
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
