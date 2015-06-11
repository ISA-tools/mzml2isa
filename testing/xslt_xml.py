import lxml.etree as ET

dom = ET.parse("small.pwiz.1.1.mzML.xml")
xslt = ET.parse("mz2tom.xsl")
transform = ET.XSLT(xslt)
newdom = transform(dom)
print(ET.tostring(newdom, pretty_print=True))