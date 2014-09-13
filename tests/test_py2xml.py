
import xml.etree.ElementTree as ET

import pytest

from pyreg.py2xml import pos_byte2str, py2xml


class TestFixUnicodeColumnPosition:
    def test_pos_byte2str(self):
        s = "coäs"
        x = pos_byte2str(s)
        assert x[0] == 0
        assert x[1] == 1
        assert x[2] == 2
        assert x[3] == 2
        assert x[4] == 3



@pytest.fixture
def s2xml(tmpdir):
    """return fixture function to easy convertion of python code to XML"""
    def py_str2xml(string, strip_body=True):
        p = tmpdir.join("x.py")
        p.write(string)
        result = py2xml(p.strpath)
        if strip_body:
            # the slice 14:-16 is to remove the string of
            # the module and body tags: <Module> ... </Module>
            return result[8:-9]
        return result
    return py_str2xml



class TestSimpleExpressions:
    def test_num(self, s2xml):
        assert s2xml('6') == '<Expr><Num>6</Num></Expr>'

    def test_num_decimal(self, s2xml):
        assert s2xml('.5') == '<Expr><Num>.5</Num></Expr>'

    def test_str(self, s2xml):
        assert s2xml('"my string"') == \
            '<Expr><Str><s>"my string"</s></Str></Expr>'
        assert s2xml("'''my 2'''") == \
            "<Expr><Str><s>'''my 2'''</s></Str></Expr>"


    def test_str_multiline(self, s2xml):
        string = '''"""line 1
line 2""" '''
        assert s2xml(string) == \
            '<Expr><Str><s>"""line 1\nline 2"""</s></Str></Expr>'


    def test_str_implicit_concat(self, s2xml):
        string = "'part 1' ' /part 2'"
        assert s2xml(string) == \
            "<Expr><Str><s>'part 1'</s> <s>' /part 2'</s></Str></Expr>"

    def test_str_implicit_concat_line_continuation(self, s2xml):
        string = r"""'part 1'  \
 ' /part 2'"""
        assert s2xml(string) == "<Expr><Str><s>'part 1'</s>  \\\n"\
            " <s>' /part 2'</s></Str></Expr>"

    def test_str_expr_concat(self, s2xml):
        string = """('part 1'\n ' /part 2')"""
        assert s2xml(string) == \
            "<Expr>(<Str><s>'part 1'</s>\n"\
            " <s>' /part 2'</s></Str>)</Expr>"

    def test_str_expr_concat_with_comment(self, s2xml):
        string = """('part 1' # ho \n ' /part 2')"""
        assert s2xml(string) == \
            "<Expr>(<Str><s>'part 1'</s> # ho \n"\
            " <s>' /part 2'</s></Str>)</Expr>"

    def test_bytes(self, s2xml):
        assert s2xml("b'as'") == "<Expr><Bytes><s>b'as'</s></Bytes></Expr>"

    def test_bytes_implicit_concat(self, s2xml):
        string = "b'part 1' b' /part 2'"
        assert s2xml(string) == \
            "<Expr><Bytes><s>b'part 1'</s> <s>b' /part 2'</s></Bytes></Expr>"

    def test_ellipsis(self, s2xml):
        assert s2xml('...') == \
            "<Expr><Ellipsis>...</Ellipsis></Expr>"


class TestTuple:
    def test_tuple(self, s2xml):
        assert s2xml('1,2,3') == '<Expr><Tuple ctx="Load"><Num>1</Num>'\
            ',<Num>2</Num>,<Num>3</Num></Tuple></Expr>'

    def test_empty(self, s2xml):
        assert s2xml('()') == '<Expr><Tuple ctx="Load">()</Tuple></Expr>'

    def test_tuple_space(self, s2xml):
        assert s2xml('1, 2 ,  3') == '<Expr><Tuple ctx="Load">'\
            '<Num>1</Num>, <Num>2</Num> ,  <Num>3</Num></Tuple></Expr>'

    def test_tuple_end_comma(self, s2xml):
        assert s2xml('1, 2 ,') == '<Expr><Tuple ctx="Load">'\
            '<Num>1</Num>, <Num>2</Num> ,</Tuple></Expr>'


class TestComment:
    def test_comment(self, s2xml):
        assert s2xml('# hi') == \
            '# hi'

    def test_expr_comment(self, s2xml):
        assert s2xml('3 # hi') == \
            '<Expr><Num>3</Num></Expr> # hi'

    def test_tupple_comment(self, s2xml):
        assert s2xml('3, 4 # hi') == \
            '<Expr><Tuple ctx="Load"><Num>3</Num>, <Num>4</Num>'\
            ' # hi</Tuple></Expr>'


class TestStarred:
    def test_starred(self, s2xml):
        assert s2xml('*foo') == \
            '<Expr><Starred ctx="Load">'\
            '*<Name ctx="Load" name="foo">foo</Name>'\
            '</Starred></Expr>'


class TestExpressions:
    def test_expr_in_parenthesis(self, s2xml):
        assert s2xml('(3 )') == '<Expr>(<Num>3</Num> )</Expr>'

    def test_tuple_in_parenthesis(self, s2xml):
        assert s2xml('( 3 , 4  )') == \
            '<Expr>( <Tuple ctx="Load"><Num>3</Num> , <Num>4</Num>'\
            '</Tuple>  )</Expr>'

    def test_tuple_in_parenthesis_comma(self, s2xml):
        assert s2xml('( 3 , 4 , )') == \
            '<Expr>( <Tuple ctx="Load"><Num>3</Num> , <Num>4</Num>'\
            ' ,</Tuple> )</Expr>'

    def test_expr_in_parenthesis2(self, s2xml):
        assert s2xml('(  3 )') == '<Expr>(  <Num>3</Num> )</Expr>'

    def test_expr_in_parenthesis3(self, s2xml):
        assert s2xml('(  3\n )') == '<Expr>(  <Num>3</Num>\n )</Expr>'

    def test_expr_in_parenthesis4(self, s2xml):
        assert s2xml('(\n  3 )') == '<Expr>(\n  <Num>3</Num> )</Expr>'

    def test_expr_nl_comment(self, s2xml):
        assert s2xml('(\n  3,\n # hi,\n4 )') == \
            '<Expr>(\n  <Tuple ctx="Load">'\
            '<Num>3</Num>,\n # hi,\n<Num>4</Num></Tuple> )</Expr>'

    def test_expr_semi_colon_separated(self, s2xml):
        assert s2xml('3 ; 5') == \
            '<Expr><Num>3</Num></Expr>'\
            ' ; <Expr><Num>5</Num></Expr>'


class TestSet:
    def test_set(self, s2xml):
        assert s2xml('{ 1 , 2 , }') == \
            '<Expr><Set>{ <Num>1</Num>'\
            ' , <Num>2</Num> , }</Set></Expr>'



