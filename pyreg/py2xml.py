
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


    def pop_merge_NL(self, lspace=False, rspace=True, exact_type=None):
        """pop one token and sorounding NL tokens

        :exact_type (str): only match given token
        :return: text of NL's and token
        """
        text = ''
        found_token = False
        include_left = lspace
        while True:
            next_token = self.tokens.next()
            if next_token.exact_type != Token.NL:
                if found_token:
                    break
                elif exact_type and exact_type != next_token.exact_type:
                    # FIXME deal with new line before figure out not a match
                    return ''
                found_token = True
            self.tokens.pop()
            if include_left:
                text += self.tokens.prev_space()
            text += next_token.string
            include_left = True
        if rspace:
            text += self.tokens.space_right()
        return text

    def _c_delimiter(self, ele, delimiters):
        """include space right"""
        text = ''
        while self.tokens.next().exact_type in delimiters:
            token = self.tokens.pop()
            text += self.tokens.prev_space() + token.string
        text += self.tokens.space_right()
        ele.appendChild(DOM.Text(text))



    @expr_wrapper
    def c_Num(self, parent):
        parent.appendChild(Element('Num', text=str(self.fields['n'].value)))
        assert self.tokens.pop().type == Token.NUMBER

    @expr_wrapper
    def c_Str(self, parent):
        ele = Element(self.class_)
        token = self.tokens.pop()
        while True:
            assert token.type == Token.STRING, self.tokens.current
            ele_s = Element('s', text=token.string)
            ele.appendChild(ele_s)

            # check if next token is a string (implicit concatenation)
            pos = -1
            continue_string = True
            while True:
                token = self.tokens.list[pos]
                if token.type == Token.STRING:
                    break
                elif token.exact_type == Token.NL:
                    pos -= 1
                else:
                    continue_string = False
                    break
            if not continue_string:
                break
            text = ''
            for x in range(-pos - 1):
                token = self.tokens.pop()
                text += self.tokens.prev_space() + token.string
            # add space before next string concatenated
            token = self.tokens.pop()
            ele.appendChild(DOM.Text(text + self.tokens.prev_space()))
        parent.appendChild(ele)

    c_Bytes = c_Str


    @expr_wrapper
    def c_Tuple(self, parent):
        ele = Element('Tuple')
        ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        first = True
        for item in self.fields['elts'].value:
            if not first:
                ele.appendChild(DOM.Text(self.tokens.space_right()))
            first = False
            item.to_xml(ele)
            text = self.pop_merge_NL(lspace=True, exact_type=Token.COMMA,
                                     rspace=False)
            ele.appendChild(DOM.Text(text))

        parent.appendChild(ele)


    @expr_wrapper
    def c_List(self, parent):
        ele = Element(self.class_)
        if 'ctx' in self.fields: # set doesnt have ctx
            ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        ele.appendChild(DOM.Text(self.pop_merge_NL())) #LSQB
        for item in self.fields['elts'].value:
            item.to_xml(ele)
            self._c_delimiter(ele, (Token.COMMA, Token.NL))

        # close brackets
        assert self.tokens.pop().type == Token.OP
        ele.appendChild(DOM.Text(self.tokens.current.string))
        parent.appendChild(ele)

    c_Set = c_List


    @expr_wrapper
    def c_Dict(self, parent):
        ele = Element('Dict')
        parent.appendChild(ele)

        ele.appendChild(DOM.Text(self.pop_merge_NL())) # LBRACE
        for key, value in zip(self.fields['keys'].value,
                              self.fields['values'].value):
            item_ele = Element('item')
            ele.appendChild(item_ele)

            key.to_xml(item_ele)
            # COLON
            item_ele.appendChild(DOM.Text(self.pop_merge_NL(lspace=True)))
            value.to_xml(item_ele)
            # optional comma
            self._c_delimiter(ele, (Token.COMMA, Token.NL))

        # close text
        assert self.tokens.pop().exact_type == Token.RBRACE
        close_text = '}'
        ele.appendChild(DOM.Text(close_text))



    @expr_wrapper
    def c_Name(self, parent):
        assert self.tokens.pop().type == Token.NAME, self.tokens.current
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
    def c_Ellipsis(self, parent):
        assert self.tokens.pop().type == Token.OP
        ele = Element('Ellipsis', text=self.tokens.current.string)
        parent.appendChild(ele)

    @expr_wrapper
    def c_Starred(self, parent):
        assert self.tokens.pop().exact_type == Token.STAR
        text = '*' + self.tokens.space_right()
        ele = Element('Starred', text=text)
        ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        self.fields['value'].value.to_xml(ele)
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


    @expr_wrapper
    def c_Index(self, parent):
        ele = Element('Index')
        self.fields['value'].value.to_xml(ele)
        parent.appendChild(ele)

    @expr_wrapper
    def c_Slice(self, parent):
        ele = Element('Slice')
        parent.appendChild(ele)

        # lower
        lower = self.fields['lower'].value
        if lower:
            ele_lower = Element('lower')
            lower.to_xml(ele_lower)
            ele.appendChild(ele_lower)
            ele.appendChild(DOM.Text(self.tokens.space_right()))

        # first colon
        assert self.tokens.pop().exact_type == Token.COLON
        ele.appendChild(DOM.Text(':'))

        # upper
        upper = self.fields['upper'].value
        if upper:
            ele.appendChild(DOM.Text(self.tokens.space_right()))
            ele_upper = Element('upper')
            upper.to_xml(ele_upper)
            ele.appendChild(ele_upper)

        # step
        step = self.fields['step'].value
        if step:
            assert self.tokens.pop().exact_type == Token.COLON
            ele.appendChild(DOM.Text(self.tokens.text_prev2next()))
            ele_step = Element('step')
            step.to_xml(ele_step)
            ele.appendChild(ele_step)


    def c_ExtSlice(self, parent):
        raise NotImplementedError()



    @expr_wrapper
    def c_Subscript(self, parent):
        sub_ele = Element('Subscript')
        sub_ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        parent.appendChild(sub_ele)

        # value
        value_ele = Element('value')
        self.fields['value'].value.to_xml(value_ele)
        sub_ele.appendChild(value_ele)

        # slice
        ele_slice = Element('slice')
        assert self.tokens.pop().exact_type == Token.LSQB
        ele_slice.appendChild(DOM.Text(self.tokens.text_prev2next()))
        self.fields['slice'].value.to_xml(ele_slice)
        assert self.tokens.pop().exact_type == Token.RSQB
        close_text = self.tokens.prev_space() + ']'
        ele_slice.appendChild(DOM.Text(close_text))
        sub_ele.appendChild(ele_slice)


    @expr_wrapper
    def c_Yield(self, parent):
        assert self.tokens.pop().string == 'yield'
        yield_text = self.tokens.current.string + self.tokens.space_right()
        ele = Element(self.class_, text=yield_text)
        # from (only for YieldFrom)
        if self.class_ == 'YieldFrom':
            assert self.tokens.pop().string == 'from'
            from_text = self.tokens.current.string + self.tokens.space_right()
            ele.appendChild(DOM.Text(from_text))
        # value
        value = self.fields['value'].value
        if value:
            value.to_xml(ele)
        parent.appendChild(ele)

    c_YieldFrom = c_Yield


    @expr_wrapper
    def c_BinOp(self, parent):
        ele = Element(self.class_)
        self.fields['left'].value.to_xml(ele)
        # operator
        op = self.fields['op'].value
        op_text = self.pop_merge_NL(lspace=True) # OP
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
                op_text = self.pop_merge_NL(lspace=True)
                ele.appendChild(DOM.Text(op_text))
            ele_value = Element('value')
            value.to_xml(ele_value)
            ele.appendChild(ele_value)
        parent.appendChild(ele)

    @expr_wrapper
    def c_UnaryOp(self, parent):
        self.tokens.pop() # operator can be an OP or NAME
        op_text = self.tokens.current.string + self.tokens.space_right()
        ele = Element(self.class_, text=op_text)
        ele.setAttribute('op', self.fields['op'].value.class_)
        self.fields['operand'].value.to_xml(ele)
        parent.appendChild(ele)


    CMP_TOKEN_COUNT = {
        'Lt': 1, # <
        'Eq': 1, # ==
        'Gt': 1, # >
        'GtE': 1, # >=
        'In': 1, # in
        'Is': 1, # is
        'IsNot': 2, # is not
        'Lt': 1, # <
        'LtE': 1, # <=
        'NotEq': 1, # !=
        'NotIn': 2, # not in
        }
    @expr_wrapper
    def c_Compare(self, parent):
        ele = Element(self.class_)

        ele_left = Element('value')
        self.fields['left'].value.to_xml(ele_left)
        ele.appendChild(ele_left)

        for op, value in zip(self.fields['ops'].value,
                             self.fields['comparators'].value):
            cmp_text = self.tokens.space_right()
            for token in range(self.CMP_TOKEN_COUNT[op.class_]):
                cmp_text += self.tokens.pop().string
                cmp_text += self.tokens.space_right()
            ele_op = Element('cmpop', text=cmp_text)
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

        ele.appendChild(DOM.Text(self.pop_merge_NL(lspace=True))) # LPAR
        # args
        args = self.fields['args'].value
        if args:
            ele_args = Element('args')
            ele.appendChild(ele_args)
            for arg in args:
                arg.to_xml(ele_args)
                # optional comma
                self._c_delimiter(ele_args, (Token.COMMA, Token.NL))

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

        for field in ('starargs', 'kwargs'):
            xargs = self.fields[field].value
            if xargs:
                token = self.tokens.pop()
                assert token.type == Token.OP # START DOUBLESTAR
                text = token.string + self.tokens.space_right()
                ele_xargs = Element(field, text=text)
                xargs.to_xml(ele_xargs)
                ele.appendChild(ele_xargs)
                # optional comma
                self._c_delimiter(ele, (Token.COMMA, Token.NL))

        assert self.tokens.pop().exact_type == Token.RPAR, self.tokens.current
        ele.appendChild(DOM.Text(')'))
        parent.appendChild(ele)


    @expr_wrapper
    def c_IfExp(self, parent):
        ele = Element('IfExpr')
        parent.appendChild(ele)

        # body
        ele_body = Element('body')
        self.fields['body'].value.to_xml(ele_body)
        ele.appendChild(ele_body)

        # if
        assert self.tokens.pop().string == 'if'
        ele.appendChild(DOM.Text(self.tokens.text_prev2next()))

        # test
        ele_test = Element('test')
        self.fields['test'].value.to_xml(ele_test)
        ele.appendChild(ele_test)

        # else
        assert self.tokens.pop().string == 'else'
        ele.appendChild(DOM.Text(self.tokens.text_prev2next()))

        # orelse
        ele_orelse = Element('orelse')
        self.fields['orelse'].value.to_xml(ele_orelse)
        ele.appendChild(ele_orelse)


    def c_GeneratorExp(self, parent):
        ele = Element(self.class_)
        ele.appendChild(DOM.Text(self.pop_merge_NL())) #LSQB

        if 'elt' in self.fields: # GeneratorExp ListComp SetComp
            # elt
            ele_elt = Element('elt')
            ele.appendChild(ele_elt)
            self.fields['elt'].value.to_xml(ele_elt)
        else: # DictComp
            ele_key = Element('key')
            ele.appendChild(ele_key)
            self.fields['key'].value.to_xml(ele_key)
            assert self.tokens.pop().exact_type == Token.COLON
            ele_value = Element('value')
            ele.appendChild(ele_value)
            self.fields['value'].value.to_xml(ele_value)

        # generators
        ele_gen = Element('generators')
        ele.appendChild(ele_gen)
        for gen in self.fields['generators'].value:
            ele_comp = Element('comprehension')
            ele_gen.appendChild(ele_comp)
            # for
            assert self.tokens.pop().string == 'for'
            ele_comp.appendChild(DOM.Text(self.tokens.text_prev2next()))
            # target
            ele_target = Element('target')
            gen.fields['target'].value.to_xml(ele_target)
            ele_comp.appendChild(ele_target)
            # in
            assert self.tokens.pop().string == 'in'
            ele_comp.appendChild(DOM.Text(self.tokens.text_prev2next()))
            # iter
            ele_iter = Element('iter')
            gen.fields['iter'].value.to_xml(ele_iter)
            ele_comp.appendChild(ele_iter)

            # ifs
            ifs = gen.fields['ifs'].value
            if ifs:
                ele_ifs = Element('ifs')
                ele_comp.appendChild(ele_ifs)
                for gif in ifs:
                    ele_if = Element('if')
                    ele_ifs.appendChild(ele_if)
                    # if
                    assert self.tokens.pop().string == 'if'
                    ele_if.appendChild(DOM.Text(self.tokens.text_prev2next()))
                    # target
                    gif.to_xml(ele_if)

        # close brackets
        assert self.tokens.pop().type == Token.OP
        ele.appendChild(DOM.Text(self.tokens.current.string))
        parent.appendChild(ele)

    c_ListComp = expr_wrapper(c_GeneratorExp)
    c_SetComp = c_ListComp
    c_DictComp = c_ListComp

    def c_Lambda(self, parent):
        raise NotImplementedError()


    ###########################################################
    # stmt
    ###########################################################

    def _c_field_list(self, parent, field_name, text=None):
        """must a field list that contains line, number information"""
        ele = Element(field_name, text=text)
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
        ele_targets = Element('targets')
        ele.appendChild(ele_targets)
        for target in self.fields['targets'].value:
            target.to_xml(ele_targets)
            # op `=`
            assert self.tokens.pop().exact_type == Token.EQUAL
            ele_targets.appendChild(DOM.Text(self.tokens.text_prev2next()))
        # value
        self.fields['value'].value.to_xml(ele)
        parent.appendChild(ele)


    def c_AugAssign(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        ele = Element('AugAssign')
        parent.appendChild(ele)
        # target
        ele_target = Element('target')
        self.fields['target'].value.to_xml(ele_target)
        ele.appendChild(ele_target)
        # op
        ele_op = Element('op')
        assert self.tokens.pop().type == Token.OP
        op = self.fields['op'].value
        ele_op_val = Element(op.class_, text=self.tokens.text_prev2next())
        ele_op.appendChild(ele_op_val)
        ele.appendChild(ele_op)
        # value
        ele_value = Element('value')
        self.fields['value'].value.to_xml(ele_value)
        ele.appendChild(ele_value)


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
        ele = Element('Return', text='return')
        value = self.fields['value'].value
        if value:
            ele.appendChild(DOM.Text(self.tokens.space_right()))
            value.to_xml(ele)
        parent.appendChild(ele)


    def _arg_element(self, arg):
        arg_ele = Element('arg')
        arg_ele.setAttribute('name', arg.fields['arg'].value)
        arg_ele.appendChild(DOM.Text(arg.fields['arg'].value))
        return arg_ele

    def c_FunctionDef(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        ele = Element('FunctionDef')

        # decorator
        decorators = self.fields['decorator_list'].value
        if decorators:
            ele_decorators = Element('decorators')
            ele.appendChild(ele_decorators)
            for deco in decorators:
                assert self.tokens.pop().exact_type == Token.AT
                deco_text = '@' + self.tokens.space_right()
                ele_deco = Element('decorator', text=deco_text)
                ele_decorators.appendChild(ele_deco)
                deco.to_xml(ele_deco)
                self.tokens.write_non_ast_tokens(ele)

        # def
        assert self.tokens.pop().string == 'def'
        ele.appendChild(DOM.Text('def' + self.tokens.space_right()))

        # name
        assert self.tokens.pop().type == Token.NAME
        name = self.fields['name'].value
        ele.setAttribute('name', name)
        ele.appendChild(DOM.Text(name))

        # arguments
        arguments = self.fields['args'].value
        start_arguments_text = self.pop_merge_NL(lspace=True) # LPAR
        arguments_ele = Element('arguments', text=start_arguments_text)

        args = arguments.fields['args'].value
        if args:
            # args
            f_defaults = arguments.fields['defaults'].value
            defaults = ([None] * (len(args) - len(f_defaults))) + f_defaults
            args_ele = Element('args')
            for arg, default in zip(args, defaults):
                assert self.tokens.pop().type == Token.NAME
                arg_ele = self._arg_element(arg)
                if default:
                    assert self.tokens.pop().exact_type == Token.EQUAL
                    default_ele = Element('default')
                    equal_text = self.tokens.text_prev2next()
                    default_ele.appendChild(DOM.Text(equal_text))
                    default.to_xml(default_ele)
                    arg_ele.appendChild(default_ele)

                args_ele.appendChild(arg_ele)
                self._c_delimiter(args_ele, (Token.COMMA, Token.NL))
            arguments_ele.appendChild(args_ele)

        # vararg, kwarg
        for field in ('vararg', 'kwarg'):
            arg = arguments.fields[field].value
            if arg:
                ele_arg = Element(field)
                token = self.tokens.pop()
                assert token.type == Token.OP # START / DOUBLESTAR
                star_text = token.string
                ele_arg.appendChild(DOM.Text(star_text))
                assert self.tokens.pop().type == Token.NAME
                ele_arg.appendChild(DOM.Text(self.tokens.prev_space()))
                ele_arg.appendChild(self._arg_element(arg))
                arguments_ele.appendChild(ele_arg)
                self._c_delimiter(arguments_ele, (Token.COMMA, Token.NL))


        if arguments.fields['kwonlyargs'].value:
            raise NotImplementedError()

        if arguments.fields['kw_defaults'].value:
            raise NotImplementedError()



        # close parent + colon
        assert self.tokens.pop().exact_type == Token.RPAR
        close_args_text = ')'
        assert self.tokens.pop().exact_type == Token.COLON
        close_args_text += self.tokens.prev_space() + ':'
        arguments_ele.appendChild(DOM.Text(close_args_text))
        ele.appendChild(arguments_ele)

        # body
        self._c_field_list(ele, 'body')
        parent.appendChild(ele)

        if self.fields['returns'].value:
            raise NotImplementedError()


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
            for item in bases:
                item.to_xml(bases_ele)
                self._c_delimiter(bases_ele, (Token.COMMA, Token.NL))
            arguments_ele.appendChild(bases_ele)


        if self.fields['keywords'].value:
            raise NotImplementedError()
        if self.fields['starargs'].value:
            raise NotImplementedError()
        if self.fields['kwargs'].value:
            raise NotImplementedError()
        if self.fields['decorator_list'].value:
            raise NotImplementedError()

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
        # orelse
        orelse = self.fields['orelse'].value
        if orelse:
            self.tokens.write_non_ast_tokens(ele)
            if self.tokens.next().string == 'elif':
                ele_orelse = Element('orelse')
                orelse[0].to_xml(ele_orelse)
                ele.appendChild(ele_orelse)
            else:
                assert self.tokens.pop().string == 'else', self.tokens.current
                else_text = self.tokens.text_prev2next() + ':'
                assert self.tokens.pop().exact_type == Token.COLON
                self._c_field_list(ele, 'orelse', text=else_text)

        parent.appendChild(ele)

    c_If = c_While


    def c_For(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().string == 'for'
        for_text = self.tokens.current.string + self.tokens.space_right()
        ele = Element(self.class_, text=for_text)
        # target expr
        ele_target = Element('target')
        self.fields['target'].value.to_xml(ele_target)
        ele.appendChild(ele_target)
        # 'in'
        assert self.tokens.pop().string == 'in'
        in_text = self.tokens.text_prev2next()
        ele.appendChild(DOM.Text(in_text))
        # iter
        ele_iter = Element('iter')
        self.fields['iter'].value.to_xml(ele_iter)
        ele.appendChild(ele_iter)
        # colon
        assert self.tokens.pop().exact_type == Token.COLON
        ele.appendChild(DOM.Text(self.tokens.prev_space() + ':'))
        # body
        self._c_field_list(ele, 'body')
        parent.appendChild(ele)

        # else
        orelse = self.fields['orelse'].value
        if orelse:
            self.tokens.write_non_ast_tokens(ele)
            assert self.tokens.pop().string == 'else', self.tokens.current
            else_text = self.tokens.text_prev2next() + ':'
            assert self.tokens.pop().exact_type == Token.COLON
            self._c_field_list(ele, 'orelse', text=else_text)


    def c_Raise(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().string == 'raise'
        ele = Element('Raise', text='raise')
        ele.appendChild(DOM.Text(self.tokens.space_right()))
        # exc
        exc = self.fields['exc'].value
        if exc:
            ele_exc = Element('exc')
            exc.to_xml(ele_exc)
            ele.appendChild(ele_exc)

        if self.fields['cause'].value:
            raise NotImplementedError()

        parent.appendChild(ele)


    def c_ExceptHandler(self, parent):
        ele = Element('ExceptHandler')
        parent.appendChild(ele)
        # except
        self.tokens.write_non_ast_tokens(ele)
        assert self.tokens.pop().string == 'except'
        except_text = 'except' + self.tokens.space_right()
        ele.appendChild(DOM.Text(except_text))
        # type
        except_type = self.fields['type'].value
        if except_type:
            ele_type = Element('type')
            except_type.to_xml(ele_type)
            ele.appendChild(ele_type)
            # name
            name = self.fields['name'].value
            if name:
                assert self.tokens.pop().string == 'as'
                ele.appendChild(DOM.Text(self.tokens.text_prev2next()))
                assert self.tokens.pop().type == Token.NAME
                ele_name = Element('name', text=name)
                ele.appendChild(ele_name)
        # :
        assert self.tokens.pop().exact_type == Token.COLON
        colon_text = self.tokens.prev_space() + ':'
        ele.appendChild(DOM.Text(colon_text))
        # body
        self._c_field_list(ele, 'body')


    def c_Try(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        ele = Element('Try')
        parent.appendChild(ele)
        assert self.tokens.pop().string == 'try'
        try_text = 'try' + self.tokens.space_right() + ':'
        ele.appendChild(DOM.Text(try_text))
        assert self.tokens.pop().exact_type == Token.COLON

        # body
        self._c_field_list(ele, 'body')

        # handlers
        handlers = self.fields['handlers'].value
        if handlers:
            ele_handlers = Element('handlers')
            ele.appendChild(ele_handlers)
            for handler in handlers:
                handler.to_xml(ele_handlers)

        orelse = self.fields['orelse'].value
        if orelse:
            self.tokens.write_non_ast_tokens(ele)
            assert self.tokens.pop().string == 'else', self.tokens.current
            else_text = self.tokens.text_prev2next() + ':'
            assert self.tokens.pop().exact_type == Token.COLON
            self._c_field_list(ele, 'orelse', text=else_text)

        final = self.fields['finalbody'].value
        if final:
            self.tokens.write_non_ast_tokens(ele)
            assert self.tokens.pop().string == 'finally', self.tokens.current
            final_text = self.tokens.text_prev2next() + ':'
            assert self.tokens.pop().exact_type == Token.COLON
            self._c_field_list(ele, 'finalbody', text=final_text)


    def c_With(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().string == 'with'
        with_text = 'with' + self.tokens.space_right()
        ele = Element(self.class_, text=with_text)
        ele_items = Element('items')
        ele.appendChild(ele_items)
        for item in self.fields['items'].value:
            ele_item = Element('withitem')
            ele_items.appendChild(ele_item)
            item.fields['context_expr'].value.to_xml(ele_item)
            opt_vars = item.fields['optional_vars'].value
            if opt_vars:
                assert self.tokens.pop().string == 'as'
                ele_item.appendChild(DOM.Text(self.tokens.text_prev2next()))
                opt_vars.to_xml(ele_item)
            self._c_delimiter(ele_items, (Token.COMMA, Token.NL))

        # colon
        assert self.tokens.pop().exact_type == Token.COLON
        ele.appendChild(DOM.Text(self.tokens.prev_space() + ':'))
        # body
        self._c_field_list(ele, 'body')
        parent.appendChild(ele)


    def c_Delete(self, parent):
        raise NotImplementedError()
    def c_Global(self, parent):
        raise NotImplementedError()
    def c_Nonlocal(self, parent):
        raise NotImplementedError()



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
