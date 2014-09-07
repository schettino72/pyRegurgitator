
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
            "<s>' /part 2'</s></Str></Expr>"

    def test_tuple(self, s2xml):
        assert s2xml('(1,2,3)') == '<Expr><Tuple ctx="Load">(<Num>1</Num>'\
            ',<Num>2</Num>,<Num>3</Num>)</Tuple></Expr>'

    def test_tuple_space(self, s2xml):
        assert s2xml('(  1, 2,3 )') == '<Expr><Tuple ctx="Load">'\
            '(  <Num>1</Num>, <Num>2</Num>,<Num>3</Num> )</Tuple></Expr>'



class TestExpressions:
    def test_expr_in_parenthesis(self, s2xml):
        assert s2xml('(3 )') == '<Expr>(<Num>3</Num> )</Expr>'

    def test_expr_in_parenthesis_n(self, s2xml):
        assert s2xml('((3 )  )') == '<Expr>((<Num>3</Num> )  )</Expr>'


class TestBinOp:
    def test_expr_in_parenthesis_any(self, s2xml):
        assert s2xml('( 2+ (3 )  )') == \
            '<Expr>( <BinOp><Num>2</Num><Add>+ </Add>(<Num>3</Num>'\
            ' )</BinOp>  )</Expr>'

    def test_binop_add(self, s2xml):
        assert s2xml('1 + 2') == \
            '<Expr><BinOp><Num>1</Num><Add> + </Add><Num>2</Num></BinOp></Expr>'

    def test_binop_add_space(self, s2xml):
        assert s2xml('3+  4') == \
            '<Expr><BinOp><Num>3</Num><Add>+  </Add><Num>4</Num></BinOp></Expr>'



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

    def test_call_arg(self, s2xml):
        assert s2xml('print(2,  "xxx" )') == \
            '<Expr><Call><func><Name ctx="Load" name="print">print</Name></func>'\
            '(<args><Num>2</Num>,  <Str><s>"xxx"</s></Str></args> )'\
            '</Call></Expr>'


class TestFuncDef_Return:
    def test_funcdef(self, s2xml):
        assert s2xml('def four (  ):\n    return 4') == \
            '<FunctionDef name="four">def four<arguments> (  ):</arguments>'\
            '<body>\n    <Return>return <Num>4</Num></Return>'\
            '</body></FunctionDef>'

    def test_funcdef_args(self, s2xml):
        assert s2xml('def p_four  (ini ):\n    return ini + 4') == \
            '<FunctionDef name="p_four">def p_four'\
            '<arguments>  (<args><arg name="ini">ini</arg></args> ):</arguments>'\
            '<body>\n    <Return>return <BinOp>'\
            '<Name ctx="Load" name="ini">ini</Name><Add> + </Add>'\
            '<Num>4</Num></BinOp></Return>'\
            '</body></FunctionDef>'



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
            '<alias> ,  <name>datetime</name></alias></Import>'

    def test_import_as_multi(self, s2xml):
        assert s2xml('import time as  t2, datetime  as dt') == \
            '<Import>import'\
            '<alias> <name>time</name> as  <asname>t2</asname></alias>'\
            '<alias>, <name>datetime</name>  as <asname>dt</asname></alias>'\
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
            '<alias>,  <name>baz</name> as <asname>zeta</asname></alias>'\
            '</names>'\
            '</ImportFrom>'

    def test_importfrom_level2_module_none(self, s2xml):
        assert s2xml('from .. import bar') == \
            '<ImportFrom level="2">from ..<module/> import<names>'\
            '<alias> <name>bar</name></alias>'\
            '</names></ImportFrom>'



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



def test_xml2py():
    assert xml2py('<a>x<b>y</b>z</a>') == 'xyz'