class TestList:
    def test_list(self, s2xml):
        assert s2xml('[1,2,3]') == '<Expr><List ctx="Load">[<Num>1</Num>'\
            ',<Num>2</Num>,<Num>3</Num>]</List></Expr>'

    def test_list_empty(self, s2xml):
        assert s2xml('[ ]') == '<Expr><List ctx="Load">[ ]</List></Expr>'

    def test_list_end_comma(self, s2xml):
        assert s2xml('[ 1 , 2 , ]') == '<Expr><List ctx="Load">[ <Num>1</Num>'\
            ' , <Num>2</Num> , ]</List></Expr>'

    def test_list_multiline(self, s2xml):
        assert s2xml('[ 1,\n  2,\n ]') == \
            '<Expr><List ctx="Load">[ <Num>1</Num>'\
            ',\n  <Num>2</Num>,\n ]</List></Expr>'

    def test_list_multiline2(self, s2xml):
        assert s2xml('[\n 1,\n  2,\n ]') == \
            '<Expr><List ctx="Load">[\n <Num>1</Num>'\
            ',\n  <Num>2</Num>,\n ]</List></Expr>'

    def test_list_multiline_comment(self, s2xml):
        assert s2xml('[ 1, # hey\n  2,\n ]') == \
            '<Expr><List ctx="Load">[ <Num>1</Num>'\
            ', # hey\n  <Num>2</Num>,\n ]</List></Expr>'


class TestDict:
    def test_dict(self, s2xml):
        assert s2xml('{"a": 2}') == \
            '<Expr><Dict>{'\
            '<item><Str><s>"a"</s></Str>: <Num>2</Num></item>}</Dict></Expr>'

    def test_dict_multiline(self, s2xml):
        assert s2xml('{\n\n  "a": 2,\n"b" :3\n}') == \
            '<Expr><Dict>{\n\n  '\
            '<item><Str><s>"a"</s></Str>: <Num>2</Num></item>'\
            ',\n<item><Str><s>"b"</s></Str> :<Num>3</Num></item>'\
            '\n}</Dict></Expr>'

    def test_dict_multiline_comma(self, s2xml):
        assert s2xml('{\n\n  "a": 2,\n"b" :3 \n, \n}') == \
            '<Expr><Dict>{\n\n  '\
            '<item><Str><s>"a"</s></Str>: <Num>2</Num></item>'\
            ',\n<item><Str><s>"b"</s></Str> :<Num>3</Num></item>'\
            ' \n, \n}</Dict></Expr>'


class TestName:
    def test_name(self, s2xml):
        assert s2xml('foo') == \
            '<Expr><Name ctx="Load" name="foo">foo</Name></Expr>'


class TestNameConstant:
    def test_name(self, s2xml):
        assert s2xml('None') == \
            '<Expr><NameConstant>None</NameConstant></Expr>'


class TestAtrribute:
    def test_attr(self, s2xml):
        assert s2xml('foo.bar') == \
            '<Expr><Attribute ctx="Load">'\
            '<value><Name ctx="Load" name="foo">foo</Name></value>'\
            '.<attr>bar</attr></Attribute></Expr>'

    def test_attr2(self, s2xml):
        assert s2xml('foo.bar.baz') == \
            '<Expr><Attribute ctx="Load"><value>'\
            '<Attribute ctx="Load"><value><Name ctx="Load" name="foo">'\
            'foo</Name></value>.<attr>bar</attr></Attribute></value>'\
            '.<attr>baz</attr></Attribute></Expr>'

    def test_attr_par(self, s2xml):
        assert s2xml('(foo).bar') == \
            '<Expr><Attribute ctx="Load">'\
            '<value>(<Name ctx="Load" name="foo">foo</Name>)</value>'\
            '.<attr>bar</attr></Attribute></Expr>'

    def test_attr_nl(self, s2xml):
        assert s2xml('(foo\n .bar)') == \
            '<Expr>(<Attribute ctx="Load">'\
            '<value><Name ctx="Load" name="foo">foo</Name></value>'\
            '\n .<attr>bar</attr></Attribute>)</Expr>'

    def test_attr_space(self, s2xml):
        assert s2xml('foo .bar') == \
            '<Expr><Attribute ctx="Load">'\
            '<value><Name ctx="Load" name="foo">foo</Name></value>'\
            ' .<attr>bar</attr></Attribute></Expr>'


class TestSubscript:
    def test_index(self, s2xml):
        assert s2xml('foo[2]') == \
            '<Expr><Subscript ctx="Load">'\
            '<value><Name ctx="Load" name="foo">foo</Name></value>'\
            '<slice>[<Index><Num>2</Num></Index>]</slice>'\
            '</Subscript></Expr>'

    def test_subscript_space_after(self, s2xml):
        assert s2xml('foo[2] #') == \
            '<Expr><Subscript ctx="Load">'\
            '<value><Name ctx="Load" name="foo">foo</Name></value>'\
            '<slice>[<Index><Num>2</Num></Index>] #</slice>'\
            '</Subscript></Expr>'

    def test_slice_lower(self, s2xml):
        assert s2xml('foo[1 : ]') == \
            '<Expr><Subscript ctx="Load">'\
            '<value><Name ctx="Load" name="foo">foo</Name></value>'\
            '<slice>[<Slice><lower><Num>1</Num></lower> :</Slice> ]</slice>'\
            '</Subscript></Expr>'

    def test_slice_upper(self, s2xml):
        assert s2xml('foo[ : 3 ]') == \
            '<Expr><Subscript ctx="Load">'\
            '<value><Name ctx="Load" name="foo">foo</Name></value>'\
            '<slice>[ <Slice>: <upper><Num>3</Num></upper></Slice> ]</slice>'\
            '</Subscript></Expr>'

    def test_slice_step(self, s2xml):
        assert s2xml('foo[: : 3 ]') == \
            '<Expr><Subscript ctx="Load">'\
            '<value><Name ctx="Load" name="foo">foo</Name></value>'\
            '<slice>[<Slice>: : <step><Num>3</Num></step></Slice> ]</slice>'\
            '</Subscript></Expr>'

    def test_slice_second_colon_without_step(self, s2xml):
        assert s2xml('foo[1:: ]') == \
            '<Expr><Subscript ctx="Load">'\
            '<value><Name ctx="Load" name="foo">foo</Name></value>'\
            '<slice>[<Slice><lower><Num>1</Num></lower>::</Slice> ]</slice>'\
            '</Subscript></Expr>'

    def test_slice_multiline(self, s2xml):
        assert s2xml('foo[\n 1 :\n 3 \n]') == \
            '<Expr><Subscript ctx="Load">'\
            '<value><Name ctx="Load" name="foo">foo</Name></value>'\
            '<slice>[\n <Slice><lower><Num>1</Num></lower> :\n '\
            '<upper><Num>3</Num></upper></Slice> \n]</slice>'\
            '</Subscript></Expr>'

    def test_slice_extended(self, s2xml):
        assert s2xml('ex1[1:3:, ::2]') == \
            '<Expr><Subscript ctx="Load">'\
            '<value><Name ctx="Load" name="ex1">ex1</Name></value>'\
            '<slice>[<Slice><lower><Num>1</Num></lower>:'\
            '<upper><Num>3</Num></upper>:</Slice>, '\
            '<Slice>::<step><Num>2</Num></step></Slice>]</slice>'\
            '</Subscript></Expr>'



