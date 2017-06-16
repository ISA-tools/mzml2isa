# coding: utf-8

import fs
import six
import json
import unittest
import itertools
import contextlib
import tempfile
import shutil

import mzml2isa



class TestMetabolightsStudies(unittest.TestCase):

    BASE_URL = 'ftp://ftp.ebi.ac.uk/pub/databases/metabolights/studies/public'
    FILES = 3

    @classmethod
    def get_studies(cls):
        study_url = 'http://ftp.ebi.ac.uk/pub/databases/metabolights/study_file_extensions/ml_file_extension.json'
        req = six.moves.urllib.request.Request(study_url)

        with contextlib.closing(six.moves.urllib.request.urlopen(req)) as con:
            studies = json.load(con)

        for study in studies:
            if cls.extension in study['extensions']:
                yield study['id']

    @classmethod
    def load_tests(cls):
        for study_id in cls.get_studies():
            cls.add_test(study_id)

    @classmethod
    def add_test(cls, study_id):

        def parse_study(self):
            with self.mtbls_ftp.opendir(study_id) as in_dir:
                files_it = in_dir.filterdir("/", files=["*"+cls.extension], exclude_dirs=["*"])

                for f in itertools.islice(files_it, cls.FILES):
                    print("Parsing: {} in {}".format(f.name, study_id))
                    meta = mzml2isa.mzml.mzMLmeta(in_file=f.name, in_dir=in_dir)


        def convert_study(self):
            with self.mtbls_ftp.opendir(study_id) as in_dir:
                files_it = in_dir.filterdir("/", files=["*"+cls.extension], exclude_dirs=["*"])

                metalist = [
                    mzml2isa.mzml.mzMLmeta(in_file=f.name, in_dir=in_dir).meta
                        for f in itertools.islice(files_it, cls.FILES)
                ]

            isa_writer = mzml2isa.isa.ISA_Tab(self.tmpdir, study_id)
            isa_writer.write(metalist, self.extension[1:].lower())

        setattr(cls, 'test_parse_study_{}'.format(study_id), parse_study)
        setattr(cls, 'test_convert_study_{}'.format(study_id), convert_study)


    @classmethod
    def setUpClass(cls):
        cls.mtbls_ftp = fs.open_fs(cls.BASE_URL)

    @classmethod
    def tearDownClass(cls):
        cls.mtbls_ftp.delegate_fs().close()
        cls.mtbls_ftp.close()

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestMetabolightsMZMLStudies(TestMetabolightsStudies):
    extension = '.mzML'

class TestMetabolightsIMZMLStudies(TestMetabolightsStudies):
    extension = '.imzML'



def load_tests(loader, tests, pattern):
    TestMetabolightsMZMLStudies.load_tests()
    TestMetabolightsIMZMLStudies.load_tests()

    tests.addTests(loader.loadTestsFromTestCase(TestMetabolightsMZMLStudies))
    tests.addTests(loader.loadTestsFromTestCase(TestMetabolightsIMZMLStudies))

    return tests
