import os.path
from pkg_resources import resource_filename

from pyreg.asdlview import asdl_view


def test_json(capsys):
    asdl_file = resource_filename('pyreg',
                                  os.path.join('asdl', 'python34.asdl'))
    asdl_view(['--format', 'json', asdl_file])
    got = capsys.readouterr()[0]
    expected = '''"Assign": {
        "category": "stmt",
        "fields": {
            "targets": {
                "cat": "expr",
                "q": "*"
            },
            "value": {
                "cat": "expr",
                "q": ""
            }
        },
        "order": [
            "targets",
            "value"
        ]
    },'''
    assert expected in got


def test_html(capsys):
    asdl_file = resource_filename('pyreg',
                                  os.path.join('asdl', 'python34.asdl'))
    asdl_view(['--format', 'html', asdl_file])
    got = capsys.readouterr()[0]
    expected = '''<div class="type stmt">
        <div>Assign</div>
                  <span title="expr" class="field expr">*targets</span>
                  <span title="expr" class="field expr">value</span>
            </div>
'''
    assert expected in got
