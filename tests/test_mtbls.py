# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import operator
import unittest

import fs
import fs.errors

from mzml2isa.mzml import MzMLFile

from ._utils import HTTPDownloader


class TestMTBLS(unittest.TestCase):

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


    ### METABOLIGHTS STUDIES #################################################

    def test_MTBLS126(self):
        self._test_study('MTBLS126', instrument='LTQ Orbitrap XL')

    def test_MTBLS267(self):
        self._test_study('MTBLS267', instrument='LTQ Orbitrap')

    def test_MTBLS341(self):
        self._test_study('MTBLS341', instrument='micrOTOF-Q')
