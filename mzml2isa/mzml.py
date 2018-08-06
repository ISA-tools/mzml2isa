"""
Content
-----------------------------------------------------------------------------
This module contains two classes, mzMLmeta and imzMLmeta, which are used
to parse and serialize the metadata of a mzML or imzML file into a Python
dictionary.

Following features are implemented but were commented out:
- retrieval of sofware version number
- retrieval of raw-data SHA-1 checksum
Both can be found by looking for the #!# comment tag in the mzml2isa.mzml
module source code.

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
from __future__ import absolute_import

import collections
import json
import os
import glob
import six
import sys
import warnings
import itertools
import pronto

from . import (
    __author__,
    __name__,
    __version__,
    __license__,
)
from .utils import (
    etree, # best in: lxml, xml.etree.cElementTree, xml.etree.ElementTree
    pyxpath,
    longest_substring,
    get_parent,
    get_ontology,
    create_terms
)

from .meta_collectors import (
    AbstractCollector,
    Polarity,
    TimeRange,
    MzRange,
    DataFileContent
)

IDENTITY_THRESHOLD = 0.4



XPATHS_META = {'file_content':      '{root}/s:fileDescription/s:fileContent/s:cvParam',
               'source_file':       '{root}/s:fileDescription/s:sourceFileList/s:sourceFile/s:cvParam',
               'ionization':        '{root}/{instrument}List/{instrument}/s:componentList/s:source/s:cvParam',
               'analyzer':          '{root}/{instrument}List/{instrument}/s:componentList/s:analyzer/s:cvParam',
               'detector':          '{root}/{instrument}List/{instrument}/s:componentList/s:detector/s:cvParam',
               'data_processing':   '{root}/s:dataProcessingList/s:dataProcessing/s:processingMethod/s:cvParam',
               'contact':           '{root}/s:fileDescription/s:contact/s:cvParam',
              }


XPATHS =      {'ic_ref':            '{root}/{instrument}List/{instrument}/s:referenceableParamGroupRef',
               'ic_elements':       '{root}/s:referenceableParamGroupList/s:referenceableParamGroup',
               'ic_nest':           '{root}/{instrument}List/{instrument}/s:cvParam',
               'ic_soft_ref':       '{root}/{instrument}List/{instrument}/{software}',
               'software_elements': '{root}/s:softwareList/s:software',
               'sp':                '{root}/s:run/{spectrum}List/{spectrum}',
               'sp_cv':             '{root}/s:run/{spectrum}List/{spectrum}/s:cvParam',
               'scan_window_cv':    '{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/{scanWindow}List/{scanWindow}/s:cvParam',
               'scan_cv':           '{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/s:cvParam',
               'scan_num':          '{root}/s:run/{spectrum}List',
               'cv':                '{root}/s:cvList/s:cv',
               'raw_file':          '{root}/s:fileDescription/s:sourceFileList/s:sourceFile',

              }



class mzMLmeta(object):
    """ Class to store and obtain the meta information from the mzML file

    The class uses the xpaths of mzML locations and then extracts meta
    information at these locations. The meta info taken is determined by the
    ontology terms and a set of rules associated with that term e.g. if it
    can be repeated, if has associated software if it has a value as well
    as name.

    Attributes:
        tree (lxml.etree.ElementTree): the tree object created from
            the mzML file
        ns (dict): a dictionary containing the xml namespace mapping
        obo (pronto.Ontology): the ontology object
        meta (dict): structured dictionary containing extracted metadata
        env (dict): the `environment variables`, tag names that are not
            standards among different mzML files.

    """

    obo = None
    _descendents = dict()

    def __init__(self, in_file, ontology=None, complete_parse=False):
        """Setup the xpaths and terms. Then run the various extraction methods

        Parameters:
            in_file (:obj:`str`): path to mzML file
            ontology (:obj:`pronto.Ontology`): a cached MS ontology
            complete_parse (bool): parse scan-specific metadata
        """

        if ontology is None and self.obo is None:
            self.obo = get_ontology('MS')
        elif self.obo is None:
            self.obo = ontology

        # setup lxml parsing
        self.in_file = in_file

        try:
            self.in_dir = os.path.dirname(in_file)
        except (AttributeError, TypeError):
            self.in_dir = None

        # Create dictionary of terms to search mzML file
        terms = create_terms()

        # Parses only the first spectrum...
        self._parse_pruned_tree()

        # ...because build_env needs at least one.
        self.build_env()

        self._make_params()

        #initalize the meta variables
        self.meta = collections.OrderedDict()

        # xpaths for the mzML locations that we want the meta information from any cvParam elements
        xpaths_meta = XPATHS_META


        # update self.meta with the relevant meta information
        self.extract_meta(terms, xpaths_meta)

        # make a memoized dict of the referenceable params
        #self.make_params()

        # The instrument information has to be extracted separately
        self.instrument()

        # Get spectrum representation (as it might not be in file content)
        self.spectrum_repr(XPATHS['sp_cv'])

        # The following information is derived from other details in the mzML file
        self.scan_num()
        self.derived()

        # Collect information from the scans

        self.meta_collectors = [Polarity(), TimeRange(), MzRange()]

        if complete_parse:
            self.meta_collectors.append(self.spectrum_meta())
        elif 'Data file content' not in self.meta:
            file_contents = self.obo['MS:1000524'].rchildren().id
            self.meta_collectors.append(DataFileContent(file_contents))

        self._collect_scan_info()

        if 'Scan m/z range' not in self.meta:
            if not isinstance(self, imzMLmeta):  # Warn only if parsing a mzML file
                warnings.warn("Could not find any m/z range.")

        # Render control vocabularies accession numbers as urls
        self.urlize()

    def extract_meta(self, terms, xpaths):
        """ Extract meta information for CV terms based on their location in the xml file

        Updates the self.meta dictionary with the relevant meta information

        Arguments:
            terms (dict): The CV and search parameters required at the xml locations
            xpath (dict): the xpath locations to search

        .. seealso::
            :obj:`cvParam_loop`
        """

        # loop though the xpaths
        for location_name, xpath in six.iteritems(xpaths):

            # get the elements from the xpath
            elements = pyxpath(self, xpath)

            # loop through the elements and see if the terms are found
            self.cvParam_loop(elements, location_name, terms)

    def cvParam_loop(self, elements, location_name, terms):
        """Loop through the elements and eventually update the self.meta dict.

        Arguments:
            elements (iterator): the element containing the cvParam tags
            location_name (:obj:`str`): Name of the xml location
            terms (:obj:`dict`): terms that are to be extracted
        """
        # memoize the descendents of the current term
        self._descendents.update({
            k: self.obo[k].rchildren().id
            for k in terms[location_name]
            if k not in self._descendents
        })

        # go through every cvParam element
        for e in elements:
            # go through the terms available for this location
            for accession, info in six.iteritems(terms[location_name]):

                # check if the element is one of the terms we are looking for
                if e.attrib['accession'] in self._descendents[accession] or e.attrib['accession'] == accession:

                    meta_name = info['name']

                    entry = {
                        'accession': e.attrib['accession'],
                        'name': e.attrib['name'],
                        'ref': e.attrib['cvRef']
                    }

                    try:
                        entry['unit'] = {
                            'accession': e.attrib['unitAccession'],
                            'name': e.attrib['unitName'],
                            'ref': e.attrib['unitCvRef']
                        }
                    except KeyError:
                        pass

                    # Check if a value is associated with this CV
                    if info['value']:
                        entry['value'] = self._convert(e.attrib['value'])

                    # Check if there can be more than one of the same term
                    if info['plus1']:
                        # Setup the dictionary for multiple entries
                        if meta_name not in self.meta:
                            self.meta[meta_name] = {'entry_list': []}

                        if entry['name'].upper() == meta_name.upper():
                            del entry['accession']
                            del entry['name']
                            del entry['ref']

                        self.meta[meta_name]['entry_list'].append(entry)
                        #c += 1
                    else:
                        if info['value']:
                            # remove name and accession if only the value is interesting

                            if entry['name'].upper() == meta_name.upper():
                                del entry['name']
                                del entry['accession']

                        # Standard CV with only with entry
                        self.meta[meta_name] = entry

                    # Check if there is expected associated software
                    if info['soft']:

                        try:             # softwareRef in <Processing Method>
                            soft_ref = get_parent(e, self.tree).attrib['softwareRef']
                        except KeyError: # softwareRef in <DataProcessing>
                            soft_ref = get_parent(get_parent(e, self.tree), self.tree).attrib['softwareRef']

                        self.software(soft_ref, meta_name)

    @staticmethod
    def _convert(value):
        """Try to convert a string to the appropriate type.

        Arguments:
            value (str): the string to convert

        Returns:
            int: if the value can be converted to int
            float: if the value can be converted to float
            str: if the value could not be converted
        """
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    def _parse_pruned_tree(self):
        """Partially parse XML file, keeping metadata and one of the spectra/chromatogram

        Since the number of spectra might be very large, parsing the whole XML into memory
        might easily consume several gigabytes of RAM which is what we try to avoid here.
        """
        elements = etree.iterparse(self.in_file, events=('start', 'end'))
        _, self.root = next(elements)

        self.build_ns()
        prefix = '{' + self.ns['s'] + '}'

        spectrum_tags = set([prefix + tag for tag in ['spectrum', 'chromatogram']])
        sp_idx = 0
        for event, elem in elements:
            if event == 'start':
                continue
            if elem.tag in spectrum_tags:
                sp_idx += 1
                if sp_idx > 1:
                    elem.clear()  # keep only the first spectrum in memory

    def _collect_scan_info(self):
        """Iterate over scans and pass each scan to all meta_collectors"""
        spectrum_tag = self.env['spectrum'].replace('s:', '{' + self.ns['s'] + '}')

        elements = etree.iterparse(self.in_file)
        for _, elem in elements:
            if elem.tag == spectrum_tag:
                for collector in self.meta_collectors:
                    collector.process_scan(elem, self.env, self.ns)
                elem.clear()

        for collector in self.meta_collectors:
            collector.populate_meta(self.meta)

        # for entry in ('Collision Energy', 'Data file content', 'Dissociation method', 'Spectrum combination',
        #               'Binary data array', 'Binary data compression type', 'Binary data type'):
        #     self.merge_entries(entry)

    @property
    def tree(self):
        return self.root

    def _instrument_byref(self):
        """Extract the instrument from its referenceableParamList entry.

        The instrument meta information is more complicated to extract so it has its own function
        Updates the self.meta with the relevant meta information. Requires looking at the hierarchy
        of ontological terms to get all the instrument information
        """

        # gets the first Instrument config (something to watch out for)
        ic_ref = next(pyxpath(self, XPATHS['ic_ref'])).attrib["ref"]

        elements = pyxpath(self, XPATHS['ic_elements'])

        # Loop through xml elements
        for e in elements:
            # get all CV information from the instrument config
            if e.attrib['id']==ic_ref:
                instrument_e = e.iterfind('s:cvParam', self.ns)

                for ie in instrument_e:

                    # Get the instrument manufacturer
                    if ie.attrib['accession'] in self.obo['MS:1000031'].rchildren().id:
                        self.meta['Instrument'] = {'accession': ie.attrib['accession'], 'name':ie.attrib['name'],
                                                   'ref':ie.attrib['cvRef']}

                        if ie.attrib['name'] != self.obo[ie.attrib['accession']].name:
                            warnings.warn(" ".join(["The instrument name in the mzML file ({})".format(ie.attrib['name']),
                                                   "does not correspond to the instrument accession ({})".format(self.obo[ie.attrib['accession']].name)]))
                            self.meta['Instrument']['name'] = self.obo[ie.attrib['accession']].name

                        # get manufacturer (actually just derived from instrument model). Want to get the top level
                        # so have to go up (should only be a maximum of 3 steps above in the heirachy but do up 8 to be
                        # sure.
                        # directly related children of the instrument model

                        parents = self.obo[ie.attrib['accession']].rparents()
                        parents.append(self.obo[ie.attrib['accession']])
                        manufacturer = next(parent for parent in parents if parent in self.obo['MS:1000031'].children)

                        self.meta['Instrument manufacturer'] = {'accession': manufacturer.id, 'name': manufacturer.name,
                                                                'ref':manufacturer.id.split(':')[0]}

                    # get serial number
                    elif ie.attrib['accession'] == 'MS:1000529':
                        self.meta['Instrument serial number'] = {'value': ie.attrib['value']}

        soft_ref = next(pyxpath(self, XPATHS['ic_soft_ref'])).attrib[self.env['softwareRef']]

        # Get associated software
        self.software(soft_ref, 'Instrument')

    def _instrument_nested(self):
        """Extract the instrument from the instrument cvParam list.

        The easy case, where version number is not in ./referenceableParamList but directly
        in instrument/cvParam
        """

        elements = pyxpath(self, XPATHS['ic_nest'])

        for i, e in enumerate(elements):

            if e.attrib['accession'] == 'MS:1000031':
                break

            elif e.attrib['accession'] in self.obo['MS:1000031'].rchildren():
                self.meta['Instrument'] = {'accession': e.attrib['accession'], 'name':e.attrib['name'],
                                           'ref':e.attrib['cvRef']}

                if e.attrib['name'] != self.obo[e.attrib['accession']].name:
                    warnings.warn(" ".join(["The instrument name in the mzML file ({})".format(e.attrib['name']),
                                           "does not correspond to the instrument accession ({})".format(self.obo[e.attrib['accession']].name)]))
                    self.meta['Instrument']['name'] = self.obo[e.attrib['accession']].name

                parents = self.obo[e.attrib['accession']].rparents()
                parents.append(self.obo[e.attrib['accession']])
                manufacturer = next(parent for parent in parents if parent in self.obo['MS:1000031'].children)

                self.meta['Instrument manufacturer'] = {'accession': manufacturer.id, 'name': manufacturer.name,
                                                        'ref':manufacturer.id.split(':')[0]}

            elif e.attrib['accession'] == 'MS:1000529':
                self.meta['Instrument serial number'] = {'value': e.attrib['value']}


        try:
            soft_ref = next(pyxpath(self, XPATHS['ic_soft_ref'])).attrib[self.env['softwareRef']]
            # Get associated software
            self.software(soft_ref, 'Instrument')
        except (IndexError, KeyError, StopIteration): #Sometimes <Instrument> contains no Software tag
            warnings.warn("Instrument {} does not have a software tag.".format( self.meta['Instrument']['name']
                                                                                if 'Instrument' in self.meta
                                                                                else "<"+self.meta['Instrument serial number']+">"
                                                                                if 'Instrument serial number' in self.meta
                                                                                else '?'))

    def software(self, soft_ref, name):
        """ Get associated software of cv term. Updates the self.meta dictionary

        Parameters:
            soft_ref (:obj:`str`): the reference to the software found in another xml "ref" attribute.
            name (:obj:`str`): Name of the associated CV term that the software is associated to.
        """

        elements = pyxpath(self, XPATHS['software_elements'])

        if name.endswith('Name'):               # We don't want Data Transformation Name Software !
            name = name.replace(' Name', '')

        for e in elements:

            if e.attrib['id'] == soft_ref:

                try: # <Softwarelist <Software <cvParam>>>

                    if e.attrib['version']:
                        self.meta[name+' software version'] = {'value': e.attrib['version']}
                    software_cvParam = e.iterfind('s:cvParam', self.ns)
                    for ie in software_cvParam:
                        self.meta[name+' software'] = {'accession':ie.attrib['accession'], 'name':ie.attrib['name'],
                                                       'ref': ie.attrib['cvRef']}

                except KeyError:  # <SoftwareList <software <softwareParam>>>

                    params = e.find('s:softwareParam', namespaces=self.ns)
                    if params.attrib['version']:
                        self.meta[name+' software version'] = {'value': params.attrib['version']}
                    self.meta[name+' software'] = {'accession':params.attrib['accession'], 'name':params.attrib['name'],
                                                   'ref': params.attrib['cvRef']}

    def derived(self):
        """ Get the derived meta information

        The derived meta information includes all tags that are solely based
        on the file name, such as `MS Assay Name`, `Derived Spectral Data File`
        or `Sample Name`.
        """

        cv = next(pyxpath(self, XPATHS['cv'])).attrib[self.env["cvLabel"]]

        if not 'MS' in cv:
            warnings.warn("Standard controlled vocab not available. Cannot parse.")
            return

        try:
            raw_file = next(pyxpath(self, XPATHS['raw_file'])).attrib[self.env["filename"]]
            self.meta['Raw Spectral Data File'] = {'entry_list': [{'value': os.path.basename(raw_file)}] }
        except StopIteration:
            warnings.warn("Could not find any metadata about Raw Spectral Data File.")

        try:
            derived_spectral_data_file = os.path.basename(self.in_file.name)
            ms_assay_name = os.path.splitext(derived_spectral_data_file)[0]
        except AttributeError:
            derived_spectral_data_file = os.path.basename(self.in_file)
            ms_assay_name = os.path.splitext(derived_spectral_data_file)[0]

        self.meta['MS Assay Name'] = {'value': ms_assay_name}
        self.meta['Derived Spectral Data File'] = {'entry_list': [{'value': derived_spectral_data_file}] } # mzML file name
        self.meta['Sample Name'] = {'value': ms_assay_name} # mzML file name w/o extension

    def spectrum_repr(self, sp_cv):
        """Checks first spectrum for spectrum representation (profile/centroid)"""

        # Not required if this is already in the 'file content' section
        if 'Spectrum representation' in self.meta:
            return

        sp_cv = pyxpath(self, sp_cv)

        for e in sp_cv:
            if e.attrib['accession'] in self.obo['MS:1000525'].rchildren():
                self.meta['Spectrum representation'] = \
                                       {'accession': e.attrib['accession'], 'name': e.attrib['name'],
                                        'ref': e.attrib['cvRef']}
                return

    def _make_params(self):
        """Create a memoized set of xml Elements in `ReferenceableParamGroupList`
        """
        self._params = {x.attrib['id']:x for x in pyxpath(self,
        '{root}/s:referenceableParamGroupList/s:referenceableParamGroup')}

    def spectrum_meta(self):
        """Extract information of each spectrum in entry lists.

        This method is only called is the **complete_parse** parameters was set
        as True when the mzMLmeta object was created. This requires more time
        as iterating through hundreds of elements is bound to be more performance
        hungry than just a few elements. It is believed to be useful when mzml2isa
        is used as a parsing library.
        """

        terms = collections.OrderedDict()

        terms['sp'] = {
            'MS:1000524': {'attribute': False, 'name': 'Data file content', 'plus1': True, 'value': False, 'soft':False},
            'MS:1000796': {'attribute': False, 'name': 'Spectrum title', 'plus1': True, 'value': True, 'soft':False},
            'MS:1000465': {'attribute': False, 'name': 'Polarity', 'plus1': True, 'value': False, 'soft': False},
            'MS:1000511': {'attribute': False, 'name': 'MS Level', 'plus1': True, 'value':True, 'soft': False},
            'MS:1000525': {'attribute': False, 'name': 'Spectrum representation', 'plus1': True, 'value':False, 'soft': False},
            'MS:1000504': {'attribute': False, 'name': 'Base Peak m/z', 'plus1': True, 'value': True, 'soft': False},
            'MS:1000505': {'attribute': False, 'name': 'Base Peak intensity', 'plus1': True, 'value': True, 'soft': False},
            'MS:1000285': {'attribute': False, 'name': 'Total ion current', 'plus1': True, 'value': True, 'soft': False},

            'MS:1000927': {'attribute': False, 'name': 'Ion injection time', 'plus1': True, 'value': True, 'soft': False},
            'MS:1000512': {'attribute': False, 'name': 'Filter string', 'plus1': True, 'value': True, 'soft': False},

            'MS:1000528': {'attribute': False, 'name': 'Lowest observed m/z', 'plus1': True, 'value': True, 'soft': False},
            'MS:1000527': {'attribute': False, 'name': 'Highest observed m/z', 'plus1': True, 'value': True, 'soft': False},
        }

        terms['combination'] = {
            'MS:1000570': {'attribute': False, 'name': 'Spectrum combination', 'plus1': True, 'value': False, 'soft': False}
        }

        terms['configuration'] = {
            'MS:1000016': {'attribute': False, 'name': 'Scan start time', 'plus1': True, 'value': True, 'soft': False},
            'MS:1000512': {'attribute': False, 'name': 'Filter string', 'plus1': True, 'value': True, 'soft': False},
            'MS:1000616': {'attribute': False, 'name': 'Preset scan configuration', 'plus1': True, 'value': True, 'soft': False},
            'MS:1000927': {'attribute': False, 'name': 'Ion injection time', 'plus1': True, 'value':True, 'soft': False},
            'MS:1000018': {'attribute': False, 'name': 'Scan direction', 'plus1': True, 'value': True, 'soft':False},
            'MS:1000019': {'attribute': False, 'name': 'Scan law', 'plus1': True, 'value': True, 'soft':False},
        }

        terms['isolation_window'] = {
            'MS:1000827': {'attribute': False, 'name': 'Isolation window target m/z', 'plus1':True, 'value': True, 'soft': False},
            'MS:1000828': {'attribute': False, 'name': 'Isolation window lower offset', 'plus1':True, 'value': True, 'soft': False},
            'MS:1000829': {'attribute': False, 'name': 'Isolation window higher offset', 'plus1':True, 'value': True, 'soft': False},
        }

        terms['selected_ion'] = {
            'MS:1000744': {'attribute': False, 'name': 'Selected ion m/z', 'plus1': True, 'value': True, 'soft': False},
            'MS:1000744': {'attribute': False, 'name': 'Charge state', 'plus1': True, 'value': True, 'soft': False},
            'MS:1000744': {'attribute': False, 'name': 'Peak intensity', 'plus1': True, 'value': True, 'soft': False},
        }

        terms['activation'] = {
            'MS:1000044': {'attribute': False, 'name': 'Dissociation method', 'plus1': True, 'value': False, 'soft': False},
            'MS:1000045': {'attribute': False, 'name': 'Collision Energy', 'plus1': True, 'value': True, 'soft':False},
        }

        terms['binary'] = {
            'MS:1000518': {'attribute': False, 'name': 'Binary data type', 'plus1': True, 'value': False, 'soft': False},
            'MS:1000572': {'attribute': False, 'name': 'Binary data compression type', 'plus1': True, 'value': False, 'soft': False},
            'MS:1000513': {'attribute': False, 'name': 'Binary data array', 'plus1': True, 'value': False, 'soft': False},
        }

        cvParam_loop = self.cvParam_loop
        _params = self._params

        class SpectrumMeta(AbstractCollector):
            def process_scan(self, spectrum, env, ns):
                for path, name in [('./s:referenceableParamGroupRef', 'sp'),
                                   ('{scanList}/s:scan/s:referenceableParamGroupRef', 'combination'),
                                   ('{root}/s:referenceableParamGroupList/s:referenceableParamGroup', 'binary')]:

                    refs = spectrum.iterfind(path.format(**env), ns)
                    for ref in refs:
                        params = _params[ref.attrib['ref']]
                        cvParam_loop(params.iterfind('s:cvParam', ns), name, terms)

                cvParam_loop(spectrum.iterfind('s:cvParam', ns), 'sp', terms)
                cvParam_loop(spectrum.iterfind('{scanList}/s:cvParam'.format(**env), ns), 'combination', terms)
                cvParam_loop(spectrum.iterfind('{scanList}/s:scan/s:cvParam'.format(**env), ns), 'configuration', terms)
                cvParam_loop(spectrum.iterfind('s:binaryDataArrayList/s:binaryDataArray/s:cvParam'.format(**env), ns), 'binary', terms)

                cvParam_loop(spectrum.iterfind('s:precursorList/s:precursor/s:activation/s:cvParam', ns), 'activation', terms)
                cvParam_loop(spectrum.iterfind('s:precursorList/s:precursor/s:isolationWindow/s:cvParam', ns), 'isolation_window', terms)
                cvParam_loop(spectrum.iterfind('s:precursorList/s:precursor/s:selectedIonList/s:selectedIon/s:cvParam', ns), 'selected_ion', terms)

        return SpectrumMeta()

    def merge_entries(self, name):
        """An unoptimized way of merging meta entries only made of duplicates.

        This is only useful when the :obj:`spectrum_meta` method is called, as
        a way of reducing the size of some meta entries that add no interesting
        information (for instance, when all binary data is compressed the same
        way, it is useless to know that for each scan).

        Arguments:
            name (str): the entry to de-duplicate

        Returns:
            list: the list of the list with deduplicated arguments

        .. note::

            Using an OrderedSet to deduplicate while preserving order may be a
            good idea (see http://code.activestate.com/recipes/576694/) for actual
            implementation
        """

        if name in self.meta.keys():
            if 'entry_list' in self.meta[name].keys():
                seen = set()
                return [x for x in self.meta[name]['entry_list'] if str(x) not in seen and not seen.add(str(x))]

    def scan_num(self):
        """Extract the total number of scans."""
        scan_num = next(pyxpath(self, XPATHS['scan_num'])).attrib["count"]
        self.meta['Number of scans'] = {'value': int(scan_num)}

    def urlize(self):
        """Urllize all accessions within the meta dictionary"""

        for meta_name in self.meta:
            #if 'accession' in self.meta[meta_name]:
            try:
                self.meta[meta_name]['accession'] = self._urlize_name(self.meta[meta_name]['accession'])
            except KeyError:
                pass

            try:
                self.meta[meta_name]['unit']['accession'] = self._urlize_name(self.meta[meta_name]['unit']['accession'])
            except KeyError:
                pass

            try:
                for index, entry in enumerate(self.meta[meta_name]['entry_list']):
                    try:
                        self.meta[meta_name]['entry_list'][index]['accession'] = self._urlize_name(entry['accession'])
                    except KeyError:
                        pass
                    try:
                        self.meta[meta_name]['entry_list'][index]['unit']['accession'] = self._urlize_name(entry['unit']['accession'])
                    except KeyError:
                        pass
            except KeyError:
                pass

    @staticmethod
    def _urlize_name(accession):
        """Turn YY:XXXXXXX accession number into an url

        Parameters:
            accession (str): a CV term accession

        Returns:
            str: an url version of the accession

        """
        if accession.startswith('MS'):
            return "http://purl.obolibrary.org/obo/{}".format(accession.replace(':', '_'))
        elif accession.startswith('IMS'):
            return "http://www.maldi-msi.org/download/imzml/imagingMS.obo#{}".format(accession)
        elif accession.startswith('UO'):
            return "http://purl.obolibrary.org/obo/{}".format(accession.replace(':', '_'))
        return accession

    def _getroot(self):
        return self.root

    def build_ns(self):
        """Build the ns dictionary."""
        try: #lxml
            self.ns = self._getroot().nsmap
            self.ns['s'] = self.ns[None] # namespace
            del self.ns[None]
        except AttributeError: #xml.(c)ElementTree
            self.ns = {'s': self._getroot().tag[1:].split("}")[0]}

    def build_env(self):
        """Build the env dictionary."""

        self.env = collections.OrderedDict()

        # Check if indexedmzML/mzML or mzML
        if isinstance(self, mzMLmeta):
            if self.tree.find('./s:mzML', self.ns) is None :
                self.env['root'] = '.'
            else:
                self.env['root'] = './s:mzML'
        else:
            if self.tree.find('./s:imzML', self.ns) is None :
                self.env['root'] = '.'
            else:
                self.env['root'] = './s:imzML'

        # check if spectrum or chromatogram
        if self.tree.find('{root}/s:run/s:spectrumList/s:spectrum/'.format(**self.env), self.ns) is not None:
            self.env['spectrum'] = 's:spectrum'
        elif self.tree.find('{root}/s:run/s:chromatogramList/s:chromatogram/'.format(**self.env), self.ns) is not None:
            self.env['spectrum'] = 's:chromatogram'

        # check if scanList or SpectrumDescription
        if self.tree.find('{root}/s:run/{spectrum}List/{spectrum}/s:scanList'.format(**self.env), self.ns) is not None:
            self.env['scanList'] = 's:scanList'
        else:
            self.env['scanList'] = 's:spectrumDescription'

        # check if scanWindow or selectionWindow
        if self.tree.find('{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/s:scanWindowList/s:scanWindow'.format(**self.env), self.ns) is not None:
            self.env['scanWindow'] = 's:scanWindow'
        else:
            self.env['scanWindow'] = 's:selectionWindow'

        # check if sourceFile/@name or sourceFile/@sourceFileName
        if self.tree.find('{root}/s:fileDescription/s:sourceFileList/s:sourceFile[@name]'.format(**self.env), self.ns) is not None:
            self.env['filename'] = 'name'
        else:
            self.env['filename'] = 'sourceFileName'

        # check if cv/@id or cv
        if self.tree.find('{root}/s:cvList/s:cv[@id]'.format(**self.env), self.ns) is not None:
            self.env['cvLabel'] = 'id'
        else:
            self.env['cvLabel'] = 'cvLabel'

        # check if instrumentList or instrumentConfigurationList
        if self.tree.find('{root}/s:instrumentConfigurationList'.format(**self.env), self.ns) is not None:
            self.env['instrument'] = 's:instrumentConfiguration'
        else:
            self.env['instrument'] = 's:instrument'

        # check if softwareRef or instrumentSoftwareRef
        if self.tree.find('{root}/{instrument}List/{instrument}/s:softwareRef[@ref]'.format(**self.env), self.ns) is not None:
            self.env['software'] = 's:softwareRef'
            self.env['softwareRef'] = 'ref'
        elif self.tree.find('{root}/{instrument}List/{instrument}/s:instrumentSoftwareRef[@ref]'.format(**self.env), self.ns) is not None:
            self.env['software'] = 's:instrumentSoftwareRef'
            self.env['softwareRef'] = 'ref'

        # check if instrument serial is in instrument or refereceableParam
        if self.tree.find('{root}/s:referenceableParamGroupList/s:referenceableParamGroup/s:cvParam[@accession="MS:1000529"]'.format(**self.env), self.ns) is not None:
            self.instrument = self._instrument_byref
        #if self.tree.find('{root}/{instrument}List/{instrument}/s:cvParam[@accession="MS:1000529"]'.format(**self.env), self.ns) is not None:
        else:
            self.instrument = self._instrument_nested

    @property
    def meta_json(self):
        """Returns the metadata dictionary in json format
        """
        return json.dumps(self.meta, indent=4, sort_keys=True)

    @property
    def meta_isa(self):
        """Returns the metadata dictionary with actual ISA headers
        """
        keep = ["Data Transformation", "Data Transformation software version", "Data Transformation software",
                "term_source", "Raw Spectral Data File", "MS Assay Name", "Derived Spectral Data File", "Sample Name"]

        meta_isa = collections.OrderedDict()

        for meta_name in self.meta:
            if meta_name in keep:
                meta_isa[meta_name] = self.meta[meta_name]
            else:
                meta_isa["Parameter Value[{}]".format(meta_name)] = self.meta[meta_name]

        return meta_isa

    @property
    def meta_isa_json(self):
        return json.dumps(self.meta_isa, indent=4, sort_keys=True)



XPATHS_I_META = {'file_content':      '{root}/s:fileDescription/s:fileContent/s:cvParam',
                 'scan_settings':     '{root}/s:scanSettingsList/s:scanSettings/s:cvParam',
                 'source':            '{root}/{instrument}List/{instrument}/s:componentList/s:source/s:cvParam',
                }

XPATHS_I =      {'scan_dimensions':   '{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/s:cvParam',
                 'scan_ref':          '{root}/s:run/{spectrum}List/{spectrum}/s:referenceableParamGroupRef',
                 'ref_param_list':    '{root}/s:referenceableParamGroupList/s:referenceableParamGroup',
                }


class imzMLmeta(mzMLmeta):

    def __init__(self, in_file, ontology=None):
        """Setup the xpaths and terms. Then run the various extraction methods

        Parameters:
            in_file (str): path to imzML file
            ontology (pronto.Ontology): a cached IMS ontology
        """

        if ontology is None and self.obo is None:
            self.obo = get_ontology('IMS')
        elif self.obo is None:
            self.obo = ontology

        super(imzMLmeta, self).__init__(in_file)

        xpaths_meta = XPATHS_I_META

        terms = create_terms()

        terms['file_content'] = {
                'MS:1000525' : {'attribute': False, 'name': 'Spectrum representation', 'plus1': False, 'value': False, 'soft': False},
                'IMS:1000008': {'attribute': False, 'name': 'Universally unique identifier', 'plus1': False, 'value': True, 'soft':False},
                'IMS:1000009': {'attribute': False, 'name': 'Binary file checksum type', 'plus1': False, 'value': True, 'soft': False},
                'IMS:1000003': {'attribute': False, 'name': 'Ibd binary type', 'plus1': False, 'value': False, 'soft':False},
        }

        terms['scan_settings'] = {
                'IMS:1000040': {'attribute': False, 'name': 'Linescan sequence', 'plus1': False, 'value': False, 'soft': False},
                'IMS:1000041': {'attribute': False, 'name': 'Scan pattern', 'plus1': False, 'value': False, 'soft': False},
                'IMS:1000042': {'attribute': False, 'name': 'Max count of pixel x', 'plus1': False, 'value': True, 'soft':False},
                'IMS:1000043': {'attribute': False, 'name': 'Max count of pixel y', 'plus1': False, 'value': True, 'soft':False},
                'IMS:1000044': {'attribute': False, 'name': 'Max dimension x', 'plus1': False, 'value': True, 'soft':False},
                'IMS:1000045': {'attribute': False, 'name': 'Max dimension y', 'plus1': False, 'value': True, 'soft':False},
                'IMS:1000046': {'attribute': False, 'name': 'Pixel size x', 'plus1': False, 'value': True, 'soft':False},
                'IMS:1000047': {'attribute': False, 'name': 'Pixel size y', 'plus1': False, 'value': True, 'soft':False},
                'IMS:1000048': {'attribute': False, 'name': 'Scan type', 'plus1': False, 'value': False, 'soft': False},
                'IMS:1000049': {'attribute': False, 'name': 'Line scan direction', 'plus1': False, 'value': False, 'soft': False},
        }

        terms['source'] = {
                'IMS:1001213': {'attribute': False, 'name': 'Solvent flowrate', 'plus1': False, 'value': True, 'soft':False },
                'IMS:1001211': {'attribute': False, 'name': 'Solvent', 'plus1': False, 'value': True, 'soft':False },
                'IMS:1000202': {'attribute': False, 'name': 'Target material', 'plus1': False, 'value': True, 'soft': False},
                'IMS:1001212': {'attribute': False, 'name': 'Spray voltage', 'plus1': False, 'value': True, 'soft': False},
        }


        self.extract_meta(terms, xpaths_meta)

        self.scan_meta()

        self.link_files()

        self.urlize()

    def link_files(self):
        """Put 'Raw Spectral Data File' and 'Spectrum Representation' in entry_lists
        """

        try:
            raw_spectral_data_file = os.path.splitext(os.path.basename(self.in_file.name))[0]
        except AttributeError:
            raw_spectral_data_file = os.path.splitext(os.path.basename(self.in_file))[0]

        self.meta['Raw Spectral Data File'] =  {'entry_list': [{'value': raw_spectral_data_file \
                                                                          + os.path.extsep + 'ibd'}] }

        self.meta['Spectrum representation'] = {'entry_list': [ self.meta['Spectrum representation'] ] }

        #if group_spectra:
        #    self.meta['MS Assay Name']['value'] = self.meta['MS Assay Name']['value']

        self.meta['High-res image'] = {'value': self.find_img('ndpi') }
        self.meta['Low-res image'] =  {'value': self.find_img('jpg', 'tif') }

    def find_img(self, *args):
        """Find associated image files in the same directory as imzML files

        Arguments:
            *args: Image file extensions to look for

        Returns:
            str: the image file corresponding to the asked extensions
        """

        identity = dict()
        sample_name = self.meta['Sample Name']['value']

        # First attempt to find image files named exactly like the imzML file
        for file in (x for x in os.listdir(self.in_dir) if x.lower().endswith(args)):
            if os.path.splitext(file)[0] == sample_name:
                return file

        # If None is found, attempt comparing identity
        for img_format in args:

            name = self.meta['Sample Name']['value']

            try:
                # Get a reduced file list with just the img_format that is in the loop
                rfilelist = [f for f in self.in_file.filelist if f.lower().endswith(img_format)]
                # loop through the reduced file list, compute and add to the identity dicitonary
                for file in rfilelist:
                    filename = os.path.splitext(os.path.basename(file))[0]
                    identity[os.path.basename(file)] = len(longest_substring(filename, name)) / len(name)

            except AttributeError:

                for file in glob.glob(os.path.join(self.in_dir, '*.{}'.format(img_format))):
                    filename = os.path.splitext(os.path.basename(file))[0]
                    identity[os.path.basename(file)] = len(longest_substring(filename, name)) / len(name)

        if identity and max(identity.values()) > IDENTITY_THRESHOLD:
            return max(identity, key=identity.get)
        else:
            return ''

    def _collect_scan_info(self):
        self.scan_refs = set()
        scan_refs = self.scan_refs

        class ScanRefs(AbstractCollector):
            def process_scan(self, elem, env, ns):
                for x in elem.iterfind('./s:referenceableParamGroupRef', ns):
                    scan_refs.add(x.attrib['ref'])

        self.meta_collectors.append(ScanRefs())
        super(imzMLmeta, self)._collect_scan_info()

    def scan_meta(self):
        """Extract scan dependant metadata
        """

        terms = collections.OrderedDict()

        terms['scan_meta'] = {
            'MS:1000511': {'attribute': False, 'name':'MS Level', 'plus1': False, 'value':True, 'soft': False},
            'MS:1000465': {'attribute': False, 'name':'Scan polarity', 'plus1': False, 'value':False, 'soft': False},
            'MS:1000525': {'attribute': False, 'name':'Spectrum representation', 'plus1': False, 'value': False, 'soft': False},
        }

        if len(self.scan_refs) != 1:
            warnings.warn("File contains scans using different parameter values, parsed metadata may be wrong.")

        for ref in self.scan_refs:
            param_group = next(x for x in pyxpath(self, XPATHS_I['ref_param_list']) if x.attrib['id'] == ref)

            self.cvParam_loop(param_group.iterfind('s:cvParam', self.ns),
                              'scan_meta', terms)

if __name__ == '__main__':

    if sys.argv[-1].endswith('.imzML'):
        print(imzMLmeta(sys.argv[-1]).meta_json)
    else:
        print(mzMLmeta(sys.argv[-1]).meta_json)
