"""
Content
-----------------------------------------------------------------------------
This module includes some tricks for switching the behaviour of the script
depending on the Python version, while keeping a proper API in the core of
the other modules, as well as miscellaneous class and function definitions.

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
import os
import sys
import six
import copy
import zipfile
import tarfile
import functools
import string
import warnings
import pronto
import itertools

from . import (
    __author__,
    __name__,
    __version__,
    __license__,
)

## RESOURCES
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
# MS_CV_URL = 'https://raw.githubusercontent.com/HUPO-PSI/psi-ms-CV/master/psi-ms.obo'
# IMS_CV_URL = 'https://raw.githubusercontent.com/ISA-tools/mzml2isa/master/mzml2isa/imagingMS.obo'

## AVAILABLE XML PARSER
try:
    from lxml import etree

    def get_parent(element, tree):
        """Finds every parent of a tree node.

        Uses the method provided by lxml.etree
        """
        return element.getparent()

except ImportError:

    try:
        from xml.etree import cElementTree as etree
    except ImportError:
        from xml.etree import ElementTree as etree

    def get_parent(element, tree):
        """Finds every parent of a tree node.

        As xml.ElementTree has no **.getparent** method, the following was
        proposed here : http://stackoverflow.com/questions/2170610#20132342
        """
        # {c:p for p in tree.iter() for c in p}[element]
        # next(p for p in tree.iter() for c in p if c==element)
        return next(p for p in tree.iter() if element in p)


## VERSION AGNOSTIC UTILS
class PermissiveFormatter(string.Formatter):
    """A formatter that replace wrong and missing key with a blank."""
    def __init__(self, missing='', bad_fmt=''):
        self.missing = missing
        self.bad_fmt = bad_fmt

    def get_field(self, field_name, args, kwargs):
        # Handle a key not found
        try:
            val=super(PermissiveFormatter, self).get_field(field_name, args, kwargs)
        except (KeyError, AttributeError, IndexError, TypeError):
            val=None,field_name
        return val

    def format_field(self, value, spec):
        # handle an invalid format
        if value==None:
            return self.missing
        try:
            return super(PermissiveFormatter, self).format_field(value, spec)
        except ValueError:
            if self.bad_fmt is not None:
                return self.bad_fmt
            else:
                raise


class _ChainMap(collections.Mapping):
    """A quick backport of collections.ChainMap
    """

    def __init__(self, *maps):
        self.maps = list(maps)

    def __getitem__(self, key):
        for mapping in self.maps:
            try:
                return mapping[key]
            except KeyError:
                pass
        return self.__missing__(key)

    @staticmethod
    def __missing__(key):
        raise KeyError(key)

    def __iter__(self):
        return itertools.chain(*self.mappings)

    def __len__(self):
        return sum(len(x) for x in self.mappings)


def merge_spectra(metalist):
    """Merge centroid and spectrum metadata of a same sample
    """
    profiles = [m for m in metalist \
        if m['Spectrum representation']['entry_list'][0]['name']=='profile spectrum']
    centroid = [m for m in metalist \
        if m['Spectrum representation']['entry_list'][0]['name']=='centroid spectrum']

    profiles.sort(key=lambda x: x['Sample Name']['value'])
    centroid.sort(key=lambda x: x['Sample Name']['value'])

    if len(profiles)!=len(centroid):
        return metalist

    for p,c in zip(profiles, centroid):
        p['Derived Spectral Data File']['entry_list'].extend(
            c['Derived Spectral Data File']['entry_list']
        )
        p['Raw Spectral Data File']['entry_list'].extend(
            c['Raw Spectral Data File']['entry_list']
        )
        p['Spectrum representation']['entry_list'].extend(
            c['Spectrum representation']['entry_list']
        )
        p['Sample Name']['value'] = longest_substring(
            p['Sample Name']['value'],c['Sample Name']['value']
        ).strip('-_;:() \n\t')
        p['MS Assay Name']['value'] = p['Sample Name']['value']

    return profiles


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


def star_args(func):
    """Unpack arguments before calling the wrapped function.
    """
    @functools.wraps(func)
    def new_func(args):
        return func(*args)
    return new_func
