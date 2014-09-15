
# print all module class and its method names
import xml.etree.ElementTree as ET
doc = ET.parse('_sample/sample.py.xml')

# get all classes from module
for classdef in doc.findall('/ClassDef'):
    print('class ', classdef.get('name'))
    for funcdef in classdef.findall('./body/FunctionDef'):
        print('  ', funcdef.get('name'))

