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
## pyxpath, getparent and iterdict are wrappers around the API changes 
## between python2 and python3.
## pyxpath also reduces the function call syntax and does the formatting
## of the xpath expression.



XPATHS_META = {'file_content':      '{root}/s:fileDescription/s:fileContent/s:cvParam',
               'source_file':       '{root}/s:fileDescription/s:sourceFileList/s:sourceFile/s:cvParam',
               'ionization':        '{root}/{instrument}List/{instrument}/s:componentList/s:source/s:cvParam',
               'analyzer':          '{root}/{instrument}List/{instrument}/s:componentList/s:analyzer/s:cvParam',
               'detector':          '{root}/{instrument}List/{instrument}/s:componentList/s:detector/s:cvParam',
               'data_processing':   '{root}/s:dataProcessingList/s:dataProcessing/s:processingMethod/s:cvParam',
              }

XPATHS =      {'ic_ref':            '{root}/{instrument}List/{instrument}/s:referenceableParamGroupRef[@ref]',
               'ic_elements':       '{root}/s:referenceableParamGroupList/s:referenceableParamGroup',
               'ic_nest':           '{root}/{instrument}List/{instrument}/s:cvParam[@accession]',
               'ic_soft_ref':       '{root}/{instrument}List/{instrument}/{softwareRef}[@ref]',
               'software_elements': '{root}/s:softwareList/s:software',
               'sp_cv':             '{root}/s:run/s:spectrumList/s:spectrum/s:cvParam',
               'scan_window_cv':    '{root}/s:run/s:spectrumList/s:spectrum/{scanList}/s:scan/{scanWindow}List/{scanWindow}/s:cvParam',                   
               'scan_cv':           '{root}/s:run/s:spectrumList/s:spectrum/{scanList}/s:scan/s:cvParam',          
               'scan_num':          '{root}/s:run/s:spectrumList[@count]',
               'cv':                '{root}/s:cvList/s:cv[@{cvLabel}]',
               'raw_file':          '{root}/s:fileDescription/s:sourceFileList/s:sourceFile[@{filename}]',
              }



try:
    from lxml import etree # Python 2.7
    pyxpath = lambda mzMLmeta, query, : mzMLmeta.tree.xpath(query.format(**mzMLmeta.env), namespaces=mzMLmeta.ns)
    getparent = lambda element, tree: element.getparent()
    iterdict = lambda dictionary: dictionary.iteritems()

    RMODE = 'rb'
    WMODE = 'wb'

except ImportError:
    from xml.etree import ElementTree as etree # Python 3.5+
    pyxpath = lambda mzMLmeta, query: mzMLmeta.tree.findall(query.format(**mzMLmeta.env), mzMLmeta.ns)
    getparent = lambda element, tree: {c:p for p in tree.iter() for c in p}[element]
    iterdict = lambda dictionary: dictionary.items()

    RMODE = 'r'
    WMODE = 'w'
