from lxml import etree
import collections
import json
import textwrap
import argparse
import os

from ISA_tab import ISA_tab
from obo_parse import oboparse
from pymzml_obo_parse import oboTranslator as OT

class mzMLmeta(object):
    """ Class to store and obtain the meta information from the mzML file

    The class uses the xpaths of mzML locations and then extracts meta information at these locations.

    The meta info taken is determined by the ontology terms and a set of rules associated with that term e.g.
    if it can be repeated, if has associated software if it has a value as well as name.

    Creates a dictionary of meta information and a JSON structure e.g:

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
        :param object app: QtGui.QApplication
        :ivar obj self.tree: The xml tree object
        :ivar dict self.ns: Dictionary of the namespace of the mzML file
        :ivar obj self.obo: Parsing object used to get children and parents of the ontological terms
        """
        self.tree = etree.parse(in_file)
        self.ns = {'s':'http://psi.hupo.org/ms/mzml'}
        dirname = os.path.dirname(os.path.realpath(__file__))
        obo_path = os.path.join(dirname, "psi-ms.obo")
        self.obo = oboparse(obo_path)

        #initalize the meta info
        self.meta = collections.OrderedDict()
        terms = collections.OrderedDict()

        # xpaths for the mzML locations that we want the meta information from any cvParam elements
        xpaths = {'file_content': '//s:indexedmzML/s:mzML/s:fileDescription/s:fileContent/s:cvParam',
                  'source_file': '//s:indexedmzML/s:mzML/s:fileDescription/s:sourceFileList/s:sourceFile/s:cvParam',
                  'ionization': '//s:indexedmzML/s:mzML/s:instrumentConfigurationList/s:instrumentConfiguration/s:componentList/s:source/s:cvParam',
                  'analyzer': '//s:indexedmzML/s:mzML/s:instrumentConfigurationList/s:instrumentConfiguration/s:componentList/s:analyzer/s:cvParam',
                  'detector': '//s:indexedmzML/s:mzML/s:instrumentConfigurationList/s:instrumentConfiguration/s:componentList/s:detector/s:cvParam',
                  'data_processing': '//s:indexedmzML/s:mzML/s:dataProcessingList/s:dataProcessing/s:processingMethod/s:cvParam'
                  }

        # The controlled vocab (cv) types we want from each of the above xpaths
        terms['file_content'] = {
                'MS:1000524': {'attribute': False, 'name': 'Parameter Value[Data file content]', 'plus1': True, 'value':False, 'soft': False},
                'MS:1000525': {'attribute': False, 'name': 'Parameter Value[Spectrum representation]', 'plus1': False, 'value':False, 'soft': False}
        }

        terms['source_file'] = {
            'MS:1000767': {'attribute': False, 'name':'Parameter Value[Native spectrum identifier format]', 'plus1': False, 'value':False, 'soft': False},
            'MS:1000561': {'attribute': False, 'name':'Parameter Value[Raw data file checksum type]', 'plus1': True, 'value':True, 'soft': False},
            'MS:1000560': {'attribute': False, 'name':'Parameter Value[Raw data file format]', 'plus1': False, 'value':False, 'soft': False}
        }

        terms['ionization'] = {
                'MS:1000482': {'attribute': True, 'name':'source_attribute', 'plus1': True, 'value':True, 'soft': False},
                'MS:1000008': {'attribute': False, 'name':'Parameter Value[Ion source]', 'plus1': False, 'value':False, 'soft': False},
                'MS:1000007': {'attribute': False, 'name':'Parameter Value[Inlet type]', 'plus1': False, 'value':False, 'soft': False}
        }

        terms['analyzer'] = {
                'MS:1000480': {'attribute': True, 'name':'analyzer_attribute', 'plus1': True, 'value':True, 'soft': False},
                'MS:1000443': {'attribute': False, 'name':'Parameter Value[Mass analyzer]', 'plus1': False, 'value':False, 'soft': False}
        }

        terms['detector'] = {
                'MS:1000481': {'attribute': True, 'name':'detector_attribute', 'plus1': True, 'value': True, 'soft': False},
                'MS:1000026': {'attribute': False, 'name':'Parameter Value[Detector]', 'plus1': False, 'value': False, 'soft': False},
                'MS:1000027': {'attribute': False, 'name':'Parameter Value[Detector mode]', 'plus1': True, 'value':False, 'soft': False}
        }

        terms['data_processing'] = {
                'MS:1000630': {'attribute': True, 'name':'data_processing_parameter', 'plus1': True, 'value': True, 'soft': True},
                'MS:1000452': {'attribute': False, 'name':'data_transformation', 'plus1': True, 'value': False, 'soft': True},
        }

        self.extract_meta(terms, xpaths)

        # Have to special stuff to get information regarding instrument and software
        self.instrument()

        # get derived data e.g. file count, polarity
        self.derived()

        self.meta_json = json.dumps(self.meta, indent=2)

        print self.meta_json

    def extract_meta(self, terms, xpaths):
        # get to the right location of the mzML file

        # loop through the different sections of the mzML file as determined by the relevant xpaths
        for location_name, xpath in xpaths.iteritems():

            # get the elements from the xpath
            elements = self.tree.xpath(xpath,namespaces=self.ns)

            self.cvParam_loop(elements, location_name, terms)

            print self.meta

    def cvParam_loop(self, elements, location_name, terms):

        # get associated meta information from each file
        descendents = {k:self.obo.getDescendents(k) for k in terms[location_name]}

        #print descendents
        c = 1

        # go through every cvParam element
        for e in elements:
            # go through the terms available for this location
            for accession, info in terms[location_name].iteritems():

                # check if the element is one of the terms we are looking for
                if e.attrib['accession'] in descendents[accession]:
                    if(info['attribute']):
                        meta_name = e.tag
                    else:
                        meta_name = info['name']

                    if(info['plus1']):

                        try:
                            self.meta[meta_name]['entry_list'][c] = {'accession':e.attrib['accession'], 'name':e.attrib['name']}
                        except KeyError:
                            self.meta[meta_name] = {'entry_list':{c:{'accession':e.attrib['accession'], 'name':e.attrib['name']}}}

                        if (info['value']):
                            self.meta[meta_name]['entry_list'][c]['value'] = e.attrib['value']
                        c += 1
                    else:
                        self.meta[meta_name] = {'accession':e.attrib['accession'], 'name':e.attrib['name']}
                        if (info['value']):
                            self.meta[meta_name]['value'] = e.attrib['value']

                    if (info['soft']):
                        soft_ref = e.getparent().attrib['softwareRef']
                        self.software(soft_ref, meta_name)






    def instrument(self):

        translator = OT()

        # gets the first Instrument config (something to watch out for)
        ic_ref = self.tree.xpath('//s:indexedmzML/s:mzML/s:instrumentConfigurationList/s:instrumentConfiguration/'
                             's:referenceableParamGroupRef/@ref', namespaces=self.ns)[0]

        elements = self.tree.xpath('//s:indexedmzML/s:mzML/s:referenceableParamGroupList/s:referenceableParamGroup',
                                 namespaces=self.ns)
        for e in elements:

            if e.attrib['id']==ic_ref:
                instrument_e = e.findall('s:cvParam', namespaces=self.ns)

                for ie in instrument_e:

                    # Get model
                    if ie.attrib['accession'] in self.obo.getDescendents('MS:1000031'):
                        self.meta['Parameter Value[Instrument]'] = {'accession': ie.attrib['accession'], 'name':ie.attrib['name']}

                        # get manufacturer (actually just derived from instrument model). Want to get the top level
                        # so have to go up (should only be a maximum of 3 steps above in the heirachy but do up 10 to be
                        # sure.
                        # directly related children of the instrument model
                        direct_c = self.obo.terms['MS:1000031']['c']

                        parent = self.obo.terms[ie.attrib['accession']]['p']

                        for i in range(10):
                            # first get direct parent of the current instrument element
                            if parent[0] in direct_c:
                                self.meta['Parameter Value[Instrument manufacturer]'] = {'accession': parent[0], 'name':translator[parent[0]]}
                                break
                            else:
                                parent = self.obo.terms[parent[0]]['p']

                    # get serial number
                    elif ie.attrib['accession'] == 'MS:1000529':
                        self.meta['Parameter Value[Instrument serial number]'] = {'value': ie.attrib['value']}

        soft_ref = self.tree.xpath('//s:indexedmzML/s:mzML/s:instrumentConfigurationList/s:instrumentConfiguration/'
                             's:softwareRef/@ref', namespaces=self.ns)[0]

        self.software(soft_ref, 'Parameter Value[Instrument')
        print self.meta

    def software(self, soft_ref, name):
        elements = self.tree.xpath('//s:indexedmzML/s:mzML/s:softwareList/s:software',
                                 namespaces=self.ns)

        for e in elements:

            if e.attrib['id'] == soft_ref:
                if e.attrib['version']:
                    self.meta[name+' software version]'] = {'value': e.attrib['version']}

                software_cvParam = e.findall('s:cvParam', namespaces=self.ns)

                for ie in software_cvParam:
                    self.meta[name+' software]'] = {'accession':ie.attrib['accession'], 'name':ie.attrib['name']}

        #print self.meta

    def derived(self):
        #######################
        # Get polarity and time
        #######################
        sp_cv = self.tree.xpath('//s:indexedmzML/s:mzML/s:run/s:spectrumList/s:spectrum/s:cvParam',
                                   namespaces=self.ns)
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

        #######################
        # Get mzrange
        #######################
        scan_window_cv = self.tree.xpath('//s:indexedmzML/s:mzML/s:run/s:spectrumList/s:spectrum/s:scanList/s:scan/'
                                 's:scanWindowList/s:scanWindow/s:cvParam',
                                   namespaces=self.ns)
        minmz_l = []
        maxmz_l = []

        for i in scan_window_cv:

            if i.attrib['accession'] == 'MS:1000501':
                minmz_l.append(float(i.attrib['value']))
            if i.attrib['accession'] == 'MS:1000500':
                maxmz_l.append(float(i.attrib['value']))

        minmz = str(int(min(minmz_l)))
        maxmz = str(int(max(maxmz_l)))
        mzrange = minmz + " - " + maxmz

        #######################
        # Get timerange
        #######################
        scan_cv =  self.tree.xpath('//s:indexedmzML/s:mzML/s:run/s:spectrumList/s:spectrum/s:scanList/s:scan/s:cvParam',
                                   namespaces=self.ns)

        time = [ float(i.attrib['value']) for i in scan_cv if i.attrib['accession'] == 'MS:1000016']

        minrt = str(round(min(time),4))
        maxrt = str(round(max(time),4))
        timerange = minrt + " - " + maxrt

        #####################
        # Some other stuff
        ####################
        scan_num = self.tree.xpath('//s:indexedmzML/s:mzML/s:run/s:spectrumList/@count', namespaces=self.ns)[0]

        cv = self.tree.xpath('//s:indexedmzML/s:mzML/s:cvList/s:cv/@id', namespaces=self.ns)[0]

        if not 'MS' in cv:
            print "Standard controlled vocab not available. Can not parse "
            return
        else:
            self.meta['term_source'] = {'value': 'MS'}

        raw_file = self.tree.xpath('//s:indexedmzML/s:mzML/s:fileDescription/s:sourceFileList/'
                             's:sourceFile/@name', namespaces=self.ns)[0]

        self.meta['Parameter Value[Raw data file format]'] = {'value': raw_file}
        self.meta['Parameter Value[Number of scans]'] = {'value': int(scan_num)}
        self.meta['Parameter Value[Scan m/z range]'] = {'value': mzrange}
        self.meta['Parameter Value[Scan polarity]'] = {'value': polarity}
        self.meta['Parameter Value[Time range]'] = {'value': timerange}


