"""
The mzml2isa parse was created by Tom Lawson (University of Birmingham). As part of a NERC funded placement at EBI
Cambridge in June 2015. Python 3 port was realized by Martin Larralde (ENS Cachan, France) in June 2016.

Birmingham supervisor: Prof Mark Viant
Help provided from  Reza Salek ‎[reza.salek@ebi.ac.uk]‎‎, Ken Haug ‎[kenneth@ebi.ac.uk]‎ and Christoph Steinbeck
‎[christoph.steinbeck@gmail.com]‎ at the EBI Cambridge.
-------------------------------------------------------
"""


## ML: This module includes utils for switching the behaviour of the script
## depending on the python version... Doing so allows to keep a proper api
## in the rest of the program.
##
## XPaths expressions are absolute with lxml.etree module (Py2) but won't work
## with xml.ElementTree so it is needed to convert those by actualy replacing the
## first node by a dot ('.') so that the xtree expression starts at the root
## element, i.e. s:indexedmzML.
##
## lxml directly returns an attrib with '/ns:something/@attrib' but this syntax
## won't work with ElementTree so the solution comes in 2 steps:
## - Python 2
##   - first we retrieve directly the attribute with pyxpath
##   - then we do nothing with attrib
## - Python 3
##   - first we just look for children with the wanted attribute
##   - then we get the attribute with attrib.
## --> Maybe it would be better in both case to select a node
## in the first time and the actual attribute in the second, 
## instead on relying on lxml.xpath behaviour.
##
## pyxpath, getparent, iterdict and attrib are wrappers around the API changes 
## between python2 and python3.
## 



# Python 2 compliants xpaths search expressions
XPATHS_META_PY2 = {'file_content': '//s:indexedmzML/s:mzML/s:fileDescription/s:fileContent/s:cvParam',
               'source_file': '//s:indexedmzML/s:mzML/s:fileDescription/s:sourceFileList/s:sourceFile/s:cvParam',
               'ionization': '//s:indexedmzML/s:mzML/s:instrumentConfigurationList/s:instrumentConfiguration/s:componentList/s:source/s:cvParam',
               'analyzer': '//s:indexedmzML/s:mzML/s:instrumentConfigurationList/s:instrumentConfiguration/s:componentList/s:analyzer/s:cvParam',
               'detector': '//s:indexedmzML/s:mzML/s:instrumentConfigurationList/s:instrumentConfiguration/s:componentList/s:detector/s:cvParam',
               'data_processing': '//s:indexedmzML/s:mzML/s:dataProcessingList/s:dataProcessing/s:processingMethod/s:cvParam',
               }

XPATHS_PY2 = {'ic_ref': '//s:indexedmzML/s:mzML/s:instrumentConfigurationList/s:instrumentConfiguration/s:referenceableParamGroupRef/@ref',



          'ic_elements': '//s:indexedmzML/s:mzML/s:referenceableParamGroupList/s:referenceableParamGroup',
          'ic_soft_ref': '//s:indexedmzML/s:mzML/s:instrumentConfigurationList/s:instrumentConfiguration/s:softwareRef/@ref',
          'software_elements': '//s:indexedmzML/s:mzML/s:softwareList/s:software',
          'sp_cv': '//s:indexedmzML/s:mzML/s:run/s:spectrumList/s:spectrum/s:cvParam',
          

          'scan_window_cv':          '//s:indexedmzML/s:mzML/s:run/s:spectrumList/s:spectrum/s:scanList/s:scan/s:scanWindowList/s:scanWindow/s:cvParam',          
          'scan_window_cv_specdesc':        '//s:indexedmzML/s:mzML/s:run/s:spectrumList/s:spectrum/s:spectrumDescription/s:scan/s:scanWindowList/s:scanWindow/s:cvParam',
          'scan_window_cv_selectionwindow': './s:run/s:spectrumList/s:spectrum/s:spectrumDescription/s:scan/s:selectionWindowList/s:selectionWindow/s:cvParam',
          


          'scan_cv':          '//s:indexedmzML/s:mzML/s:run/s:spectrumList/s:spectrum/s:scanList/s:scan/s:cvParam',
          'scan_cv_specdesc': '//s:indexedmzML/s:mzML/s:run/s:spectrumList/s:spectrum/s:spectrumDescription/s:scan/s:cvParam',
          'scan_cv_selectionwindow': './s:run/s:spectrumList/s:spectrum/s:spectrumDescription/s:scan/s:cvParam',
          
          #'scan_num': '//s:indexedmzML/s:mzML/s:run/s:spectrumList/@count',
          'scan_num': './s:run/s:spectrumList/@count',

          'cv': '//s:indexedmzML/s:mzML/s:cvList/s:cv/@id',
          'cv_cvlabel': './s:cvList/s:cv/@cvLabel',

          'raw_file': '//s:indexedmzML/s:mzML/s:fileDescription/s:sourceFileList/s:sourceFile/@name',
          'raw_file_sourcefilename': './s:fileDescription/s:sourceFileList/s:sourceFile/@sourceFileName',

         }


try:
    from lxml import etree # Python 2.7.8
    pyxpath = lambda tree, query, ns: tree.xpath(query, namespaces=ns)
    getparent = lambda element, tree: element.getparent()
    attrib = lambda element, attrib: element
    iterdict = lambda dictionary: dictionary.iteritems()

    XPATHS = XPATHS_PY2
    XPATHS_META = XPATHS_META_PY2

    RMODE = 'rb'
    WMODE = 'wb'

except ImportError:
    from xml.etree import ElementTree as etree # Python 3.5+
    pyxpath = lambda tree, query, ns: tree.findall(query, ns)
    getparent = lambda element, tree: {c:p for p in tree.iter() for c in p}[element]
    attrib = lambda element, attrib: element.attrib[attrib]
    iterdict = lambda dictionary: dictionary.items()

    # Build Python3 compliants xpaths search expressions
    XPATHS_META = {k:v.replace('//s:indexedmzML', '.') for (k, v) in XPATHS_META_PY2.items()}

    XPATHS = {}
    for k, v in XPATHS_PY2.items():
        v = v.replace('//s:indexedmzML', '.')
        if '/@' in v:
            v = v.replace('/@', '[@') + ']'
        XPATHS[k] = v

    RMODE = 'r'
    WMODE = 'w'