class TestBinOp:
    def test_binop_add(self, s2xml):
        assert s2xml('1 + 2') == \
            '<Expr><BinOp><Num>1</Num><Add> + </Add><Num>2</Num></BinOp></Expr>'

    def test_binop_add_space(self, s2xml):
        assert s2xml('3+  4') == \
            '<Expr><BinOp><Num>3</Num><Add>+  </Add><Num>4</Num></BinOp></Expr>'

    def test_binop_multiply(self, s2xml):
        assert s2xml('1 *2') == \
            '<Expr><BinOp><Num>1</Num><Mult> *</Mult><Num>2</Num></BinOp></Expr>'

    def test_binop_subtract(self, s2xml):
        assert s2xml('1 - 2') == \
            '<Expr><BinOp><Num>1</Num><Sub> - </Sub><Num>2</Num></BinOp></Expr>'

    def test_expr_with_line_continuation(self, s2xml):
        assert s2xml('''5 + \\\n  9''') == \
            '<Expr><BinOp><Num>5</Num><Add> + \\\n  </Add><Num>9</Num></BinOp></Expr>'

    def test_binop_multiline(self, s2xml):
        assert s2xml('''(1 +\n 1)''') == \
            '<Expr>(<BinOp><Num>1</Num><Add> +\n </Add>'\
            '<Num>1</Num></BinOp>)</Expr>'

    def test_binop_multiline_xtreme(self, s2xml):
        assert s2xml('''(1 \n\n+\n\n 1)''') == \
            '<Expr>(<BinOp><Num>1</Num><Add> \n\n+\n\n </Add>'\
            '<Num>1</Num></BinOp>)</Expr>'

    def test_expr_in_parenthesis_any(self, s2xml):
        assert s2xml('( 2+ (3 )  )') == \
            '<Expr>( <BinOp><Num>2</Num><Add>+ </Add>(<Num>3</Num>'\
            ' )</BinOp>  )</Expr>'

    def test_expr_parenthesis_first_ele(self, s2xml):
        assert s2xml('(1) + 2') == \
            '<Expr><BinOp>(<Num>1</Num>)<Add> + </Add><Num>2</Num>'\
            '</BinOp></Expr>'





class TestBoolOp:
    def test_bool_op(self, s2xml):
        assert s2xml('1 and 2') == \
            '<Expr><BoolOp op="And">'\
            '<value><Num>1</Num></value> and '\
            '<value><Num>2</Num></value>'\
            '</BoolOp></Expr>'

    def test_bool_op_more_than_2(self, s2xml):
        assert s2xml('1 or 2 or 3') == \
            '<Expr><BoolOp op="Or">'\
            '<value><Num>1</Num></value> or '\
            '<value><Num>2</Num></value> or '\
            '<value><Num>3</Num></value>'\
            '</BoolOp></Expr>'

    def test_bool_op_multiline(self, s2xml):
        assert s2xml('(1 and\n 2)') == \
            '<Expr>(<BoolOp op="And">'\
            '<value><Num>1</Num></value> and\n '\
            '<value><Num>2</Num></value>'\
            '</BoolOp>)</Expr>'



class TestUnaryOp:
    def test_unary_not(self, s2xml):
        assert s2xml('not 2') == \
            '<Expr><UnaryOp op="Not">'\
            'not <Num>2</Num>'\
            '</UnaryOp></Expr>'

    def test_unary_invert(self, s2xml):
        assert s2xml('~ 2') == \
            '<Expr><UnaryOp op="Invert">'\
            '~ <Num>2</Num>'\
            '</UnaryOp></Expr>'

    def test_unary_add(self, s2xml):
        assert s2xml('+ 2') == \
            '<Expr><UnaryOp op="UAdd">'\
            '+ <Num>2</Num>'\
            '</UnaryOp></Expr>'

    def test_unary_sub(self, s2xml):
        assert s2xml('- 2') == \
            '<Expr><UnaryOp op="USub">'\
            '- <Num>2</Num>'\
            '</UnaryOp></Expr>'

    def test_unary_multiline(self, s2xml):
        assert s2xml('(not\n 2)') == \
            '<Expr>(<UnaryOp op="Not">'\
            'not\n <Num>2</Num>'\
            '</UnaryOp>)</Expr>'


class TestCompare:
    def test_compare(self, s2xml):
        assert s2xml('1 < 2') == \
            '<Expr><Compare>'\
            '<value><Num>1</Num></value>'\
            '<cmpop> &lt; </cmpop>'\
            '<value><Num>2</Num></value>'\
            '</Compare></Expr>'

    def test_compare_2_token_cmp(self, s2xml):
        assert s2xml('1 is  not 2') == \
            '<Expr><Compare>'\
            '<value><Num>1</Num></value>'\
            '<cmpop> is  not </cmpop>'\
            '<value><Num>2</Num></value>'\
            '</Compare></Expr>'

    def test_compare_multi(self, s2xml):
        assert s2xml('1 < 2 <= 3') == \
            '<Expr><Compare>'\
            '<value><Num>1</Num></value>'\
            '<cmpop> &lt; </cmpop>'\
            '<value><Num>2</Num></value>'\
            '<cmpop> &lt;= </cmpop>'\
            '<value><Num>3</Num></value>'\
            '</Compare></Expr>'

    def test_compare_multiline(self, s2xml):
        assert s2xml('(1 <\n 2)') == \
            '<Expr>(<Compare>'\
            '<value><Num>1</Num></value>'\
            '<cmpop> &lt;\n </cmpop>'\
            '<value><Num>2</Num></value>'\
            '</Compare>)</Expr>'


class TestIfExp:
    def test_ifexp(self, s2xml):
        assert s2xml('1 if True else 0') == \
            '<Expr><IfExpr><body><Num>1</Num></body>'\
            ' if <test><NameConstant>True</NameConstant></test>'\
            ' else <orelse><Num>0</Num></orelse>'\
            '</IfExpr></Expr>'


class TestMultiline:
    def test_2_lines(self, s2xml):
        assert s2xml('6\n7') == \
            '<Expr><Num>6</Num></Expr>\n<Expr><Num>7</Num></Expr>'

    def test_blank_line(self, s2xml):
        assert s2xml('6\n\n7') == \
            '<Expr><Num>6</Num></Expr>\n\n<Expr><Num>7</Num></Expr>'

    def test_comment(self, s2xml):
        assert s2xml('6\n# my comment\n7') == \
            '<Expr><Num>6</Num></Expr>\n# my comment\n<Expr><Num>7</Num></Expr>'

    def test_2line_end_with_op(self, s2xml):
        assert s2xml('(4)\n(5)\n') == \
            '<Expr>(<Num>4</Num>)</Expr>\n'\
            '<Expr>(<Num>5</Num>)</Expr>\n'



