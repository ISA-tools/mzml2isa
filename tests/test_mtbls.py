from __future__ import absolute_import

import os
import sys
import unittest
import tempfile
import shutil
import glob
import six
import itertools
import logging
import warnings
import ftplib
import json
import isatools.isatab
import fs.ftpfs
import fs.tempfs

from . import utils

# Import the local library
sys.path.insert(0, utils.MAINDIR)
import mzml2isa.mzml
import mzml2isa.isa



class TestMtbls(unittest.TestCase):

    CONFIGS_DIR = "/pub/databases/metabolights/submissionTool/configurations"
    STUDIES_DIR = "/pub/databases/metabolights/studies/public/"

    @classmethod
    def setUpClass(cls):
        # create temporary filesystem for the test environment
        # and for the EBI FTP server
        cls._test_temp_fs = fs.tempfs.TempFS()
        #fs# cls._ebi_ftp_fs = fs.ftpfs.FTPFS("ftp.ebi.ac.uk", timeout=1)

        # create ftp connection to EBI FTP server
        cls._ebi_ftp = cls.connect_to_ebi_ftp()

        # create a directory for the configuration files
        cls._test_temp_fs.makedir("/conf")

        # Download latest MetaboLights configurations from
        # the EBI FTP server
        cls._ebi_ftp.cwd(cls.CONFIGS_DIR)
        mtbl_conf_dir = next(f for f in cls._ebi_ftp.nlst() if f.startswith("MetaboLights"))
        cls._ebi_ftp.cwd(mtbl_conf_dir)

        for conf_file in cls._ebi_ftp.nlst():
            with cls._test_temp_fs.openbin("/conf/{}".format(conf_file), 'w') as out_file:
                cls._ebi_ftp.retrbinary("RETR {}".format(conf_file), out_file.write)

        # mtbl_conf_dir = next(cls._ebi_ftp_fs.filterdir(
        #         cls.CONFIGS_DIR, exclude_files=True, dirs=["MetaboLights*"])
        #     ).make_path(cls.CONFIGS_DIR)
        # for conf_file in cls._ebi_ftp_fs.filterdir(mtbl_conf_dir):
        #     with cls._ebi_ftp_fs.openbin(conf_file.make_path(mtbl_conf_dir)) as src_file:
        #         cls._test_temp_fs.setbin("/conf/{}".format(conf_file.name), src_file)




    @classmethod
    def tearDownClass(cls):
        #cls._ebi_ftp_fs.close()
        cls._test_temp_fs.close()
        cls._ebi_ftp.close()


    @staticmethod
    def connect_to_ebi_ftp():
        ebi_ftp = ftplib.FTP("ftp.ebi.ac.uk")
        ebi_ftp.login()
        return ebi_ftp





    def setUp(self):
        self._test_temp_fs.makedir("/run")
        self.run_dir = self._test_temp_fs.getsyspath("/run")

    def tearDown(self):
        self._test_temp_fs.removetree("/run")

    @property
    def mlparser(self):
        """
        """
        if self.extension == "mzml":
            return mzml2isa.mzml.mzMLmeta
        elif self.extension == "imzml":
            return mzml2isa.mzml.imzMLmeta
        else:
            raise ValueError("Unknown filetype: {}".format(getattr(self, "filetype", None)))





    def get_mzml_files(self, study_id):
        """Get a list of handles of all mzml files for given MTBLS study
        """
        study_url = "{}/{}/".format(self.STUDIES_DIR, study_id)
        self._ebi_ftp.cwd(study_url)
        mzml_files = [f for f in self._ebi_ftp.nlst() if f.endswith('mzML')]
        #mzml_files = itertools.islice(self._ebi_ftp_fs.filterdir(study_url, files=["*mzML"]), self.files_per_study)
        #datatype = next(self._ebi_ftp_fs.filterdir(study_url, files=["*mzML", "*.imzml"])).name.split(os.path.extsep)[-1].lower()
        return ["http://ftp.ebi.ac.uk{}/{}/{}".format(self.STUDIES_DIR, study_id, f) for f in mzml_files[:self.files_per_study]]

    def convert(self, study_id, usermeta=None):
        """Convert given MTBLS to ISA-Tab format into out_dir
        """

        #print("Getting mzml_handles for:", study_id)
        files = self.get_mzml_files(study_id)
        extension = files[0].split('.')[-1]
        #metalist = []

        # Get the right metadata parser
        if extension == "mzML":
            metadata_parser = mzml2isa.mzml.mzMLmeta
        elif extension == "imzML":
            metadata_parser = mzml2isa.mzml.imzMLmeta

        # Parse all files (use HTTP instead of FTP to go quicker)
        # for f in files:
        #     #print("Parsing:", f)
        #     metalist.append(metadata_parser("http://ftp.ebi.ac.uk"+f).meta)
        #metalist = [metadata_parser("http://ftp.ebi.ac.uk{}".format(f)).meta for f in files]
        metalist = [metadata_parser(f).meta for f in files]

        #print("Writing ISA files to", self.run_dir)
        isa_writer = mzml2isa.isa.ISA_Tab(self.run_dir, study_id, usermeta=usermeta)
        isa_writer.write(metalist, extension, split=True)







    @staticmethod
    def get_concerned_studies():
        return NotImplemented

    @classmethod
    def register_tests(cls):
        studies = cls.get_concerned_studies()
        for study_id in studies:
            cls.add_test(study_id)

    @classmethod
    def add_test(cls, study_id):

        def _test_study(self):

            self.convert(study_id)

            # checks if tempdir contains generated files
            for isa_glob in ("i_Investigation.txt", "a_*.txt", "s_*.txt"):
                isa_glob = os.path.join(self.run_dir, study_id, isa_glob)
                self.assertTrue(glob.glob(isa_glob))

            # validates generated ISA using isa-api
            result = isatools.isatab.validate2(
                open(os.path.join(self.run_dir, study_id, "i_Investigation.txt")),
                self._test_temp_fs.getsyspath("/conf"),
                log_level=50,
            )
            self.assertEqual(result['errors'], [])

        setattr(cls, "test_{}".format(study_id).lower(), _test_study)



