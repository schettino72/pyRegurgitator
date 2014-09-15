"""change the value assigned to a variable `__version__`"""

import xml.etree.ElementTree as ET


# parse XML document
doc = ET.parse('_sample/sample.py.xml')

# get node for assignment
assign = doc.find("/Assign/targets/Name[@name='__version__']/../..")
# in an assignment the value is on the second node
assign.remove(assign[1])
new_val = ET.Element('value')
new_val.text = '0, 2, 0'
new_val.tail = ')'
assign.append(new_val)

# save the contents in a new file
source = ET.tostring(doc.getroot(), encoding='unicode', method='text')
print(source)