class TestCall:
    def test_call(self, s2xml):
        assert s2xml('foo()') == \
            '<Expr><Call><func><Name ctx="Load" name="foo">foo</Name></func>'\
            '()</Call></Expr>'

    def test_call_arg(self, s2xml):
        assert s2xml('print(2)') == \
            '<Expr><Call><func><Name ctx="Load" name="print">print</Name></func>'\
            '(<args><Num>2</Num></args>)'\
            '</Call></Expr>'

    def test_call_arg_spaces(self, s2xml):
        assert s2xml('print (  2   )') == \
            '<Expr><Call>'\
            '<func><Name ctx="Load" name="print">print</Name></func>'\
            ' (  <args><Num>2</Num>   </args>)'\
            '</Call></Expr>'

    def test_call_multiline(self, s2xml):
        assert s2xml('print ( \n  2\n\n   )') == \
            '<Expr><Call>'\
            '<func><Name ctx="Load" name="print">print</Name></func>'\
            ' ( \n  <args><Num>2</Num>\n\n   </args>)'\
            '</Call></Expr>'

    def test_call_arg2(self, s2xml):
        assert s2xml('print(2,  "xxx" )') == \
            '<Expr><Call><func><Name ctx="Load" name="print">print</Name></func>'\
            '(<args><Num>2</Num>,  <Str><s>"xxx"</s></Str> </args>)'\
            '</Call></Expr>'

    def test_call_comment(self, s2xml):
        assert s2xml('foo() #') == \
            '<Expr><Call><func><Name ctx="Load" name="foo">foo</Name></func>'\
            '()</Call></Expr> #'

    def test_call_keyword(self, s2xml):
        assert s2xml('foo( x = 2 )') == \
            '<Expr><Call><func><Name ctx="Load" name="foo">foo</Name></func>'\
            '( <keyword><arg>x</arg> = <value><Num>2</Num></value>'\
            '</keyword> )'\
            '</Call></Expr>'

    def test_call_keyword_multiline(self, s2xml):
        assert s2xml('foo( x =\n 2 )') == \
            '<Expr><Call><func><Name ctx="Load" name="foo">foo</Name></func>'\
            '( <keyword><arg>x</arg> =\n <value><Num>2</Num></value>'\
            '</keyword> )'\
            '</Call></Expr>'

    def test_call_arg_keyword(self, s2xml):
        assert s2xml('foo(1, x=2)') == \
            '<Expr><Call><func><Name ctx="Load" name="foo">foo</Name></func>'\
            '(<args><Num>1</Num>, </args>'\
            '<keyword><arg>x</arg>=<value><Num>2</Num></value>'\
            '</keyword>)'\
            '</Call></Expr>'

    def test_call_starargs(self, s2xml):
        assert s2xml('foo( *a)') == \
            '<Expr><Call><func><Name ctx="Load" name="foo">foo</Name></func>'\
            '( <starargs>*<Name ctx="Load" name="a">a</Name></starargs>)'\
            '</Call></Expr>'

    def test_call_kwargs(self, s2xml):
        assert s2xml('foo(**a)') == \
            '<Expr><Call><func><Name ctx="Load" name="foo">foo</Name></func>'\
            '(<kwargs>**<Name ctx="Load" name="a">a</Name></kwargs>)'\
            '</Call></Expr>'

    def test_call_paramenter_order(self, s2xml):
        assert s2xml('foo(*a, b=1, **c)') == \
            '<Expr><Call><func><Name ctx="Load" name="foo">foo</Name></func>('\
            '<starargs>*<Name ctx="Load" name="a">a</Name></starargs>, '\
            '<keyword><arg>b</arg>=<value><Num>1</Num></value></keyword>, '\
            '<kwargs>**<Name ctx="Load" name="c">c</Name></kwargs>)'\
            '</Call></Expr>'


    def test_call_keywords_before_after_starargs(self, s2xml):
        assert s2xml('foo(a=1, *b, c=2)') == \
            '<Expr><Call><func><Name ctx="Load" name="foo">foo</Name></func>('\
            '<keyword><arg>a</arg>=<value><Num>1</Num></value></keyword>, '\
            '<starargs>*<Name ctx="Load" name="b">b</Name></starargs>, '\
            '<keyword><arg>c</arg>=<value><Num>2</Num></value></keyword>'\
            ')</Call></Expr>'


class TestListComp:
    def test_listcomp(self, s2xml):
        assert s2xml('[a for a in b ]') == \
            '<Expr><ListComp>[<elt><Name ctx="Load" name="a">a</Name></elt>'\
            '<generators><comprehension> for '\
            '<target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter><Name ctx="Load" name="b">b</Name></iter>'\
            '</comprehension></generators> ]</ListComp></Expr>'

    def test_listcomp_ifs(self, s2xml):
        assert s2xml('[a for a in b if a if True]') == \
            '<Expr><ListComp>[<elt><Name ctx="Load" name="a">a</Name></elt>'\
            '<generators><comprehension> for '\
            '<target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter><Name ctx="Load" name="b">b</Name></iter>'\
            '<ifs><if> if <Name ctx="Load" name="a">a</Name></if>'\
            '<if> if <NameConstant>True</NameConstant></if></ifs>'\
            '</comprehension></generators>]</ListComp></Expr>'

    def test_listcomp_2(self, s2xml):
        assert s2xml('[a for a in b for c in d]') == \
            '<Expr><ListComp>[<elt><Name ctx="Load" name="a">a</Name></elt>'\
            '<generators><comprehension> for '\
            '<target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter><Name ctx="Load" name="b">b</Name></iter>'\
            '</comprehension><comprehension> for '\
            '<target><Name ctx="Store" name="c">c</Name></target>'\
            ' in <iter><Name ctx="Load" name="d">d</Name></iter>'\
            '</comprehension></generators>]</ListComp></Expr>'

    def test_listcomp_multiline_on_if(self, s2xml):
        assert s2xml('[a for a in b\n if a\n ]') == \
            '<Expr><ListComp>[<elt><Name ctx="Load" name="a">a</Name></elt>'\
            '<generators><comprehension> for '\
            '<target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter><Name ctx="Load" name="b">b</Name></iter>'\
            '<ifs><if>\n if <Name ctx="Load" name="a">a</Name></if></ifs>'\
            '</comprehension></generators>\n ]</ListComp></Expr>'

    def test_listcomp_multiline_on_in(self, s2xml):
        assert s2xml('[a for a\n in b if a]') == \
            '<Expr><ListComp>[<elt><Name ctx="Load" name="a">a</Name></elt>'\
            '<generators><comprehension> for '\
            '<target><Name ctx="Store" name="a">a</Name></target>'\
            '\n in <iter><Name ctx="Load" name="b">b</Name></iter>'\
            '<ifs><if> if <Name ctx="Load" name="a">a</Name></if></ifs>'\
            '</comprehension></generators>]</ListComp></Expr>'

    def test_listcomp_multiline_on_for(self, s2xml):
        assert s2xml('[a\n for a in b if a]') == \
            '<Expr><ListComp>[<elt><Name ctx="Load" name="a">a</Name></elt>'\
            '<generators><comprehension>\n for '\
            '<target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter><Name ctx="Load" name="b">b</Name></iter>'\
            '<ifs><if> if <Name ctx="Load" name="a">a</Name></if></ifs>'\
            '</comprehension></generators>]</ListComp></Expr>'



class TestGeneratorExp:
    def test_generatorexp(self, s2xml):
        assert s2xml('(a for a in b)') == \
            '<Expr>(<GeneratorExp><elt><Name ctx="Load" name="a">a</Name></elt>'\
            '<generators><comprehension> for '\
            '<target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter><Name ctx="Load" name="b">b</Name></iter>'\
            '</comprehension></generators></GeneratorExp>)</Expr>'

    def test_generatorexp_inside_call(self, s2xml):
        assert s2xml('foo(a for a in b)') == \
            '<Expr><Call>'\
            '<func><Name ctx="Load" name="foo">foo</Name></func>(<args>'\
            '<GeneratorExp><elt><Name ctx="Load" name="a">a</Name></elt>'\
            '<generators><comprehension> for '\
            '<target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter><Name ctx="Load" name="b">b</Name></iter>'\
            '</comprehension></generators></GeneratorExp></args>)</Call></Expr>'