@unittest.skipUnless(utils.IN_CI, "short test is for CI only")
class TestMtblsTravis(TestMtbls):

    @staticmethod
    def get_concerned_studies():
        return [os.environ.get("MTBLS_STUDY", "MTBLS32")]

    @classmethod
    def setUpClass(cls):
        super(TestMtblsTravis, cls).setUpClass()
        cls.files_per_study = 6


@unittest.skipIf(utils.IN_CI, "long test takes too much time for CI")
class TestMtblsDesktop(TestMtbls):

    @classmethod
    def get_concerned_studies(cls):
        study_exts = six.BytesIO()

        ebi_ftp = cls.connect_to_ebi_ftp()
        ebi_ftp.cwd("/pub/databases/metabolights/study_file_extensions")
        ebi_ftp.retrbinary("RETR ml_file_extension.json", study_exts.write)
        stats = json.loads(study_exts.getvalue().decode('utf-8'))
        return [s['id'] for s in stats if '.mzML' in s['extensions'] or '.imzML' in s['extensions']]

    @classmethod
    def setUpClass(cls):
        super(TestMtblsDesktop, cls).setUpClass()
        cls.files_per_study = 2




def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()

    TestMtblsTravis.register_tests()
    TestMtblsDesktop.register_tests()

    if utils.IN_CI:
        suite.addTests(loader.loadTestsFromTestCase(TestMtblsTravis))
    else:
        suite.addTests(loader.loadTestsFromTestCase(TestMtblsDesktop))

    return suite


def setUpModule():
    warnings.simplefilter('ignore')

def tearDownModule():
    warnings.simplefilter(warnings.defaultaction)
