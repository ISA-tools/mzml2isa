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

# class _TarFile(tarfile.TarFile):
#     """A TarFile proxy with a setable name
#     """
#
#     def __init__(self, name, buffered_reader):
#         self.name = name
#         self.BufferedReader = buffered_reader
#
#     def __getattr__(self, attr):
#         if attr=="name":
#             return self.name
#         return getattr(self.BufferedReader, attr)

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

# def dict_update(d, u):
#     """Update a nested dictionnary of various depth
#
#     Shamelessly taken from here: http://stackoverflow.com/a/3233356/623424
#     And updated to work with dictionaries nested in lists.
#     """
#     for k, v in six.iteritems(u):
#         if isinstance(v, collections.Mapping):
#             if not k in d:
#                 warnings.warn("Unrecognized key: {}".format(k), UserWarning)
#             r = dict_update(d.get(k, {}), v)
#             d[k] = r
#         elif isinstance(v, list):
#             r = []
#             for x in v:                      # v Mandatory because of Python linking lists
#                 r.append(dict_update(copy.deepcopy(d[k][0]), copy.deepcopy(x)))
#             d[k] = r
#         else:
#             d[k] = u[k]
#     return d

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
    """Unpack arguments if they come packed
    """
    @functools.wraps(func)
    def new_func(*args):
        if len(args)==1:
            return func(*args[0])
        else:
            return func(*args)
    return new_func
