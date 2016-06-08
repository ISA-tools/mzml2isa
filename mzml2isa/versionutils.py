"""
Content
-----------------------------------------------------------------------------
This module includes some tricks for switching the behaviour of the script
depending on the Python version, while keeping a proper API in the core of
the other modules.

About
-----------------------------------------------------------------------------
The mzml2isa parser was created by Tom Lawson (University of Birmingham, UK) 
as part of a NERC funded placement at EBI Cambridge in June 2015. Python 3
port and small enhancements were carried out by Martin Larralde (ENS Cachan, 
France) in June 2016 during an internship at the EBI Cambridge.

License
-----------------------------------------------------------------------------
GNU General Public License version 3.0 (GPLv3)
"""

try: # Python 2
    from lxml import etree 
    
    def pyxpath(mzMLmeta, query): 
      """Finds every occurence of *query* in *mzMLmeta.tree* with proper namespace

      This function also formats the xpath query using the *mzMLmeta.env 
      dictionnary created by the **mzml.mzMLmeta.build_env** function.
      """ 
      return mzMLmeta.tree.xpath(query.format(**mzMLmeta.env), namespaces=mzMLmeta.ns)
    
    def getparent(element, tree): 
      """Finds every parent of a tree node.

      Uses the method provided by lxml.etree
      """
      return element.getparent()
    
    def iterdict(dictionary): 
      """Creates an iterator on the items of a dictionnary"""
      return dictionary.iteritems()

    RMODE = 'rb'
    WMODE = 'wb'


except ImportError: # Python 3
    from xml.etree import ElementTree as etree 
    
    def pyxpath(mzMLmeta, query):
      """Finds every occurence of *query* in *mzMLmeta.tree* with proper namespace

      This function also formats the xpath query using the *mzMLmeta.env 
      dictionnary created by the **mzml.mzMLmeta.build_env** function.
      """ 
      return mzMLmeta.tree.findall(query.format(**mzMLmeta.env), mzMLmeta.ns)
    
    def getparent(element, tree): 
      """Finds every parent of a tree node.

      As xml.ElementTree has no **.getparent** method, the following was
      proposed here : http://stackoverflow.com/questions/2170610#20132342
      """
      return {c:p for p in tree.iter() for c in p}[element]
    
    def iterdict(dictionary): 
      """Creates an iterator on the items of a dictionnary"""
      return dictionary.items()

    RMODE = 'r'
    WMODE = 'w'
