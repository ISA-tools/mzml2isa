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
port and enhancements were carried out by Martin Larralde (ENS Cachan, FR)
in June 2016 during an internship at the EBI Cambridge.

License
-----------------------------------------------------------------------------
GNU General Public License version 3.0 (GPLv3)
"""

import collections
import sys
import copy




## GET THE BEST AVAILABLE PARSER

try:
    from lxml import etree

    def getparent(element, tree):
        """Finds every parent of a tree node.

        Uses the method provided by lxml.etree
        """
        return element.getparent()

except ImportError:

    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree

    def getparent(element, tree):
        """Finds every parent of a tree node.

        As xml.ElementTree has no **.getparent** method, the following was
        proposed here : http://stackoverflow.com/questions/2170610#20132342
        """
        return {c:p for p in tree.iter() for c in p}[element]


## VERSION SPECIFIC UTILS

if sys.version_info == 2:

    RMODE = 'rb'
    WMODE = 'wb'

    def iterdict(dictionary):
        """Creates an iterator on the items of a dictionnary"""
        return dictionary.iteritems()

else:

    def iterdict(dictionary):
        """Creates an iterator on the items of a dictionnary"""
        return dictionary.items()

    RMODE = 'r'
    WMODE = 'w'



## VERSION AGNOSTIC UTILS

def dict_update(d, u):
    """Update a nested dictionnary of various depth

    Shamelessly taken from here: http://stackoverflow.com/a/3233356/623424
    And updated to work with dictionaries nested in lists.
    """
    for k, v in iterdict(u):
        if isinstance(v, collections.Mapping):
            if not k in d:
                warnings.warn("Unrecognized key: {}".format(k), UserWarning)
            r = dict_update(d.get(k, {}), v)
            d[k] = r
        elif isinstance(v, list):
            r = []
            for x in v:                      # v Mandatory because of Python linking lists
                r.append(dict_update(copy.deepcopy(d[k][0]), copy.deepcopy(x)))
            d[k] = r
        else:
            d[k] = u[k]
    return d

def pyxpath(mzMLmeta, query):
        """Finds every occurence of *query* in *mzMLmeta.tree* with proper namespace

        This function also formats the xpath query using the *mzMLmeta.env
        dictionnary created by the **mzml.mzMLmeta.build_env** function.
        """
        return mzMLmeta.tree.iterfind(query.format(**mzMLmeta.env), mzMLmeta.ns)

def longest_substring(string1, string2):
    answer = ""
    len1, len2 = len(string1), len(string2)
    for i in range(len1):
        match = ""
        for j in range(len2):
            if (i + j < len1 and string1[i + j] == string2[j]):
                match += string2[j]
            else:
                if (len(match) > len(answer)): answer = match
                match = ""
    return answer