class TestSetComp:
    def test_setcomp(self, s2xml):
        assert s2xml('{a for a in b}') == \
            '<Expr><SetComp>{<elt><Name ctx="Load" name="a">a</Name></elt>'\
            '<generators><comprehension> for '\
            '<target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter><Name ctx="Load" name="b">b</Name></iter>'\
            '</comprehension></generators>}</SetComp></Expr>'

class TestDictComp:
    def test_setcomp(self, s2xml):
        assert s2xml('{a : 0 for a in b}') == \
            '<Expr><DictComp>{<key><Name ctx="Load" name="a">a</Name></key>'\
            ' : <value><Num>0</Num></value>'\
            '<generators><comprehension> for '\
            '<target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter><Name ctx="Load" name="b">b</Name></iter>'\
            '</comprehension></generators>}</DictComp></Expr>'


class TestYield:
    def test_yield(self, s2xml):
        assert s2xml('yield') == \
            '<Expr><Yield>yield</Yield></Expr>'

    def test_yield_value(self, s2xml):
        assert s2xml('yield 5') == \
            '<Expr><Yield>yield <Num>5</Num></Yield></Expr>'

    def test_yield_from(self, s2xml):
        assert s2xml('yield from 5') == \
            '<Expr><YieldFrom>yield from <Num>5</Num></YieldFrom></Expr>'


class TestLambda:
    def test_lambda(self, s2xml):
        assert s2xml('lambda : 4') == \
            '<Expr><Lambda>lambda <arguments/>: '\
            '<body><Num>4</Num></body></Lambda></Expr>'

    def test_lambda_args(self, s2xml):
        assert s2xml('lambda a, b=2 : 4') == \
            '<Expr><Lambda>lambda <arguments>'\
            '<arg name="a">a</arg>, '\
            '<arg name="b">b<default>=<Num>2</Num></default></arg> '\
            '</arguments>: '\
            '<body><Num>4</Num></body></Lambda></Expr>'


####################### stmt

class TestFuncDef:
    def test_funcdef(self, s2xml):
        assert s2xml('def four (  ):\n    4') == \
            '<FunctionDef name="four">def four<arguments> (  ):</arguments>'\
            '<body>\n    <Expr><Num>4</Num></Expr></body></FunctionDef>'

    def test_funcdef_decorator(self, s2xml):
        assert s2xml('@foodeco #1\n@deco2 #2\ndef four (  ):\n    4') == \
            '<FunctionDef name="four">'\
            '<decorator>@<Name ctx="Load" name="foodeco">'\
            'foodeco</Name></decorator> #1\n'\
            '<decorator>@<Name ctx="Load" name="deco2">'\
            'deco2</Name></decorator> #2\n'\
            'def four<arguments> (  ):</arguments>'\
            '<body>\n    <Expr><Num>4</Num></Expr></body></FunctionDef>'

    def test_funcdef_arg(self, s2xml):
        assert s2xml('def p_four  ( ini ):\n    return ini + 4') == \
            '<FunctionDef name="p_four">def p_four'\
            '<arguments>  ( <arg name="ini">ini</arg> ):</arguments>'\
            '<body>\n    <Return>return <BinOp>'\
            '<Name ctx="Load" name="ini">ini</Name><Add> + </Add>'\
            '<Num>4</Num></BinOp></Return>'\
            '</body></FunctionDef>'

    def test_funcdef_args(self, s2xml):
        assert s2xml('def foo(a,  b):\n    pass') == \
            '<FunctionDef name="foo">def foo'\
            '<arguments>(<arg name="a">a</arg>,  '\
            '<arg name="b">b</arg>):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_args_default(self, s2xml):
        assert s2xml('def foo(a,  b= 5):\n    pass') == \
            '<FunctionDef name="foo">def foo'\
            '<arguments>(<arg name="a">a</arg>,  '\
            '<arg name="b">b<default>= <Num>5</Num></default></arg>'\
            '):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_args_defaults(self, s2xml):
        assert s2xml('def foo(a=3, b= 5):\n    pass') == \
            '<FunctionDef name="foo">def foo'\
            '<arguments>('\
            '<arg name="a">a<default>=<Num>3</Num></default></arg>, '\
            '<arg name="b">b<default>= <Num>5</Num></default></arg>'\
            '):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_comment(self, s2xml):
        assert s2xml('def foo():\n    # comment\n    pass') == \
            '<FunctionDef name="foo">def foo<arguments>():</arguments>'\
            '<body>\n    # comment\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_after(self, s2xml):
        assert s2xml('def foo():\n    pass\n8') == \
            '<FunctionDef name="foo">def foo<arguments>():</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>\n'\
            '<Expr><Num>8</Num></Expr>'

    def test_funcdef_vararg(self, s2xml):
        assert s2xml('def foo(*pos):\n    pass') == \
            '<FunctionDef name="foo">def foo<arguments>('\
            '<vararg>*<arg name="pos">pos</arg></vararg>):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'


    def test_funcdef_kwarg(self, s2xml):
        assert s2xml('def foo(**bar):\n    pass') == \
            '<FunctionDef name="foo">def foo<arguments>('\
            '<kwarg>**<arg name="bar">bar</arg></kwarg>):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'


    def test_funcdef_kwonly(self, s2xml):
        assert s2xml('def foo(*a, b= 5):\n    pass') == \
            '<FunctionDef name="foo">def foo'\
            '<arguments>('\
            '<vararg>*<arg name="a">a</arg></vararg>, '\
            '<arg kwonly="" name="b">b<default>= <Num>5</Num></default></arg>'\
            '):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_kwonly_no_default(self, s2xml):
        assert s2xml('def foo(*a, b ):\n    pass') == \
            '<FunctionDef name="foo">def foo'\
            '<arguments>('\
            '<vararg>*<arg name="a">a</arg></vararg>, '\
            '<arg kwonly="" name="b">b</arg>'\
            ' ):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_kwonly_kwarg(self, s2xml):
        assert s2xml('def foo(*a, b= 5, **c):\n    pass') == \
            '<FunctionDef name="foo">def foo'\
            '<arguments>('\
            '<vararg>*<arg name="a">a</arg></vararg>, '\
            '<arg kwonly="" name="b">b<default>= <Num>5</Num></default></arg>'\
            ', <kwarg>**<arg name="c">c</arg></kwarg>'\
            '):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_kwonly_no_vararg(self, s2xml):
        assert s2xml('def foo(*, b= 5):\n    pass') == \
            '<FunctionDef name="foo">def foo'\
            '<arguments>('\
            '*, '\
            '<arg kwonly="" name="b">b<default>= <Num>5</Num></default></arg>'\
            '):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_annotation(self, s2xml):
        assert s2xml('def test(a:"spam") -> "ham": pass') == \
            '<FunctionDef name="test">def test<arguments>('\
            '<arg name="a">a<annotation>:<Str><s>"spam"</s></Str></annotation>'\
            '</arg>) <returns>-&gt; <Str><s>"ham"</s></Str></returns>'\
            ':</arguments><body> <Pass>pass</Pass></body></FunctionDef>'


