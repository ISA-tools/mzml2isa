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
import warnings

from mzml2isa.obo import oboparse, oboTranslator
from mzml2isa.versionutils import *



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
               'ic_soft_ref':       '{root}/{instrument}List/{instrument}/{software}[@{softwareRef}]',
               'software_elements': '{root}/s:softwareList/s:software',
               'sp_cv':             '{root}/s:run/{spectrum}List/{spectrum}/s:cvParam',
               'scan_window_cv':    '{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/{scanWindow}List/{scanWindow}/s:cvParam',
               'scan_cv':           '{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/s:cvParam',
               'scan_num':          '{root}/s:run/{spectrum}List[@count]',
               'cv':                '{root}/s:cvList/s:cv[@{cvLabel}]',
               'raw_file':          '{root}/s:fileDescription/s:sourceFileList/s:sourceFile[@{filename}]',
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

    def __init__(self, in_file):
        """ **Constructor**: Setup the xpaths and terms. Then run the various extraction methods

        :param str in_file: path to mzML file
        :ivar obj self.tree: The xml tree object
        :ivar dict self.ns: Dictionary of the namespace of the mzML file
        :ivar obj self.obo: Parsing object used to get children and parents of the ontological terms
        :ivar obj self.meta: Meta information in python dictionary
        :ivar obj self.meta_json: Meta information in json format
        :ivar obj self.meta_isa: Meta information with names compatible with ISA-Tab
        """            

        # setup lxml parsing
        self.in_file = in_file
        self.tree = etree.parse(in_file)

        self.build_env()
      


        # Get controlled vocb from the obo ontology file
        dirname = os.path.dirname(os.path.realpath(__file__))
        obo_path = os.path.join(dirname, "psi-ms.obo")
        self.obo = oboparse(obo_path)

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
                'MS:1000525': {'attribute': False, 'name': 'Spectrum representation', 'plus1': False, 'value':False, 'soft': False}
        }

        terms['source_file'] = {
            'MS:1000767': {'attribute': False, 'name':'Native spectrum identifier format', 'plus1': False, 'value':False, 'soft': False},
        #!# 'MS:1000561': {'attribute': False, 'name':'data file checksum type', 'plus1': True, 'value':True, 'soft': False},
            'MS:1000560': {'attribute': False, 'name':'Raw data file format', 'plus1': False, 'value':False, 'soft': False},
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
                'MS:1000027': {'attribute': False, 'name':'Detector mode', 'plus1': True, 'value':False, 'soft': False}
        }

        terms['data_processing'] = {
                'MS:1000630': {'attribute': True, 'name':'data_processing_parameter', 'plus1': True, 'value': True, 'soft': True},
                'MS:1000452': {'attribute': False, 'name':'data transformation', 'plus1': True, 'value': False, 'soft': True},
        }

        # update self.meta with the relevant meta infromation
        self.extract_meta(terms, xpaths_meta)

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
        self.derived()

        #
        self.urlize()

        # Get the isa_tab compatible meta dictionary
        self.isa_tab_compatible()

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
        descendents = {k:self.obo.getDescendents(k) for k in terms[location_name]}

        #print descendents
        c = 1

        # go through every cvParam element
        for e in elements:
            # go through the terms available for this location
            for accession, info in iterdict(terms[location_name]):

                # check if the element is one of the terms we are looking for
                if e.attrib['accession'] in descendents[accession]:
                    
                    meta_name = info['name']
                    
                    # Check if there can be more than one of the same term
                    if(info['plus1']):
                        # Setup the dictionary for multiple entries
                        try:
                            self.meta[meta_name]['entry_list'][c] = {'accession':e.attrib['accession'], 'name':e.attrib['name']}
                        except KeyError:
                            self.meta[meta_name] = {'entry_list':{c:{'accession':e.attrib['accession'], 'name':e.attrib['name']}}}
                        # Check if a value is associated with this CV
                        if (info['value']):
                            self.meta[meta_name]['entry_list'][c]['value'] = e.attrib['value']
                        c += 1
                    else:

                        if 'name' in info.keys():
                            # Standard CV with only with entry
                            self.meta[meta_name] = {'accession':e.attrib['accession'], 'name':e.attrib['name']}
                            # Check if value associated
                            if (info['value']):
                                self.meta[meta_name]['value'] = e.attrib['value']
                                # remove name and accession if only the value is interesting
                                if self.meta[meta_name]['name'] == meta_name:
                                    del self.meta[meta_name]['name']
                                    del self.meta[meta_name]['accession']

                    # Check if there is expected associated software
                    if (info['soft']):
                        
                        try: # softwareRef in <Processing Method>
                            soft_ref = getparent(e, self.tree).attrib['softwareRef']
                        except KeyError: # softwareRef in <DataProcessing>
                            soft_ref = getparent(getparent(e, self.tree), self.tree).attrib['softwareRef']

                        self.software(soft_ref, meta_name)

    def _instrument_byref(self):
        """ The instrument meta information is more complicated to extract so it has its own function

        Updates the self.meta with the relevant meta information.

        Requires looking at the hierarchy of ontological terms to get all the instrument information
        """
        # To convert accession number to name
        translator = oboTranslator()

        # gets the first Instrument config (something to watch out for)
        ic_ref = pyxpath(self, XPATHS['ic_ref'])[0].attrib["ref"]

        elements = pyxpath(self, XPATHS['ic_elements'])
        
        # Loop through xml elements
        for e in elements:
            # get all CV information from the instrument config
            if e.attrib['id']==ic_ref:
                instrument_e = e.findall('s:cvParam', self.ns)

                for ie in instrument_e:

                    # Get the instrument manufacturer
                    if ie.attrib['accession'] in self.obo.getDescendents('MS:1000031'):
                        self.meta['Instrument'] = {'accession': ie.attrib['accession'], 'name':ie.attrib['name']}

                        # get manufacturer (actually just derived from instrument model). Want to get the top level
                        # so have to go up (should only be a maximum of 3 steps above in the heirachy but do up 10 to be
                        # sure.
                        # directly related children of the instrument model
                        direct_c = self.obo.terms['MS:1000031']['c']

                        parent = self.obo.terms[ie.attrib['accession']]['p']

                        for i in range(10):
                            # first get direct parent of the current instrument element
                            if parent[0] in direct_c:
                                self.meta['Instrument manufacturer'] = {'accession': parent[0], 'name':translator[parent[0]]}
                                break
                            else:
                                parent = self.obo.terms[parent[0]]['p']

                    # get serial number
                    elif ie.attrib['accession'] == 'MS:1000529':
                        self.meta['Instrument serial number'] = {'value': ie.attrib['value']}

        
        soft_ref = pyxpath(self, XPATHS['ic_soft_ref'])[0].attrib[self.env['softwareRef']]
        
        # Get associated software
        self.software(soft_ref, 'Instrument')

    def _instrument_nested(self):
        """
        The easy case, where version number is not in ./referenceableParamList but directly
        in instrument/cvParam
        """

        translator = oboTranslator()

        elements = pyxpath(self, XPATHS['ic_nest'])

        for i, e in enumerate(elements):
            
            if e.attrib['accession'] == 'MS:1000031':
                break

            elif e.attrib['accession'] in self.obo.getDescendents('MS:1000031'):
                self.meta['Instrument'] = {'accession': e.attrib['accession'], 'name':e.attrib['name']}

                parent = self.obo.terms[e.attrib['accession']]['p']

                if parent[0] == 'MS:1000031': #case accession is just manufacturer
                    self.meta['Instrument manufacturer'] = {'accession': e.attrib['accession'], 'name':translator[e.attrib['accession']]}

                else: #case accession is instrument model
                    direct_c = self.obo.terms['MS:1000031']['c']

                    for i in range(10):
                        # first get direct parent of the current instrument element
                        if parent[0] in direct_c:
                            self.meta['Instrument manufacturer'] = {'accession': parent[0], 'name':translator[parent[0]]}
                            break
                        else:
                            #print(self.obo.terms)
                            parent = self.obo.terms[parent[0]]['p']

            elif e.attrib['accession'] == 'MS:1000529':
                self.meta['Instrument serial number'] = {'value': e.attrib['value']}


        try: 
            soft_ref = pyxpath(self, XPATHS['ic_soft_ref'])[0].attrib[self.env['softwareRef']]
            # Get associated software
            self.software(soft_ref, 'Instrument')
        except (IndexError, KeyError): #Sometimes <Instrument> contains no Software tag
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


        for e in elements:

            if e.attrib['id'] == soft_ref:

                try: # <Softwarelist <Software <cvParam>>>
                   
                    #!# if e.attrib['version']:
                    #!#     self.meta[name+' software version'] = {'value': e.attrib['version']}
                    software_cvParam = e.findall('s:cvParam', namespaces=self.ns)
                    for ie in software_cvParam:
                        self.meta[name+' software'] = {'accession':ie.attrib['accession'], 'name':ie.attrib['name']}
                
                except KeyError:  # <SoftwareList <software <softwareParam>>>

                    params = e.find('s:softwareParam', namespaces=self.ns)
                    #!# if params.attrib['version']:
                    #!#     self.meta[name+' software version'] = {'value': params.attrib['version']}
                    self.meta[name+' software'] = {'accession':params.attrib['accession'], 'name':params.attrib['name']}


    def derived(self):
        """ Get the derived meta information. Updates the self.meta dictionary"""

        cv = pyxpath(self, XPATHS['cv'])[0].attrib[self.env["cvLabel"]]            

        if not 'MS' in cv:
            warnings.warn("Standard controlled vocab not available. Can not parse.", UserWarning)
            #print("Standard controlled vocab not available. Can not parse ")
            return
        else:
            self.meta['term_source'] = {'value': 'MS'}


        try:
            raw_file = pyxpath(self, XPATHS['raw_file'])[0].attrib[self.env["filename"]]
            self.meta['Raw Spectral Data File'] = {'value': os.path.basename(raw_file)}
        except IndexError:
            warnings.warn("Could not find any metadata about Raw Spectral Data File", UserWarning)

        in_dir = os.path.dirname(self.in_file)

        
        self.meta['MS Assay Name'] = {'value': os.path.splitext(os.path.basename(self.in_file))[0]}
        self.meta['Derived Spectral Data File'] = {'value': os.path.basename(self.in_file)} # mzML file name
        self.meta['Sample Name'] = {'value': os.path.splitext(os.path.basename(self.in_file))[0]} # mzML file name

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
            polarity = "positive/negative"
        elif pos:
            polarity = "positive"
        elif neg:
            polarity = "negative"
        else:
            polarity = "Not determined"

        self.meta['Scan polarity'] = {'value': polarity}


    def timerange(self):
        
        try:
            scan_cv =  pyxpath(self, XPATHS['scan_cv'])

            time = [ float(i.attrib['value']) for i in scan_cv if i.attrib['accession'] == 'MS:1000016']

            minrt = str(round(min(time),4))
            maxrt = str(round(max(time),4))
            timerange = minrt + "-" + maxrt
        
        except ValueError:
            # THIS IS NOT SOMETHING TO BE WARNED ABOUT
            # warnings.warn("Could not find any time range.", UserWarning)
            timerange = ''
        
        self.meta['Time range'] = {'value': timerange}


    def mzrange(self):
        try: #case with detection range
            scan_window_cv = pyxpath(self, XPATHS['scan_window_cv'])
            minmz_l = []
            maxmz_l = []

            for i in scan_window_cv:
                if i.attrib['accession'] == 'MS:1000501':
                    minmz_l.append(float(i.attrib['value']))
                if i.attrib['accession'] == 'MS:1000500':
                    maxmz_l.append(float(i.attrib['value']))
            
            minmz = str(int(min(minmz_l)))
            maxmz = str(int(max(maxmz_l)))
            mzrange = minmz + "-" + maxmz
        
        except ValueError: #Case with windowed target
            if not isinstance(self, imzMLmeta): #Warn only if parsing a mzML file
                warnings.warn("Could not find any m/z range.", UserWarning)
            mzrange = ''

        self.meta['Scan m/z range'] = {'value': mzrange}


    def scan_num(self):
        scan_num = pyxpath(self, XPATHS['scan_num'])[0].attrib["count"]
        self.meta['Number of scans'] = {'value': int(scan_num)}



    def isa_tab_compatible(self):
        """ Get the ISA-tab comptibale meta dictionary. Updates self.meta_isa"""
        keep = ["data transformation", "data transformation software version", "data transformation software",
                "term_source", "Raw Spectral Data File", "MS Assay Name", "Derived Spectral Data File", "Sample Name"]

        for meta_name in self.meta:
            if meta_name in keep:
                self.meta_isa[meta_name] = self.meta[meta_name]
            else:
                #print(meta_name)
                self.meta_isa["Parameter Value["+meta_name+"]"] = self.meta[meta_name]


    def urlize(self):
        """Turns YY:XXXXXXX accession number into an url to http://purl.obolibrary.org/obo/MS_XXXXXXX"""
        for meta_name in self.meta:
            if 'accession' in self.meta[meta_name].keys():
                if self.meta[meta_name]['accession'].startswith('MS'):
                    self.meta[meta_name]['accession'] = "http://purl.obolibrary.org/obo/" + self.meta[meta_name]['accession'].replace(':', '_')
            elif 'entry_list' in self.meta[meta_name].keys():
                for index, entry in iterdict(self.meta[meta_name]['entry_list']):
                    if 'accession' in entry.keys():
                        if entry['accession'].startswith('MS'):
                            entry['accession'] = "http://purl.obolibrary.org/obo/" + entry['accession'].replace(':', '_')                
            

    def build_env(self):

        self.env = collections.OrderedDict()

        self.ns = self.tree.getroot().nsmap
        self.ns['s'] = self.ns[None] #{'s': self.tree.getroot().tag[1:].split("}")[0]} # namespace
        del self.ns[None]
        
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
        keep = ["data transformation", "data transformation software version", "data transformation software",
                "term_source", "Raw Spectral Data File", "MS Assay Name", "Derived Spectral Data File", "Sample Name"]

        meta_isa = collections.OrderedDict()

        for meta_name in self.meta:
            if meta_name in keep:
                meta_isa[meta_name] = self.meta[meta_name]
            else:
                #print(meta_name)
                meta_isa["Parameter Value["+meta_name+"]"] = self.meta[meta_name]
        
        return meta_isa
    
    @property
    def meta_isa_json(self):
        return json.dumps(self.meta_isa, indent=4, sort_keys=True)
    


