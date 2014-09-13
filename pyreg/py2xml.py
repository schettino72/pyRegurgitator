
import argparse
from tokenize import tokenize
import tokenize as Token
import xml.etree.ElementTree as ET
from xml.dom.minidom import getDOMImplementation, Text

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



# create DOM Document
impl = getDOMImplementation()
DOM = impl.createDocument(None, None, None)
DOM.Text = DOM.createTextNode
def Element(tag_name, text=None):
    ele = DOM.createElement(tag_name)
    if text:
        ele.appendChild(DOM.Text(text))
    return ele


def pos_byte2str(s):
    """return a list where the element value is the characther index/pos
    in the string from the byte position
    """
    pos_map = []
    for index, c in enumerate(s):
        pos_map.extend([index] * len(c.encode('utf-8')))
    return pos_map



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
        else: # pragma: no cover
            raise Exception("**** unimplemented coverter %s" % self.class_)


    def real_start(self):
        """Because of http://bugs.python.org/issue18374"""
        if self.class_ in ('Attribute', 'Subscript'):
            first = self.fields['value'].value
            return first.real_start()
        if self.class_ == 'BinOp':
            first = self.fields['left'].value
            return first.real_start()
        if self.class_ == 'Call':
            first = self.fields['func'].value
            return first.real_start()

        # AST node shows column in as byte position,
        # convert to char position in unicode string
        line_byte = self.line_list[self.line-1]
        try:
            line_uni = line_byte.decode('utf-8')
        except:
            raise Exception(line_byte)
        if len(line_byte) != len(line_uni):
            column = pos_byte2str(line_uni)[self.column]
        else:
            column = self.column
        return (self.line, column)

    ###########################################################
    # expr
    ###########################################################

    def expr_wrapper(func):
        """deals with optional "()" around expressions

        Because of http://bugs.python.org/issue18374
        The column number of nodes is not reliable.

        So we need to parse until the end of an expression
        to determine if the open parenthesis is being applied to
        the whole expression or just the first element.
        """
        def _build_expr(self, parent):
            next_token = self.tokens.next()
            if next_token.exact_type == Token.LPAR:
                if next_token.start < (self.line, self.column):
                    lpar_str = self.pop_merge_NL()
                    element1_start = self.tokens.next().start
                    self.tokens.lpar.append([lpar_str, element1_start, self])
            fragment = Element('frag')
            func(self, fragment)

            # detect if next significant token is RPAR
            has_rparen = False
            pos = -1
            while True:
                token = self.tokens.list[pos]
                if token.exact_type == Token.RPAR:
                    has_rparen = True
                    break
                elif token.exact_type in (Token.NL, Token.COMMENT):
                    pos -= 1
                    continue
                else:
                    break

            # check if the paren is closing this node
            if has_rparen and self.tokens.lpar:
                lpar_text, start, node = self.tokens.lpar[-1]
                #print(self.class_, start, self.real_start())
                if start == self.real_start() or node is self:
                    close_paren = True
                else:
                    close_paren = False
            else:
                close_paren = False

            # append paren (if any) and fragment to parent
            if close_paren:
                self.tokens.lpar.pop()
                parent.appendChild(DOM.Text(lpar_text))
                for child in fragment.childNodes:
                    parent.appendChild(child)
                text = self.pop_merge_NL(lspace=True, rspace=False)
                parent.appendChild(DOM.Text(text))
            else:
                for child in fragment.childNodes:
                    parent.appendChild(child)

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
            if next_token.exact_type not in (Token.NL, Token.COMMENT):
                if found_token:
                    break
                elif exact_type and exact_type != next_token.exact_type:
                    # FIXME deal with new line before figure out not a match
                    return text
                found_token = True
            self.tokens.pop()
            if include_left:
                text += self.tokens.prev_space()
            text += next_token.string
            include_left = True
        if rspace:
            text += self.tokens.space_right()
        return text

    def _c_delimiter(self, ele):
        """include space right"""
        delimiters = (Token.COMMA, Token.NL, Token.COMMENT)
        text = ''
        while self.tokens.next().exact_type in delimiters:
            token = self.tokens.pop()
            text += self.tokens.prev_space() + token.string
        text += self.tokens.space_right()
        ele.appendChild(DOM.Text(text))


    def c_Module(self, parent):
        ele = Element('Module')
        for stmt in self.fields['body'].value:
            stmt.to_xml(ele)
        return ele


    @expr_wrapper
    def c_Num(self, parent):
        token = self.tokens.pop()
        assert token.type == Token.NUMBER, self.tokens.current
        parent.appendChild(Element('Num', text=token.string))


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
                elif token.exact_type in (Token.NL, Token.COMMENT):
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
        elts = self.fields['elts'].value
        if elts:
            first = True
            for item in elts:
                if not first:
                    ele.appendChild(DOM.Text(self.tokens.space_right()))
                first = False
                item.to_xml(ele)
                text = self.pop_merge_NL(lspace=True, exact_type=Token.COMMA,
                                         rspace=False)
                ele.appendChild(DOM.Text(text))
        else:
            # special case, empty tuple is represented by an empty `()`
            assert self.tokens.pop().exact_type == Token.LPAR
            assert self.tokens.pop().exact_type == Token.RPAR
            ele.appendChild(DOM.Text('(' + self.tokens.text_prev2next()))
        parent.appendChild(ele)


    @expr_wrapper
    def c_List(self, parent):
        ele = Element(self.class_)
        if 'ctx' in self.fields: # set doesnt have ctx
            ele.setAttribute('ctx', self.fields['ctx'].value.class_)
        ele.appendChild(DOM.Text(self.pop_merge_NL())) #LSQB
        for item in self.fields['elts'].value:
            item.to_xml(ele)
            self._c_delimiter(ele)
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
            self._c_delimiter(ele)
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
        text = self.pop_merge_NL(lspace=True)
        attribute_ele.appendChild(DOM.Text(text))
        # attr name
        assert self.tokens.pop().type == Token.NAME, self.tokens.current
        attr_ele = Element('attr', text=self.tokens.current.string)
        attribute_ele.appendChild(attr_ele)
        parent.appendChild(attribute_ele)


    def c_Index(self, parent):
        ele = Element('Index')
        self.fields['value'].value.to_xml(ele)
        parent.appendChild(ele)

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
        ele.appendChild(DOM.Text(self.pop_merge_NL(rspace=False)))

        # upper
        upper = self.fields['upper'].value
        if upper:
            ele.appendChild(DOM.Text(self.tokens.space_right()))
            ele_upper = Element('upper')
            upper.to_xml(ele_upper)
            ele.appendChild(ele_upper)

        if self.tokens.next().exact_type == Token.COLON:
            colon2_text = self.pop_merge_NL(lspace=True, rspace=False)
            ele.appendChild(DOM.Text(colon2_text)) # COLON

        # step
        step = self.fields['step'].value
        if step:
            ele.appendChild(DOM.Text(self.tokens.prev_space()))
            ele_step = Element('step')
            step.to_xml(ele_step)
            ele.appendChild(ele_step)


    def c_ExtSlice(self, parent):
        dims = self.fields['dims'].value
        for item in dims:
            item.to_xml(parent)
            self._c_delimiter(parent)


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
        ele_slice.appendChild(DOM.Text(self.pop_merge_NL())) # LSQB
        self.fields['slice'].value.to_xml(ele_slice)
        close_text = self.pop_merge_NL(lspace=True, rspace=False) #RSQB
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
        op_text = self.tokens.current.string
        ele = Element(self.class_, text=op_text)
        self.tokens.write_non_ast_tokens(ele)
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
                cmp_text += self.pop_merge_NL()
            ele_op = Element('cmpop', text=cmp_text)
            ele.appendChild(ele_op)
            # value
            ele_value = Element('value')
            value.to_xml(ele_value)
            ele.appendChild(ele_value)
        parent.appendChild(ele)


    def _c_call_keyword(self, parent, keyword):
        ele_keyword = Element('keyword')
        parent.appendChild(ele_keyword)
        # arg
        assert self.tokens.pop().type == Token.NAME, self.tokens.current
        ele_arg = Element('arg', text=keyword.fields['arg'].value)
        ele_keyword.appendChild(ele_arg)
        # equal
        ele_keyword.appendChild(DOM.Text(self.pop_merge_NL(lspace=True)))
        # value
        ele_val = Element('value')
        keyword.fields['value'].value.to_xml(ele_val)
        ele_keyword.appendChild(ele_val)
        self._c_delimiter(parent)


    def _c_call_star_arg(self, ele, xarg, field):
        token = self.tokens.pop()
        # START DOUBLESTAR
        assert token.type == Token.OP, self.tokens.current
        text = token.string + self.tokens.space_right()
        ele_xargs = Element(field, text=text)
        xarg.to_xml(ele_xargs)
        ele.appendChild(ele_xargs)
        # optional comma
        self._c_delimiter(ele)


    def _c_call_keywords_starargs(self, ele):
        # keywords args can appear both before and after starargs
        # so it is required to sort them by position
        keywds_and_star = []

        # get starargs
        starargs = self.fields['starargs'].value
        if starargs:
            start_pos = (starargs.line, starargs.column)
            keywds_and_star.append((start_pos, 'starargs', starargs))

        # get keywords
        keywords = self.fields['keywords'].value
        for keyword in keywords:
            kw_val = keyword.fields['value'].value
            start_pos = (kw_val.line, kw_val.column)
            keywds_and_star.append((start_pos, 'keyword', keyword))

        # add keywords and starargs
        for _, atype, arg in sorted(keywds_and_star):
            if atype == 'starargs':
                self._c_call_star_arg(ele, arg, 'starargs')
            else:
                self._c_call_keyword(ele, arg)


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
                self._c_delimiter(ele_args)

        self._c_call_keywords_starargs(ele)

        kwargs = self.fields['kwargs'].value
        if kwargs:
            self._c_call_star_arg(ele, kwargs, 'kwargs')

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
        ele.appendChild(DOM.Text(self.pop_merge_NL(lspace=True)))

        # test
        ele_test = Element('test')
        self.fields['test'].value.to_xml(ele_test)
        ele.appendChild(ele_test)

        # else
        ele.appendChild(DOM.Text(self.pop_merge_NL(lspace=True)))

        # orelse
        ele_orelse = Element('orelse')
        self.fields['orelse'].value.to_xml(ele_orelse)
        ele.appendChild(ele_orelse)


    @expr_wrapper
    def c_GeneratorExp(self, parent):
        ele = Element(self.class_)
        if self.class_ != 'GeneratorExp':
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
            ele.appendChild(DOM.Text(self.tokens.text_prev2next()))
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
            for_text = self.pop_merge_NL(lspace=True) # for
            ele_comp.appendChild(DOM.Text(for_text))
            # target
            ele_target = Element('target')
            gen.fields['target'].value.to_xml(ele_target)
            ele_comp.appendChild(ele_target)
            # in
            in_text = self.pop_merge_NL(lspace=True) # in
            ele_comp.appendChild(DOM.Text(in_text))
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
                    if_text = self.pop_merge_NL(lspace=True) # if
                    ele_if.appendChild(DOM.Text(if_text))
                    # target
                    gif.to_xml(ele_if)

        # close brackets
        if self.class_ != 'GeneratorExp':
            close_text = self.pop_merge_NL(lspace=True, rspace=False)
            ele.appendChild(DOM.Text(close_text))
        parent.appendChild(ele)

    c_ListComp = c_GeneratorExp
    c_SetComp = c_GeneratorExp
    c_DictComp = c_GeneratorExp


    @expr_wrapper
    def c_Lambda(self, parent):
        assert self.tokens.pop().string == 'lambda'
        ele = Element('Lambda', text='lambda' + self.tokens.space_right())
        # arguments
        ele_arguments = Element('arguments')
        self._arguments(ele_arguments)
        ele.appendChild(ele_arguments)

        # COLON :
        assert self.tokens.pop().exact_type == Token.COLON
        ele.appendChild(DOM.Text(':' + self.tokens.space_right()))

        # body
        ele_body = Element('body')
        self.fields['body'].value.to_xml(ele_body)
        ele.appendChild(ele_body)
        parent.appendChild(ele)



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


    def c_Delete(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().string == 'del'
        ele = Element('Delete', text='del' + self.tokens.space_right())
        # targets
        ele_targets = Element('targets')
        ele.appendChild(ele_targets)
        for target in self.fields['targets'].value:
            target.to_xml(ele_targets)
            # optional comma
            self._c_delimiter(ele_targets)
        parent.appendChild(ele)


    def c_Global(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().type == Token.NAME
        text = self.tokens.current.string + self.tokens.space_right()
        ele = Element(self.class_, text=text)
        # names
        ele_names = Element('names')
        ele.appendChild(ele_names)
        for name in self.fields['names'].value:
            assert self.tokens.pop().type == Token.NAME
            ele_name = Element('name', text=name.value)
            ele_names.appendChild(ele_name)
            # optional comma
            self._c_delimiter(ele_names)
        parent.appendChild(ele)

    c_Nonlocal = c_Global


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
            alias = Element('alias')

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
            self._c_delimiter(ele)


    def c_Import(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        assert self.tokens.pop().string == 'import'
        ele = Element('Import', text='import' + self.tokens.space_right())
        self._c_import_names(ele)
        parent.appendChild(ele)

    def c_ImportFrom(self, parent):
        self.tokens.write_non_ast_tokens(parent)

        ele = Element('ImportFrom')
        # level
        ele.setAttribute('level', str(self.fields['level'].value))

        # from <module>
        assert self.tokens.pop().string == 'from'
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
        ele.appendChild(DOM.Text(self.tokens.text_prev2next()))

        # parenthesis
        token = self.tokens.next()
        has_paren = False
        if token.exact_type == Token.LPAR:
            has_paren = True
            ele.appendChild(DOM.Text(self.pop_merge_NL())) # LPAR

        # names
        names = Element('names')
        self._c_import_names(names)
        ele.appendChild(names)

        if has_paren:
            ele.appendChild(DOM.Text(self.pop_merge_NL())) #RPAR

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


    def _arg_element(self, arg, default=None, kwonly=False):
        """:return: XML node"""
        arg_ele = Element('arg')
        arg_ele.setAttribute('name', arg.fields['arg'].value)
        arg_ele.appendChild(DOM.Text(arg.fields['arg'].value))
        if kwonly:
            arg_ele.setAttribute('kwonly', None)

        ann = arg.fields['annotation'].value
        if ann:
            assert self.tokens.pop().exact_type == Token.COLON
            ann_ele = Element('annotation')
            ann_text = self.tokens.text_prev2next()
            ann_ele.appendChild(DOM.Text(ann_text))
            ann.to_xml(ann_ele)
            arg_ele.appendChild(ann_ele)

        # keyword_only arg might not have a default None instead of an ast node
        if hasattr(default, 'fields'):
            assert self.tokens.pop().exact_type == Token.EQUAL
            default_ele = Element('default')
            equal_text = self.tokens.text_prev2next()
            default_ele.appendChild(DOM.Text(equal_text))
            default.to_xml(default_ele)
            arg_ele.appendChild(default_ele)

        return arg_ele


    def _star_arg(self, ele_arguments, arguments, field):
        """handle vararg and kwarg"""
        arg = arguments.fields[field].value
        if arg:
            ele_arg = Element(field)
            token = self.tokens.pop()
             # START / DOUBLESTAR
            assert token.type == Token.OP, self.tokens.current
            star_text = token.string
            ele_arg.appendChild(DOM.Text(star_text))
            assert self.tokens.pop().type == Token.NAME
            ele_arg.appendChild(DOM.Text(self.tokens.prev_space()))
            ele_arg.appendChild(self._arg_element(arg))
            ele_arguments.appendChild(ele_arg)
            self._c_delimiter(ele_arguments)

    def _arguments(self, ele_arguments):
        """convert arugments for FuncDef and Lambda"""
        arguments = self.fields['args'].value
        # args
        args = arguments.fields['args'].value
        if args:
            f_defaults = arguments.fields['defaults'].value
            defaults = ([None] * (len(args) - len(f_defaults))) + f_defaults
            for arg, default in zip(args, defaults):
                assert self.tokens.pop().type == Token.NAME, self.tokens.current
                arg_ele = self._arg_element(arg, default)
                ele_arguments.appendChild(arg_ele)
                self._c_delimiter(ele_arguments)

        # vararg
        self._star_arg(ele_arguments, arguments, 'vararg')

        # kwonlyargs
        kwonlyargs = arguments.fields['kwonlyargs'].value
        kw_defaults = arguments.fields['kw_defaults'].value
        if kwonlyargs and not arguments.fields['vararg'].value:
            # if there is kwonly args but no vararg it needs an extra '*' arg
            assert self.tokens.pop().exact_type == Token.STAR
            ele_arguments.appendChild(DOM.Text('*' + self.tokens.space_right()))
            self._c_delimiter(ele_arguments)
        for arg, default in zip(kwonlyargs, kw_defaults):
            assert self.tokens.pop().type == Token.NAME, self.tokens.current
            arg_ele = self._arg_element(arg, default, kwonly=True)
            ele_arguments.appendChild(arg_ele)
            self._c_delimiter(ele_arguments)

        # kwarg
        self._star_arg(ele_arguments, arguments, 'kwarg')


    def _c_decorator_list(self, parent):
        decorators = self.fields['decorator_list'].value
        for deco in decorators:
            assert self.tokens.pop().exact_type == Token.AT
            deco_text = '@' + self.tokens.space_right()
            ele_deco = Element('decorator', text=deco_text)
            parent.appendChild(ele_deco)
            deco.to_xml(ele_deco)
            self.tokens.write_non_ast_tokens(parent)


    def c_FunctionDef(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        ele = Element('FunctionDef')

        # decorator
        self._c_decorator_list(ele)

        # def
        assert self.tokens.pop().string == 'def'
        ele.appendChild(DOM.Text('def' + self.tokens.space_right()))

        # name
        assert self.tokens.pop().type == Token.NAME
        name = self.fields['name'].value
        ele.setAttribute('name', name)
        ele.appendChild(DOM.Text(name))

        # args
        start_arguments_text = self.pop_merge_NL(lspace=True) # LPAR
        ele_arguments = Element('arguments', text=start_arguments_text)
        self._arguments(ele_arguments)

        # close parent + colon
        assert self.tokens.pop().exact_type == Token.RPAR
        close_args_text = ')' + self.tokens.space_right()
        ele_arguments.appendChild(DOM.Text(close_args_text))

        returns = self.fields['returns'].value
        if returns:
            assert self.tokens.pop().type == Token.OP # ->
            arrow_text = '->' + self.tokens.space_right()
            ele_returns = Element('returns', text=arrow_text)
            ele_arguments.appendChild(ele_returns)
            returns.to_xml(ele_returns)
            ele_returns.appendChild(DOM.Text(self.tokens.space_right()))

        # colon
        assert self.tokens.pop().exact_type == Token.COLON
        colon_text = ':'
        ele_arguments.appendChild(DOM.Text(colon_text))
        ele.appendChild(ele_arguments)

        # body
        self._c_field_list(ele, 'body')
        parent.appendChild(ele)


    def c_ClassDef(self, parent):
        self.tokens.write_non_ast_tokens(parent)
        ele = Element('ClassDef')

        # decorator
        self._c_decorator_list(ele)

        # class
        assert self.tokens.pop().string == 'class'
        ele.appendChild(DOM.Text('class'))

        # name
        assert self.tokens.pop().type == Token.NAME
        name = self.fields['name'].value
        ele.setAttribute('name', name)
        text = self.tokens.prev_space() + name
        ele.appendChild(DOM.Text(text))

        # arguments
        if self.tokens.next().exact_type == Token.LPAR:
            start_arguments_text = self.pop_merge_NL(lspace=True)
            ele_arguments = Element('arguments', text=start_arguments_text)

            bases = self.fields['bases'].value
            for item in bases:
                ele_base = Element('base')
                item.to_xml(ele_base)
                ele_arguments.appendChild(ele_base)
                self._c_delimiter(ele_arguments)

            self._c_call_keywords_starargs(ele_arguments)

            kwargs = self.fields['kwargs'].value
            if kwargs:
                self._c_call_star_arg(ele_arguments, kwargs, 'kwargs')

            # close arguments
            assert self.tokens.pop().exact_type == Token.RPAR
            ele_arguments.appendChild(DOM.Text(')'))
            ele.appendChild(ele_arguments)

        # colon
        assert self.tokens.pop().exact_type == Token.COLON
        ele.appendChild(DOM.Text(self.tokens.prev_space() + ':'))

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
            self.tokens.write_non_ast_tokens(ele, rspace=False)
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
        # exc
        exc = self.fields['exc'].value
        if exc:
            ele.appendChild(DOM.Text(self.tokens.space_right()))
            ele_exc = Element('exc')
            exc.to_xml(ele_exc)
            ele.appendChild(ele_exc)

        # cause
        cause = self.fields['cause'].value
        if cause:
            assert self.tokens.pop().string == 'from'
            ele.appendChild(DOM.Text(self.tokens.text_prev2next()))
            ele_cause = Element('cause')
            cause.to_xml(ele_cause)
            ele.appendChild(ele_cause)
        parent.appendChild(ele)


    def c_ExceptHandler(self, parent):
        ele = Element('ExceptHandler')
        parent.appendChild(ele)
        # except
        self.tokens.write_non_ast_tokens(ele)
        assert self.tokens.pop().string == 'except', self.tokens.current
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
        assert self.tokens.pop().string == 'try', self.tokens.current
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
            self.tokens.write_non_ast_tokens(ele, rspace=False)
            assert self.tokens.pop().string == 'else', self.tokens.current
            else_text = self.tokens.text_prev2next() + ':'
            assert self.tokens.pop().exact_type == Token.COLON
            self._c_field_list(ele, 'orelse', text=else_text)

        final = self.fields['finalbody'].value
        if final:
            self.tokens.write_non_ast_tokens(ele, rspace=False)
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
            self._c_delimiter(ele_items)

        # colon
        assert self.tokens.pop().exact_type == Token.COLON
        ele.appendChild(DOM.Text(self.tokens.prev_space() + ':'))
        # body
        self._c_field_list(ele, 'body')
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
        # helper to determine in which expression the () is being applied
        # list of tuple with 3 elements:
        #  - string containing Token.LPAR
        #  - 2-tuple with line, column position of first element in expr
        #  - first node to see the LPAR
        self.lpar = []

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
    def write_non_ast_tokens(self, parent_ele, rspace=True):
        text = ''
        while self.next().exact_type in self.NON_AST_TOKENS:
            token = self.pop()
            text += self.prev_space() + token.string
        if rspace:
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


def xml2py(filename):
    """convert XML back to python

    To convert back, just get all text from all nodes.
    """
    with open(filename) as fp_in:
        root = ET.fromstring(fp_in.read())
        return ET.tostring(root, encoding='unicode', method='text')


def main(args=None): # pragma: no cover
    """command line program for py2xml"""
    import sys
    description = """convert python module to XML representation"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-r', '--reverse', dest='reverse',
                        action='store_true',
                        help='reverse - convert XML back to python code')
    parser.add_argument(
        'py_file', metavar='MODULE', nargs=1,
        help='python module')

    args = parser.parse_args(args)
    if args.reverse:
        sys.stdout.buffer.write(xml2py(args.py_file[0]).encode('utf8'))
    else:
        sys.stdout.buffer.write(py2xml(args.py_file[0]).encode('utf8'))


if __name__ == "__main__": # pragma: no cover
    main()
