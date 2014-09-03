
import pytest

from pyreg.py2xml import py2xml


@pytest.fixture
def s2xml(tmpdir):
    def py_str2xml(string):
        p = tmpdir.join("x.py")
        p.write(string)
        # the slice 14:-16 is to remove the string of
        # the module and body tags: <Module><body> ... </body></Module>
        return py2xml(p.strpath)[14:-16]
    return py_str2xml

class TestXml:
    def test_num(self, s2xml):
        assert s2xml('6') == '<Expr><Num>6</Num></Expr>'
    def test_binop(self, s2xml):
        assert s2xml('1 + 2') == \
            '<Expr><BinOp><Num>1</Num><Add> + </Add><Num>2</Num></BinOp></Expr>'
    def test_assign(self, s2xml):
        assert s2xml('d = 5') == \
            '<Assign><targets><Name ctx="Store" name="d">d</Name></targets><AssignOp> = </AssignOp><Num>5</Num></Assign>'