# Need to determine if indexedmzML present or not


# Get spectrum information


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='PROG',
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 description='''Extract meta information from mzML as json''',
                                 epilog=textwrap.dedent('''\
                                 -------------------------------------------------------------------------

                                 Example Usage:
                                 python mzML.py -i [infile] -o [out folder]
                                 '''))

    parser.add_argument('-i', dest='in_file', help='mzML file', required=True)
    parser.add_argument('-o', dest='out_dir', help='out directory for json file', required=False)

    args = parser.parse_args()

    mzML = mzMLmeta(args.in_file)

    with open(args.out_file, 'w') as outfile:
        outfile.write(mzML.meta_json)


    #dirname = os.path.dirname(os.path.realpath(__file__))
    #testing_path = os.path.join(dirname, "testing")

    # get a the example dataset
    #in_file = os.path.join(testing_path, 'small.pwiz.1.1.mzML')
    #in_file = '/mnt/hgfs/DATA/MEGA/metabolomics/example_data/C30_LCMS/Daph_C18_Frac1_run3_neg.mzML'

    ####################################
    #  Create ISA-Tab
    ####################################
    # CURRENTLY RESTRUCTURING! Comeback later!
    # Two options:
    #   * use existing ISA tab folder and populate an assay file with the mzML files
    #   * Create a new ISA-Tab folder with investigation/samples/ etc
    # get 2 examples meta file infor just for testing
    # metalist = [ mzMLmeta(in_file).meta for i in range(2)]
    #
    #
    # # update isa-tab file
    # # assay_file = os.path.join(testing_path, 'a_ap_amp1_amd_metabolite_profiling_mass_spectrometry.txt')
    # isa_assay = ISA_tab(metalist)


