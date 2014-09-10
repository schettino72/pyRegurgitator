
import xml.etree.ElementTree as ET

import pytest

from pyreg.py2xml import py2xml, xml2py


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


class TestTuple:
    def test_tuple(self, s2xml):
        assert s2xml('1,2,3') == '<Expr><Tuple ctx="Load"><Num>1</Num>'\
            ',<Num>2</Num>,<Num>3</Num></Tuple></Expr>'

    def test_tuple_space(self, s2xml):
        assert s2xml('1, 2 ,  3') == '<Expr><Tuple ctx="Load">'\
            '<Num>1</Num>, <Num>2</Num> ,  <Num>3</Num></Tuple></Expr>'

    def test_tuple_end_comma(self, s2xml):
        assert s2xml('1, 2 ,') == '<Expr><Tuple ctx="Load">'\
            '<Num>1</Num>, <Num>2</Num> ,</Tuple></Expr>'


class TestExpressions:
    def test_expr_in_parenthesis(self, s2xml):
        assert s2xml('(3 )') == '<Expr>(<Num>3</Num> )</Expr>'

    def test_tuple_in_parenthesis(self, s2xml):
        assert s2xml('( 3 , 4 , )') == \
            '<Expr>( <Tuple ctx="Load"><Num>3</Num> , <Num>4</Num>'\
            ' ,</Tuple> )</Expr>'

    def test_expr_in_parenthesis2(self, s2xml):
        assert s2xml('(  3 )') == '<Expr>(  <Num>3</Num> )</Expr>'

    def test_expr_semi_colon_separated(self, s2xml):
        assert s2xml('3 ; 5') == \
            '<Expr><Num>3</Num></Expr>'\
            ' ; <Expr><Num>5</Num></Expr>'



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


class TestDict:
    def test_dict(self, s2xml):
        assert s2xml('{"a": 2}') == \
            '<Expr><Dict>{'\
            '<item><Str><s>"a"</s></Str>: <Num>2</Num></item>}</Dict></Expr>'


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

    def test_expr_in_parenthesis_any(self, s2xml):
        assert s2xml('( 2+ (3 )  )') == \
            '<Expr>( <BinOp><Num>2</Num><Add>+ </Add>(<Num>3</Num>'\
            ' )</BinOp>  )</Expr>'


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

class TestUnaryOp:
    def test_bool_op(self, s2xml):
        assert s2xml('not 2') == \
            '<Expr><UnaryOp op="Not">'\
            'not <Num>2</Num>'\
            '</UnaryOp></Expr>'

class TestCompare:
    def test_compare(self, s2xml):
        assert s2xml('1 < 2') == \
            '<Expr><Compare>'\
            '<value><Num>1</Num></value>'\
            '<cmpop> &lt; </cmpop>'\
            '<value><Num>2</Num></value>'\
            '</Compare></Expr>'


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
            '<Expr><Call><func><Name ctx="Load" name="print">print</Name></func>'\
            ' (  <args><Num>2</Num></args>   )'\
            '</Call></Expr>'

    def test_call_arg2(self, s2xml):
        assert s2xml('print(2,  "xxx" )') == \
            '<Expr><Call><func><Name ctx="Load" name="print">print</Name></func>'\
            '(<args><Num>2</Num>,  <Str><s>"xxx"</s></Str></args> )'\
            '</Call></Expr>'

    def test_call_comment(self, s2xml):
        assert s2xml('foo() #') == \
            '<Expr><Call><func><Name ctx="Load" name="foo">foo</Name></func>'\
            '()</Call></Expr> #'

    def test_call_keyword(self, s2xml):
        assert s2xml('foo(x=2)') == \
            '<Expr><Call><func><Name ctx="Load" name="foo">foo</Name></func>'\
            '(<keywords><keyword><arg>x</arg>=<value><Num>2</Num></value>'\
            '</keyword></keywords>)'\
            '</Call></Expr>'



class TestFuncDef:
    def test_funcdef(self, s2xml):
        assert s2xml('def four (  ):\n    4') == \
            '<FunctionDef name="four">def four<arguments> (  ):</arguments>'\
            '<body>\n    <Expr><Num>4</Num></Expr></body></FunctionDef>'

    def test_funcdef_arg(self, s2xml):
        assert s2xml('def p_four  ( ini ):\n    return ini + 4') == \
            '<FunctionDef name="p_four">def p_four'\
            '<arguments>  (<args> <arg name="ini">ini</arg></args> ):</arguments>'\
            '<body>\n    <Return>return <BinOp>'\
            '<Name ctx="Load" name="ini">ini</Name><Add> + </Add>'\
            '<Num>4</Num></BinOp></Return>'\
            '</body></FunctionDef>'

    def test_funcdef_args(self, s2xml):
        assert s2xml('def foo(a,  b):\n    pass') == \
            '<FunctionDef name="foo">def foo'\
            '<arguments>(<args><arg name="a">a</arg>,  '\
            '<arg name="b">b</arg></args>):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_args_default(self, s2xml):
        assert s2xml('def foo(a,  b= 5):\n    pass') == \
            '<FunctionDef name="foo">def foo'\
            '<arguments>(<args><arg name="a">a</arg>,  '\
            '<arg name="b">b<default>= <Num>5</Num></default></arg>'\
            '</args>):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_args_defaults(self, s2xml):
        assert s2xml('def foo(a=3, b= 5):\n    pass') == \
            '<FunctionDef name="foo">def foo'\
            '<arguments>('\
            '<args><arg name="a">a<default>=<Num>3</Num></default></arg>, '\
            '<arg name="b">b<default>= <Num>5</Num></default></arg>'\
            '</args>):</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_comment(self, s2xml):
        assert s2xml('def foo():\n    # comment\n    pass') == \
            '<FunctionDef name="foo">def foo''<arguments>():</arguments>'\
            '<body>\n    # comment\n    <Pass>pass</Pass></body></FunctionDef>'

    def test_funcdef_after(self, s2xml):
        assert s2xml('def foo():\n    pass\n8') == \
            '<FunctionDef name="foo">def foo''<arguments>():</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></FunctionDef>\n'\
            '<Expr><Num>8</Num></Expr>'