class TestClassDef:
    def test_classdef(self, s2xml):
        assert s2xml('class Foo (  ) :\n    pass') == \
            '<ClassDef name="Foo">class Foo<arguments> (  )</arguments> :'\
            '<body>\n    <Pass>pass</Pass></body></ClassDef>'

    def test_classdef_bases(self, s2xml):
        assert s2xml('class Foo (Base) :\n    pass') == \
            '<ClassDef name="Foo">class Foo<arguments> ('\
            '<base><Name ctx="Load" name="Base">Base</Name></base>'\
            ')</arguments> :'\
            '<body>\n    <Pass>pass</Pass></body></ClassDef>'

    def test_classdef_bases_multiline(self, s2xml):
        assert s2xml('class Foo (\n Base,\n Base2) :\n    pass') == \
            '<ClassDef name="Foo">class Foo<arguments> (\n '\
            '<base><Name ctx="Load" name="Base">Base</Name></base>,\n '\
            '<base><Name ctx="Load" name="Base2">Base2</Name></base>'\
            ')</arguments> :'\
            '<body>\n    <Pass>pass</Pass></body></ClassDef>'

    def test_classdef_dcorator(self, s2xml):
        assert s2xml('@deco\nclass Foo():\n    pass') == \
            '<ClassDef name="Foo">'\
            '<decorator>@<Name ctx="Load" name="deco">'\
            'deco</Name></decorator>\n'\
            'class Foo<arguments>()</arguments>:'\
            '<body>\n    <Pass>pass</Pass></body></ClassDef>'

    def test_classdef_no_args(self, s2xml):
        assert s2xml('class Foo :\n    pass') == \
            '<ClassDef name="Foo">class Foo :'\
            '<body>\n    <Pass>pass</Pass></body></ClassDef>'

    def test_classdef_keyword(self, s2xml):
        assert s2xml('class Foo (bar=1) :\n    pass') == \
            '<ClassDef name="Foo">class Foo<arguments> ('\
            '<keyword><arg>bar</arg>=<value><Num>1</Num></value></keyword>'\
            ')</arguments> :'\
            '<body>\n    <Pass>pass</Pass></body></ClassDef>'

    def test_classdef_all_args(self, s2xml):
        class_def = 'class Foo(Base, xx=1, *aa, yy=2, **dd): pass'
        assert s2xml(class_def) == \
            '<ClassDef name="Foo">class Foo<arguments>('\
            '<base><Name ctx="Load" name="Base">Base</Name></base>, '\
            '<keyword><arg>xx</arg>=<value><Num>1</Num></value></keyword>, '\
            '<starargs>*<Name ctx="Load" name="aa">aa</Name></starargs>, '\
            '<keyword><arg>yy</arg>=<value><Num>2</Num></value></keyword>, '\
            '<kwargs>**<Name ctx="Load" name="dd">dd</Name></kwargs>'\
            ')</arguments>:'\
            '<body> <Pass>pass</Pass></body></ClassDef>'



class TestReturn:
    def test_return_single(self, s2xml):
        assert s2xml('def four (  ):\n    return 4') == \
            '<FunctionDef name="four">def four<arguments> (  ):</arguments>'\
            '<body>\n    <Return>return <Num>4</Num></Return>'\
            '</body></FunctionDef>'

    def test_return_nothing(self, s2xml):
        assert s2xml('def foo (  ):\n    return') == \
            '<FunctionDef name="foo">def foo<arguments> (  ):</arguments>'\
            '<body>\n    <Return>return</Return>'\
            '</body></FunctionDef>'


class TestAssert:
    def test_assert(self, s2xml):
        assert s2xml('assert 1') == \
            '<Assert>assert <test><Num>1</Num></test></Assert>'

    def test_assert_msg(self, s2xml):
        assert s2xml('assert 1, "opa"') == \
            '<Assert>assert <test><Num>1</Num></test>'\
            ', <msg><Str><s>"opa"</s></Str></msg></Assert>'


class TestAssign:
    def test_assign(self, s2xml):
        assert s2xml('d = 5') == \
            '<Assign><targets><Name ctx="Store" name="d">d</Name>'\
            ' = </targets><Num>5</Num></Assign>'

    def test_comment_assign(self, s2xml):
        assert s2xml('# hello\nd = 5') == \
            '# hello\n<Assign><targets><Name ctx="Store" name="d">d</Name>'\
            ' = </targets><Num>5</Num></Assign>'

    def test_assign_space(self, s2xml):
        assert s2xml('f  =   7') == \
            '<Assign><targets>'\
            '<Name ctx="Store" name="f">f</Name>  =   </targets>'\
            '<Num>7</Num></Assign>'

    def test_expr_semi_colon_separated2(self, s2xml):
        assert s2xml('x=3; y=5') == \
            '<Assign>'\
            '<targets><Name ctx="Store" name="x">x</Name>=</targets>'\
            '<Num>3</Num></Assign>'\
            '; <Assign>'\
            '<targets><Name ctx="Store" name="y">y</Name>=</targets>'\
            '<Num>5</Num></Assign>'

    def test_assign_tuple(self, s2xml):
        assert s2xml('d, e = 5, 6') == \
            '<Assign><targets><Tuple ctx="Store">'\
            '<Name ctx="Store" name="d">d</Name>'\
            ', <Name ctx="Store" name="e">e</Name></Tuple> = </targets>'\
            '<Tuple ctx="Load"><Num>5</Num>, <Num>6</Num>'\
            '</Tuple></Assign>'

    def test_assign_multi(self, s2xml):
        assert s2xml('d = e = 5') == \
            '<Assign><targets>'\
            '<Name ctx="Store" name="d">d</Name> = '\
            '<Name ctx="Store" name="e">e</Name> = </targets>'\
            '<Num>5</Num></Assign>'


class TestAugAssign:
    def test_add(self, s2xml):
        assert s2xml('d += 5') == \
            '<AugAssign><target><Name ctx="Store" name="d">d</Name>'\
            '</target><op><Add> += </Add></op>'\
            '<value><Num>5</Num></value></AugAssign>'


class TestImport:
    def test_import(self, s2xml):
        assert s2xml('import time') == \
            '<Import>import <alias><name>time</name></alias></Import>'

    def test_import_as(self, s2xml):
        assert s2xml('import time as t2') == \
            '<Import>import '\
            '<alias><name>time</name> as <asname>t2</asname></alias>'\
            '</Import>'

    def test_import_multi(self, s2xml):
        assert s2xml('import time ,  datetime') == \
            '<Import>import <alias><name>time</name></alias>'\
            ' ,  <alias><name>datetime</name></alias></Import>'

    def test_import_as_multi(self, s2xml):
        assert s2xml('import time as  t2, datetime  as dt') == \
            '<Import>import '\
            '<alias><name>time</name> as  <asname>t2</asname></alias>'\
            ', <alias><name>datetime</name>  as <asname>dt</asname></alias>'\
            '</Import>'

    def test_import_dot_as(self, s2xml):
        assert s2xml('import time.sleep as dorme') == \
            '<Import>import '\
            '<alias><name>time.sleep</name> as <asname>dorme</asname></alias>'\
            '</Import>'



