import os

from pyreg.astview import ast_view

SAMPLE = os.path.join(os.path.dirname(__file__), 'sample.py')

def test_txt(capsys):
    ast_view(['--format', 'txt', SAMPLE])
    out = capsys.readouterr()[0]
    expected = """Module(body=[Assign(lineno=1, col_offset=0, targets=[Name(lineno=1, col_offset=0, ctx=Store(), id='foo')], value=BinOp(lineno=1, col_offset=6, left=Num(lineno=1, col_offset=6, n=7), op=Add(), right=Num(lineno=1, col_offset=10, n=2)))])\n"""
    assert expected == out


def test_map(capsys):
    ast_view(['--format', 'map', SAMPLE])
    out = capsys.readouterr()[0]
    expected = """.body[0] []
.body[0] (Assign)
.body[0].targets[0] []
.body[0].targets[0] (Name)
.body[0].targets[0].ctx (Store)
.body[0].targets[0].id => 'foo'
.body[0].value (BinOp)
.body[0].value.left (Num)
.body[0].value.left.n => 7
.body[0].value.op (Add)
.body[0].value.right (Num)
.body[0].value.right.n => 2
"""
    assert expected == out


# XXX not testing much, just make sure program can run
def test_html(capsys):
    ast_view(['--format', 'html', SAMPLE])
    out = capsys.readouterr()[0]
    expected = """<tr>
              <td class="field_name">id</td>
              <td><span class="final">'foo'</span></td>
            </tr>
"""
    assert expected in out
