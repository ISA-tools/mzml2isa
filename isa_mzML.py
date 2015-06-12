from lxml import etree
import collections
import json
import csv
from obo_parse import oboparse
from pymzml_obo_parse import oboTranslator as OT

class mzMLmeta(object):
    def __init__(self, in_file):
        '''
        todo
        '''

        self.tree = etree.parse(in_file)
        self.ns = {'s':'http://psi.hupo.org/ms/mzml'}
        self.obo = oboparse('/home/tomnl/MEGA/metabolomics/isatab/psi-ms.obo')

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
                'MS:1000524': {'attribute': False, 'name': 'data_file_content', 'plus1': True, 'value':False, 'soft': False},
                'MS:1000525': {'attribute': False, 'name': 'spectrum_representation', 'plus1': False, 'value':False, 'soft': False}
        }

        terms['source_file'] = {
            'MS:1000767': {'attribute': False, 'name':'raw_spectrum_identifier_format', 'plus1': False, 'value':False, 'soft': False},
            'MS:1000561': {'attribute': False, 'name':'raw_data_file_checksum_type', 'plus1': True, 'value':True, 'soft': False},
            'MS:1000560': {'attribute': False, 'name':'raw_file_format', 'plus1': False, 'value':False, 'soft': False}
        }

        terms['ionization'] = {
                'MS:1000482': {'attribute': True, 'name':'source_attribute', 'plus1': True, 'value':True, 'soft': False},
                'MS:1000008': {'attribute': False, 'name':'ionization_type', 'plus1': False, 'value':False, 'soft': False},
                'MS:1000007': {'attribute': False, 'name':'inlet_type', 'plus1': False, 'value':False, 'soft': False}
        }

        terms['analyzer'] = {
                'MS:1000480': {'attribute': True, 'name':'analyzer_attribute', 'plus1': True, 'value':True, 'soft': False},
                'MS:1000443': {'attribute': False, 'name':'mass_analyzer_type', 'plus1': False, 'value':False, 'soft': False}
        }

        terms['detector'] = {
                'MS:1000481': {'attribute': True, 'name':'detector_attribute', 'plus1': True, 'value': True, 'soft': False},
                'MS:1000026': {'attribute': False, 'name':'detector_type', 'plus1': False, 'value': False, 'soft': False},
                'MS:1000027': {'attribute': False, 'name':'detector_acquisition_mode', 'plus1': True, 'value':False, 'soft': False}
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
                    if(info['attribute'] & info['plus1']):
                        meta_name = e.tag+str(c)
                        c += 1
                    elif(info['attribute']):
                        meta_name = e.tag
                    elif info['plus1']:
                        meta_name = info['name']+str(c)
                        c += 1
                    else:
                        meta_name = info['name']

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
                        self.meta['instrument_model'] = {'accession': ie.attrib['accession'], 'name':ie.attrib['name']}

                        # get manufacturer (actually just derived from instrument model). Want to get the top level
                        # so have to go up (should only be a maximum of 3 steps above in the heirachy but do up 10 to be
                        # sure.
                        # directly related children of the instrument model
                        direct_c = self.obo.terms['MS:1000031']['c']

                        parent = self.obo.terms[ie.attrib['accession']]['p']

                        for i in range(10):
                            # first get direct parent of the current instrument element
                            if parent[0] in direct_c:
                                self.meta['instrument_manufacturer'] = {'accession': parent[0], 'name':translator[parent[0]]}
                                break
                            else:
                                parent = self.obo.terms[parent[0]]['p']

                    # get serial number
                    elif ie.attrib['accession'] == 'MS:1000529':
                        self.meta['instrument_serial_number'] = {'value': ie.attrib['value']}


        soft_ref = self.tree.xpath('//s:indexedmzML/s:mzML/s:instrumentConfigurationList/s:instrumentConfiguration/'
                             's:softwareRef/@ref', namespaces=self.ns)[0]

        self.software(soft_ref, 'instrument')
        print self.meta

    def software(self, soft_ref, name):
        elements = self.tree.xpath('//s:indexedmzML/s:mzML/s:softwareList/s:software',
                                 namespaces=self.ns)

        for e in elements:

            if e.attrib['id'] == soft_ref:
                if e.attrib['version']:
                    self.meta[name+'_software_version'] = {'value': e.attrib['version']}

                software_cvParam = e.findall('s:cvParam', namespaces=self.ns)

                for ie in software_cvParam:
                    self.meta[name+'_software'] = {'accession':ie.attrib['accession'], 'name':ie.attrib['name']}

        #print self.meta

    def derived(self):
        # hard coded for now
        self.meta['mzrange'] = {'value': '100 - 1000'}
        self.meta['polarity'] = {'value': 'Positive'}
        self.meta['scan_number'] = {'value': '1000'}
        self.meta['scan_start'] = {'value': '0.05'}
        self.meta['scan_finish'] = {'value': '1500'}
        self.meta['term_source'] = {'value': 'MS'}
        self.meta['raw_data_file'] = {'value': 'test.raw'}





class isa_assay_file(object):
    def __init__(self, isa_tab_assay_file, metalist):
        ######################
        # get index info
        ######################
        with open(isa_tab_assay_file, 'rb') as isa_orig:

            for index, line in enumerate(isa_orig):
                line = line.replace('"', '')
                if index == 0:

                    headers_l = line.split('\t')


                elif index == 1:
                    standard_row = line.split('\t')
                    mass_protocol_idx = standard_row.index('Mass spectrometry')
                    adj = mass_protocol_idx+1

                    head_short = headers_l[mass_protocol_idx+1:]

                    try:
                        polarity_idx = head_short.index('Parameter Value[Scan polarity]')+adj
                        mzrange_idx = head_short.index('Parameter Value[Scan m/z range]')+adj
                        instrument_idx = head_short.index('Parameter Value[Instrument]')+adj
                        ionsource_idx = head_short.index('Parameter Value[Ion source]')+adj
                        detector_idx = head_short.index('Parameter Value[Mass analyzer]')+adj
                        raw_data_idx = head_short.index('Raw Spectral Data File')+adj
                    except ValueError as e:
                        print e

        ######################
        # update the file
        ######################
        with open("isa_new.txt", 'wb') as new_file:
            writer = csv.writer(new_file)
            writer.writerow(headers_l)

            for file in metalist:
                current_row = standard_row
                current_row[polarity_idx] = file['polarity']['value']
                current_row[mzrange_idx] = file['mzrange']['value']
                current_row[instrument_idx] = file['instrument_manufacturer']['name']
                current_row[instrument_idx+1] = file['term_source']['value']
                current_row[instrument_idx+2] = file['instrument_manufacturer']['accession']

                current_row[ionsource_idx] = file['ionization_type']['name']
                current_row[ionsource_idx+1] = file['term_source']['value']
                current_row[ionsource_idx+2] = file['ionization_type']['accession']

                current_row[detector_idx] = file['detector_type']['name']
                current_row[detector_idx+1] = file['term_source']['value']
                current_row[detector_idx+2] = file['detector_type']['accession']

                current_row[raw_data_idx] = file['raw_data_file']['value']

                writer.writerow(current_row)











# Need to determine if indexedmzML present or not


# Get spectrum information


if __name__ == "__main__":

    # get a fake dataset of multiple files
    in_file = '/home/tomnl/MEGA/metabolomics/inclusion_list_test_21april/InclusionLCMSMS/mzML/inc1/SerumSample_pos_split1_Incl1_150422000904.mzML'
    assay_file = '/home/tomnl/soft/ISAcreatorMetaboLights/isatab files/dma_test2/a_ap_amp1_amd_metabolite_profiling_mass_spectrometry.txt'

    #in_file = '/home/tomnl/MEGA/metabolomics/isatab/small.pwiz.1.1.mzML'

    # get 10 examples just for testing
    metalist = [ mzMLmeta(in_file).meta for i in range(10)]


    isa_assay = isa_assay_file(assay_file, metalist)


