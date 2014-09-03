
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
            # the module and body tags: <Module><body> ... </body></Module>
            return result[14:-16]
        return result
    return py_str2xml


class TestXml:
    def test_num(self, s2xml):
        assert s2xml('6') == '<Expr><Num>6</Num></Expr>'

    def test_str(self, s2xml):
        assert s2xml('"my string"') == '<Expr><Str>"my string"</Str></Expr>'
        assert s2xml("'''my 2'''") == "<Expr><Str>'''my 2'''</Str></Expr>"

    def test_binop_add(self, s2xml):
        assert s2xml('1 + 2') == \
            '<Expr><BinOp><Num>1</Num><Add> + </Add><Num>2</Num></BinOp></Expr>'

    def test_binop_add_space(self, s2xml):
        assert s2xml('3+  4') == \
            '<Expr><BinOp><Num>3</Num><Add>+  </Add><Num>4</Num></BinOp></Expr>'

    def test_assign(self, s2xml):
        assert s2xml('d = 5') == \
            '<Assign><targets><Name ctx="Store" name="d">d</Name></targets><delimiter> = </delimiter><Num>5</Num></Assign>'

    def test_assign_space(self, s2xml):
        assert s2xml('f  =   7') == \
            '<Assign><targets><Name ctx="Store" name="f">f</Name></targets><delimiter>  =   </delimiter><Num>7</Num></Assign>'


def test_xml2py():
    assert xml2py('<a>x<b>y</b>z</a>') == 'xyz'
