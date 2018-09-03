# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import operator
import os
import re
import unittest

import fs
import fs.errors
import fs.path
import six
from fs.tarfs import TarFS
from fs.tempfs import TempFS
from fs.copy import copy_fs

from mzml2isa.mzml import MzMLFile

from ._utils import HTTPDownloader


class TestRemoteMTBLS(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        try:
            cls.ebifs = HTTPDownloader(fs.open_fs(
                'ftp://ftp.ebi.ac.uk/pub/databases/metabolights/studies/public/'
            ))
        except fs.errors.CreateFailed:
            raise unittest.SkipTest('cannot connect to the EBI FTP')

    def setUp(self):
        self.tmpfs = fs.open_fs('temp://')

    def tearDown(self):
        self.tmpfs.close()

    @classmethod
    def tearDownClass(cls):
        cls.ebifs.close()

    def _test_study(self, study_id, instrument=None):

        # open the study directory and find the smallest mzML file
        study_fs = self.ebifs.opendir(study_id)
        file_info = next(iter(sorted(
            study_fs.filterdir('/', files=['*.mzML'], exclude_dirs=['*'], namespaces=['details']),
            key=operator.attrgetter('size'),
        )))

        # open and parse mzML file
        mzml_file = MzMLFile(study_fs, file_info.name)
        self.assertIsNotNone(mzml_file.tree)
        self.assertIsNotNone(mzml_file.metadata)

        # check instrument
        if instrument is not None:
            self.assertEqual(mzml_file.metadata['Instrument']['name'], instrument)


    # METABOLIGHTS STUDIES ###################################################

    def test_MTBLS126(self):
        self._test_study('MTBLS126', instrument='LTQ Orbitrap XL')

    def test_MTBLS267(self):
        self._test_study('MTBLS267', instrument='LTQ Orbitrap')

    def test_MTBLS341(self):
        self._test_study('MTBLS341', instrument='micrOTOF-Q')



class TestLocalMTBLS(unittest.TestCase):

    @classmethod
    def _get_json_meta_results(cls, data_fs):



        # example_files_dir = os.path.join(os.path.abspath(os.path.join(__file__, os.pardir, os.pardir)), 'tests', 'data')
        # json_meta_pth = os.path.join(example_files_dir, 'MTBLS-json-meta.tar.lzma')

        # tmpfs = TempFS()
        # copy_fs(TarFS(json_meta_pth), tmpfs)

        results = {}

        with TarFS(data_fs.getsyspath('MTBLS-json-meta.tar.xz')) as archive:
            for path in archive.walk.files(filter=['*.json']):
                match = re.match("^(MTBLS\d*)-(.*).json", fs.path.basename(path))
                if match is not None:
                    id_, name = match.groups()
                    with archive.open(path) as f:
                        results[id_] = {name: json.load(f)}
        return results


    @classmethod
    def setUpClass(cls):
        cls.fs_project = fs.open_fs(os.path.join(__file__, os.pardir, os.pardir))
        cls.data_dir = cls.fs_project.opendir('tests/data')
        cls.results_original = cls._get_json_meta_results(cls.data_dir)


    def test_mtbls_meta_data_extraction_mtbls(self):
        # get previously created results
        example_files_dir = self.data_dir.getsyspath('/')
        meta_results_original = self.results_original

        # get new results dictionary from the tar.lzma diretory of mzML files
        # where the binary has been removed
        datasets = os.path.join(example_files_dir, 'MTBLS-no-binary.tar.xz')
        tmpfs = TempFS()
        copy_fs(TarFS(datasets), tmpfs)

        meta_results_new = {}
        for path in tmpfs.walk.files(filter=['*.mzml', '*mzML']):
            mzml_pth = tmpfs.getospath(path.strip("/"))
            study = os.path.basename(os.path.abspath(os.path.join(path, os.pardir)))
            mzml_name, mzml_ext = os.path.splitext(os.path.basename(mzml_pth))
            mz = MzMLFile(tmpfs, path)
            meta_results_new[study] = {mzml_name.decode(): mz.metadata}
            del mzml_ext

        # check each meta data for all the files, check in the original file details if the parameter is available
        # first though
        for study, file_details in six.iteritems(meta_results_original):
            for mzml_file, details in six.iteritems(file_details):
                if 'Data Transformation Name' in details:
                    self.assertEqual(
                         meta_results_new[study][mzml_file]['Data Transformation Name'],
                         details['Data Transformation Name']
                    )
                if 'Data Transformation Name' in details:
                    self.assertEqual(
                        meta_results_new[study][mzml_file]['Data Transformation software'],
                        details['Data Transformation software']
                    )
                if 'Data Transformation software version' in details:
                    self.assertEqual(
                        meta_results_new[study][mzml_file]['Data Transformation software version'],
                        details['Data Transformation software version']
                    )
                if 'Derived Spectral Data File' in details:

                    self.assertEqual(
                        meta_results_new[study][mzml_file]['Derived Spectral Data File']['entry_list'][0]['value'].decode(),
                        details['Derived Spectral Data File']['entry_list'][0]['value']
                    )
                if 'Detector' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Detector'],
                        details['Detector']
                    )

                if 'Inlet type' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Inlet type'],
                        details['Inlet type']
                    )

                if 'Instrument' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Instrument'],
                        details['Instrument']
                    )

                if 'Instrument manufacturer' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Instrument manufacturer'],
                        details['Instrument manufacturer']
                    )

                if 'Instrument serial number' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Instrument serial number'],
                        details['Instrument serial number']
                    )

                if 'Instrument software' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Instrument software'],
                        details['Instrument software']
                    )

                if 'Ion source' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Ion source'],
                        details['Ion source']
                    )

                if 'MS Assay Name' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['MS Assay Name'],
                        details['MS Assay Name']
                    )

                if 'Mass analyzer' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Mass analyzer'],
                        details['Mass analyzer']
                    )

                if 'Native spectrum identifier format' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Native spectrum identifier format'],
                        details['Native spectrum identifier format']
                    )

                if 'Number of scans' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Number of scans'],
                        details['Number of scans']
                    )

                if 'Raw Spectral Data File' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Raw Spectral Data File'],
                        details['Raw Spectral Data File']
                    )

                if 'Sample Name' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Sample Name'],
                        details['Sample Name']
                    )

                if 'Scan m/z range' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Scan m/z range'],
                        details['Scan m/z range']
                    )

                if 'Scan polarity' in details:
                    self.assertEqual(
                        meta_results_original[study][mzml_file]['Scan polarity'],
                        details['Scan polarity']
                    )

                break

if __name__ == '__main__':
    unittest.main()