class TestClassDef:
    def test_classdef(self, s2xml):
        assert s2xml('class Foo (  ) :\n    pass') == \
            '<ClassDef name="Foo">class Foo<arguments> (  ) :</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></ClassDef>'

    def test_classdef_bases(self, s2xml):
        assert s2xml('class Foo (Base) :\n    pass') == \
            '<ClassDef name="Foo">class Foo<arguments> ('\
            '<bases><Name ctx="Load" name="Base">Base</Name></bases>'\
            ') :</arguments>'\
            '<body>\n    <Pass>pass</Pass></body></ClassDef>'



class TestReturn:
    def test_return_single(self, s2xml):
        assert s2xml('def four (  ):\n    return 4') == \
            '<FunctionDef name="four">def four<arguments> (  ):</arguments>'\
            '<body>\n    <Return>return <Num>4</Num></Return>'\
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
            '</targets> = <Num>5</Num></Assign>'

    def test_comment_assign(self, s2xml):
        assert s2xml('# hello\nd = 5') == \
            '# hello\n<Assign><targets><Name ctx="Store" name="d">d</Name>'\
            '</targets> = <Num>5</Num></Assign>'

    def test_assign_space(self, s2xml):
        assert s2xml('f  =   7') == \
            '<Assign><targets><Name ctx="Store" name="f">f</Name></targets>'\
            '  =   <Num>7</Num></Assign>'

    def test_expr_semi_colon_separated2(self, s2xml):
        assert s2xml('x=3; y=5') == \
            '<Assign>'\
            '<targets><Name ctx="Store" name="x">x</Name></targets>'\
            '=<Num>3</Num></Assign>'\
            '; <Assign>'\
            '<targets><Name ctx="Store" name="y">y</Name></targets>'\
            '=<Num>5</Num></Assign>'


class TestImport:
    def test_import(self, s2xml):
        assert s2xml('import time') == \
            '<Import>import<alias> <name>time</name></alias></Import>'

    def test_import_as(self, s2xml):
        assert s2xml('import time as t2') == \
            '<Import>import'\
            '<alias> <name>time</name> as <asname>t2</asname></alias>'\
            '</Import>'

    def test_import_multi(self, s2xml):
        assert s2xml('import time ,  datetime') == \
            '<Import>import<alias> <name>time</name></alias>'\
            ' ,<alias>  <name>datetime</name></alias></Import>'

    def test_import_as_multi(self, s2xml):
        assert s2xml('import time as  t2, datetime  as dt') == \
            '<Import>import'\
            '<alias> <name>time</name> as  <asname>t2</asname></alias>'\
            ',<alias> <name>datetime</name>  as <asname>dt</asname></alias>'\
            '</Import>'

    def test_import_dot_as(self, s2xml):
        assert s2xml('import time.sleep as dorme') == \
            '<Import>import'\
            '<alias> <name>time.sleep</name> as <asname>dorme</asname></alias>'\
            '</Import>'



class TestImportFrom:
    def test_importfrom(self, s2xml):
        assert s2xml('from time import sleep') == \
            '<ImportFrom level="0">from <module>time</module> import'\
            '<names><alias> <name>sleep</name></alias></names>'\
            '</ImportFrom>'

    def test_importfrom_dot_as(self, s2xml):
        assert s2xml('from foo.bar import baz as zeta') == \
            '<ImportFrom level="0">from <module>foo.bar</module> import'\
            '<names><alias> <name>baz</name> as <asname>zeta</asname>'\
            '</alias></names></ImportFrom>'

    def test_importfrom_level(self, s2xml):
        assert s2xml('from .foo import bar,  baz as zeta') == \
            '<ImportFrom level="1">from .<module>foo</module> import<names>'\
            '<alias> <name>bar</name></alias>'\
            ',<alias>  <name>baz</name> as <asname>zeta</asname></alias>'\
            '</names>'\
            '</ImportFrom>'

    def test_importfrom_level2_module_none(self, s2xml):
        assert s2xml('from .. import bar') == \
            '<ImportFrom level="2">from ..<module/> import<names>'\
            '<alias> <name>bar</name></alias>'\
            '</names></ImportFrom>'


class TestWhile:
    def test_while(self, s2xml):
        assert s2xml('while True:\n    pass') == \
            '<While>while <test><NameConstant>True</NameConstant></test>:'\
            '<body>\n    <Pass>pass</Pass></body></While>'

class TestIf:
    def test_if(self, s2xml):
        assert s2xml('if True:\n    pass') == \
            '<If>if <test><NameConstant>True</NameConstant></test>:'\
            '<body>\n    <Pass>pass</Pass></body></If>'


class TestRaise:
    def test_raise(self, s2xml):
        assert s2xml('raise 2') == \
            '<Raise>raise <exc><Num>2</Num></exc></Raise>'


def test_xml2py():
    assert xml2py('<a>x<b>y</b>z</a>') == 'xyz'