class TestImportFrom:
    def test_importfrom(self, s2xml):
        assert s2xml('from time import sleep') == \
            '<ImportFrom level="0">from <module>time</module> import '\
            '<names><alias><name>sleep</name></alias></names>'\
            '</ImportFrom>'

    def test_importfrom_dot_as(self, s2xml):
        assert s2xml('from foo.bar import baz as zeta') == \
            '<ImportFrom level="0">from <module>foo.bar</module> import '\
            '<names><alias><name>baz</name> as <asname>zeta</asname>'\
            '</alias></names></ImportFrom>'

    def test_importfrom_level(self, s2xml):
        assert s2xml('from .foo import bar,  baz as zeta') == \
            '<ImportFrom level="1">from .<module>foo</module> import <names>'\
            '<alias><name>bar</name></alias>'\
            ',  <alias><name>baz</name> as <asname>zeta</asname></alias>'\
            '</names>'\
            '</ImportFrom>'

    def test_importfrom_level2_module_none(self, s2xml):
        assert s2xml('from .. import bar') == \
            '<ImportFrom level="2">from ..<module/> import <names>'\
            '<alias><name>bar</name></alias>'\
            '</names></ImportFrom>'

    def test_importfrom_par(self, s2xml):
        assert s2xml('from foo import (bar, baz)') == \
            '<ImportFrom level="0">from <module>foo</module> import'\
            ' (<names><alias><name>bar</name></alias>'\
            ', <alias><name>baz</name></alias></names>)'\
            '</ImportFrom>'

    def test_importfrom_par_nl(self, s2xml):
        assert s2xml('from foo import (bar,\n baz)') == \
            '<ImportFrom level="0">from <module>foo</module> import'\
            ' (<names><alias><name>bar</name></alias>'\
            ',\n <alias><name>baz</name></alias></names>)'\
            '</ImportFrom>'

    def test_importfrom_par_nl2(self, s2xml):
        assert s2xml('from foo import (\nbar,\n baz\n)') == \
            '<ImportFrom level="0">from <module>foo</module> import'\
            ' (\n<names><alias><name>bar</name></alias>'\
            ',\n <alias><name>baz</name></alias>\n</names>)'\
            '</ImportFrom>'



class TestWhile:
    def test_while(self, s2xml):
        assert s2xml('while True:\n    pass') == \
            '<While>while <test><NameConstant>True</NameConstant></test>:'\
            '<body>\n    <Pass>pass</Pass></body></While>'

    def test_while_else(self, s2xml):
        assert s2xml('while True:\n    pass\nelse:\n    pass') == \
            '<While>while <test><NameConstant>True</NameConstant></test>:'\
            '<body>\n    <Pass>pass</Pass></body>'\
            '\n<orelse>else:\n    <Pass>pass</Pass></orelse>'\
            '</While>'

class TestBreak:
    def test_break(self, s2xml):
        assert s2xml('while True:\n    break') == \
            '<While>while <test><NameConstant>True</NameConstant></test>:'\
            '<body>\n    <Break>break</Break></body></While>'

class TestContinue:
    def test_continue(self, s2xml):
        assert s2xml('while True:\n    continue') == \
            '<While>while <test><NameConstant>True</NameConstant></test>:'\
            '<body>\n    <Continue>continue</Continue></body></While>'


class TestIf:
    def test_if(self, s2xml):
        assert s2xml('if True:\n    pass') == \
            '<If>if <test><NameConstant>True</NameConstant></test>:'\
            '<body>\n    <Pass>pass</Pass></body></If>'

    def test_else(self, s2xml):
        assert s2xml('if True:\n    pass\nelse:\n    pass') == \
            '<If>if <test><NameConstant>True</NameConstant></test>:'\
            '<body>\n    <Pass>pass</Pass></body>'\
            '\n<orelse>else:\n    <Pass>pass</Pass></orelse></If>'

    def test_elif(self, s2xml):
        assert s2xml('if True:\n    pass\nelif True:\n    pass') == \
            '<If>if <test><NameConstant>True</NameConstant></test>:'\
            '<body>\n    <Pass>pass</Pass></body>\n'\
            '<orelse><If>elif <test><NameConstant>True</NameConstant></test>'\
            ':<body>\n    <Pass>pass</Pass></body></If></orelse></If>'

    def test_if_single_line(self, s2xml):
        assert s2xml('if True : pass') == \
            '<If>if <test><NameConstant>True</NameConstant></test> :'\
            '<body> <Pass>pass</Pass></body></If>'

    def test_if_else_single_line(self, s2xml):
        assert s2xml('while 1:\n    if True: pass\n    else: 2') == \
            '<While>while <test><Num>1</Num></test>:<body>\n'\
            '    <If>if <test><NameConstant>True</NameConstant></test>:'\
            '<body> <Pass>pass</Pass></body>\n'\
            '<orelse>    else: <Expr><Num>2</Num></Expr></orelse>'\
            '</If></body></While>'


class TestFor:
    def test_for(self, s2xml):
        assert s2xml('for a in b:\n    pass') == \
            '<For>for <target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter><Name ctx="Load" name="b">b</Name></iter>:'\
            '<body>\n    <Pass>pass</Pass></body></For>'

    def test_for_else(self, s2xml):
        assert s2xml('for a in b:\n    pass\nelse:\n    pass') == \
            '<For>for <target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter><Name ctx="Load" name="b">b</Name></iter>:'\
            '<body>\n    <Pass>pass</Pass></body>'\
            '\n<orelse>else:\n    <Pass>pass</Pass></orelse>'\
            '</For>'

    def test_for_in_parenthesis_nl(self, s2xml):
        assert s2xml('for a in (\nb):\n    pass') == \
            '<For>for <target><Name ctx="Store" name="a">a</Name></target>'\
            ' in <iter>(\n<Name ctx="Load" name="b">b</Name>)</iter>:'\
            '<body>\n    <Pass>pass</Pass></body></For>'

class TestRaise:
    def test_raise(self, s2xml):
        assert s2xml('raise') == \
            '<Raise>raise</Raise>'

    def test_raise_exc(self, s2xml):
        assert s2xml('raise 2') == \
            '<Raise>raise <exc><Num>2</Num></exc></Raise>'

    def test_raise_exc_from(self, s2xml):
        assert s2xml('raise 2 from a') == \
            '<Raise>raise <exc><Num>2</Num></exc>'\
            ' from <cause><Name ctx="Load" name="a">a</Name></cause></Raise>'

    def test_raise_comment(self, s2xml):
        assert s2xml('raise # hi') == \
            '<Raise>raise</Raise> # hi'


class TestTry:
    def test_try(self, s2xml):
        assert s2xml('try:\n    4\nexcept:\n    pass') == \
            '<Try>try:<body>\n    <Expr><Num>4</Num></Expr></body>'\
            '<handlers><ExceptHandler>\nexcept:'\
            '<body>\n    <Pass>pass</Pass></body></ExceptHandler>'\
            '</handlers></Try>'

    def test_try_except(self, s2xml):
        assert s2xml('try:\n    4\nexcept Exception:\n    pass') == \
            '<Try>try:<body>\n    <Expr><Num>4</Num></Expr></body>'\
            '<handlers><ExceptHandler>\nexcept '\
            '<type><Name ctx="Load" name="Exception">Exception</Name></type>'\
            ':<body>\n    <Pass>pass</Pass></body></ExceptHandler>'\
            '</handlers></Try>'

    def test_try_except_as(self, s2xml):
        assert s2xml('try:\n    4\nexcept Exception as foo:\n    pass') == \
            '<Try>try:<body>\n    <Expr><Num>4</Num></Expr></body>'\
            '<handlers><ExceptHandler>\nexcept '\
            '<type><Name ctx="Load" name="Exception">Exception</Name></type>'\
            ' as <name>foo</name>:'\
            '<body>\n    <Pass>pass</Pass></body></ExceptHandler>'\
            '</handlers></Try>'


    def test_try_except_else(self, s2xml):
        code = 'try:\n    4\nexcept Exception:\n    pass\nelse:\n    pass'
        assert s2xml(code) == \
            '<Try>try:<body>\n    <Expr><Num>4</Num></Expr></body>'\
            '<handlers><ExceptHandler>\nexcept '\
            '<type><Name ctx="Load" name="Exception">Exception</Name></type>'\
            ':<body>\n    <Pass>pass</Pass></body></ExceptHandler>'\
            '</handlers>\n<orelse>else:\n    <Pass>pass</Pass></orelse></Try>'

    def test_try_finally(self, s2xml):
        assert s2xml('try:\n    4\nfinally:\n    pass') == \
            '<Try>try:<body>\n    <Expr><Num>4</Num></Expr></body>'\
            '\n<finalbody>finally:\n    <Pass>pass</Pass></finalbody></Try>'

