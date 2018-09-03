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
import parameterized
import six
from fs.archive.tarfs import TarFS
from fs.tempfs import TempFS
from fs.copy import copy_fs

from mzml2isa.mzml import MzMLFile

from ._utils import HTTPDownloader


class TestRemoteMTBLS(unittest.TestCase):

    # --- Setup / Teardown --------------------------------------------------

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


    # --- Generic test case  ------------------------------------------------

    def _test_study(self, study_id, instrument=None):

        # open the study directory and find the smallest mzML file
        study_fs = self.ebifs.opendir(study_id)
        file_info = next(iter(sorted(
            study_fs.filterdir('/', files=['*.mzML'], exclude_dirs=['*'], namespaces=['expected']),
            key=operator.attrgetter('size'),
        )))

        # open and parse mzML file
        mzml_file = MzMLFile(study_fs, file_info.name)
        self.assertIsNotNone(mzml_file.tree)
        self.assertIsNotNone(mzml_file.metadata)

        # check instrument
        if instrument is not None:
            self.assertEqual(mzml_file.metadata['Instrument']['name'], instrument)


    # --- Metabolights studies -----------------------------------------------

    def test_MTBLS126(self):
        self._test_study('MTBLS126', instrument='LTQ Orbitrap XL')

    def test_MTBLS267(self):
        self._test_study('MTBLS267', instrument='LTQ Orbitrap')

    def test_MTBLS341(self):
        self._test_study('MTBLS341', instrument='micrOTOF-Q')



class TestLocalMTBLS(unittest.TestCase):

    # --- Setup / Teardown --------------------------------------------------

    _DATA_FS = fs.open_fs(os.path.join(__file__, os.pardir, 'data'))
    _MZML_FS = TarFS(_DATA_FS.getsyspath('MTBLS-no-binary.tar.xz'))

    @classmethod
    def _get_json_meta_results(cls, data_fs):
        results = {}
        with TarFS(data_fs.getsyspath('MTBLS-json-meta.tar.xz')) as archive:
            for path in archive.walk.files(filter=['*.json']):
                match = re.match("^(MTBLS\d*)-(.*).json", fs.path.basename(path))
                if match is not None:
                    id_, name = match.groups()
                    with archive.open(path) as f:
                        results[id_] = json.load(f)
        return results

    @classmethod
    def setUpClass(cls):
        cls.results_original = cls._get_json_meta_results(cls._DATA_FS)

    @classmethod
    def tearDownClass(cls):
        cls._DATA_FS.close()
        cls._MZML_FS.close()


    # --- Parameterised test case  ------------------------------------------

    @parameterized.parameterized.expand(
        _MZML_FS.listdir('/'),
        name_func=lambda f, n, p: str("{}_{}".format(f.__name__, p.args[0]))
    )
    def test(self, id_):

        data_fs = self._MZML_FS.opendir(id_)
        path = next(data_fs.walk.files(filter=['*.mzml', '*.mzML']))

        result = MzMLFile(data_fs, path).metadata
        expected = self.results_original[id_]


        keys = (
            'Data Transformation Name',
            'Data Transformation software',
            'Data Transformation software version',
            'Detector',
            'Inlet Type',
            'Instrument',
            'Instrument manufacturer',
            'Instrument software',
            'Ion source',
            'MS Assay Name',
            'Mass analyzer',
            'Native spectrum identifier format',
            'Number of scans',
            'Sample Name',
            'Scan m/z range',
            'Scan polarity',


        )

        for key in filter(expected.__contains__, keys):
            self.assertEqual(
                result[key], expected[key],
                'parsed "{}" differs from the expected value'.format(key)
            )

        if 'Derived Spectral Data File' in expected:
            self.assertEqual(
                result['Derived Spectral Data File']['entry_list'][0]['value'],
                expected['Derived Spectral Data File']['entry_list'][0]['value']
            )

        if 'Instrument serial number' in expected:
            self.assertEqual(
                result['Instrument serial number']['value'],
                expected['Instrument serial number']['value'],
                'parsed "Instrument serial number" differs from the expected valued'
            )








if __name__ == '__main__':
    unittest.main()
