#!/usr/bin/env python
#  -*- coding: utf-8 -*-
import unittest
import os
import re
import mzml2isa
from fs import open_fs
from fs.tarfs import TarFS
from fs.copy import copy_fs
from fs.tempfs import TempFS
import json
import six
import sys
from isatools import isatab
import subprocess

def get_json_meta_results():
    example_files_dir = os.path.join(os.path.abspath(os.path.join(__file__, os.pardir, os.pardir)), 'example_files')
    json_meta_pth = os.path.join(example_files_dir, 'MTBLS-json-meta')
    json_meta_fs = open_fs(json_meta_pth)

    json_results = {}

    for path in json_meta_fs.walk.files(filter=['*.json']):
        # get dictionary of pre made json meta

        mtch = re.match("^(MTBLS\d*)-(.*).json", os.path.basename(path))

        if mtch:
            with open(os.path.join(json_meta_pth, os.path.basename(path))) as f:
                json_results[mtch.group(1)] = {mtch.group(2): json.load(f)}

    return json_results


class MtblsTestCase(unittest.TestCase):

    def test_mtbls_meta_data_extraction_mtbls(self):
        # get previously created results
        example_files_dir = os.path.join(os.path.abspath(os.path.join(__file__, os.pardir, os.pardir)), 'example_files')
        meta_results_original = get_json_meta_results()

        # get new results dictionary from the tar.lzma diretory of mzML files
        # where the binary has been removed
        datasets = os.path.join(example_files_dir, 'MTBLS-no-binary.tar.lzma')
        tmpfs = TempFS()
        copy_fs(TarFS(datasets), tmpfs)

        meta_results_new = {}
        for path in tmpfs.walk.files(filter=['*.mzml', '*mzML']):
            mzml_pth = tmpfs.getospath(path.strip("/"))
            study = os.path.basename(os.path.abspath(os.path.join(path, os.pardir)))
            mzml_name, mzml_ext = os.path.splitext(os.path.basename(mzml_pth))
            mz = mzml2isa.mzml.mzMLmeta(mzml_pth)
            meta_results_new[study] = {mzml_name.decode(): mz.meta}


        # check each meta data for all the files
        for study, file_details in six.iteritems(meta_results_original):
            for mzml_file, details in six.iteritems(file_details):
                print(study, mzml_file)
                if 'Data Transformation Name' in meta_results_new[study][mzml_file]:
                    self.assertEqual(meta_results_new[study][mzml_file]['Data Transformation Name'],
                                 details['Data Transformation Name']
                                     )
                if 'Data Transformation Name' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_new[study][mzml_file]['Data Transformation software'],
                        details['Data Transformation software']
                    )
                if 'Data Transformation software version' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_new[study][mzml_file]['Data Transformation software version'],
                        details['Data Transformation software version']
                    )
                if 'Derived Spectral Data File' in meta_results_new[study][mzml_file]:

                    self.assertEqual(
                        meta_results_new[study][mzml_file]['Derived Spectral Data File']['entry_list'][0]['value'].decode(),
                        details['Derived Spectral Data File']['entry_list'][0]['value']
                    )
                if 'Detector' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Detector'],
                        details['Detector']
                    )

                if 'Inlet type' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Inlet type'],
                        details['Inlet type']
                    )

                if 'Instrument' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Instrument'],
                        details['Instrument']
                    )

                if 'Instrument manufacturer' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Instrument manufacturer'],
                        details['Instrument manufacturer']
                    )

                if 'Instrument serial number' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Instrument serial number'],
                        details['Instrument serial number']
                    )

                if 'Instrument software' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Instrument software'],
                        details['Instrument software']
                    )

                if 'Ion source' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Ion source'],
                        details['Ion source']
                    )

                if 'MS Assay Name' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['MS Assay Name'],
                        details['MS Assay Name']
                    )

                if 'Mass analyzer' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Mass analyzer'],
                        details['Mass analyzer']
                    )

                if 'Native spectrum identifier format' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Native spectrum identifier format'],
                        details['Native spectrum identifier format']
                    )

                if 'Number of scans' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Number of scans'],
                        details['Number of scans']
                    )

                if 'Raw Spectral Data File' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Raw Spectral Data File'],
                        details['Raw Spectral Data File']
                    )

                if 'Sample Name' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Sample Name'],
                        details['Sample Name']
                    )

                if 'Scan m/z range' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Scan m/z range'],
                        details['Scan m/z range']
                    )

                if 'Scan polarity' in meta_results_new[study][mzml_file]:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Scan polarity'],
                        details['Scan polarity']
                    )



if __name__ == '__main__':
    unittest.main()