class TestWith:
    def test_with(self, s2xml):
        assert s2xml('with 5:\n    pass') == \
            '<With>with <items><withitem><Num>5</Num></withitem></items>:'\
            '<body>\n    <Pass>pass</Pass></body></With>'

    def test_with_var(self, s2xml):
        assert s2xml('with 5 as foo:\n    pass') == \
            '<With>with <items><withitem><Num>5</Num> as '\
            '<Name ctx="Store" name="foo">foo</Name></withitem></items>:'\
            '<body>\n    <Pass>pass</Pass></body></With>'

    def test_with_multi(self, s2xml):
        assert s2xml('with 5 as foo, 6 as bar:\n    pass') == \
            '<With>with <items><withitem><Num>5</Num> as '\
            '<Name ctx="Store" name="foo">foo</Name></withitem>'\
            ', <withitem><Num>6</Num> as '\
            '<Name ctx="Store" name="bar">bar</Name></withitem></items>:'\
            '<body>\n    <Pass>pass</Pass></body></With>'


class TestDelete:
    def test_delete(self, s2xml):
        assert s2xml('del a') == \
            '<Delete>del <targets>'\
            '<Name ctx="Del" name="a">a</Name>'\
            '</targets></Delete>'

    def test_delete_n(self, s2xml):
        assert s2xml('del a , b') == \
            '<Delete>del <targets>'\
            '<Name ctx="Del" name="a">a</Name>'\
            ' , <Name ctx="Del" name="b">b</Name>'\
            '</targets></Delete>'

    def test_delete_n_comma(self, s2xml):
        assert s2xml('del a , b ,') == \
            '<Delete>del <targets>'\
            '<Name ctx="Del" name="a">a</Name>'\
            ' , <Name ctx="Del" name="b">b</Name>'\
            ' ,</targets></Delete>'


class TestGlobal:
    def test_global(self, s2xml):
        assert s2xml('global a , b') == \
            '<Global>global <names>'\
            '<name>a</name>'\
            ' , <name>b</name>'\
            '</names></Global>'


class TestNonLocal:
    def test_nonlocal(self, s2xml):
        assert s2xml('nonlocal a , b') == \
            '<Nonlocal>nonlocal <names>'\
            '<name>a</name>'\
            ' , <name>b</name>'\
            '</names></Nonlocal>'



class TestBugs:
    def test_expr_parenthesis_complex(self, s2xml):
        assert s2xml('str((1-2)*23//10)') == \
            '<Expr><Call><func><Name ctx="Load" name="str">str</Name></func>'\
            '(<args><BinOp><BinOp>'\
            '(<BinOp><Num>1</Num><Sub>-</Sub><Num>2</Num></BinOp>)'\
            '<Mult>*</Mult><Num>23</Num></BinOp>'\
            '<FloorDiv>//</FloorDiv><Num>10</Num></BinOp></args>)</Call></Expr>'

    def test_binop_attr(self, s2xml):
        assert s2xml('(1 + 2 + 3).bit_len') == \
            '<Expr><Attribute ctx="Load"><value>'\
            '(<BinOp><BinOp><Num>1</Num><Add> + </Add><Num>2</Num></BinOp>'\
            '<Add> + </Add><Num>3</Num></BinOp>)'\
            '</value>.<attr>bit_len</attr></Attribute></Expr>'

    def test_more_binop_attr(self, s2xml):
        assert s2xml('((bytes[0]<<4) + (bytes<<1) - (bytes<<8) + bytes)') == \
            '<Expr>(<BinOp><BinOp><BinOp>(<BinOp><Subscript ctx="Load">'\
            '<value><Name ctx="Load" name="bytes">bytes</Name></value><slice>'\
            '[<Index><Num>0</Num></Index>]</slice></Subscript>'\
            '<LShift>&lt;&lt;</LShift><Num>4</Num></BinOp>)<Add> + </Add>'\
            '(<BinOp><Name ctx="Load" name="bytes">bytes</Name>'\
            '<LShift>&lt;&lt;</LShift><Num>1</Num></BinOp>)</BinOp>'\
            '<Sub> - </Sub>(<BinOp><Name ctx="Load" name="bytes">bytes</Name>'\
            '<LShift>&lt;&lt;</LShift><Num>8</Num></BinOp>)</BinOp>'\
            '<Add> + </Add><Name ctx="Load" name="bytes">bytes</Name>'\
            '</BinOp>)</Expr>'

    def test_elif_prev_space(self, s2xml):
        assert s2xml('if 0:\n    if 1: 2\n    elif 3: 4') == \
            '<If>if <test><Num>0</Num></test>:<body>\n'\
            '    <If>if <test><Num>1</Num></test>:<body> '\
            '<Expr><Num>2</Num></Expr></body>'\
            '\n<orelse>    <If>elif <test><Num>3</Num></test>:'\
            '<body> <Expr><Num>4</Num></Expr></body></If></orelse>'\
            '</If></body></If>'

    def test_elif_prev_space(self, s2xml):
        assert s2xml('("colä", lambda x, y: (x > y) - (x < y))') == \
            '<Expr>(<Tuple ctx="Load"><Str><s>"colä"</s></Str>, '\
            '<Lambda>lambda <arguments><arg name="x">x</arg>, '\
            '<arg name="y">y</arg></arguments>: <body>'\
            '<BinOp>(<Compare><value><Name ctx="Load" name="x">x</Name>'\
            '</value><cmpop> &gt; </cmpop><value><Name ctx="Load" name="y">'\
            'y</Name></value></Compare>)<Sub> - </Sub>(<Compare><value>'\
            '<Name ctx="Load" name="x">x</Name></value><cmpop> &lt; </cmpop>'\
            '<value><Name ctx="Load" name="y">y</Name></value></Compare>'\
            ')</BinOp></body></Lambda></Tuple>)</Expr>'

    def test_attr_par(self, s2xml):
        assert s2xml('(chr(i) + "A").splitlines') == \
            '<Expr><Attribute ctx="Load"><value>('\
            '<BinOp><Call><func><Name ctx="Load" name="chr">chr</Name></func>'\
            '(<args><Name ctx="Load" name="i">i</Name></args>)</Call>'\
            '<Add> + </Add><Str><s>"A"</s></Str></BinOp>)</value>.<attr>'\
            'splitlines</attr></Attribute></Expr>'