XPATHS_I_META = {'file_content':      '{root}/s:fileDescription/s:fileContent/s:cvParam',                 
                 'scan_settings':     '{root}/s:scanSettingsList/s:scanSettings/s:cvParam',
                }

XPATHS_I =      {'scan_dimensions':   '{root}/s:run/{spectrum}List/{spectrum}/{scanList}/s:scan/s:cvParam',
                }


class imzMLmeta(mzMLmeta):

    def __init__(self, in_file):
        # Extract same informations as mzml file
        super(imzMLmeta, self).__init__(in_file)

        # change the ontology and start extracting imaging specific metadata
        dirname = os.path.dirname(os.path.realpath(__file__))
        obo_path = os.path.join(dirname, "imagingMS.obo")
        self.obo = oboparse(obo_path)

        xpaths_meta = XPATHS_I_META

        terms = collections.OrderedDict()
        terms['file_content'] = {
                'IMS:1000080': {'attribute': False, 'name': 'universally unique identifier', 'plus1': False, 'value': True, 'soft':False},
                'IMS:1000009': {'attribute': False, 'name': 'binary file checksum type', 'plus1': False, 'value':False, 'soft': False},
                'IMS:1000003': {'attribute': False, 'name': 'ibd binary type', 'plus1': True, 'value': True, 'soft':False},
        }

        terms['scan_settings'] = {
                'IMS:1000042': {'attribute': False, 'name': 'max count of pixel x', 'plus1': False, 'value': True, 'soft':False},
                'IMS:1000043': {'attribute': False, 'name': 'max count of pixel y', 'plus1': False, 'value': True, 'soft':False},
                'IMS:1000040': {'attribute': False, 'name': 'linescan sequence', 'plus1': False, 'value': True, 'soft': False},
                'IMS:1000041': {'attribute': False, 'name': 'scan pattern', 'plus1': False, 'value': True, 'soft': False},
                'IMS:1000048': {'attribute': False, 'name': 'scan type', 'plus1': False, 'value': True, 'soft': False},
                'IMS:1000049': {'attribute': False, 'name': 'line scan direction', 'plus1': False, 'value': True, 'soft': False},

        }

        self.extract_meta(terms, xpaths_meta)
        
        self.meta['Raw Spectral Data File'] = {'value': os.path.splitext(os.path.basename(self.in_file))[0] \
                                                            + os.path.extsep + 'ibd'}
        self.meta['Low-res image'] = {'value': os.path.splitext(os.path.basename(self.in_file))[0] \
                                                            + os.path.extsep + 'tif'}


if __name__ == '__main__':
    import sys
    
    if sys.argv[-1].endswith('.imzML'):
        print(imzMLmeta(sys.argv[-1]).meta_json)
    else:
        print(mzMLmeta(sys.argv[-1]).meta_json)
