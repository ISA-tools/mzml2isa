"""
Content
-----------------------------------------------------------------------------
This module contains a single class, mzMLmeta, which is used to parse and
serialize an mzML file into a Python dictionnary. This class was slightly
modified from the pymzml implementation[1]_.

Following features are implemented but were commented out:
- retrieval of sofware version number
- retrieval of raw-data SHA-1 checksum
Both can be found by looking for the #!# comment tag in the mzml2isa.mzml
module source code.

Reference:
-----------------------------------------------------------------------------
- [1] http://pymzml.github.io

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

import collections
import json
import os
import glob
import warnings
import itertools

from pronto import Ontology
from mzml2isa.versionutils import *


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

    Creates a dictionary of meta information and a JSON structure e.g::
        "mass_analyzer_type": {
            "accession": "MS:1000484",
            "name": "orbitrap"
        },
        "ionization_type": {
            "accession": "MS:1000073",
            "name": "electrospray ionization"
        }
    """

    obo = None
    _descendents = dict()

    def __init__(self, in_file, ontology=None):
        """ **Constructor**: Setup the xpaths and terms. Then run the various extraction methods

        :param str in_file: path to mzML file
        :ivar obj self.tree: The xml tree object
        :ivar dict self.ns: Dictionary of the namespace of the mzML file
        :ivar obj self.obo: Parsing object used to get children and parents of the ontological terms
        :ivar obj self.meta: Meta information in python dictionary
        :ivar obj self.meta_json: Meta information in json format
        :ivar obj self.meta_isa: Meta information with names compatible with ISA-Tab
        """

        if ontology is None and self.obo is None:
            warnings.simplefilter('ignore')
            try:
                self.obo = Ontology('http://www.berkeleybop.org/ontologies/ms.obo', False)
            except:
                self.obo = Ontology(os.path.join(
                                   os.path.dirname(os.path.realpath(__file__)),
                                  "psi-ms.obo"))
        elif self.obo is None:
            self.obo = ontology

        # setup lxml parsing
        self.in_file = in_file
        self.in_dir = os.path.dirname(in_file)
        self.tree = etree.parse(in_file, etree.XMLParser())

        self.build_env()

        self.make_params()

        #initalize the meta variables
        self.meta = collections.OrderedDict()

        # xpaths for the mzML locations that we want the meta information from any cvParam elements
        xpaths_meta = XPATHS_META

        # We create a dictionary that contains "search parameters" that we use to parse the xml location from the xpaths
        # above
        #
        # name: [string], What the CV will be saved as
        # plus1: [Boolean], If there are multiple of this CV
        # value: [Boolean], if there is an associated value with this CV
        # soft: [Boolean], If there is associated software CV associated with this CV
        # attribute: [Boolean], if the CV is an attribute then has to be handled differently
        terms = collections.OrderedDict()
        terms['file_content'] = {
                'MS:1000524': {'attribute': False, 'name': 'Data file content', 'plus1': True, 'value':False, 'soft': False},
                'MS:1000525': {'attribute': False, 'name': 'Spectrum representation', 'plus1': True, 'value':False, 'soft': False}
        }

        terms['source_file'] = {
            'MS:1000767': {'attribute': False, 'name':'Native spectrum identifier format', 'plus1': False, 'value':False, 'soft': False},
            'MS:1000561': {'attribute': False, 'name':'Data file checksum type', 'plus1': False, 'value':True, 'soft': False},
            'MS:1000560': {'attribute': False, 'name':'Raw data file format', 'plus1': False, 'value':False, 'soft': False},
        }

        terms['contact'] = {
            'MS:1000586': {'attribute': False, 'name': 'Contact name', 'plus1':False, 'value':True, 'soft':False},
            'MS:1000587': {'attribute': False, 'name': 'Contact adress', 'plus1':False, 'value':True, 'soft':False},
            'MS:1000588': {'attribute': False, 'name': 'Contact url', 'plus1':False, 'value':True, 'soft':False},
            'MS:1000589': {'attribute': False, 'name': 'Contact email', 'plus1':False, 'value':True, 'soft':False},
            'MS:1000590': {'attribute': False, 'name': 'Contact affiliation', 'plus1':False, 'value':True, 'soft':False},
        }

        terms['ionization'] = {
                'MS:1000482': {'attribute': True, 'name':'source_attribute', 'plus1': True, 'value':True, 'soft': False},
                'MS:1000008': {'attribute': False, 'name':'Ion source', 'plus1': False, 'value':False, 'soft': False},
                'MS:1000007': {'attribute': False, 'name':'Inlet type', 'plus1': False, 'value':False, 'soft': False}
        }

        terms['analyzer'] = {
                'MS:1000480': {'attribute': True, 'name':'analyzer_attribute', 'plus1': True, 'value':True, 'soft': False},
                'MS:1000443': {'attribute': False, 'name':'Mass analyzer', 'plus1': False, 'value':False, 'soft': False},
        }

        terms['detector'] = {
                'MS:1000481': {'attribute': True, 'name':'detector_attribute', 'plus1': True, 'value': True, 'soft': False},
                'MS:1000026': {'attribute': False, 'name':'Detector', 'plus1': False, 'value': False, 'soft': False},
                'MS:1000027': {'attribute': False, 'name':'Detector mode', 'plus1': False, 'value':False, 'soft': False}
        }

        terms['data_processing'] = {
                'MS:1000630': {'attribute': True, 'name':'data_processing_parameter', 'plus1': True, 'value': True, 'soft': True},
                'MS:1000452': {'attribute': False, 'name':'Data Transformation Name', 'plus1': True, 'value': False, 'soft': True},
        }

        # update self.meta with the relevant meta infromation
        self.extract_meta(terms, xpaths_meta)

        # make a memoized dict of the referenceable params
        self.make_params()

        # The instrument information has to be extracted separately
        self.instrument()

        #
        self.polarity()

        #
        self.timerange()

        #
        self.mzrange()

        #
        self.scan_num()

        #
        self.spectrum_meta()

        #
        self.derived()

        #
        self.urlize()

        #self.meta['Data Transformation Name'] = self.meta['Data Transformation']
        #del self.meta['Data Transformation']

    def extract_meta(self, terms, xpaths):
        """ Extract meta information for CV terms based on their location in the xml file

        Updates the self.meta dictionary with the relevant meta information

        :param dict terms: The CV and "search parameters" required at the xml locations
        :param dict xpath: The xpath locations to be searched
        .. seealso::
            :func:`cvParam_loop`
        """

        # loop though the xpaths
        for location_name, xpath in iterdict(xpaths):


            # get the elements from the xpath
            elements = pyxpath(self, xpath)

            # loop through the elements and see if the terms are found
            self.cvParam_loop(elements, location_name, terms)

    def cvParam_loop(self, elements, location_name, terms):
        """ loop through the elements and see if the terms are found. If they are update the self.meta dict

        :param obj elements: lxml object
        :param str location_name: Name of the xml location
        :param dict terms: CV terms we want
        """
        # get associated meta information from each file

        #descendents = {}

        for k in terms[location_name].keys():
            if not k in self._descendents.keys():
                self._descendents[k] = self.obo[k].rchildren().id
        #    descendents[k] = self._obo_memo[k]

        #descendents = {k: self.obo[k].rchildren().id for k in terms[location_name]}

        #c = 0

        #if elements is None:
        #    return

        # go through every cvParam element
        for e in elements:
            # go through the terms available for this location
            for accession, info in iterdict(terms[location_name]):

                # check if the element is one of the terms we are looking for
                if e.attrib['accession'] in self._descendents[accession] or e.attrib['accession']==accession:

                    meta_name = info['name']

                    # Check if there can be more than one of the same term
                    if(info['plus1']):
                        # Setup the dictionary for multiple entries
                        if not meta_name in self.meta.keys():
                            self.meta[meta_name] = {'entry_list': []}

                        self.meta[meta_name]['entry_list'].append( {'accession':e.attrib['accession'], 'name':e.attrib['name'], 'ref':e.attrib['cvRef']} )

                        if 'unitName' in e.attrib:
                            self.meta[meta_name]['entry_list'][-1]['unit'] = {'name': e.attrib['unitName'], 'ref': e.attrib['unitCvRef'],
                                                                                'accession': e.attrib['unitAccession']}

                        # Check if a value is associated with this CV
                        if info['value']:
                            self.meta[meta_name]['entry_list'][-1]['value'] = self._convert(e.attrib['value'])

                        if self.meta[meta_name]['entry_list'][-1]['name'].upper() == meta_name.upper():
                            del self.meta[meta_name]['entry_list'][-1]['name']
                            del self.meta[meta_name]['entry_list'][-1]['accession']
                            del self.meta[meta_name]['entry_list'][-1]['ref']

                        #c += 1
                    else:

                        #if 'name' in info.keys():

                        # Standard CV with only with entry
                        self.meta[meta_name] = {'accession':e.attrib['accession'], 'name':e.attrib['name'], 'ref':e.attrib['cvRef']}


                        if 'unitName' in e.attrib:
                            self.meta[meta_name]['unit'] = {'name': e.attrib['unitName'], 'ref': e.attrib['unitCvRef'],
                                                            'accession': e.attrib['unitAccession']}

                        # Check if value associated
                        if (info['value']):
                            self.meta[meta_name]['value'] = self._convert(e.attrib['value'])
                            # remove name and accession if only the value is interesting

                            if self.meta[meta_name]['name'].upper() == meta_name.upper():
                                del self.meta[meta_name]['name']
                                del self.meta[meta_name]['accession']



                    # Check if there is expected associated software
                    if (info['soft']):

                        try: # softwareRef in <Processing Method>
                            soft_ref = getparent(e, self.tree).attrib['softwareRef']
                        except KeyError: # softwareRef in <DataProcessing>
                            soft_ref = getparent(getparent(e, self.tree), self.tree).attrib['softwareRef']

                        self.software(soft_ref, meta_name)

    @staticmethod
    def _convert(value):
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value

    def _instrument_byref(self):
        """ The instrument meta information is more complicated to extract so it has its own function

        Updates the self.meta with the relevant meta information.

        Requires looking at the hierarchy of ontological terms to get all the instrument information
        """

        # gets the first Instrument config (something to watch out for)
        ic_ref = next(pyxpath(self, XPATHS['ic_ref'])).attrib["ref"]

        elements = pyxpath(self, XPATHS['ic_elements'])

        # Loop through xml elements
        for e in elements:
            # get all CV information from the instrument config
            if e.attrib['id']==ic_ref:
                instrument_e = e.findall('s:cvParam', self.ns)

                for ie in instrument_e:

                    # Get the instrument manufacturer
                    if ie.attrib['accession'] in self.obo['MS:1000031'].rchildren().id:
                        self.meta['Instrument'] = {'accession': ie.attrib['accession'], 'name':ie.attrib['name'],
                                                   'ref':ie.attrib['cvRef']}

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
        """
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
                                                                                if 'Instrument' in self.meta.keys()
                                                                                else "<"+self.meta['Instrument serial number']+">"
                                                                                if 'Instrument serial number' in self.meta.keys()
                                                                                else '?'),
                           UserWarning)

    def software(self, soft_ref, name):
        """ Get associated software of cv term. Updates the self.meta dictionary

        :param str soft_ref: Reference to software found in xml file
        :param str name: Name of the associated CV term that the software is associated to
        """

        elements = pyxpath(self, XPATHS['software_elements'])

        if name.endswith('Name'):               # We don't want Data Transformation Name Software !
            name = name.replace(' Name', '')

        for e in elements:

            if e.attrib['id'] == soft_ref:

                try: # <Softwarelist <Software <cvParam>>>

                    if e.attrib['version']:
                        self.meta[name+' software version'] = {'value': e.attrib['version']}
                    software_cvParam = e.findall('s:cvParam', namespaces=self.ns)
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
        """ Get the derived meta information. Updates the self.meta dictionary"""

        cv = next(pyxpath(self, XPATHS['cv'])).attrib[self.env["cvLabel"]]

        if not 'MS' in cv:
            warnings.warn("Standard controlled vocab not available. Can not parse.", UserWarning)
            return
        #else:
        #    self.meta['term_source'] = {'value': 'MS'}


        try:
            raw_file = next(pyxpath(self, XPATHS['raw_file'])).attrib[self.env["filename"]]
            self.meta['Raw Spectral Data File'] = {'entry_list': [{'value': os.path.basename(raw_file)}] }
        except StopIteration:
            warnings.warn("Could not find any metadata about Raw Spectral Data File", UserWarning)


        self.meta['MS Assay Name'] = {'value': os.path.splitext(os.path.basename(self.in_file))[0]}
        self.meta['Derived Spectral Data File'] = {'entry_list': [{'value': os.path.basename(self.in_file)}] } # mzML file name
        self.meta['Sample Name'] = {'value': os.path.splitext(os.path.basename(self.in_file))[0]} # mzML file name w/o extension

    def polarity(self):

        sp_cv = pyxpath(self, XPATHS['sp_cv'])

        pos = False
        neg = False

        for i in sp_cv:
            if i.attrib['accession'] == 'MS:1000130':
                pos = True
            if i.attrib['accession'] == 'MS:1000129':
                neg = True

        if pos & neg:
            polarity = {'name': "alternating scan", 'ref':'', 'accession':''}
        elif pos:
            polarity = {'name':"positive scan", 'ref':'MS', 'accession':'MS:1000130'}
        elif neg:
            polarity = {'name':"negative scan", 'ref':'MS', 'accession':'MS:1000129'}
        else:
            polarity = {'name': "n/a", 'ref':'', 'accession':''}

        self.meta['Scan polarity'] = polarity

    def make_params(self):
        self._params = {x.attrib['id']:x for x in pyxpath(self, '{root}/s:referenceableParamGroupList/s:referenceableParamGroup')}


    def spectrum_meta(self):
        """Extract information of each spectrum in entry lists."""

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

        for spectrum in pyxpath(self, XPATHS['sp']):

            for path,name in [('./s:referenceableParamGroupRef', 'sp'),
                              ('{scanList}/s:scan/s:referenceableParamGroupRef', 'combination'),
                              ('{root}/s:referenceableParamGroupList/s:referenceableParamGroup', 'binary')]:

                refs = spectrum.iterfind(path.format(**self.env), self.ns)
                for ref in refs:
                    params = self._params[ref.attrib['ref']]
                    self.cvParam_loop(params.iterfind('s:cvParam', self.ns), name, terms)



            self.cvParam_loop(spectrum.iterfind('s:cvParam', self.ns), 'sp', terms)
            self.cvParam_loop(spectrum.iterfind('{scanList}/s:cvParam'.format(**self.env), self.ns), 'combination', terms)
            self.cvParam_loop(spectrum.iterfind('{scanList}/s:scan/s:cvParam'.format(**self.env), self.ns), 'configuration', terms)
            self.cvParam_loop(spectrum.iterfind('s:binaryDataArrayList/s:binaryDataArray/s:cvParam'.format(**self.env), self.ns), 'binary', terms)

            self.cvParam_loop(spectrum.iterfind('s:precursorList/s:precursor/s:activation/s:cvParam', self.ns), 'activation', terms)
            self.cvParam_loop(spectrum.iterfind('s:precursorList/s:precursor/s:isolationWindow/s:cvParam', self.ns), 'isolation_window', terms)
            self.cvParam_loop(spectrum.iterfind('s:precursorList/s:precursor/s:selectedIonList/s:selectedIon/s:cvParam', self.ns), 'selected_ion', terms)

        for entry in ('Collision Energy', 'Data file content', 'Dissociation method', 'Spectrum combination',
                      'Binary data array', 'Binary data compression type', 'Binary data type'):
            self.merge_entries(entry)

    def merge_entries(self, name):

        if name in self.meta.keys():
            if 'entry_list' in self.meta[name].keys():
                seen = set()
                return [x for x in self.meta[name]['entry_list'] if str(x) not in seen and not seen.add(str(x))]


                #return [next(g) for k,g in itertools.groupby(self.meta[name]['entry_list'], lambda x: x['name'])]

                #self.meta[name]['entry_list'] = [i for n, i in enumerate(self.meta[name]['entry_list'])
                #                                   if i not in self.meta[name]['entry_list'][n + 1:]]


    def timerange(self):

        try:
            scan_cv =  pyxpath(self, XPATHS['scan_cv'])

            time = [ float(i.attrib['value']) for i in scan_cv if i.attrib['accession'] == 'MS:1000016']
            unit = next( ( {'name': i.attrib['unitName'],'accession': i.attrib['unitAccession'],'ref': i.attrib['unitCvRef'] }
                            for i in scan_cv if i.attrib['accession'] == 'MS:1000016' and 'unitName' in i.attrib.keys() ), None)

            minrt = str(round(min(time),4))
            maxrt = str(round(max(time),4))
            timerange = minrt + "-" + maxrt

        except ValueError:
            # THIS IS NOT SOMETHING TO BE WARNED ABOUT
            # warnings.warn("Could not find any time range.", UserWarning)
            timerange = ''

        if timerange:
            self.meta['Time range'] = {'value': timerange}
            if unit is not None:
                self.meta['Time range']['unit'] = unit

    def mzrange(self):
        try: #case with detection range
            scan_window_cv = pyxpath(self, XPATHS['scan_window_cv'])
            minmz_l = []
            maxmz_l = []

            unit = None

            for i in scan_window_cv:
                if i.attrib['accession'] == 'MS:1000501':
                    minmz_l.append(float(i.attrib['value']))

                    unit = unit or {'name': i.attrib['unitName'],
                                    'ref': i.attrib['unitCvRef'],
                                    'accession': i.attrib['unitAccession']}

                if i.attrib['accession'] == 'MS:1000500':
                    maxmz_l.append(float(i.attrib['value']))

            minmz = str(int(min(minmz_l)))
            maxmz = str(int(max(maxmz_l)))
            mzrange = minmz + "-" + maxmz

        except ValueError: #Case with windowed target
            if not isinstance(self, imzMLmeta): #Warn only if parsing a mzML file
                warnings.warn("Could not find any m/z range.", UserWarning)
            mzrange = ''

        if mzrange:
            self.meta['Scan m/z range'] = {'value': mzrange}
            if unit is not None:
                self.meta['Scan m/z range']['unit'] = unit

    def scan_num(self):
        scan_num = next(pyxpath(self, XPATHS['scan_num'])).attrib["count"]
        self.meta['Number of scans'] = {'value': int(scan_num)}

    def urlize(self):
        """Turns YY:XXXXXXX accession number into an url"""
        for meta_name in self.meta:
            if 'accession' in self.meta[meta_name].keys():
                self.meta[meta_name]['accession'] = self._urlize_name(self.meta[meta_name]['accession'])
            if 'unit' in self.meta[meta_name].keys():
                self.meta[meta_name]['unit']['accession'] = self._urlize_name(self.meta[meta_name]['unit']['accession'])
            elif 'entry_list' in self.meta[meta_name].keys():
                for index, entry in enumerate(self.meta[meta_name]['entry_list']):
                    if 'accession' in entry.keys():
                        self.meta[meta_name]['entry_list'][index]['accession'] = self._urlize_name(entry['accession'])
                    if 'unit' in entry.keys():
                        self.meta[meta_name]['entry_list'][index]['unit']['accession'] = self._urlize_name(entry['unit']['accession'])

    @staticmethod
    def _urlize_name(name):
        if name.startswith('MS'):
            return "http://purl.obolibrary.org/obo/{}".format(name.replace(':', '_'))
        elif name.startswith('IMS'):
            return "http://www.maldi-msi.org/download/imzml/imagingMS.obo#{}".format(name)
        elif name.startswith('UO'):
            return "http://purl.obolibrary.org/obo/{}".format(name.replace(':', '_'))
        return name

    def build_env(self):

        self.env = collections.OrderedDict()

        try: #lxml
            self.ns = self.tree.getroot().nsmap
            self.ns['s'] = self.ns[None] # namespace
            del self.ns[None]
        except AttributeError: #xml.(c)ElementTree
            self.ns = {'s': self.tree.getroot().tag[1:].split("}")[0]}

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
        return json.dumps(self.meta, indent=4, sort_keys=True)

    @property
    def meta_isa(self):
        keep = ["Data Transformation", "Data Transformation software version", "Data Transformation software",
                "term_source", "Raw Spectral Data File", "MS Assay Name", "Derived Spectral Data File", "Sample Name"]

        meta_isa = collections.OrderedDict()

        for meta_name in self.meta:
            if meta_name in keep:
                meta_isa[meta_name] = self.meta[meta_name]
            else:
                meta_isa["Parameter Value["+meta_name+"]"] = self.meta[meta_name]

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
                 'ref_param_list':    '{root}/s:referenceableParamGroupList/s:referenceableParamGroup'
                }


class imzMLmeta(mzMLmeta):

    def __init__(self, in_file, ontology=None):
        # Extract same informations as mzml file

        if ontology is None:
            warnings.simplefilter('ignore')
            dirname = os.path.dirname(os.path.realpath(__file__))
            obo_path = os.path.join(dirname, "imagingMS.obo")
            self.obo = Ontology(obo_path, True, import_depth=1)
        else:
            self.obo = ontology

        super(imzMLmeta, self).__init__(in_file, self.obo)


        xpaths_meta = XPATHS_I_META

        terms = collections.OrderedDict()
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

        self.link_files()

        self.scan_meta()

        self.urlize()

    def link_files(self):
        self.meta['Raw Spectral Data File'] =  {'entry_list': [{'value': os.path.splitext(os.path.basename(self.in_file))[0] \
                                                                         + os.path.extsep + 'ibd'}] }

        self.meta['Spectrum representation'] = {'entry_list': [ self.meta['Spectrum representation'] ] }

        #if group_spectra:
        #    self.meta['MS Assay Name']['value'] = self.meta['MS Assay Name']['value']

        self.meta['High-res image'] = {'value': self.find_img('ndpi') }
        self.meta['Low-res image'] =  {'value': self.find_img('jpg', 'tif') }

    def find_img(self, *img_formats):

        identity = dict()

        for img_format in img_formats:

            name = self.meta['Sample Name']['value']

            for file in glob.glob(os.path.join(self.in_dir, '*.{}'.format(img_format))):

                filename = os.path.splitext(os.path.basename(file))[0]
                identity[os.path.basename(file)] = len(longest_substring(filename, name)) / len(name)

        if identity and max(identity.values()) > IDENTITY_THRESHOLD:
            return max(identity, key=identity.get)
        else:
            return ''

    def scan_meta(self):
        """Extract scan dependant metadata"""

        scan_refs = { x.attrib['ref'] for x in pyxpath(self, XPATHS_I['scan_ref']) }

        terms = collections.OrderedDict()

        terms['scan_meta'] = {
            'MS:1000511': {'attribute': False, 'name':'MS Level', 'plus1': False, 'value':True, 'soft': False},
            'MS:1000465': {'attribute': False, 'name':'Scan polarity', 'plus1': False, 'value':False, 'soft': False},
        }

        if len(scan_refs) != 1:
            warnings.warn("File contains scans using different parameter values, parsed metadata may be wrong.", UserWarning)

        for ref in scan_refs:

            param_group = next( x for x in pyxpath(self, XPATHS_I['ref_param_list']) if x.attrib['id'] == ref)

            self.cvParam_loop(param_group.iterfind('s:cvParam', self.ns),
                              'scan_meta', terms)




if __name__ == '__main__':
    import sys


    if sys.argv[-1].endswith('.imzML'):
        print(imzMLmeta(sys.argv[-1]).meta_json)
    else:
        print(mzMLmeta(sys.argv[-1]).meta_json)
