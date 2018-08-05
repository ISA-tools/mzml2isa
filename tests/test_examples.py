# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import unittest
from os.path import pardir

import fs
from isatools import isatab

from mzml2isa.mzml import MzMLFile
from mzml2isa.isa import ISA_Tab


class TestExamples(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fs_project = fs.open_fs(os.path.join(__file__, pardir, pardir))
        cls.fs_examples = cls.fs_project.opendir('examples')
        cls.dir_config = cls.fs_project.getsyspath('static/isa-config')

    def setUp(self):
        self.fs_tmp = fs.open_fs('temp://')

    def tearDown(self):
        self.fs_tmp.close()

    @classmethod
    def tearDownClass(cls):
        cls.fs_project.close()

    def _test_example(self, example_name):
        # Parse all example files
        fs_example = self.fs_examples.opendir(example_name)
        mzml_files = fs_example.filterdir('/', files=['*.mzML'], exclude_dirs=['*'])
        metadata = [MzMLFile(fs_example, m.name).metadata for m in mzml_files]
        # Write the study files
        writer = ISA_Tab(self.fs_tmp.getsyspath('/'), name=example_name)
        writer.write(metadata, 'mzML')
        # Check the file have been created as expected
        self.assertTrue(self.fs_tmp.isfile('i_Investigation.txt'))
        # Validate the created study
        with open(self.fs_tmp.getsyspath('i_Investigation.txt')) as f:
            result = isatab.validate(f, config_dir=self.dir_config)
        self.assertTrue(result['validation_finished'])
        self.assertFalse(result['errors'])

    ### EXAMPLES #############################################################

    def test_hupo_psi_1(self):
        self._test_example('hupo-psi-1')

    def test_hupo_psi_2(self):
        self._test_example('hupo-psi-2')

    def test_hupo_psi_4(self):
        self._test_example('hupo-psi-4')

    def test_hupo_psi_msdata(self):
        self._test_example('hupo-psi-msdata')

    def test_hupo_psi_pwiz(self):
        self._test_example('hupo-psi-pwiz')

    def test_metabolomics_study(self):
        self._test_example('metabolomics_study')
